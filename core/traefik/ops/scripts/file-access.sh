# Sourced by bouncer-key.sh and validate.sh — a host file as Traefik's process can use it.
#
# Traefik runs as root with cap_drop: ALL (docker-compose.yml). Without
# CAP_DAC_OVERRIDE the kernel checks a bind-mounted file against root like
# against any other account: the owner bits when the file belongs to uid 0, the
# group bits when its group is gid 0, the bits for everyone else otherwise. A
# directory made by hand as a normal user (mode 755) is therefore readable for
# Traefik but not writable, and a file of yours with mode 600 is not readable.
#
# TRAEFIK_RUN_AS is the uid:gid the container runs as — 0:0 as shipped. A test
# runs as another user and names itself there to stand in for Traefik.

# traefik_stat <path>: sets T_UID, T_GID, T_MODE (three digits) and T_BITS, the
# permission digit Traefik gets. Returns 1 when the file cannot be inspected.
traefik_stat() {
  local out run_as="${TRAEFIK_RUN_AS:-0:0}"
  out="$(stat -c '%u %g %a' "$1" 2>/dev/null || stat -f '%u %g %Lp' "$1" 2>/dev/null)" || return 1
  [ -n "${out}" ] || return 1
  read -r T_UID T_GID T_MODE <<< "${out}"
  T_MODE="$(printf '%03d' "${T_MODE}")"
  T_MODE="${T_MODE: -3}"
  if [ "${T_UID}" = "${run_as%%:*}" ]; then T_BITS="${T_MODE:0:1}"
  elif [ "${T_GID}" = "${run_as##*:}" ]; then T_BITS="${T_MODE:1:1}"
  else T_BITS="${T_MODE:2:1}"
  fi
}

# traefik_can <path> <r|w|x combination>: 0 when Traefik has every named right,
# 1 when it lacks one, 2 when the file cannot be inspected.
traefik_can() {
  local need=0
  traefik_stat "$1" || return 2
  case "$2" in *r*) need=$((need | 4)) ;; esac
  case "$2" in *w*) need=$((need | 2)) ;; esac
  case "$2" in *x*) need=$((need | 1)) ;; esac
  [ $((T_BITS & need)) -eq "${need}" ]
}

# traefik_meta: the last inspected file's owner, group and mode, for a message.
traefik_meta() {
  printf 'owner %s, group %s, mode %s' "${T_UID}" "${T_GID}" "${T_MODE}"
}
