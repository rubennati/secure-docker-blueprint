#!/usr/bin/env bash
# Generates the secret and prepares the data directories. Refuses to overwrite.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -e ".secrets/grafana_admin_password.txt" ]; then
  echo "refusing: .secrets/grafana_admin_password.txt exists" >&2
  exit 1
fi

umask 077
mkdir -p .secrets
openssl rand -base64 24 | tr -d '\n' > .secrets/grafana_admin_password.txt
chmod 644 .secrets/*.txt
chmod 700 .secrets

mkdir -p volumes/grafana volumes/prometheus

echo "Created .secrets/grafana_admin_password.txt"
echo
echo "Next:"
echo "  sudo chown -R 472:472 volumes/grafana        # the uid Grafana runs as"
echo "  sudo chown -R 65534:65534 volumes/prometheus # the uid Prometheus runs as"
echo "  docker compose up -d"
echo
echo "Sign in as the user in .env with the password above. Prometheus has no"
echo "login and no route: Grafana reaches it over the internal network."
