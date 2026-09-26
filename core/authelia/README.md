# Authelia

A login portal with two-factor authentication that sits in front of other stacks.
Traefik asks Authelia, through forward-auth, whether a request may pass; an
application behind it needs no identity integration of its own and receives the
signed-in user as request headers.

Users live in a file (`volumes/data/users_database.yml`), sessions in Redis, and
second factors — TOTP, WebAuthn — in PostgreSQL. There is no admin interface:
users and rules are edited in files.

## Architecture

| Service | Image | Purpose |
|---------|-------|---------|
| `authelia` | `authelia/authelia` | Portal and forward-auth endpoint, port 9091 |
| `db` | `postgres` | Second factors, settings per user, audit of sign-ins |
| `redis` | `redis` | Sessions |

```text
Browser → Traefik ──forward-auth──→ Authelia :9091 ── Redis (sessions)
             │                           └──────────── PostgreSQL (second factors)
             └──→ protected app (receives Remote-User, Remote-Groups, …)
```

## Try it locally

Authelia refuses a portal that is not served over HTTPS and a session cookie on a
bare `localhost`, so the local file differs from the others: Authelia serves TLS
itself with a certificate `ops/init.sh --local` creates, and runs under
`auth.example.localhost`, which browsers resolve to `127.0.0.1` on their own. One
container — SQLite instead of PostgreSQL, sessions in memory.

```bash
cp .env.local.example .env.local # fill the three __REPLACE_ME__ values
ops/init.sh --local              # certificate and the user admin
docker compose -f docker-compose.local.yml --env-file .env.local up -d
# https://auth.example.localhost:9091 — accept the self-signed certificate
# password: volumes/local/admin_pwd.txt
docker compose -f docker-compose.local.yml --env-file .env.local down
```

Registering a second factor asks for a one-time code; locally it is written to
`volumes/local/data/notification.txt`. `.env.local` holds plain values, not
Docker Secrets — local only.

## Setup

```bash
# 1. Create .env
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, SESSION_COOKIE_DOMAIN, TZ; SMTP_* when a mail relay exists

# 2. Secrets, data directories and the first user
ops/init.sh                      # user admin; or: ops/init.sh <name> <email>

# 3. Start
docker compose up -d
```

`ops/init.sh` generates every secret, writes the first user with an Argon2 hash —
Authelia creates the password and prints it once, so it never appears on a command
line — and stores the password in `.secrets/admin_pwd.txt`. It sets ownership with a
throwaway container, so no `sudo` is needed: Authelia runs as `1000:1000` and Redis
as `999:1000`, and the secret files get group `1000` and mode `640`
([`docs/standards/secrets.md`](../../docs/standards/secrets.md)).

`SESSION_COOKIE_DOMAIN` is the parent of the portal and of every protected app —
`example.com` for `auth.example.com` and `wiki.example.com`. Apps on another domain
cannot share the sign-in.

Without `SMTP_ADDRESS`, one-time codes and reset links are written to
`volumes/data/notification.txt` instead of being mailed. That is enough for one
administrator; with more users, set the relay.

## Verify

```bash
docker compose ps                                  # three services, all healthy
docker compose logs authelia | grep -i "startup complete"
```

Open `https://<APP_TRAEFIK_HOST>`, sign in as `admin`, and register a second
factor. Then protect one app (below) and open it: the browser goes to the portal
and comes back signed in.

## Protecting an application

Define the middleware once, in a dynamic configuration file of
[`core/traefik`](../traefik/) (`config/dynamic/`, hot-reloaded):

```yaml
http:
  middlewares:
    authelia:
      forwardAuth:
        address: "http://authelia-app:9091/api/authz/forward-auth"
        authResponseHeaders:
          - Remote-User
          - Remote-Groups
          - Remote-Email
          - Remote-Name
```

Then add `authelia@file` to the middleware list of the router to protect, after
the access policy and the security chain:

```yaml
- "traefik.http.routers.${COMPOSE_PROJECT_NAME}.middlewares=${APP_TRAEFIK_THREAT}${APP_TRAEFIK_ACCESS}@file,${APP_TRAEFIK_SECURITY}@file,authelia@file"
```

The protected stack must share a network with `authelia-app` — `proxy-public`
does. `trustForwardHeader` is left unset on purpose: Traefik then sends Authelia
the headers it built itself, not ones a client supplied. The entrypoint already
trusts forwarded headers from Cloudflare alone
([`core/traefik`](../traefik/)).

**Who may enter is decided in `config/configuration.yml`.** The shipped rule
requires two factors on every host under `SESSION_COOKIE_DOMAIN`, and everything
else is denied. Rules are read top to bottom and the first match wins, so a rule
for one app goes above the wildcard:

```yaml
access_control:
  default_policy: 'deny'
  rules:
    - domain: 'wiki.example.com'
      subject: 'group:admins'
      policy: 'two_factor'
    - domain: '*.example.com'
      policy: 'two_factor'
```

## Security model

- **Deny by default, two factors everywhere.** A host that no rule names is
  refused.
- **Secrets as files.** Session, reset-link and storage keys and the database
  password arrive through Authelia's `_FILE` variables; the mail password is read
  from its file by the configuration template, and only when a relay is set.
- **`storage_encryption_key.txt` encrypts the second factors in the database.**
  Lose it and every user has to register TOTP and security keys again. It belongs
  in the same backup as the database.
- **Read-only container, no capabilities, not root.** Authelia rewrites
  `/app/.healthcheck.env` at every start and exits without naming the cause when it
  cannot; that one file is mounted writable, the rest of `/app` stays read-only.
  The healthcheck asks `/api/health` directly instead of going through the image's
  script, which reports healthy whenever that file lacks its marker line.
- **The portal's first load is 43 requests** (measured 2026-09-26, headless
  Chrome) — under the burst of 50 in `sec-3`, the shipped chain.
- **The portal's access policy follows the apps it protects.** It ships
  `acc-public`, because a public app needs a public login page. When every
  protected app is VPN-only, set `acc-tailscale` here as well.

## Choosing between Authelia, Authentik and Keycloak

| | Authelia | [Authentik](../authentik/) | [Keycloak](../keycloak/) |
|---|---|---|---|
| Built around | forward-auth for a reverse proxy | identity provider with flows and outposts | realms, clients, federation |
| Users and rules | YAML files | web interface | web interface |
| Protocols to apps | headers through the proxy | forward-auth, OIDC, SAML, LDAP, RADIUS | OIDC, SAML, LDAP federation |

## Backup

| | |
|---|---|
| **Database** | PostgreSQL · container `authelia-db` · database `authelia` · user `authelia` — second factors, per-user settings, sign-in history |
| **Password** | `.secrets/db_pwd.txt` |
| **State** | `./volumes/postgres` (database) · `./volumes/data/users_database.yml` (users and password hashes) · `.secrets/storage_encryption_key.txt` |
| **Reproducible** | `./volumes/redis` (sessions — users sign in again) · `./volumes/runtime` |
| **Quiescing** | Not needed for the dump. The users file changes only when a password does. |

```yaml
postgresql_databases:
    - name: authelia
      container: authelia-db
      username: authelia
      password: "{credential file /srv/docker/core/authelia/.secrets/db_pwd.txt}"
```

**The dump is useless without `storage_encryption_key.txt`** — Authelia cannot
read the second factors it holds. Borgmatic archives `.secrets/` with the rest of
the deployment root, so both travel together.

**Restore order:** database, users file and secrets, then the containers.
Authelia migrates the schema at start and refuses one newer than its own
version.

For the general PostgreSQL restore procedure, see
[Restore](../../docs/standards/restore.md).

## Details

- [UPSTREAM.md](UPSTREAM.md) — source, version, what changed and why
- [Authelia documentation](https://www.authelia.com/configuration/prologue/introduction/)
