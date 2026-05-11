# Upstream Reference

## Source

- **Project:** https://www.opensignlabs.com
- **GitHub:** https://github.com/OpenSignLabs/OpenSign
- **Docker Hub (frontend):** https://hub.docker.com/r/opensign/opensign
- **Docker Hub (backend):** https://hub.docker.com/r/opensign/opensignserver
- **License:** AGPL-3.0
- **Origin:** India · OpenSign Inc · non-EU
- **Based on version:** `main` (no semver tags published — see Known Issues in README)
- **Last checked:** 2026-05-11

## What we use

- Two official images: `opensign/opensignserver:main` (Parse Server API) + `opensign/opensign:main` (React SPA)
- MongoDB as backing database (with authentication — upstream default has no auth)
- Docker Secret for MongoDB root password (`DB_ROOT_PWD`)
- `MONGODB_URI` + `MASTER_KEY` as inline env vars (no `_FILE` support in Parse Server)
- Traefik path-based routing: `/app` → API (priority 100), everything else → UI (priority 1)
- Local file storage (`USE_LOCAL=true`) — no S3/DigitalOcean Spaces required

## What we changed vs. upstream

| Change from upstream | Reason |
|---|---|
| **Traefik labels instead of Caddy + port mapping** | Blueprint routing standard |
| **MongoDB with authentication** | Upstream default exposes Mongo with no auth; we add `MONGO_INITDB_ROOT_USERNAME/PASSWORD_FILE` |
| **`app-internal: internal: true` for MongoDB** | Upstream exposes port 27018 publicly — we isolate DB to internal network only |
| **`security_opt: no-new-privileges:true`** | Baseline hardening |
| **`SERVER_URL` without `/api` prefix** | Caddy (upstream) strips `/api` before forwarding to Parse; Traefik routes directly to `/app` |
| **`PARSE_MOUNT=/app` explicit** | Make the API mount path visible and intentional |
| **`USE_LOCAL=true`** | Avoid mandatory S3 dependency; files stored in `volumes/api-files/` |
| **`APP_ID=opensign` hardcoded** | Deprecated upstream constant — must not be a random value |

## Architecture note

OpenSign uses Parse Server (Node.js) as the backend API with MongoDB as the data store. The React SPA (frontend) communicates with Parse at `/app` (the `PARSE_MOUNT` path). Upstream uses Caddy as a reverse proxy, which strips the `/api` path prefix before forwarding to Parse — our Traefik setup routes `/app` directly without any prefix stripping.

## Upgrade checklist

1. Check [OpenSign releases](https://github.com/OpenSignLabs/OpenSign/releases) for changelog
2. **Note:** Docker Hub only has `main` / `staging` / `docker_beta` — no semver tags. Upgrading means pulling the latest `main`.
3. Back up MongoDB:
   ```bash
   docker compose exec db mongodump --username opensign \
     --password "$(cat .secrets/db_root_pwd.txt)" \
     --authenticationDatabase admin --out /tmp/backup
   docker compose cp db:/tmp/backup ./opensign-backup-$(date +%Y%m%d)
   ```
4. `docker compose pull && docker compose up -d`
5. Verify: log in, upload a document, send for signature

## Useful commands

```bash
# Shell into the API server
docker compose exec api sh

# Check MongoDB status (with auth)
docker compose exec db mongosh \
  --username opensign \
  --password "$(cat .secrets/db_root_pwd.txt)" \
  --authenticationDatabase admin \
  --eval "db.adminCommand('ping')"

# View API logs
docker compose logs api --follow
# Watch for: "parse-server-example running on port 8080"
```
