#!/bin/sh
set -e

# =============================================
# Docker Secrets → environment, then the service.
#
# Seafile's services read their passwords and keys from environment
# variables only — none of them knows a _FILE variant. Each container
# mounts the secrets it needs under /run/secrets/; this wrapper exports
# those it finds under the names the service reads, then exec's the
# service's own command. The values never stand in .env or in
# `docker inspect`.
#
# Used by every Seafile service of this stack. It writes no file, so it
# is safe in containers that share /shared with the app.
# =============================================

read_secret() { [ -f "/run/secrets/$1" ] && cat "/run/secrets/$1"; }

if [ -f /run/secrets/DB_ROOT_PWD ]; then
  export INIT_SEAFILE_MYSQL_ROOT_PASSWORD="$(read_secret DB_ROOT_PWD)"
fi

if [ -f /run/secrets/SEAFILE_DB_PWD ]; then
  export SEAFILE_MYSQL_DB_PASSWORD="$(read_secret SEAFILE_DB_PWD)"
  # SeaDoc reads the same password as DB_PASSWORD.
  export DB_PASSWORD="${SEAFILE_MYSQL_DB_PASSWORD}"
fi

if [ -f /run/secrets/SEAFILE_ADMIN_PWD ]; then
  export INIT_SEAFILE_ADMIN_PASSWORD="$(read_secret SEAFILE_ADMIN_PWD)"
  # SeaSearch creates its first administrator with the same credentials.
  export SS_FIRST_ADMIN_PASSWORD="${INIT_SEAFILE_ADMIN_PASSWORD}"
fi

if [ -f /run/secrets/JWT_KEY ]; then
  export JWT_PRIVATE_KEY="$(read_secret JWT_KEY)"
  # Seahub and Seafile AI authenticate each other with the same key, and
  # the face embedding service uses it unless FACE_EMBEDDING_SERVICE_KEY is set.
  export SEAFILE_AI_SECRET_KEY="${JWT_PRIVATE_KEY}"
  export FACE_EMBEDDING_SERVICE_KEY="${FACE_EMBEDDING_SERVICE_KEY:-${JWT_PRIVATE_KEY}}"
fi

if [ -f /run/secrets/REDIS_PWD ]; then
  export REDIS_PASSWORD="$(read_secret REDIS_PWD)"
fi

if [ -f /run/secrets/ONLYOFFICE_JWT_SECRET ]; then
  export ONLYOFFICE_JWT_SECRET="$(read_secret ONLYOFFICE_JWT_SECRET)"
fi

if [ -f /run/secrets/SEAFILE_SMTP_PWD ]; then
  export SEAFILE_SMTP_PASSWORD="$(read_secret SEAFILE_SMTP_PWD)"
fi

if [ -f /run/secrets/SEAFILE_AI_LLM_KEY ]; then
  export SEAFILE_AI_LLM_KEY="$(read_secret SEAFILE_AI_LLM_KEY)"
fi

exec "$@"
