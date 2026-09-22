#!/usr/bin/env bash
# Generates the three secrets LiteLLM needs. Refuses to overwrite existing files.
set -euo pipefail
cd "$(dirname "$0")/.."

for f in db_pwd litellm_master_key litellm_salt_key; do
  if [ -e ".secrets/$f.txt" ]; then
    echo "refusing: .secrets/$f.txt exists" >&2
    exit 1
  fi
done

umask 077
mkdir -p .secrets
printf '%s' "$(openssl rand -hex 32)" > .secrets/db_pwd.txt
printf '%s' "sk-$(openssl rand -hex 24)" > .secrets/litellm_master_key.txt
printf '%s' "$(openssl rand -hex 32)" > .secrets/litellm_salt_key.txt

# The proxy runs as uid/gid 65534 and Compose mounts secrets with the host
# file's owner and mode: group read access, handed to 65534 by the chown below.
chmod 640 .secrets/db_pwd.txt .secrets/litellm_master_key.txt .secrets/litellm_salt_key.txt

echo "Created .secrets/{db_pwd,litellm_master_key,litellm_salt_key}.txt"
echo "Master key (operator and admin API): $(cat .secrets/litellm_master_key.txt)"
echo "Keep litellm_salt_key.txt: it encrypts provider credentials stored in the database."
echo "Next: sudo chown \"\$USER\":65534 .secrets/*.txt   # the proxy reads them as gid 65534"
echo "      docker compose up -d"
