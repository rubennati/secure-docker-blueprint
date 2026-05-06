# OpenProject CE

**Status: 🚧 Draft — not yet live-tested**

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

# 2. Create secrets
mkdir -p .secrets
echo -n "$(openssl rand -base64 64 | tr -d '\n')" > .secrets/OP_SECRET_KEY_BASE
echo -n "$(openssl rand -base64 32 | tr -d '\n')" > .secrets/OP_DB_PWD

# 3. Configure .env — set HOST_DOMAIN, TZ, OPENPROJECT_DEFAULT_LANGUAGE, MIDDLEWARES

# 4. Start (seeder runs first and exits, then web/worker/cron start)
docker compose up -d

# 5. Wait ~2 minutes for the seeder to complete migrations
docker compose logs -f seeder

# 6. Open https://<HOST_DOMAIN>
# Default credentials: admin / admin — change immediately
```

## Open items (before ✅ Ready)

- [ ] Live test: `docker compose up -d` — watch seeder logs until exit 0
- [ ] Change default admin password immediately after first login
- [ ] Test Gantt chart, kanban board, work packages, time tracking
- [ ] SMTP: configure outgoing email (Administration → Email)
- [ ] Calibrate memory limits — web container may need more than 1G under load
- [ ] **OIDC/SSO**: not available in CE (Enterprise add-on). Users are local accounts only.
- [ ] Verify `no-new-privileges` does not break the slim image startup scripts
- [ ] Verify `service_completed_successfully` condition works for seeder → web dependency

## Verify

- [ ] Seeder exited cleanly: `docker compose ps` shows seeder as exited (0)
- [ ] All other services healthy: `docker compose ps`
- [ ] Web UI loads at configured domain
- [ ] Log in as admin and change the default password
- [ ] Create a project, add a work package — verify persistence after restart
- [ ] Gantt view and kanban board load correctly
- [ ] Check Administration → System Settings → Host name matches `HOST_DOMAIN`

## Security Model

| Control | Status | Notes |
|---|---|---|
| `no-new-privileges` | ✅ | On all services |
| Secrets | ✅ | SECRET_KEY_BASE + DB password via Docker Secrets |
| Database isolation | ✅ | `db` and `cache` on internal network only |
| Docker socket | ✅ | Not mounted (autoheal service omitted by design) |
| TLS termination | ✅ | Traefik — `OPENPROJECT_HTTPS=true` set |

## Notes

- **`OPENPROJECT_DEFAULT_LANGUAGE`** — only affects the first-run seed. Changing it later has no effect on already-seeded data.
- **Seeder** uses `restart: on-failure`. If it fails (e.g., DB not ready), it restarts automatically. Check logs if `web` never becomes healthy.
- **Autoheal** (from upstream compose) is omitted — it requires a direct Docker socket mount. OpenProject's own healthcheck restarts via `restart: unless-stopped` on failure.
- **Hocuspocus** (real-time collaborative editing) is omitted. Enable by adding the `hocuspocus` service from the upstream compose when needed.
- **Git repository integration** is not supported in the Docker setup. Use the packaged installation for that feature.
- **Plugins** require building a custom image on top of `openproject/openproject:17-slim`. See upstream docs.
