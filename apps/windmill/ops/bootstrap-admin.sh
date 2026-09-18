#!/usr/bin/env bash
# Replace Windmill's built-in superadmin (admin@windmill.dev / changeme) with an
# operator account, then prove the built-in one no longer authenticates.
#
#   ops/bootstrap-admin.sh you@example.com
#
# Talks to the server container directly, so it needs no Traefik route — run it
# while APP_TRAEFIK_ACCESS is still acc-deny. The new password is written to
# .secrets/windmill_admin_pwd.txt (mode 600).
set -euo pipefail

EMAIL="${1:-}"
DC="${DC:-docker compose}"
DEFAULT_EMAIL="admin@windmill.dev"
DEFAULT_PWD="changeme"
PWD_FILE=".secrets/windmill_admin_pwd.txt"

[[ "$EMAIL" =~ ^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$ ]] || {
  echo "usage: $0 <operator-email>" >&2; exit 2; }
[[ "$EMAIL" != "$DEFAULT_EMAIL" ]] || { echo "choose an address other than $DEFAULT_EMAIL" >&2; exit 2; }

# curl inside the server container; the request body arrives on stdin so the
# password never appears in a process list.
api() { # api METHOD PATH [TOKEN] — body on stdin, prints "<body>\n<http-code>"
  local method="$1" path="$2" token="${3:-}"
  $DC exec -T windmill-server curl -s -w '\n%{http_code}' -X "$method" \
    "http://127.0.0.1:8000/api$path" -H 'Content-Type: application/json' \
    ${token:+-H "Authorization: Bearer $token"} -d @-
}
code() { tail -n1; }
body() { sed '$d'; }
login() { # login EMAIL PASSWORD — sets LOGIN_CODE and, on 200, TOKEN (no subshell)
  local out; out="$(printf '{"email":"%s","password":"%s"}' "$1" "$2" | api POST /auth/login)"
  LOGIN_CODE="$(printf '%s' "$out" | code)"; TOKEN="$(printf '%s' "$out" | body)"
}

TOKEN=""
login "$DEFAULT_EMAIL" "$DEFAULT_PWD"
case "$LOGIN_CODE" in
  200) ;;
  400|401) echo "Built-in $DEFAULT_EMAIL does not authenticate — already bootstrapped."; exit 0 ;;
  *) echo "server not answering (HTTP '${LOGIN_CODE}') — is the stack up and healthy?" >&2; exit 1 ;;
esac
DEFAULT_TOKEN="$TOKEN"

umask 077
mkdir -p "$(dirname "$PWD_FILE")"
NEWPW="$(openssl rand -hex 24)"
printf '%s' "$NEWPW" > "$PWD_FILE"

create="$(printf '{"email":"%s","password":"%s","super_admin":true,"name":"Operator"}' "$EMAIL" "$NEWPW" \
  | api POST /users/create "$DEFAULT_TOKEN")"
[[ "$(printf '%s' "$create" | code)" == 201 ]] || {
  echo "creating $EMAIL failed: $(printf '%s' "$create" | body)" >&2; rm -f "$PWD_FILE"; exit 1; }

login "$EMAIL" "$NEWPW"
[[ "$LOGIN_CODE" == 200 ]] || { echo "new account cannot log in (HTTP $LOGIN_CODE)" >&2; exit 1; }
NEW_TOKEN="$TOKEN"

del="$(printf '{}' | api DELETE "/users/delete/$DEFAULT_EMAIL" "$NEW_TOKEN")"
[[ "$(printf '%s' "$del" | code)" == 200 ]] || {
  echo "deleting $DEFAULT_EMAIL failed: $(printf '%s' "$del" | body)" >&2; exit 1; }

login "$DEFAULT_EMAIL" "$DEFAULT_PWD"
[[ "$LOGIN_CODE" == 400 || "$LOGIN_CODE" == 401 ]] || {
  echo "built-in credential check returned HTTP $LOGIN_CODE, expected 400/401" >&2; exit 1; }

echo "Superadmin $EMAIL created; $DEFAULT_EMAIL removed and no longer authenticates."
echo "Password: $PWD_FILE"
