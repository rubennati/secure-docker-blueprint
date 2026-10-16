#!/usr/bin/env bash
# =============================================
# Secure Docker Blueprint – host files
# =============================================
# Some stacks need files outside the checkout: a logrotate stanza, systemd
# units, a watchdog script, a backup agent's configuration. Each such stack
# lists them in ops/host-files.manifest. This tool renders them with the real
# deployment path into <stack>/config/host/, compares the rendered copies with
# what is installed, and prints the commands an operator runs to install them.
# It never writes outside the checkout and never runs sudo.
#
#   scripts/host-files.sh render [<stack>...]
#   scripts/host-files.sh check  [<stack>...]
#   scripts/host-files.sh diff   <stack> <target> [--show]
#   scripts/host-files.sh install-commands <stack>
#
# Without <stack>, render and check cover every stack that carries a manifest;
# check limits itself to the stacks that have been rendered — rendering is the
# operator's statement that the stack is in use on this host.
#
# The format of the manifest and the meaning of every state is
# docs/standards/host-files.md.
# =============================================
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLACEHOLDER="/path/to/secure-docker-blueprint"
PREFIX="${HOST_FILES_PREFIX:-}"      # tests point this at a scratch directory

usage() { sed -n '2,22p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 2; }

# ---------------------------------------------------------------------------
# Portability: Debian hosts run GNU stat, the test machine may run BSD stat.
# ---------------------------------------------------------------------------
file_mode() {  # file -> e.g. 644
  local m
  m="$(stat -c '%a' "$1" 2>/dev/null)" || m="$(stat -f '%Lp' "$1" 2>/dev/null)" || return 1
  printf '%s' "${m}"
}
file_owner() {  # file -> user:group
  local o
  o="$(stat -c '%U:%G' "$1" 2>/dev/null)" || o="$(stat -f '%Su:%Sg' "$1" 2>/dev/null)" || return 1
  printf '%s' "${o}"
}
norm_mode() { printf '%d' "0${1#0}" 2>/dev/null || printf '%s' "$1"; }  # 0644 and 644 compare equal

# ---------------------------------------------------------------------------
# Manifests
# ---------------------------------------------------------------------------
stacks_with_manifest() {
  find "${ROOT_DIR}"/core "${ROOT_DIR}"/apps "${ROOT_DIR}"/business "${ROOT_DIR}"/monitoring "${ROOT_DIR}"/backup \
       -mindepth 3 -maxdepth 3 -path '*/ops/host-files.manifest' -type f 2>/dev/null \
    | sed 's|/ops/host-files.manifest$||' | sort
}

stack_dir() {  # name or path -> absolute stack directory
  local s="$1"
  case "$s" in
    /*) printf '%s' "${s%/}" ;;
    *)  printf '%s' "${ROOT_DIR}/${s%/}" ;;
  esac
}

# read_manifest <stack-dir>: prints one record per line, tab-separated:
#   source<TAB>target<TAB>mode<TAB>owner<TAB>compare<TAB>required
read_manifest() {
  local dir="$1" line_no=0 line src tgt mode owner cmp req
  local manifest="${dir}/ops/host-files.manifest"
  [ -f "${manifest}" ] || { echo "ERROR: ${manifest} not found" >&2; return 1; }
  while IFS= read -r line || [ -n "${line}" ]; do
    line_no=$((line_no + 1))
    line="${line%%#*}"
    # shellcheck disable=SC2086
    set -- ${line}
    [ "$#" -eq 0 ] && continue
    if [ "$#" -ne 6 ]; then
      echo "ERROR: ${manifest} line ${line_no}: expected 6 fields (source target mode owner compare required), got $#" >&2
      return 1
    fi
    src="$1"; tgt="$2"; mode="$3"; owner="$4"; cmp="$5"; req="$6"
    case "${cmp}" in exact|derived|presence) ;; *) echo "ERROR: ${manifest} line ${line_no}: compare must be exact, derived or presence (got '${cmp}')" >&2; return 1 ;; esac
    case "${req}" in required|optional) ;; *) echo "ERROR: ${manifest} line ${line_no}: last field must be required or optional (got '${req}')" >&2; return 1 ;; esac
    case "${tgt}" in /*) ;; *) echo "ERROR: ${manifest} line ${line_no}: target must be an absolute host path (got '${tgt}')" >&2; return 1 ;; esac
    if [ "${cmp}" != presence ] && [ ! -f "${dir}/${src}" ]; then
      echo "ERROR: ${manifest} line ${line_no}: source ${src} does not exist in $(basename "${dir}")" >&2
      return 1
    fi
    if [ "${cmp}" = presence ] && [ "${src}" != "-" ]; then
      echo "ERROR: ${manifest} line ${line_no}: a presence entry has no source — write '-'" >&2
      return 1
    fi
    printf '%s\t%s\t%s\t%s\t%s\t%s\n' "${src}" "${tgt}" "${mode}" "${owner}" "${cmp}" "${req}"
  done < "${manifest}"
}

rendered_path() {  # <stack-dir> <target> -> where the rendered copy lives
  printf '%s/config/host/%s' "$1" "$(basename "$2")"
}

# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------
render_stack() {
  local dir="$1" name src tgt mode owner cmp req out
  name="$(basename "${dir}")"
  read_manifest "${dir}" >/dev/null || exit 1
  mkdir -p "${dir}/config/host"
  echo "${name}:"
  while IFS=$'\t' read -r src tgt mode owner cmp req; do
    [ "${cmp}" = presence ] && continue
    out="$(rendered_path "${dir}" "${tgt}")"
    # The one placeholder in use: the checkout path. Everything else is copied
    # as it is — a derived file is the operator's to fill in after installing.
    sed "s|${PLACEHOLDER}|${ROOT_DIR}|g" "${dir}/${src}" > "${out}.tmp"
    mv -f "${out}.tmp" "${out}"
    echo "  -> config/host/$(basename "${tgt}")  (from ${src})"
  done < <(read_manifest "${dir}")
}

# ---------------------------------------------------------------------------
# derived comparison: the settings the example names, not the values
# ---------------------------------------------------------------------------
# A setting is a top-level key — NAME= in an env-style file, name: in YAML.
# Uncommented in the example: required. Commented out ("# NAME=") in the
# example: optional. Present in the installed file and known to neither: not
# in the example.
setting_names() {  # <file> <active|commented> -> names, one per line
  local file="$1" which="$2"
  # grep exits 1 on no match; under set -e that must not end the check.
  case "${which}" in
    active)    { grep -oE '^[A-Za-z_][A-Za-z0-9_]*(=|:)' "${file}" 2>/dev/null || true; } | sed -E 's/[=:]$//' | sort -u ;;
    commented) { grep -oE '^#[[:space:]]*[A-Za-z_][A-Za-z0-9_]*(=|:)' "${file}" 2>/dev/null || true; } | sed -E 's/^#[[:space:]]*//; s/[=:]$//' | sort -u ;;
  esac
}

# derived_state <rendered> <installed> -> prints "state<TAB>detail" and a newline
derived_state() {
  local rendered="$1" installed="$2" required optional present missing unknown
  if cmp -s "${rendered}" "${installed}"; then
    printf 'identical\t\n'
    return 0
  fi
  required="$(setting_names "${rendered}" active)"
  optional="$(setting_names "${rendered}" commented)"
  present="$(setting_names "${installed}" active)"
  missing="$(comm -23 <(printf '%s\n' "${required}") <(printf '%s\n' "${present}") | sed '/^$/d' | paste -sd, - || true)"
  unknown="$(comm -23 <(printf '%s\n' "${present}") <(printf '%s\n' "${required}"$'\n'"${optional}" | sort -u) | sed '/^$/d' | paste -sd, - || true)"
  if [ -n "${missing}" ]; then
    printf 'differs\tmissing setting(s): %s\n' "${missing}"
    return 0
  fi
  if [ -n "${unknown}" ]; then
    printf 'adapted\tlocally adapted; not in the example: %s\n' "${unknown}"
    return 0
  fi
  printf 'adapted\tlocally adapted\n'
}

# ---------------------------------------------------------------------------
# check
# ---------------------------------------------------------------------------
# States and what they mean for the exit code:
#   identical      rendered and installed are the same (exact), or the
#                  installed secret exists with the right mode and owner
#   adapted        derived: every setting the example names is present —
#                  values are the operator's
#   not installed  an optional file that is absent
#   missing        a required file that is absent                  -> error
#   differs        content, mode or owner differ from the manifest -> error
#   unreadable     the installed file cannot be read as this user  -> error
#   not rendered   check asked for, render not run yet             -> error
problems=0

report() {  # <state> <stack> <source> <target> <detail>
  local state="$1" stack="$2" src="$3" tgt="$4" detail="$5"
  case "${state}" in missing|differs|unreadable|"not rendered") problems=$((problems + 1)) ;; esac
  if [ -n "${detail}" ]; then
    printf '  %-14s %s: %s -> %s  (%s)\n' "${state}" "${stack}" "${src}" "${tgt}" "${detail}"
  else
    printf '  %-14s %s: %s -> %s\n' "${state}" "${stack}" "${src}" "${tgt}"
  fi
}

check_stack() {
  local dir="$1" name src tgt mode owner cmp req installed rendered state detail have_mode have_owner
  name="$(basename "${dir}")"
  read_manifest "${dir}" >/dev/null || exit 1
  while IFS=$'\t' read -r src tgt mode owner cmp req; do
    installed="${PREFIX}${tgt}"
    detail=""
    # A file that was never rendered cannot be compared; say so before anything
    # about the host, so "missing" always means "rendered, and absent there".
    if [ "${cmp}" != presence ] && [ ! -f "$(rendered_path "${dir}" "${tgt}")" ]; then
      report "not rendered" "${name}" "${src}" "${tgt}" "run: scripts/host-files.sh render ${name}"
      continue
    fi
    if [ ! -e "${installed}" ]; then
      if [ "${req}" = required ]; then
        report missing "${name}" "${src}" "${tgt}" "required; install it — scripts/host-files.sh install-commands ${name}"
      else
        report "not installed" "${name}" "${src}" "${tgt}" "optional"
      fi
      continue
    fi
    # mode and owner: readable through stat even when the content is not
    have_mode="$(file_mode "${installed}" || true)"
    have_owner="$(file_owner "${installed}" || true)"
    if [ -n "${have_mode}" ] && [ "$(norm_mode "${have_mode}")" != "$(norm_mode "${mode}")" ]; then
      detail="mode ${have_mode}, manifest ${mode}"
    fi
    if [ -n "${have_owner}" ] && [ "${have_owner}" != "${owner}" ]; then
      detail="${detail:+${detail}; }owner ${have_owner}, manifest ${owner}"
    fi
    if [ "${cmp}" = presence ]; then
      # Content is never read: existence, mode and owner are the whole check.
      if [ -n "${detail}" ]; then report differs "${name}" "-" "${tgt}" "${detail}"; else report identical "${name}" "-" "${tgt}" "present"; fi
      continue
    fi
    rendered="$(rendered_path "${dir}" "${tgt}")"
    if [ ! -r "${installed}" ]; then
      report unreadable "${name}" "${src}" "${tgt}" "${detail:+${detail}; }no read permission — run with sudo to compare the content"
      continue
    fi
    case "${cmp}" in
      exact)
        if cmp -s "${rendered}" "${installed}"; then
          state=identical
        else
          state=differs; detail="${detail:+${detail}; }content differs — scripts/host-files.sh diff ${name} ${tgt}"
        fi
        ;;
      derived)
        IFS=$'\t' read -r state d2 < <(derived_state "${rendered}" "${installed}") || true
        if [ -n "${d2}" ]; then detail="${detail:+${detail}; }${d2}"; fi
        ;;
    esac
    # A mode or owner mismatch is a difference whatever the content says.
    if [ -n "${detail}" ] && [ "${state}" != differs ] && printf '%s' "${detail}" | grep -qE 'mode |owner '; then
      state=differs
    fi
    report "${state}" "${name}" "${src}" "${tgt}" "${detail}"
  done < <(read_manifest "${dir}")
}

# ---------------------------------------------------------------------------
# diff and install-commands
# ---------------------------------------------------------------------------
diff_file() {
  local dir="$1" want="$2" show="${3:-}" src tgt mode owner cmp req rendered installed
  read_manifest "${dir}" >/dev/null || exit 1
  while IFS=$'\t' read -r src tgt mode owner cmp req; do
    [ "${tgt}" = "${want}" ] || continue
    installed="${PREFIX}${tgt}"
    case "${cmp}" in
      presence)
        echo "${tgt} is a secret — existence, mode and owner are checked, the content is never shown."
        return 0 ;;
      derived)
        if [ "${show}" != "--show" ]; then
          echo "${tgt} is an operator-edited file and may hold secrets; the settings are compared, not shown."
          echo "To see the full difference anyway: scripts/host-files.sh diff $(basename "${dir}") ${tgt} --show"
          rendered="$(rendered_path "${dir}" "${tgt}")"
          [ -f "${rendered}" ] && [ -r "${installed}" ] && derived_state "${rendered}" "${installed}" | tr '\t' '\n'
          echo
          return 0
        fi ;;
    esac
    rendered="$(rendered_path "${dir}" "${tgt}")"
    [ -f "${rendered}" ] || { echo "not rendered — run: scripts/host-files.sh render $(basename "${dir}")"; return 1; }
    [ -e "${installed}" ] || { echo "${tgt} is not installed"; return 1; }
    diff -u "${installed}" "${rendered}" && echo "identical"
    return 0
  done < <(read_manifest "${dir}")
  echo "ERROR: ${want} is not in $(basename "${dir}")/ops/host-files.manifest" >&2
  return 1
}

install_commands() {
  local dir="$1" name src tgt mode owner cmp req rendered user group reload="" logrotate=""
  name="$(basename "${dir}")"
  read_manifest "${dir}" >/dev/null || exit 1
  echo "# ${name}: commands to install or update the host files. Printed, never run."
  echo "# Review each one; a derived file is copied only when it is not installed yet,"
  echo "# because the installed copy carries the operator's values."
  while IFS=$'\t' read -r src tgt mode owner cmp req; do
    user="${owner%%:*}"; group="${owner#*:}"
    rendered="$(rendered_path "${dir}" "${tgt}")"
    case "${cmp}" in
      presence)
        echo "# ${tgt}: a secret the operator creates (see ${name}/README.md); expected mode ${mode}, owner ${owner}" ;;
      derived)
        echo "[ -e ${tgt} ] || sudo install -m ${mode} -o ${user} -g ${group} ${rendered} ${tgt}   # then edit the values" ;;
      exact)
        echo "sudo install -m ${mode} -o ${user} -g ${group} ${rendered} ${tgt}" ;;
    esac
    case "${tgt}" in
      /etc/systemd/system/*) reload=yes ;;
      /etc/logrotate.d/*)    logrotate="${logrotate} ${tgt}" ;;
    esac
  done < <(read_manifest "${dir}")
  [ -n "${reload}" ] && echo "sudo systemctl daemon-reload"
  for t in ${logrotate}; do echo "sudo logrotate -d ${t}   # dry run: every log must be listed"; done
  return 0
}

# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
cmd="${1:-}"; shift || true
case "${cmd}" in
  render)
    if [ "$#" -eq 0 ]; then set -- $(stacks_with_manifest); fi
    for s in "$@"; do render_stack "$(stack_dir "$s")"; done
    ;;
  check)
    if [ "$#" -eq 0 ]; then
      any=0
      for s in $(stacks_with_manifest); do
        if [ -d "${s}/config/host" ]; then any=1; check_stack "${s}"; else
          printf '  %-14s %s: not rendered — not in use on this host, or run: scripts/host-files.sh render %s\n' "skipped" "$(basename "${s}")" "$(basename "${s}")"
        fi
      done
      [ "${any}" -eq 1 ] || echo "  (no stack rendered yet — nothing is checked)"
    else
      for s in "$@"; do check_stack "$(stack_dir "$s")"; done
    fi
    [ "${problems}" -eq 0 ] || { echo "  ${problems} host file(s) need attention."; exit 1; }
    ;;
  diff)
    [ "$#" -ge 2 ] || usage
    diff_file "$(stack_dir "$1")" "$2" "${3:-}"
    ;;
  install-commands)
    [ "$#" -eq 1 ] || usage
    install_commands "$(stack_dir "$1")"
    ;;
  *) usage ;;
esac
