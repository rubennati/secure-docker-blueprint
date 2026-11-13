# Sourced by render.sh and validate.sh — the CrowdSec bouncer key as Traefik reads it.
#
# The key is a Docker secret. crowdsec-bouncer.yml mounts .secrets/crowdsec_bouncer_key.txt
# at /run/secrets/crowdsec_bouncer_key, and dynamic/crowdsec.yml names that path as
# crowdsecLapiKeyFile, so no rendered file carries the key. config/dynamic has to stay
# readable for Traefik as a whole; a key inside it was readable by every account on
# the host.
#
# Traefik runs as root without capabilities (docker-compose.yml, cap_drop: ALL). With
# no CAP_DAC_OVERRIDE, the kernel applies the file's mode to root like to any other
# user: root reads the file as its owner (uid 0) or through group 0, not as a file of
# yours with mode 600. A key Traefik cannot read stops the plugin from loading; the
# threat middleware is then missing from the entrypoint, and every router on
# websecure is disabled. render.sh refuses that state before it writes anything.

BOUNCER_KEY_FILE=".secrets/crowdsec_bouncer_key.txt"
BOUNCER_KEY_TARGET="/run/secrets/crowdsec_bouncer_key"
BOUNCER_KEY_OVERLAY="crowdsec-bouncer.yml"

bouncer_key_fix() {
  echo "         sudo chown \"\$USER\":0 ${BOUNCER_KEY_FILE} && chmod 640 ${BOUNCER_KEY_FILE}"
}

# bouncer_key_check <stack dir>: returns 0 when Traefik can read the key file, 1
# with the reason printed. Reads the file's owner, group and mode, never its content.
bouncer_key_check() {
  local f="$1/${BOUNCER_KEY_FILE}" uid gid mode bits
  if [ ! -s "${f}" ]; then
    if [ -f "${f}" ]; then
      echo "ERROR: ${BOUNCER_KEY_FILE} is empty."
    else
      echo "ERROR: CROWDSEC_BOUNCER_ENABLED=true, but ${BOUNCER_KEY_FILE} does not exist."
    fi
    if [ -n "${CROWDSEC_BOUNCER_KEY:-}" ]; then
      echo "       CROWDSEC_BOUNCER_KEY in .env is no longer read; the key lives in that file now."
    fi
    echo "       Issue a key on the engine into the file, then let Traefik read it:"
    echo "         docker exec crowdsec cscli bouncers add traefik-bouncer -o raw > ${BOUNCER_KEY_FILE}"
    bouncer_key_fix
    return 1
  fi
  read -r uid gid mode <<EOF
$(stat -c '%u %g %a' "${f}" 2>/dev/null || stat -f '%u %g %Lp' "${f}")
EOF
  mode="$(printf '%03d' "${mode}")"
  mode="${mode: -3}"
  if [ "${uid}" = 0 ]; then bits="${mode:0:1}"
  elif [ "${gid}" = 0 ]; then bits="${mode:1:1}"
  else bits="${mode:2:1}"
  fi
  if [ $(( bits & 4 )) -eq 0 ]; then
    echo "ERROR: Traefik cannot read ${BOUNCER_KEY_FILE} (owner ${uid}, group ${gid}, mode ${mode})."
    echo "       It runs as root without CAP_DAC_OVERRIDE and reads the file only as its owner"
    echo "       (uid 0) or through group 0. Unread, the plugin does not load and every router"
    echo "       on websecure is disabled. Keep the file yours and give root the group:"
    bouncer_key_fix
    return 1
  fi
  if [ $(( ${mode:2:1} & 4 )) -ne 0 ]; then
    echo "WARNING: ${BOUNCER_KEY_FILE} is readable by every account on this host (mode ${mode})."
    bouncer_key_fix
  fi
  return 0
}
