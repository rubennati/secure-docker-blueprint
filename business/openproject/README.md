# OpenProject CE

> **Local accounts only** — the Community Edition has no OIDC or SSO.

Full project management platform — Gantt charts, kanban boards, work packages, time tracking, wikis, and team planning. Community Edition (GPL-3.0).

Uses the **slim image** (recommended for production) with separate PostgreSQL and memcached containers. The upstream proxy service is omitted — Traefik terminates TLS and routes directly to the web container.

Project, source, licence and origin: [`UPSTREAM.md`](UPSTREAM.md).

## Services

| Service | Image | Purpose |
|---|---|---|
| `web` | `openproject/openproject:17.9.6-slim` | Application server (port 8080) |
| `worker` | same image | Background job processor |
| `cron` | same image | Scheduled tasks (email digests, cleanup) |
| `seeder` | same image | One-shot: DB migrations + seed data |
| `cache` | `memcached` | Rails cache |
| `db` | `postgres:18.6-alpine` | Persistent storage |

## Try it locally

Runs on `http://localhost:8080` without Traefik, DNS or a certificate.

```bash
# Local settings; the secrets ship empty, so fill the ones this stack needs
cp .env.local.example .env.local
printf 'DB_PASSWORD=%s\n' "$(openssl rand -hex 32)" >> .env.local
printf 'SECRET_KEY_BASE=%s\n' "$(openssl rand -base64 64 | tr -d '\n')" >> .env.local

docker compose -f docker-compose.local.yml --env-file .env.local up -d
# http://localhost:8080
docker compose -f docker-compose.local.yml --env-file .env.local down
```

`.env.local` holds plain values, not Docker Secrets — local only.

## Setup

```bash
# 1. Copy env file
cp .env.example .env
# → set APP_TRAEFIK_HOST, TZ, OPENPROJECT_DEFAULT_LANGUAGE

# 2. Create secrets
mkdir -p .secrets
openssl rand -base64 64 | tr -d '\n' > .secrets/secret_key_base.txt
openssl rand -base64 32 | tr -d '\n' > .secrets/db_pwd.txt

# 3. Start (seeder runs first and exits, then web/worker/cron start)
docker compose up -d

# 4. Watch the seeder — it runs migrations and seeds initial data (~2 min)
docker compose logs -f seeder

# 5. Once seeder exits cleanly, check all services are up
docker compose ps

# 6. Open https://<APP_TRAEFIK_HOST>
#    Default credentials: admin / admin — change immediately
```

> **First run timing**: PostgreSQL initialises its data directory before accepting connections. If `web` or `seeder` start before `db` is fully ready, they wait via `depends_on: condition: service_healthy`. On very slow hosts the DB healthcheck may need a full minute — just wait or run `docker compose up -d` again.

## Open items

- [ ] SMTP: configure outgoing email (Administration → Email)
- [ ] Calibrate memory limits — web container may need more than 1G under load
- [ ] Verify `no-new-privileges` does not break the slim image startup scripts

## Verify

- [x] Seeder exited cleanly: `docker compose ps` shows seeder as exited (0)
- [x] All other services healthy: `docker compose ps`
- [x] Web UI loads at configured domain
- [x] Log in as admin, change the default password
- [ ] Create a project, add a work package — verify persistence after restart
- [ ] Gantt view and kanban board load correctly
- [ ] Check Administration → System Settings → Host name matches `APP_TRAEFIK_HOST`

## Security Model

| Control | Status | Notes |
|---|---|---|
| `no-new-privileges` | ✅ | On all services |
| Secrets | ✅ | SECRET_KEY_BASE + DB password via Docker Secrets |
| Network isolation | ✅ | `internal: true` — `db`, `cache`, `worker`, `cron` and `seeder` have no route out |
| Docker socket | ✅ | Not mounted (autoheal service omitted by design) |
| TLS termination | ✅ | Traefik — `OPENPROJECT_HTTPS=true` set |
| SSO / OIDC | ✗ | Enterprise Edition only — not available in CE |

### What the isolated network costs

`web` also joins the proxy network and keeps its outbound path. The other five
services do not have one. OpenProject delivers mail from background jobs in
`worker`, so a configured SMTP relay outside the host is unreachable from there.

This has not been run on a host yet. If mail does not leave, or an outbound step
during first-run seeding fails, give `worker` and `cron` a second network rather
than removing `internal: true` — the pattern and what it costs are documented in
[`apps/nextcloud/README.md`](../../apps/nextcloud/README.md#network-exception--why-the-application-containers-reach-the-internet).

## What it sends outward

The security badge requests `releases.openproject.com/v1/check.svg` with a
**uuid**, the installation type and the version. It is on by default.

Turn it off in **Administration → System settings → General**, or set
`security_badge_display=false`. It is stored in the database, so it is a step
after the first login.

## Backup

| | |
|---|---|
| **Database** | PostgreSQL · container `openproject-db` · database `openproject` · user `openproject` |
| **Password** | `.secrets/db_pwd.txt` |
| **State** | `db_data` (database) · `op_assets` (work-package attachments) |
| **Reproducible** | the memcached container holds no disk state |
| **Quiescing** | Not needed for the dump. Attachments are written during use; each file is independent. |

This stack uses **named volumes**. Their host paths are
`/var/lib/docker/volumes/openproject_<name>/_data` — that is what belongs in
`source_directories`.

```yaml
postgresql_databases:
    - name: openproject
      username: openproject
      # The server's own client, inside its container (FA-03)
      pg_dump_command: docker exec openproject-db pg_dump
      pg_restore_command: docker exec -i openproject-db pg_restore
      psql_command: docker exec -i openproject-db psql
```

`secret_key_base` in `.secrets/` derives session and token values. Restoring
without it logs everyone out and invalidates issued tokens.

**Restore order:** database first, then `web`, `worker`, `cron`. The `seeder`
runs migrations — let it finish before the others come up, or a half-migrated
schema gets written over the restore.

## Notes

- **No OIDC in CE**: OAuth2 / OpenID Connect is an Enterprise add-on. CE supports local accounts and basic LDAP only. See [docs/bugfixes/vikunja-openproject-2026-05-06.md](../../docs/bugfixes/vikunja-openproject-2026-05-06.md).
- **`OPENPROJECT_DEFAULT_LANGUAGE`**: only affects the first-run seed. Changing it later has no effect on already-seeded data.
- **Seeder** uses `restart: on-failure`. If it fails (e.g., DB not ready), it restarts automatically. Check `docker compose logs seeder` if `web` never becomes healthy.
- **Base64 passwords and DATABASE_URL**: base64 passwords contain `+`, `/`, `=` which break the `postgres://` URL parser. The entrypoint URL-encodes the password with `sed` before embedding it. See `config/entrypoint.sh`.
- **Autoheal** (from upstream compose) is omitted — it requires a direct Docker socket mount. OpenProject restarts via `restart: unless-stopped` on failure.
- **Hocuspocus** (real-time collaborative editing) is omitted. Enable by adding the `hocuspocus` service from the upstream compose when needed.
- **Plugins** require building a custom image on top of `openproject/openproject:17.9.6-slim`. See upstream docs.

## Open findings

<!-- findings:start — generated by scripts/ci/lifecycle-report.py from upstream-status.json; edit the text around it -->

**Findings in the upstream images** at the pin `17.9.6-slim` — upstream has released `17.9.7-slim` since. Scanned 2026-11-09; counted are findings with a published fix, as CRITICAL · HIGH. They come with the images as upstream publishes them.

| Image | Base system | Libraries | Programs |
|---|---|---|---|
| `memcached:1.6.45-alpine` | — | — | — |
| `openproject/openproject:17.9.6-slim` | 0 · 22 | 2 · 6 | — |
| `postgres:18.6-alpine` | — | — | 1 · 25 |

<!-- findings:end -->

The pinned image, `openproject/openproject:17.9.6-slim`, ships with 2 CRITICAL vulnerabilities that have published fixes, in Rails Active Storage and the Ruby json gem. 17.9.6 is the newest release; 18.0 is still a release candidate.

**Risk:** whether OpenProject reaches either code path has not been checked. Keep the stack on `access-vpn` and move to the next release.

The PostgreSQL image, `postgres`, carries one CRITICAL finding, CVE-2025-68121, in the Go runtime of `gosu`, the helper that drops root privileges at start. Every current image of this line ships the same gosu build, and its maintainer has not rebuilt it with a fixed Go.

**Risk:** the flaw is in TLS session resumption, and gosu opens no network connection, so it is not reached. The finding clears when upstream ships a rebuilt gosu.
