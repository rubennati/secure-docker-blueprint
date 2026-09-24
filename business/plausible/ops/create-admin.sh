#!/usr/bin/env bash
# Creates the first account from the command line, so the sign-up form never
# has to be the thing that does it.
#
# Run this straight after `docker compose up -d`, with the application healthy.
# Until one account exists, Plausible sends /login and /sites to /register no
# matter what DISABLE_REGISTRATION says — and whoever completes that form owns
# the instance. Once this script has run, /register redirects to /login.
#
# There is no upstream CLI for it: v3.2.1 ships `db createdb`, `db migrate`,
# `db rollback` and `db seed`, and nothing that makes a user. This goes through
# the release's own remote console instead, which is a supported entry point.
#
# All three values are handed over as files inside the container's tmpfs and
# read back in Elixir — never as arguments, and never interpolated into the
# expression. So the password stays out of the process list, out of `docker
# inspect` and out of your shell history, and a name with a quote in it cannot
# turn into code.
#
# `rpc` evaluates on the RUNNING node, whose environment is the one the
# container started with. Values passed with `docker compose exec -e` never
# reach it — which is why this uses files rather than environment variables.
set -euo pipefail
cd "$(dirname "$0")/.."

SERVICE=plausible-app
D=/tmp/.admin

read -r -p "Email: " ADMIN_EMAIL
read -r -p "Name: " ADMIN_NAME
read -r -s -p "Password: " ADMIN_PW; echo
read -r -s -p "Password (again): " ADMIN_PW2; echo

if [ "$ADMIN_PW" != "$ADMIN_PW2" ]; then
  echo "passwords do not match" >&2
  exit 1
fi

cleanup() { docker compose exec -T "$SERVICE" rm -rf "$D" >/dev/null 2>&1 || true; }
trap cleanup EXIT

docker compose exec -T "$SERVICE" mkdir -p "$D"
printf '%s' "$ADMIN_EMAIL" | docker compose exec -T "$SERVICE" sh -c "cat > $D/email"
printf '%s' "$ADMIN_NAME"  | docker compose exec -T "$SERVICE" sh -c "cat > $D/name"
printf '%s' "$ADMIN_PW"    | docker compose exec -T "$SERVICE" sh -c "cat > $D/pw"
unset ADMIN_PW ADMIN_PW2

docker compose exec -T "$SERVICE" /app/bin/plausible rpc "
    email = File.read!(\"$D/email\")
    name  = File.read!(\"$D/name\")
    pw    = File.read!(\"$D/pw\")

    changeset =
      Plausible.Auth.User.new(%{
        name: name,
        email: email,
        password: pw,
        password_confirmation: pw
      })

    case Plausible.Repo.insert(changeset) do
      {:ok, user} ->
        IO.puts(\"created: #{user.email} (id #{user.id}, verified: #{user.email_verified})\")

      {:error, cs} ->
        IO.puts(:stderr, \"failed: #{inspect(cs.errors)}\")
        System.halt(1)
    end
"

echo
echo "Sign in at the host name in .env. /register now redirects to /login."
echo "Further accounts are invited from a site's settings, not created here."
