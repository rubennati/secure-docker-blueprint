#!/usr/bin/env bash
# =============================================
# Secure Docker Blueprint – stacks on this host
# =============================================
# A host carries only the stacks it runs, as a Git partial checkout. The file
# `stacks` at the repository root (template: stacks.example) lists them, one
# path per line; this tool makes the checkout match the file and takes
# releases for exactly those paths. The file is only read, never written.
#
#   scripts/stacks.sh apply             check out what the file lists
#   scripts/stacks.sh update <tag> [--yes]
#                                       preview a release for these stacks, then take it
#   scripts/stacks.sh status            release, and where file and checkout differ
#
# `scripts` and `docs/standards` are always checked out. apply refuses to drop
# a stack that still has local files — .env, .secrets/, volumes/ or anything
# else Git does not track — because Git deletes them with the directory. Move
# or back up that data, delete it, then apply again. For the same reason apply
# and update refuse while a release path that is not checked out holds a
# symbolic link or files: Git deletes those too, through the link.
#
# Own stacks live in custom/<name>, each a checkout of its own repository. This
# tool never checks them out or removes them; status and update list them with
# the Blueprint release their README names (`**Blueprint:** vX.Y.Z`).
#
# The procedure around it is docs/standards/deployment-lifecycle.md.
# =============================================
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STACKS_FILE="${STACKS_FILE:-${ROOT_DIR}/stacks}"
REQUIRED="docs/standards scripts"

usage() { sed -n '2,26p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 2; }
die() { printf 'stacks: %s\n' "$*" >&2; exit 1; }
g() { git -C "${ROOT_DIR}" "$@"; }

is_partial() { [ "$(g config --bool core.sparseCheckout 2>/dev/null || true)" = "true" ]; }
require_partial() {
  g rev-parse --git-dir >/dev/null 2>&1 || die "${ROOT_DIR} is not a Git checkout"
  is_partial || die "this is a full clone, not a partial checkout — nothing to manage (docs/standards/deployment-lifecycle.md, section 2)"
}

# The paths the file asks for, plus the required ones; sorted, one per line.
wanted() {
  [ -f "${STACKS_FILE}" ] || die "no stacks file at ${STACKS_FILE} — start with: cp stacks.example stacks"
  local line path bad=0
  {
    for path in ${REQUIRED}; do printf '%s\n' "${path}"; done
    while IFS= read -r line || [ -n "${line}" ]; do
      line="${line%%#*}"
      path="$(printf '%s' "${line}" | tr -d '[:space:]')"
      path="${path%/}"
      [ -n "${path}" ] || continue
      case "${path}" in custom|custom/*)
        printf 'stacks: %s is an own stack — it lives in custom/ and is managed by its own repository, not by this file (docs/standards/deployment-lifecycle.md, section 11)\n' "${path}" >&2
        bad=1; continue ;;
      esac
      if ! printf '%s' "${path}" | grep -Eq '^[A-Za-z0-9_][A-Za-z0-9._-]*(/[A-Za-z0-9_][A-Za-z0-9._-]*)*$' \
         || printf '%s' "${path}" | grep -Eq '(^|/)\.\.?(/|$)'; then
        printf 'stacks: not a repository path: %s\n' "${path}" >&2; bad=1; continue
      fi
      printf '%s\n' "${path}"
    done < "${STACKS_FILE}"
    [ "${bad}" -eq 0 ] || printf '%s\n' "__INVALID__"
  } | sort -u
}

current() { g sparse-checkout list | sort -u; }

# Is $1 equal to, or inside, one of the paths in the newline list $2?
covered() {
  local p="$1" w
  while IFS= read -r w; do
    [ -n "${w}" ] || continue
    case "${p}" in "${w}"|"${w}"/*) return 0 ;; esac
  done <<< "$2"
  return 1
}

# Paths of $1 that no tree in $2 (a commit) contains as a directory.
missing_in() {
  local paths="$1" rev="$2" p
  while IFS= read -r p; do
    [ -n "${p}" ] || continue
    [ "$(g cat-file -t "${rev}:${p}" 2>/dev/null || true)" = "tree" ] || printf '%s\n' "${p}"
  done <<< "${paths}"
}

# Local files (ignored or untracked) under a path that leaves the checkout,
# leaving out whatever stays because a wanted path still covers it.
local_files() {
  local p="$1" want="$2" f
  { g ls-files --others --ignored --exclude-standard -- "${p}"
    g ls-files --others --exclude-standard -- "${p}"; } | sort -u |
  while IFS= read -r f; do
    [ -n "${f}" ] || continue
    covered "${f}" "${want}" || printf '%s\n' "${f}"
  done
}

# Is $1 a parent directory of one of the paths in the newline list $2?
parent_of() {
  local d="$1" w
  while IFS= read -r w; do
    [ -n "${w}" ] || continue
    case "${w}" in "${d}"/*) return 0 ;; esac
  done <<< "$2"
  return 1
}

# What sits on release directory $2 of release $1, which is not checked out:
# "path<TAB>what" lines, or status 1 for nothing (directories without a file
# count as nothing). A category is looked into, so the stack is named, not the
# category.
probe() {
  local rev="$1" d="$2" f="${ROOT_DIR}/$2" c found=1
  if [ -L "${f}" ]; then
    printf '%s\tsymbolic link to %s\n' "${d}" "$(readlink "${f}")"
    return 0
  fi
  if [ -d "${f}" ]; then
    [ -n "$(find "${f}" -mindepth 1 ! -type d -print -quit 2>/dev/null)" ] || return 1
    case "${d}" in
      */*) ;;
      *) while IFS= read -r c; do
           [ -n "${c}" ] || continue
           if probe "${rev}" "${c}"; then found=0; fi
         done <<< "$(g ls-tree -d --name-only "${rev}" -- "${d}/")" ;;
    esac
    [ "${found}" -eq 0 ] || printf '%s\tdirectory with files\n' "${d}"
    return 0
  fi
  [ -e "${f}" ] || return 1
  printf '%s\tfile\n' "${d}"
}

# Release directories outside the checkout that hold something on this host,
# one "path<TAB>what" per line, for the releases named after $1. $1 is every
# path checked out now or wanted; what those hold is local_files' concern.
# Git counts a release directory outside the checkout as its own: once nothing
# in it is untracked and unignored, `git sparse-checkout` deletes it with
# .env, .secrets/ and volumes/, following a symbolic link into the directory
# it points to.
foreign() {
  local paths="$1" rev queue next d
  shift
  for rev in "$@"; do
    queue="$(g ls-tree -d --name-only "${rev}")"
    while [ -n "${queue}" ]; do
      next=""
      while IFS= read -r d; do
        [ -n "${d}" ] || continue
        covered "${d}" "${paths}" && continue
        if parent_of "${d}" "${paths}"; then
          next="${next}$(g ls-tree -d --name-only "${rev}" -- "${d}/")"$'\n'
        else
          probe "${rev}" "${d}" || true
        fi
      done <<< "${queue}"
      queue="${next}"
    done
  done | sort -u
}

print_foreign() {
  printf '%s\n' "$1" | while IFS="$(printf '\t')" read -r d what; do
    printf '   %-28s %s\n' "${d}" "${what}"
  done
}

refuse_foreign() {  # refuse_foreign <findings> <what did not happen>
  printf 'REFUSED: release paths that are not checked out here hold something on this host:\n'
  print_foreign "$1"
  printf 'Git deletes what is there once only ignored files are left, and follows a\n'
  printf 'symbolic link to do it. List the stack in %s to run it from here, or move\n' "${STACKS_FILE##*/}"
  printf 'its files to a path outside the release (rm <path> removes a link, not its target).\n'
  die "$2"
}

# Own stacks: one line per directory under custom/ — name, the application's
# release (its tag, else its commit), and the Blueprint release its README names.
own_stacks() {
  local d name ref bp
  for d in "${ROOT_DIR}"/custom/*/; do
    [ -d "${d}" ] || continue
    name="custom/$(basename "${d}")"
    if git -C "${d}" rev-parse --git-dir >/dev/null 2>&1; then
      ref="$(git -C "${d}" describe --tags --exact-match 2>/dev/null || git -C "${d}" describe --tags --always 2>/dev/null || echo '-')"
    else
      ref="not a Git checkout"
    fi
    bp="$(grep -hoE '^\*\*Blueprint:\*\*[[:space:]]*v[0-9][0-9A-Za-z.+-]*' "${d}README.md" 2>/dev/null | head -1 | sed -E 's/^\*\*Blueprint:\*\*[[:space:]]*//' || true)"
    printf '%s|%s|%s\n' "${name}" "${ref}" "${bp}"
  done
}

# Paths in the checkout that the file no longer covers.
leaving() {
  local want="$1" have="$2" p
  while IFS= read -r p; do
    [ -n "${p}" ] || continue
    covered "${p}" "${want}" || printf '%s\n' "${p}"
  done <<< "${have}"
}

cmd_apply() {
  require_partial
  local want have miss p files refused=0 added removed stray
  want="$(wanted)"
  case "${want}" in *__INVALID__*) die "fix the stacks file; nothing applied" ;; esac
  miss="$(missing_in "${want}" HEAD)"
  if [ -n "${miss}" ]; then
    printf 'stacks: not in this release (%s): %s\n' "$(g describe --tags --always)" "$(printf '%s' "${miss}" | tr '\n' ' ')" >&2
    die "fix the stacks file; nothing applied"
  fi
  have="$(current)"
  stray="$(foreign "$(printf '%s\n%s\n' "${want}" "${have}" | sed '/^$/d' | sort -u)" HEAD)"
  [ -z "${stray}" ] || refuse_foreign "${stray}" "nothing applied"
  while IFS= read -r p; do
    [ -n "${p}" ] || continue
    files="$(local_files "${p}" "${want}")"
    if [ -n "${files}" ]; then
      printf 'REFUSED: %s would lose:\n' "${p}"
      printf '%s\n' "${files}" | sed 's/^/   /'
      refused=1
    fi
  done <<< "$(leaving "${want}" "${have}")"
  [ "${refused}" -eq 0 ] || die "nothing applied — stop the stack, move or back up its data, delete it, then apply again"

  added="$(comm -13 <(printf '%s\n' "${have}") <(printf '%s\n' "${want}") | sed '/^$/d')"
  removed="$(leaving "${want}" "${have}")"
  printf '%s\n' "${want}" | g sparse-checkout set --stdin
  [ -z "${added}" ]   || printf 'added:   %s\n' ${added}
  [ -z "${removed}" ] || printf 'removed: %s\n' ${removed}
  [ -n "${added}${removed}" ] || echo "checkout already matches ${STACKS_FILE##*/}"
}

cmd_update() {
  require_partial
  local tag="${1:-}" yes="${2:-}" want have miss touched answer own name ref bp stray
  [ -n "${tag}" ] || usage
  [ -z "${yes}" ] || [ "${yes}" = "--yes" ] || usage
  want="$(wanted)"
  case "${want}" in *__INVALID__*) die "fix the stacks file; nothing changed" ;; esac
  have="$(current)"
  [ "${want}" = "${have}" ] || die "the checkout does not match ${STACKS_FILE##*/} — run scripts/stacks.sh apply first"
  [ -z "$(g status --porcelain --untracked-files=no)" ] || die "tracked files are modified — restore them before an update (git status)"

  g fetch --tags --quiet 2>/dev/null || echo "stacks: fetch failed — using the tags already known locally" >&2
  g rev-parse --verify --quiet "${tag}^{commit}" >/dev/null || die "no such release: ${tag}"
  stray="$(foreign "${want}" HEAD "${tag}")"
  [ -z "${stray}" ] || refuse_foreign "${stray}" "nothing changed"

  echo "From: $(g describe --tags --always)"
  echo "To:   ${tag}"
  miss="$(missing_in "${want}" "${tag}")"
  if [ -n "${miss}" ]; then
    echo "Not in ${tag} (removed or renamed upstream; the directory and its data stay):"
    printf '%s\n' "${miss}" | sed 's/^/   /'
  fi
  touched="$(g diff --name-only HEAD "${tag}" -- ${want} | cut -d/ -f1,2 | sort -u)"
  if [ -z "${touched}" ]; then
    echo "No changes to the stacks on this host."
  else
    echo "Changes to the stacks on this host:"
    g diff --stat HEAD "${tag}" -- ${want} | sed 's/^/   /'
  fi
  echo "Read the CHANGELOG.md entries between the two releases for operator actions."
  own="$(own_stacks)"
  if [ -n "${own}" ]; then
    echo "Own stacks (custom/) — this update does not change them:"
    while IFS='|' read -r name ref bp; do
      if [ -z "${bp}" ]; then
        printf '   %s names no Blueprint release in its README — check it against the Migration notes up to %s\n' "${name}" "${tag}"
      elif [ "${bp}" = "${tag}" ]; then
        printf '   %s follows %s\n' "${name}" "${bp}"
      else
        printf '   %s follows %s — read the Migration notes in CHANGELOG.md between %s and %s\n' "${name}" "${bp}" "${bp}" "${tag}"
      fi
    done <<< "${own}"
  fi

  if [ "${yes}" != "--yes" ]; then
    [ -t 0 ] || die "not a terminal — pass --yes to take ${tag} without asking"
    printf 'Take %s? [y/N] ' "${tag}"
    read -r answer
    case "${answer}" in y|Y|yes|YES) ;; *) echo "nothing changed"; exit 0 ;; esac
  fi
  g -c advice.detachedHead=false checkout --quiet "${tag}"
  echo "Now on ${tag}."
  if [ -n "${touched}" ]; then
    echo "Recreate the stacks this release touched (docs/standards/deployment-lifecycle.md, section 7):"
    printf '%s\n' "${touched}" | grep -vE '^(docs|scripts)/' | sed 's/^/   /' || true
  fi
}

print_own() {
  local own name ref bp
  own="$(own_stacks)"
  [ -n "${own}" ] || return 0
  echo "Own stacks (custom/):"
  while IFS='|' read -r name ref bp; do
    if [ -n "${bp}" ]; then bp="follows Blueprint ${bp}"; else bp="no Blueprint line in README.md"; fi
    printf '   %-24s %-20s %s\n' "${name}" "${ref}" "${bp}"
  done <<< "${own}"
}

cmd_status() {
  g rev-parse --git-dir >/dev/null 2>&1 || die "${ROOT_DIR} is not a Git checkout"
  local release want have only_file only_checkout stray
  release="$(g describe --tags --exact-match 2>/dev/null || true)"
  [ -n "${release}" ] && echo "Release: ${release}" || echo "Release: not on a release — $(g describe --tags --always 2>/dev/null)"
  if ! is_partial; then echo "Checkout: full clone"; print_own; return 0; fi
  want="$(wanted)"
  case "${want}" in *__INVALID__*) die "fix the stacks file" ;; esac
  have="$(current)"
  echo "Checkout: partial, $(printf '%s\n' "${have}" | sed '/^$/d' | wc -l | tr -d ' ') path(s)"
  only_file="$(comm -23 <(printf '%s\n' "${want}") <(printf '%s\n' "${have}") | sed '/^$/d')"
  only_checkout="$(leaving "${want}" "${have}")"
  [ -z "${only_file}" ]     || { echo "In the file, not checked out (apply adds them):"; printf '%s\n' "${only_file}" | sed 's/^/   /'; }
  [ -z "${only_checkout}" ] || { echo "Checked out, not in the file (apply removes them, refused while they hold local files):"; printf '%s\n' "${only_checkout}" | sed 's/^/   /'; }
  [ -n "${only_file}${only_checkout}" ] || echo "File and checkout match."
  stray="$(foreign "$(printf '%s\n%s\n' "${want}" "${have}" | sed '/^$/d' | sort -u)" HEAD)"
  [ -z "${stray}" ] || { echo "Not checked out, yet something is there (apply and update refuse until it is moved):"; print_foreign "${stray}"; }
  print_own
}

cmd="${1:-}"; shift || true
case "${cmd}" in
  apply)  [ "$#" -eq 0 ] || usage; cmd_apply ;;
  update) [ "$#" -ge 1 ] && [ "$#" -le 2 ] || usage; cmd_update "$@" ;;
  status) [ "$#" -eq 0 ] || usage; cmd_status ;;
  *) usage ;;
esac
