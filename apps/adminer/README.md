# Adminer

Stateless web-based database administration tool. Supports MySQL, MariaDB, PostgreSQL, SQLite, MS SQL, Oracle, Elasticsearch, MongoDB, and more via drivers. Single PHP file, no dependencies.

## Architecture

Single service:

| Service | Image | Purpose |
|---------|-------|---------|
| `app` | `adminer:4-standalone` | Adminer web UI on port 8080 |

**No database of its own.** Adminer is a client that connects to databases running in other containers or on other hosts. It stays on `proxy-public` only; it joins individual app networks on demand (see below).

## Setup

```bash
# 1. Create .env
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, TZ

# 2. Start
docker compose up -d

# 3. Access via browser
# https://<APP_TRAEFIK_HOST>
# Only reachable through Tailscale/VPN by default (acc-tailscale).
```

No secrets or initial setup — you log in via the Adminer UI each time with DB credentials.

## Connecting to app databases

Adminer needs network reachability to the database container it wants to manage. Blueprint apps keep their databases on internal networks (`internal: true`), so Adminer can't see them by default. You have three options:

### Option A — per-app network attach (recommended)

```bash
# One-off: attach adminer to a specific app's internal network
docker network connect wordpress-internal adminer-app

# Now in Adminer login form:
# Server:   wordpress-db
# Username: wordpress_user
# Password: (from apps/wordpress/.secrets/db_pwd.txt)
# Database: wordpress
```

Detach when done:

```bash
docker network disconnect wordpress-internal adminer-app
```

### Option B — permanent network-list in compose

If you manage the same few DBs often, add them to `docker-compose.yml`:

```yaml
networks:
  - proxy-public
  - wordpress-internal
  - ghost-internal
```

Then declare those networks as `external: true` in the same file. Requires each target app to already be running.

### Option C — remote host

For DBs on other machines, enter the hostname/IP directly in the Adminer login form. Adminer reaches them through `proxy-public` → host routing — network requirements depend on your setup.

## Security model

- **Access policy default `acc-tailscale`** — Adminer exposes full database access including schema changes and `DROP TABLE`. It must never be publicly reachable without additional authentication.
- **Security chain default `sec-4`** — hard rate limit (20 avg / 40 burst) to mitigate credential-stuffing against the DB-login form.
- **Stateless** — Adminer keeps no persistent state; sessions die with the browser. No volumes, no secrets files.
- **Single-file PHP** — smaller attack surface than phpMyAdmin. Upstream has historically been careful with security patches.
- **No credentials stored** — you type DB password at every login. This is a feature, not a limitation.

## Known issues

- **Live-tested: no.** Expect small bugs on first deployment.
- **Session timeout** is short (~20 min idle). Adminer won't let you stay logged in long — acceptable for an admin tool, occasionally annoying during long query sessions.
- **No query history across sessions.** Copy-paste your queries into a local file if you need to keep them.
- **Network-attach dance** (Option A above) is manual. Until the blueprint has a dedicated "admin-internal" network pattern, this is the trade-off.

## Variants (not in this install by default)

- **Bundled MariaDB for throwaway local DB testing** — the original import source included a standalone MariaDB next to Adminer for development-only use cases. Dropped from the blueprint version because Adminer's main purpose is managing existing app DBs. The pattern still makes sense for isolated local dev; reference compose and rationale live under `docs/apps/adminer/setup-notes.md` on the repository's `docs` branch.

## Details

- [UPSTREAM.md](UPSTREAM.md) — source, upgrade checklist
