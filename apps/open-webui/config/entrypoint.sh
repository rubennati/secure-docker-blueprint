#!/bin/sh
set -e

# Open WebUI has no _FILE variant for its session-signing key, the initial
# administrator password or the backend API key. Read the Docker Secrets here
# and hand off to the image's own start script.
# Intermediate variables so set -e aborts if a secret file is missing.
_sk="$(cat /run/secrets/WEBUI_SECRET_KEY)"
_ap="$(cat /run/secrets/WEBUI_ADMIN_PASSWORD)"
export WEBUI_SECRET_KEY="$_sk"
export WEBUI_ADMIN_PASSWORD="$_ap"
if [ -f /run/secrets/OPENAI_API_KEY ]; then
  _ak="$(cat /run/secrets/OPENAI_API_KEY)"
  export OPENAI_API_KEY="$_ak"
fi
unset _sk _ap _ak

exec "$@"
