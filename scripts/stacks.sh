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
# or back up that data, delete it, then apply again.
#
# The procedure around it is docs/standards/deployment-lifecycle.md.
# =============================================
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STACKS_FILE="${STACKS_FILE:-${ROOT_DIR}/stacks}"
REQUIRED="docs/standards scripts"

usage() { sed -n '2,20p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 2; }
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
  local want have miss p files refused=0 added removed
  want="$(wanted)"
  case "${want}" in *__INVALID__*) die "fix the stacks file; nothing applied" ;; esac
  miss="$(missing_in "${want}" HEAD)"
  if [ -n "${miss}" ]; then
    printf 'stacks: not in this release (%s): %s\n' "$(g describe --tags --always)" "$(printf '%s' "${miss}" | tr '\n' ' ')" >&2
    die "fix the stacks file; nothing applied"
  fi
  have="$(current)"
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
  local tag="${1:-}" yes="${2:-}" want have miss touched answer
  [ -n "${tag}" ] || usage
  [ -z "${yes}" ] || [ "${yes}" = "--yes" ] || usage
  want="$(wanted)"
  case "${want}" in *__INVALID__*) die "fix the stacks file; nothing changed" ;; esac
  have="$(current)"
  [ "${want}" = "${have}" ] || die "the checkout does not match ${STACKS_FILE##*/} — run scripts/stacks.sh apply first"
  [ -z "$(g status --porcelain --untracked-files=no)" ] || die "tracked files are modified — restore them before an update (git status)"

  g fetch --tags --quiet 2>/dev/null || echo "stacks: fetch failed — using the tags already known locally" >&2
  g rev-parse --verify --quiet "${tag}^{commit}" >/dev/null || die "no such release: ${tag}"

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

cmd_status() {
  g rev-parse --git-dir >/dev/null 2>&1 || die "${ROOT_DIR} is not a Git checkout"
  local release want have only_file only_checkout
  release="$(g describe --tags --exact-match 2>/dev/null || true)"
  [ -n "${release}" ] && echo "Release: ${release}" || echo "Release: not on a release — $(g describe --tags --always 2>/dev/null)"
  if ! is_partial; then echo "Checkout: full clone"; return 0; fi
  want="$(wanted)"
  case "${want}" in *__INVALID__*) die "fix the stacks file" ;; esac
  have="$(current)"
  echo "Checkout: partial, $(printf '%s\n' "${have}" | sed '/^$/d' | wc -l | tr -d ' ') path(s)"
  only_file="$(comm -23 <(printf '%s\n' "${want}") <(printf '%s\n' "${have}") | sed '/^$/d')"
  only_checkout="$(leaving "${want}" "${have}")"
  [ -z "${only_file}" ]     || { echo "In the file, not checked out (apply adds them):"; printf '%s\n' "${only_file}" | sed 's/^/   /'; }
  [ -z "${only_checkout}" ] || { echo "Checked out, not in the file (apply removes them, refused while they hold local files):"; printf '%s\n' "${only_checkout}" | sed 's/^/   /'; }
  [ -n "${only_file}${only_checkout}" ] || echo "File and checkout match."
}

cmd="${1:-}"; shift || true
case "${cmd}" in
  apply)  [ "$#" -eq 0 ] || usage; cmd_apply ;;
  update) [ "$#" -ge 1 ] && [ "$#" -le 2 ] || usage; cmd_update "$@" ;;
  status) [ "$#" -eq 0 ] || usage; cmd_status ;;
  *) usage ;;
esac
