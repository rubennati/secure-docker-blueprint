# Immich

Self-hosted photo and video backup with machine-learning–based search, facial recognition, and mobile apps for iOS/Android. Four-service stack: web server, ML worker, Postgres (with the VectorChord extension for embeddings), and Valkey (Redis-compatible).

Project, source, licence and origin: [`UPSTREAM.md`](UPSTREAM.md).

## Architecture

| Service | Image | Purpose |
|---------|-------|---------|
| `immich-app` | `ghcr.io/immich-app/immich-server:v3.3.6` | Web UI + REST API + upload handler |
| `machine-learning` | `ghcr.io/immich-app/immich-machine-learning:v3.3.6` | CLIP embeddings, face detection, object recognition |
| `db` | `ghcr.io/immich-app/postgres:14-vectorchord1.1.1` (digest-pinned) | Postgres with vector extensions for similarity search |
| `redis` | `valkey/valkey:9.1.3` | Background job queue (Bull/BullMQ) |

## Try it locally

Runs on `http://localhost:2283` without Traefik, DNS or a certificate.

```bash
cp .env.local.example .env.local # fill the __REPLACE_ME__ values
docker compose -f docker-compose.local.yml --env-file .env.local up -d
# http://localhost:2283
docker compose -f docker-compose.local.yml --env-file .env.local down
```

`.env.local` holds plain values, not Docker Secrets — local only.

## Setup

```bash
# 1. Create .env
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, TZ, UPLOAD_LOCATION

# 2. Generate DB secret
mkdir -p .secrets
openssl rand -base64 32 | tr -d '/+=\n' > .secrets/db_pwd.txt
# Immich restricts DB_PASSWORD to [A-Za-z0-9] — no special chars.
# The tr above strips +/= produced by base64.

# 3. Sync DB_PWD_INLINE with the secret file
sed -i "s|^DB_PWD_INLINE=.*|DB_PWD_INLINE=$(cat .secrets/db_pwd.txt)|" .env

# 4. Create volume directories
mkdir -p volumes/postgres volumes/redis volumes/model-cache volumes/library
# Valkey runs as the image's own user and cannot fix ownership itself
sudo chown 999:999 volumes/redis

# 5. Start
docker compose up -d

# 6. Wait for first-run migrations (~2 minutes)
docker compose logs immich-app --follow
# Watch for: "Immich Server is listening on..."

# 7. Over the VPN, open the UI and create the admin account. The route ships
#    closed (APP_TRAEFIK_ACCESS=access-vpn); switch it to access-public afterwards
#    if the mobile apps reach it without the VPN
# https://<APP_TRAEFIK_HOST>
# First user to sign up becomes admin.
```

## Verify

```bash
docker compose ps                              # all four services healthy
curl -fsSI https://<APP_TRAEFIK_HOST>/api/server/ping   # 200 OK, {"res":"pong"}
```

## Security Model

- **First-user-wins admin** — until an admin exists, `POST /api/auth/admin-sign-up` makes the first caller the admin, with no setup secret; afterwards it answers `Admin setup is not available` (measured on the lab host at v3.3.6). With a public route that is whoever arrives first, which is why the route ships at `access-vpn`: create the admin over the VPN, then open it.
- **`DB_PASSWORD` restricted to `[A-Za-z0-9]`** — Immich does not support special characters in the DB password. Keep generation aligned (see Setup step 2).
- **`DB_PWD_INLINE` duplicates the DB password** — see Known Issues.
- **Postgres on `app-internal` (`internal: true`)** — only the Immich services can reach it.
- **`no-new-privileges:true`** on all services.
- **Redis is `read_only: true` + tmpfs** — persistence via `/data` volume only.
- **ML container** — downloads models to `./volumes/model-cache/` on first use (~2-3 GB).

## Backup

| | |
|---|---|
| **Database** | PostgreSQL (Immich's own image, with the vector extension) · container `immich-db` · database `immich` · user `immich` |
| **Password** | `.secrets/db_pwd.txt` |
| **State** | `./volumes/postgres` (database) · **`${UPLOAD_LOCATION}`** — the photo and video library itself |
| **Reproducible** | `./volumes/redis` (cache) · `./volumes/model-cache` (re-downloaded models) |
| **Quiescing** | Stop `immich-app` for the dump (see Restore); pause uploads for a large library copy if you want the two halves to match exactly. |

```yaml
postgresql_databases:
    - name: immich
      container: immich-db
      username: immich
      password: "{credential file /srv/docker/apps/immich/.secrets/db_pwd.txt}"
```

**`UPLOAD_LOCATION` can point outside the stack directory** (the example keeps it
in `./volumes/library`), which is exactly why it gets forgotten. It is also, by volume, the largest thing this repository backs up
and the only part that is irreplaceable — the database holds albums, faces and
metadata, all of which can be rebuilt from the originals. The reverse is not true.

Immich's database uses a vector extension; restore into the same image version
that produced the dump, not into a stock `postgres` image.

## Restore

**A plain `psql < dump.sql` does not restore this database**, and it does not
report that it failed. Three parts of the [upstream
procedure](https://docs.immich.app/administration/backup-and-restore) are load
bearing. The dump it expects is one database in plain SQL, taken with the app
stopped:

```bash
docker compose stop immich-app
docker compose exec -T db sh -c 'pg_dump --username="$POSTGRES_USER" "$POSTGRES_DB"' | gzip > dump.sql.gz
docker compose start immich-app
```

Restore it into the fresh database:

```bash
gunzip --stdout dump.sql.gz \
  | sed "s/SELECT pg_catalog.set_config('search_path', '', false);/SELECT pg_catalog.set_config('search_path', 'public, pg_catalog', true);/g" \
  | docker compose exec -T db sh -c \
      'psql --dbname="$POSTGRES_DB" --username="$POSTGRES_USER" \
            --single-transaction --set ON_ERROR_STOP=on'
```

| Part | What it does |
|---|---|
| the `sed` | rewrites `search_path` so the vector extension's types and functions resolve. Without it the objects that depend on them are not created |
| `--single-transaction` | a failure rolls the whole restore back instead of leaving a half-populated database that starts and looks plausible |
| `ON_ERROR_STOP=on` | without it `psql` continues past errors and exits 0. This is the part that turns a failed restore into one you find out about later |

Measured on the lab host (v3.2.0): this pipeline restored the `pg_dump` above
with every row count and the originals intact. The upstream page's `pg_dumpall
--clean` dump stops it at once — `DROP DATABASE cannot run inside a transaction
block` — and the `postgresql_databases` entry under Backup fails on a host whose
`pg_restore` is newer than the server's PostgreSQL 14 (`transaction_timeout`).

Two preconditions upstream states, both of which invalidate a restore if missed:

- **Stop `app` before taking the dump.** A dump taken while the server writes can capture a torn state.
- **Restore only into a fresh install** — a database the Immich server has never started against. If the server has run, recreate the volume first. Where the database cannot be started on its own, set `DB_SKIP_MIGRATIONS=true` before bringing the stack up, so the server does not migrate a database that is about to be replaced.

**Restore order:** database first, then the library, then the app.

## Known Issues

- **A `429` on first install leaves the app on a black screen** — Immich's service worker pre-caches about 100 JS chunks in parallel. With a burst of 50 part of them were answered `429`. `.env.example` ships `limit-standard`, whose burst of 500 holds them.
- **`DB_PWD_INLINE` duplicates the DB password** — Immich-server's `DB_PASSWORD` env var has no `_FILE` support. The Postgres service reads `POSTGRES_PASSWORD_FILE` from a Docker Secret, but immich-server needs the same value inline in `.env`. Setup step 3 syncs them. Mismatch = connection refused.
- **Custom Postgres image is required** — the vector extension (VectorChord) used for photo similarity search are Immich-specific. Do NOT substitute a stock `postgres:14` image.
- **Upload volume** — `UPLOAD_LOCATION` can be an NFS/SMB share. The `db` volume must be local storage (Postgres corrupts on network filesystems).
- **Hardware acceleration** — transcoding and ML inference can use GPU/NPU. See [Immich hwaccel docs](https://docs.immich.app/features/ml-hardware-acceleration) — add the `extends:` block and change the image tag (e.g. `v2-cuda`).
- **First ML inference is slow** — CLIP model downloads on first photo upload (~5-10 min on slow links).

## Importing photos

### Official CLI — `immich-cli`

The official Immich CLI (`@immich/cli`). Suitable for straightforward folder imports.

```bash
# Install (requires Node.js)
npm install -g @immich/cli

# Import a folder
immich upload --recursive /path/to/photos \
  --key <API-KEY> \
  --server https://<APP_TRAEFIK_HOST>
```

API key: Immich UI → Account Settings → API Keys → New API Key.

### Community importer — `immich-go`

[`immich-go`](https://github.com/simulot/immich-go) by simulot. Go binary, no Node.js required. More features than the official CLI:

- **Google Photos Takeout import** — parses `.json` sidecar metadata (dates, albums, descriptions) correctly
- **Duplicate detection** — skips files already in Immich by content hash
- **Album creation** from folder structure or Google Photos albums
- **Dry-run mode** — preview what would be uploaded without actually uploading
- **Stack detection** — groups RAW + JPEG pairs automatically

```bash
# Download binary (replace VERSION and ARCH as needed)
# https://github.com/simulot/immich-go/releases
curl -L https://github.com/simulot/immich-go/releases/latest/download/immich-go_Linux_amd64.tar.gz | tar xz

# Import a local folder
./immich-go upload from-folder \
  --server https://<APP_TRAEFIK_HOST> \
  --api-key <API-KEY> \
  /path/to/photos

# Import Google Photos Takeout (zip or extracted folder)
./immich-go upload from-google-photos \
  --server https://<APP_TRAEFIK_HOST> \
  --api-key <API-KEY> \
  /path/to/takeout
```

> Use `immich-go` for Google Photos migrations or large libraries with duplicate risk. Use the official CLI for simple folder syncs.

## Open findings

<!-- findings:start — generated by scripts/ci/lifecycle-report.py from upstream-status.json; edit the text around it -->

**Findings in the upstream images** at the pin `v3.3.6` — the newest upstream release. Scanned 2026-11-08; counted are findings with a published fix, as CRITICAL · HIGH. They come with the images as upstream publishes them.

| Image | Base system | Libraries | Programs |
|---|---|---|---|
| `ghcr.io/immich-app/immich-machine-learning:v3.3.6` | 0 · 3 | 7 · 35 | — |
| `ghcr.io/immich-app/immich-server:v3.3.6` | 1 · 3 | 4 · 30 | — |
| `ghcr.io/immich-app/postgres:14-vectorchord1.1.1@sha256:b38cad4a8bdb…` | 3 · 10 | — | 1 · 25 |
| `valkey/valkey:9.1.3` | 0 · 3 | — | — |

<!-- findings:end -->

The Immich server image, `immich-server:v3.3.6`, carries 5 CRITICAL findings that have published fixes: brotli from its Debian base and the Node packages handlebars, `proxy-addr` and `tar`. The machine-learning image, `immich-machine-learning:v3.3.6`, carries 7, five of them in Pillow 12.3.0, plus anyio and certifi. v3.3.6 is the newest stable release.

**Risk:** the machine-learning service decodes uploaded photos with Pillow, so allow uploads only from trusted users. The server's findings need admin-set templates, unusual proxy settings or crafted archives. Watch for v3.4.0.

The Immich database image, `ghcr.io/immich-app/postgres:14-vectorchord1.1.1`, carries 4 CRITICAL findings: Perl 5.36 from its Debian 12 base (CVE-2026-13221, CVE-2026-42496, CVE-2026-8376) and the `gosu` Go runtime (CVE-2025-68121). Every current Immich PostgreSQL build, on any supported major, ships the same packages.

**Risk:** PostgreSQL does not run Perl on user data, and gosu makes no network connection. Keep the database on the internal network and watch for a rebuilt image.

## Details

- [UPSTREAM.md](UPSTREAM.md)
