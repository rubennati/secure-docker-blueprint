#!/usr/bin/env bash
# Generates the session key, the initial administrator password and an (empty)
# backend API key file. Refuses to overwrite existing files.
set -euo pipefail
cd "$(dirname "$0")/.."

for f in webui_secret_key webui_admin_password openai_api_key; do
  if [ -e ".secrets/$f.txt" ]; then
    echo "refusing: .secrets/$f.txt exists" >&2
    exit 1
  fi
done

umask 077
mkdir -p .secrets
printf '%s' "$(openssl rand -hex 32)" > .secrets/webui_secret_key.txt
printf '%s' "$(openssl rand -hex 16)" > .secrets/webui_admin_password.txt
# The backend key: replace the placeholder with the real key, or keep it if the
# backend needs none. Open WebUI requires a non-empty value.
printf '%s' "none" > .secrets/openai_api_key.txt

echo "Created .secrets/{webui_secret_key,webui_admin_password,openai_api_key}.txt"
echo "Administrator: the address in ADMIN_EMAIL (.env), password: $(cat .secrets/webui_admin_password.txt)"
echo "Set .secrets/openai_api_key.txt to the backend's API key if it needs one."
echo "Next: docker compose up -d"
