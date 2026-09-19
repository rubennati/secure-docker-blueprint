#!/usr/bin/env bash
# Create the credentials and the config file agentgateway needs, once.
#
#   ops/init.sh [ui-user]        # default UI user: admin
#
# Writes (all gitignored; the two files the container reads are mode 644, and
# hold only hashes):
#   .secrets/agw_api_key.txt        the client key — give it to API and MCP clients
#   .secrets/agw_ui_password.txt    the UI password for <ui-user>
#   .secrets/agw_ui_htpasswd.txt    the htpasswd file mounted into the container
#   config/config.yaml              rendered from config/config.yaml.example with
#                                   the key's SHA-256 (the key itself is not stored there)
# Refuses to overwrite anything that already exists.
set -euo pipefail
cd "$(dirname "$0")/.."

UI_USER="${1:-admin}"
[[ "$UI_USER" =~ ^[A-Za-z0-9._-]+$ ]] || { echo "invalid UI user name" >&2; exit 2; }
for f in .secrets/agw_api_key.txt .secrets/agw_ui_password.txt .secrets/agw_ui_htpasswd.txt config/config.yaml; do
  [[ ! -e "$f" ]] || { echo "$f already exists — remove it deliberately to regenerate" >&2; exit 1; }
done
command -v openssl >/dev/null || { echo "openssl is required" >&2; exit 1; }

umask 077
mkdir -p .secrets config volumes/data

api_key="sk-$(openssl rand -hex 24)"
ui_password="$(openssl rand -hex 16)"
printf '%s' "$api_key" > .secrets/agw_api_key.txt
printf '%s' "$ui_password" > .secrets/agw_ui_password.txt
printf '%s:%s\n' "$UI_USER" "$(openssl passwd -apr1 "$ui_password")" > .secrets/agw_ui_htpasswd.txt

hash="$(printf '%s' "$api_key" | openssl dgst -sha256 | awk '{print $NF}')"
sed "s/__API_KEY_HASH__/$hash/g" config/config.yaml.example > config/config.yaml
# The container runs as uid 65532 and Compose bind-mounts secret files with their
# host permissions, so the two files it reads must be world-readable. Both hold
# only hashes; the plaintext key and password files stay 600.
chmod 644 config/config.yaml .secrets/agw_ui_htpasswd.txt

echo "Created. Next:"
echo "  sudo chown 65532:65532 volumes/data     # the image runs as uid 65532"
echo "  docker compose up -d"
echo "Client key:  .secrets/agw_api_key.txt"
echo "UI login:    $UI_USER / $(cat .secrets/agw_ui_password.txt)   (also in .secrets/agw_ui_password.txt)"
