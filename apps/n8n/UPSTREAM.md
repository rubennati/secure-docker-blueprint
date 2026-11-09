# Upstream Reference

## Source

- **n8n project:** https://n8n.io/
- **GitHub:** https://github.com/n8n-io/n8n
- **Docker docs:** https://docs.n8n.io/hosting/installation/docker/
- **License:** [Sustainable Use License](https://github.com/n8n-io/n8n/blob/master/LICENSE.md) (source-available, not OSI-approved)
- **Use restrictions:** free for internal business purposes and for non-commercial use; it may be given to others only free of charge and for non-commercial purposes, and its licensing and copyright notices may not be altered, removed or obscured — https://github.com/n8n-io/n8n/blob/master/LICENSE.md · checked 2026-09-21
- **Edition gating:** files and directories whose names contain `.ee.` are covered by a separate enterprise licence rather than by the Sustainable Use License — https://github.com/n8n-io/n8n/blob/master/LICENSE.md · checked 2026-09-21
- **Commercial model:** commercial licence — https://github.com/n8n-io/n8n/blob/master/LICENSE.md · checked 2026-09-21
- **Decision facts checked:** 2026-09-21
- **Origin:** Germany · n8n GmbH · EU
- **Domain:** Automation and data
- **Role:** Visual workflow automation
- **Last verified:** 2026-11-09 (2.46.7) — lab host (VM), IPv4 LAN, moved from 2.46.6 on a new installation: a webhook workflow imported and published with the n8n CLI answered `{"sum":42}` through Traefik before and after `down`/`up`, the refused client answered `403`; 3.x not taken — 3.1.0 is still a GitHub pre-release (docs/labs/stack-refresh/2026-11-08-results.md)

## What we use

- Upstream `n8nio/n8n` from Docker Hub, the repository n8n's release workflow
  pushes to, pinned by the digest of the multi-arch index. `docker.n8n.io`, the
  address n8n's documentation also names, is a download-counting gateway in
  front of the same Docker Hub repository: it authenticates against Docker Hub,
  and Docker Hub counts its anonymous pulls against the gateway's shared
  addresses. That quota was exhausted on every image scan from 2026-10-05 to
  2026-10-19, so the image was never scanned through it.
- Built-in SQLite database (in `./volumes/data/`)
- Docker Secret for `N8N_ENCRYPTION_KEY`
- Bind-mount `./volumes/data` (n8n state) and `./volumes/files` (workflow scratch space)

## What we changed and why

| Change | Reason |
|--------|--------|
| **`${SUBDOMAIN}.${DOMAIN_NAME}` → single `APP_TRAEFIK_HOST`** | Blueprint uses one variable for the full hostname |
| **Inline Traefik header middlewares removed** — inbox defined HSTS/XSS/nosniff/etc. inline | Replaced with the shared `headers-standard@file` profile (same headers, centralized) |
| **Traefik router entrypoints pared down** — inbox used `web,websecure` + `SSLRedirect: true` | Now just `websecure`; blueprint handles HTTP→HTTPS redirect at the entrypoint level |
| **`certresolver=dnsResolver` replaced with `APP_TRAEFIK_CERT_RESOLVER`** | Blueprint variable |
| **Port `8015:5678` exposure removed** | Blueprint routes via Traefik |
| **`N8N_ENCRYPTION_KEY_FILE` added** (Docker Secret) | n8n supports `_FILE` suffixes on every secret env var — the encryption key is the single most important secret |
| **Basic auth enabled by default** | Community Edition has no user management unless opted in; basic auth is the minimum viable gate |
| **`security_opt: no-new-privileges:true`** | Baseline hardening |
| **`traefik` external network → `proxy-public`** | Blueprint standard network name |
| **Unused `traefik_data` volume removed** | Stray leftover from a full Traefik+n8n bundle |
| **Access `access-vpn`, `limit-standard` and `headers-standard` defaults** | n8n hosts API tokens for many third-party services — VPN-only is safer than public |

## Version notes

- Moved to `2.46.7` on 2026-11-09 (released the same day, upstream's `stable`
  channel; not a pre-release) and run on the lab host. One fix: resume attempts
  for waiting and queued executions are limited (n8n-io/n8n#42862). Pinned by
  the digest of the multi-arch index,
  `sha256:e97b4f576cd21de5c7676858f7006126581faeca8046d9d23fda0e06468008d4`.
  No configuration change.
- Moved to `2.46.6` on 2026-11-05 (released 2026-11-04, upstream's `stable`
  channel), across 2.42 to 2.46, not run on a host at this tag. Pinned by the
  digest of the multi-arch index (linux/amd64, linux/arm64),
  `sha256:8602f5dfacbe2c931eeafd010de0e68182310e9f309921e780ab69182e92b3ae`.
  The 3.x tags on Docker Hub (`3.0.0`, `3.0.1`, `3.1.0`) are GitHub
  pre-releases built with `N8N_RELEASE_TYPE=rc`, not stable releases, so the
  pin stays on the 2.x line; before a later move to 3.x, read
  https://docs.n8n.io/changelog/v30-breaking-changes and the v3 migration
  report that 2.45 and later show in the UI.
  The image's npm dependencies move to `@simple-git/argv-parser` 2.0.1,
  `simple-git` 4.0.2, `handlebars` 4.7.10, `proxy-addr` 2.0.8 and
  `shell-quote` 1.11.0, and `openssh` to `10.3_p1-r1`; 3.1.0 carries the same
  versions. `brotli-libs` is still `1.2.0-r1` in this tag, in 2.47.2 (`beta`)
  and in 3.1.0, so CVE-2026-111497 remains until upstream rebuilds its base.
  Node.js 26.7.0 becomes 26.12.1 (`n8nio/base:26.12.1`). No breaking change in
  `packages/cli/BREAKING-CHANGES.md` touches this stack (the only entry is for
  the n8n Packages preview); `N8N_SCHEDULER_MIN_INTERVAL` is removed (2.45.0,
  not set here); the entrypoint, port 5678 and `/healthz` are unchanged, so
  the compose files keep their configuration. Behaviour changes: creating or
  updating a workflow that contains a deprecated node is refused (2.42.6, the
  fix for GHSA-9p7v-45m2-wxgj), so such workflows must be migrated to the
  current node first; the image removes GraphicsMagick's MSL, MVG, PCD, SVG
  and URL coders and sets `MAGICK_CODER_STABILITY=PRIMARY`, so the Edit Image
  node no longer reads those formats (GHSA-f2cw-9483-7vcp); JavaScript task
  runners no longer have Node Web Storage. Database migrations run on first
  start, so back up `volumes/data/` before. Fixes the advisories affecting
  2.41.7, among them the high-severity GHSA-wvjj-qg37-pv73,
  GHSA-mp7q-23hg-35cf, GHSA-m7gv-mpg5-7c9v (2.43.5), GHSA-gx3v-3x3v-f8r5,
  GHSA-f2cw-9483-7vcp (2.45.5) and GHSA-9p7v-45m2-wxgj (2.42.6), plus 16
  medium-severity ones published 2026-10-14 and 2026-10-28 —
  https://github.com/n8n-io/n8n/security/advisories,
  https://github.com/n8n-io/n8n/releases.

## Upgrade checklist

1. Check [n8n releases](https://github.com/n8n-io/n8n/releases) — minor bumps can contain breaking changes to nodes and workflows
2. Back up:

   ```bash
   tar czf n8n-data-$(date +%Y%m%d).tgz volumes/data/
   ```

3. Bump `APP_TAG` in `.env` (pin to a specific release)
4. `docker compose pull && docker compose up -d`
5. Watch logs:

   ```bash
   docker compose logs app --follow
   ```

6. Verify: log in, open a workflow, trigger a manual execution, confirm credentials still decrypt (encryption key unchanged)

### Rollback

Restore `volumes/data/`, revert `APP_TAG`. SQLite schema migrations are forward-only; a downgrade after a major bump may need manual SQL intervention.

## Useful commands

```bash
# Shell into n8n
docker compose exec app sh

# CLI commands
docker compose exec app n8n --help
docker compose exec app n8n list:workflow
docker compose exec app n8n export:workflow --all --output=/files/backup.json
docker compose exec app n8n import:workflow --input=/files/backup.json

# User management (CE multi-user)
docker compose exec app n8n user-management:reset
```

## Upgrading to Postgres

For larger deployments, swap SQLite for Postgres:

```yaml
# Add to compose:
db:
  image: postgres:16
  environment:
    POSTGRES_DB: n8n
    POSTGRES_USER: n8n
    POSTGRES_PASSWORD_FILE: /run/secrets/DB_PWD
  secrets: [DB_PWD]
  volumes: ["./volumes/postgres:/var/lib/postgresql/data"]
  networks: [app-internal]

# On app, add env:
DB_TYPE: postgresdb
DB_POSTGRESDB_HOST: db
DB_POSTGRESDB_DATABASE: n8n
DB_POSTGRESDB_USER: n8n
DB_POSTGRESDB_PASSWORD_FILE: /run/secrets/DB_PWD
```

n8n supports `_FILE` on every secret env var, so no `DB_PWD_INLINE` duplication is needed.
