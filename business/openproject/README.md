# OpenProject CE

**Status: ✅ Live-tested — local accounts only (CE has no OIDC/SSO)**

Full project management platform — Gantt charts, kanban boards, work packages, time tracking, wikis, and team planning. Community Edition (GPL-3.0).

Uses the **slim image** (recommended for production) with separate PostgreSQL and memcached containers. The upstream proxy service is omitted — Traefik terminates TLS and routes directly to the web container.

## Services

| Service | Image | Purpose |
|---|---|---|
| `web` | `openproject/openproject:17.x-slim` | Application server (port 8080) |
| `worker` | same image | Background job processor |
| `cron` | same image | Scheduled tasks (email digests, cleanup) |
| `seeder` | same image | One-shot: DB migrations + seed data |
| `cache` | `memcached` | Rails cache |
| `db` | `postgres:17-alpine` | Persistent storage |

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
| Database isolation | ✅ | `db` and `cache` on internal network only |
| Docker socket | ✅ | Not mounted (autoheal service omitted by design) |
| TLS termination | ✅ | Traefik — `OPENPROJECT_HTTPS=true` set |
| SSO / OIDC | ✗ | Enterprise Edition only — not available in CE |

## Notes

- **No OIDC in CE**: OAuth2 / OpenID Connect is an Enterprise add-on. CE supports local accounts and basic LDAP only. See [docs/bugfixes/vikunja-openproject-2026-05-06.md](../../docs/bugfixes/vikunja-openproject-2026-05-06.md).
- **`OPENPROJECT_DEFAULT_LANGUAGE`**: only affects the first-run seed. Changing it later has no effect on already-seeded data.
- **Seeder** uses `restart: on-failure`. If it fails (e.g., DB not ready), it restarts automatically. Check `docker compose logs seeder` if `web` never becomes healthy.
- **Base64 passwords and DATABASE_URL**: base64 passwords contain `+`, `/`, `=` which break the `postgres://` URL parser. The entrypoint URL-encodes the password with `sed` before embedding it. See `config/entrypoint.sh`.
- **Autoheal** (from upstream compose) is omitted — it requires a direct Docker socket mount. OpenProject restarts via `restart: unless-stopped` on failure.
- **Hocuspocus** (real-time collaborative editing) is omitted. Enable by adding the `hocuspocus` service from the upstream compose when needed.
- **Plugins** require building a custom image on top of `openproject/openproject:17-slim`. See upstream docs.
