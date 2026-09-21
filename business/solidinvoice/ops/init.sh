#!/usr/bin/env bash
# Prepares the configuration directory. SolidInvoice generates its own secrets
# during installation and keeps them there, so there is nothing to create here.
set -euo pipefail
cd "$(dirname "$0")/.."

# The SQLite database lives in db/ under the configuration directory. The
# application does not create that directory itself.
mkdir -p volumes/config/db

echo "Created volumes/config/db"
echo
echo "Next:"
echo "  sudo chown -R 1000:1000 volumes/config"
echo "  docker compose up -d"
echo "  open https://<your host>/install — over the VPN, see the README"
