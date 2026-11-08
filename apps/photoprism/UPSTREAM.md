# Upstream Reference

## Source

- **PhotoPrism project:** https://www.photoprism.app/
- **GitHub:** https://github.com/photoprism/photoprism
- **Docker Hub:** https://hub.docker.com/r/photoprism/photoprism
- **Compose docs:** https://docs.photoprism.app/getting-started/docker-compose/
- **License:** AGPL-3.0
- **Edition gating:** the admin web UI for user management and any role beyond Super Admin, Admin and Guest, together with session monitoring and hardened security, require a paid Essentials or Plus membership; two-factor login and OpenID Connect are in the Community edition — https://www.photoprism.app/editions · checked 2026-09-21
- **Commercial model:** paid self-hosted edition — https://www.photoprism.app/editions · checked 2026-09-21
- **Decision facts checked:** 2026-09-21
- **Origin:** Germany · PhotoPrism AG · EU
- **Domain:** Photos
- **Role:** Photo library with machine-learning classification and WebDAV
- **Last checked:** 2026-04-17

## What we use

- Upstream `photoprism/photoprism`
- Official `mariadb:11` as backend
- Docker Secrets for MariaDB password + root password
- Bind-mount `./volumes/database`, `./volumes/storage`
- Configurable `ORIGINALS_PATH` for photo source

## What we changed and why

| Change | Reason |
|--------|--------|
| **Real IP + hardcoded admin password removed** — inbox had an RFC1918 URL in `PHOTOPRISM_SITE_URL` and `PHOTOPRISM_ADMIN_PASSWORD="admin"` | Prevent leak; now `https://${APP_TRAEFIK_HOST}/` + generated admin password via `.env` |
| **`insecure` DB passwords replaced** — inbox had `PHOTOPRISM_DATABASE_PASSWORD`, `MARIADB_PASSWORD`, `MARIADB_ROOT_PASSWORD` all set to `"insecure"` | Now Docker Secrets (`.secrets/db_pwd.txt`, `.secrets/db_root_pwd.txt`) + `DB_PWD_INLINE` duplicate for PhotoPrism |
| **Traefik labels instead of `ports: 8009:2342`** | Blueprint routes via Traefik |
| **`PHOTOPRISM_DISABLE_TLS=true` + `DEFAULT_TLS=false`** | Traefik terminates TLS; PhotoPrism's internal HTTPS stack not needed |
| **`PHOTOPRISM_INIT: ""`** — dropped the image default `https` | Init would create a certificate for internal TLS — not needed behind Traefik. Until 260919 the value was `tensorflow`, a target 261029 removes |
| **`PHOTOPRISM_DISABLE_MCP: "true"`** | 261029 turns on an MCP API for AI agents by default; the blueprint keeps the surface it had before that release |
| **`security_opt: seccomp:unconfined + apparmor:unconfined` → `no-new-privileges:true`** on app | The unconfined profile was upstream-specific to an old MariaDB issue, not PhotoPrism itself. Kept as commented fallback on DB service only |
| **`cap_drop: ALL` + minimal `cap_add` on MariaDB** | Baseline hardening |
| **`app-internal` network (`internal: true`)** | Isolate DB from host |
| **Ollama service dropped** | Upstream opt-in profile for vision-LLM captioning. Not imported; add back if needed |
| **Watchtower service dropped** | Blueprint policy: explicit `APP_TAG` bump + `docker compose pull`, no auto-updates |
| **`ADMIN_USER / ADMIN_PASSWORD` via `.env`** | Inbox hardcoded both; now configurable + documented as only read on first boot |
| **Site metadata as variables** (`SITE_TITLE`, `SITE_CAPTION`, `DEFAULT_LOCALE`, `PLACES_LOCALE`) | Inbox hardcoded "PhotoPrism / AI-Powered Photos App / en / local" |
| **`PUID` / `PGID`** wired to `PHOTOPRISM_UID / GID` | Inbox had both commented out — app ran as root |
| **Container names standardized** — `photoprism-app/db` | Project-scoped naming |
| **Volume paths** — inbox used `./Pictures`, `./storage`, `./database` | Now `${ORIGINALS_PATH}` (default `./volumes/originals`), `./volumes/storage`, `./volumes/database` |
| **`access-public`, `limit-standard` and `headers-standard` as shipped** | Consider `access-vpn` for family-only galleries |

## Upgrade checklist

1. Check [PhotoPrism release notes](https://docs.photoprism.app/release-notes/) — PhotoPrism ships frequent breaking changes on `latest`
2. Back up:

   ```bash
   # DB dump
   docker compose exec db sh -c \
     'mariadb-dump -u root -p"$(cat /run/secrets/DB_ROOT_PWD)" photoprism' \
     > photoprism-db-$(date +%Y%m%d).sql
   # Storage (sidecars, cache, settings)
   tar czf photoprism-storage-$(date +%Y%m%d).tgz volumes/storage/
   ```

3. Bump `APP_TAG` in `.env` (consider pinning to a dated tag)
4. `docker compose pull && docker compose up -d`
5. Watch logs:

   ```bash
   docker compose logs app --follow
   ```

6. Verify: log in, browse library, trigger a rescan, confirm face-recognition still works

### Rollback

Restore DB dump and `volumes/storage/`, revert `APP_TAG`.

## Version notes

- Moved to `261029` on 2026-11-05 (released 2026-10-29), from `260919` across
  `261007`, not run on a host at this tag. The automatic proposal `20220121` is an old
  date-style tag, not a newer release. `260919` carried CRITICAL findings in
  `linux-libc-dev` of the Ubuntu base; the release notes name no base-image change, so
  whether `261029` clears them needs the next image scan. Fixed in the app: libheif
  1.23.4 → 1.23.7 (23 GHSA advisories), Go 1.27.1 → 1.27.3 (11 CVEs), ONNX Runtime
  1.29.1 → 1.31.0.
  Breaking in `261007`: classification and NSFW detection run on ONNX models; existing
  labels stay, and `photoprism vision reset -m labels` then
  `photoprism vision run -m labels --force` replaces them; custom TensorFlow models in
  `vision.yml` are no longer supported; `PHOTOPRISM_DISABLE_TENSORFLOW` now covers only
  the legacy FaceNet model, `PHOTOPRISM_DISABLE_CLASSIFICATION` is deprecated for
  `PHOTOPRISM_LABELS_MODEL=none`; the default `PHOTOPRISM_TRUSTED_PROXY` adds the
  loopback addresses to `172.16.0.0/12` (no effect here, Traefik reaches the app from
  a bridge network).
  Breaking in `261029`: schema migrations on the first start with an existing
  database (GORM 1.9.16 → 1.31.2), so take the database dump of the upgrade checklist
  first — a rollback means restoring it; files and folders whose names contain
  ``|"?*%<>{}:~$`` are no longer indexed, imported or synced; new usernames must be
  ASCII; MCP for AI agents is on by default for users and viewers, with OAuth sign-in
  for external apps (`PHOTOPRISM_OAUTH_APPS`, default `registered`); the `tensorflow`
  init targets are removed (upstream commit 41ef81c48).
  Compose changes: `PHOTOPRISM_INIT` goes from `tensorflow` to empty, since the target
  no longer exists and the image default `https` is not wanted behind Traefik;
  `PHOTOPRISM_DISABLE_CLASSIFICATION` is dropped, its value `false` being the default
  of `PHOTOPRISM_LABELS_MODEL=auto`; `PHOTOPRISM_DISABLE_MCP: "true"` keeps the MCP
  endpoint off, as it was before this release. Sources: https://docs.photoprism.app/release-notes/ ,
  https://docs.photoprism.app/getting-started/config-options/ ,
  https://github.com/photoprism/photoprism/blob/261029-963b58c50/setup/docker/compose.yaml ,
  https://github.com/photoprism/photoprism/commit/41ef81c48
- Moved `mariadb` from `11.4` to `12.3.3`, the current LTS line, on 2026-11-05,
  not run on a host at this tag. Support: PhotoPrism's own compose files pin
  `mariadb:12.3.3` (https://dl.photoprism.app/docker/compose.yaml) and its FAQ
  requires MariaDB 10.5.12 or newer
  (https://docs.photoprism.app/getting-started/faq/). `MARIADB_AUTO_UPGRADE: "1"`, already set in
  both compose files, runs `mariadb-upgrade` at the first start on 12.3 after a
  backup of the system tables; the data directory `./volumes/database` is
  reused. Take the `mariadb-dump` before the tag changes: going back to 11.4 is
  only a restore of that dump. Changed on the way (11.8 and 12.x):
  `innodb_snapshot_isolation` is on by default, so a transaction that writes a
  row another transaction changed after its snapshot fails with error 1020
  instead of overwriting it; the new default collation `utf8mb4_uca1400_ai_ci`
  does not apply, as the stack sets `utf8mb4_unicode_ci` explicitly.

## Useful commands

```bash
# Shell into the app
docker compose exec app bash

# CLI — index originals
docker compose exec app photoprism index

# CLI — import a folder into originals
docker compose exec app photoprism import /photoprism/import

# CLI — reset password for a user
docker compose exec app photoprism users reset-password <username>

# Manual DB backup
docker compose exec db sh -c \
  'mariadb-dump -u root -p"$(cat /run/secrets/DB_ROOT_PWD)" photoprism' > dump.sql

# Restore DB
cat dump.sql | docker compose exec -T db sh -c \
  'mariadb -u root -p"$(cat /run/secrets/DB_ROOT_PWD)" photoprism'
```

## Optional profiles (not included)

The upstream compose included two optional service profiles worth mentioning:

- **Ollama** — runs a local vision LLM for photo captioning via the `PHOTOPRISM_VISION_*` options. Requires a GPU for reasonable performance. Add back with `profiles: ["ollama"]` on an `ollama/ollama:latest` service and set `PHOTOPRISM_VISION_URI` / `PHOTOPRISM_VISION_KEY`.
- **Watchtower** — auto-updates PhotoPrism on a schedule. Blueprint policy avoids this; prefer explicit `APP_TAG` bumps with a backup step.
