# Upstream Reference

## Source

- **Image:** https://hub.docker.com/r/fnsys/dockhand
- **GitHub:** https://github.com/Finsys/dockhand
- **Docs:** Project-internal (see image description on Docker Hub)
- **License:** BSL 1.1 — source-available, **not** open source. Each version converts to Apache-2.0 four years after Licensor first distributes it publicly, so the date differs per version rather than being one fixed day
- **Use restrictions:** production use is granted free only for personal non-commercial use, recognised non-profit and charitable organisations, and schools or non-commercial research institutions. **Production use by or on behalf of a company, sole trader, public body or any other organisation requires a Commercial Licence**, and offering it to third parties as a hosted, managed or SaaS container-management service requires a separate written agreement — https://github.com/Finsys/dockhand/blob/main/LICENSE.md · checked 2026-09-21
- **Edition gating:** Enterprise Features are gated by a License Key, which the licence forbids sharing, publishing or circumventing — https://github.com/Finsys/dockhand/blob/main/LICENSE.md · checked 2026-09-21
- **Commercial model:** commercial licence — https://github.com/Finsys/dockhand/blob/main/LICENSE.md · checked 2026-09-21
- **Decision facts checked:** 2026-09-21
- **Origin:** Finsys · **no country or legal entity stated** — no imprint on fnsys.pro or dockhand.pro
- **Domain:** Infrastructure
- **Role:** Docker management with Git-based stacks: deploy and update by pushing to Git
- **Last verified:** 2026-11-08 (v1.0.57) — over IPv4, with Postgres 16 under cap_drop: the local host through the socket proxy and a remote host through Hawser (edge) — containers listed, a log read, one stopped and started — before and after `down`/`up`, the refused client answered `403`; authentication is off on a new instance; a restore through `docker exec` (docs/labs/stack-refresh/2026-11-08-results.md)

## What we use

- Official `fnsys/dockhand` image, pinned tag
- `postgres:16.16-alpine` as backend database
- `tecnativa/docker-socket-proxy` with a restricted permission set for Docker API access

## What we changed and why

| Change | Reason |
|--------|--------|
| Custom entrypoint wrapper (`config/entrypoint.sh`) | Reads `DB_PWD` and `ENCRYPTION_KEY` from Docker Secrets at runtime; Dockhand itself does not support `_FILE` env vars |
| Socket proxy instead of direct socket mount | Dockhand requires Docker API access but must not get the raw socket; the proxy filters to only the required endpoints |
| `POSTGRES_INITDB_ARGS: --data-checksums` | Extra integrity checks on the PostgreSQL data files |
| `read_only: true` + `tmpfs` on socket proxy | Defense in depth — the proxy container has no writable root filesystem |
| `access-vpn`, `limit-standard` | Admin tool, VPN-only |

## Version / tag notes

- `v1.0.39` → `v1.0.47` on 2026-09-13, eight patches. No published advisory against either.

## Version notes

- Moved to `v1.0.56` on 2026-10-31 (released 2026-10-30), together with Hawser
  0.2.53. No breaking change or migration labelled; v1.0.55
  adds `EXPORT_METRICS_PUBLIC` (off by default, keeps `/metrics` private) and
  raises docker-compose to 5.6.0-r2 for CVE fixes and Node.js to 24.22.1; v1.0.52's
  PUID change was reverted in v1.0.53. The releases live at
  https://github.com/finsys/dockhand/releases; Docker Hub shows no notes.
- Moved to `v1.0.57` on 2026-11-05 (released 2026-11-04). No breaking change, new variable or migration in the notes. The
  release is a security hardening one: path-write guards, filtering of the
  environment passed to deployments, origin checks on requests and framing
  headers, with no advisory ID given; the notes do not say what the origin check
  compares against, so a request through Traefik that the UI now refuses is the
  first thing to look at on a host. Also: OIDC back-channel logout, conversion
  of a stack between local and git management, nodemailer and undici updated.
  No Hawser version requirement is stated.
  https://github.com/Finsys/dockhand/releases/tag/v1.0.57
- Moved from `v1.0.57` to `v1.0.59` on 2026-11-23 (v1.0.58 released 2026-11-16,
  v1.0.59 on 2026-11-22). No breaking change, new required variable or migration
  step; the schema migrations run on start. Fixed in v1.0.58: GHSA-rw9p-wgwm-pp4v
  (medium) — the SSRF guard on notification and webhook URLs checked only literal IP
  addresses, so a host name resolving to a private range passed; GHSA-m325-jpjj-xwrw
  (medium) — the SMTP host in the notification settings was not validated, allowing
  probes of the internal network and cloud metadata. Both need an account that can
  edit notification settings; with `access-vpn` that account sits behind the VPN.
  v1.0.58 also ships docker-compose 5.7.0 and an updated restic for CVE-2026-116591,
  stops writing `.env` contents of stack deploys to the log, and no longer answers
  `403` when the UI is opened by an address other than `ORIGIN` (this stack sets no
  `ORIGIN`). v1.0.59 adds permission and environment-variable hardening in settings
  and compose validation, and updates Node.js to 24.22.3 and docker-compose to
  5.7.1-r1. v1.0.58 adds `DISABLE_FRAME_PROTECTION` (off by default; leave it off).
  https://github.com/Finsys/dockhand/releases/tag/v1.0.58,
  https://github.com/Finsys/dockhand/releases/tag/v1.0.59,
  https://github.com/Finsys/dockhand/security/advisories

## Upgrade checklist

1. Check the new Dockhand release for breaking changes and migration notes: https://hub.docker.com/r/fnsys/dockhand/tags
2. Back up the Postgres volume (`./volumes/postgres/`) — Dockhand stores stack definitions here
3. Back up `./volumes/data/` — Git repo clones and encryption state
4. Bump `APP_TAG` in `.env`
5. `docker compose pull && docker compose up -d`
6. Check: `docker compose logs app --tail 100` for DB migration messages or startup errors
7. Verify the web UI loads, existing stacks are still listed and can be reconciled

## Related images to keep in sync

- `postgres:16.16-alpine` — upgrade within minor versions is safe; major upgrades (15 → 16) require a manual `pg_upgrade` procedure, not covered here
- `tecnativa/docker-socket-proxy` — safe to update within the same major version

## Useful commands

```bash
# Shell into the app container
docker compose exec app sh

# Show Dockhand's effective DATABASE_URL (after entrypoint assembled it)
docker compose exec app env | grep DATABASE_URL

# Inspect socket proxy permissions in effect
docker compose exec socket-proxy env | grep -v ^_

# Backup Postgres dump
docker compose exec db pg_dump -U dockhand dockhand > dump.sql

# Restore Postgres dump (into a fresh DB — see upgrade checklist)
cat dump.sql | docker compose exec -T db psql -U dockhand -d dockhand
```
