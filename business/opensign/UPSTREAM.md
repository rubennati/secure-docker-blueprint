# Upstream Reference

## Source

- **Project:** https://www.opensignlabs.com
- **GitHub:** https://github.com/OpenSignLabs/OpenSign
- **Docker Hub (frontend):** https://hub.docker.com/r/opensign/opensign
- **Docker Hub (backend):** https://hub.docker.com/r/opensign/opensignserver
- **License:** AGPL-3.0
- **Decision facts checked:** not yet
- **Origin:** India · OpenSign Inc · non-EU
- **Domain:** Documents and e-signature
- **Role:** Document signing with qualified-certificate support
- **Last verified:** 2026-11-08 (main) — lab host (VM), IPv4 LAN, at the closed default, the `main` images built on 2026-11-02 (upstream publishes no version tags): the first admin created through the `addadmin` cloud function, `checkadminexist` then `exist`, a login with a session before and after `down`/`up`, the refused client answered `403` (docs/labs/stack-refresh/2026-11-08-results.md)

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

## Version notes

- Re-pinned `main` on 2026-11-05 to the images built on 2026-11-02 from
  upstream commit `9258b593c0` (after the v3.1.0 release), not run on a host at
  these digests: UI `opensign/opensign`
  `sha256:093910c698c135e272a794ec1df81324c584b0c1011bb95da0c04ff22adb45ac`,
  API `opensign/opensignserver`
  `sha256:49819bc883aa5b0053106f2d60d49334231c723cc37c01a304a9322e46bfc06f`.
  The previous API digest was built on 2026-06-30, so the move spans the
  GitHub releases v3.0.0, v3.0.1 and v3.1.0: a redesigned interface, qualified
  electronic signatures (QES), undo and redo in the editor, decline reasons in
  the document API and dependency updates. No breaking change, variable change
  or migration step is listed. The reason for the move is the CVE findings in
  the old images. Source: https://github.com/OpenSignLabs/OpenSign/releases

## Upgrade checklist

1. Check [OpenSign releases](https://github.com/OpenSignLabs/OpenSign/releases) for changelog
2. **Note:** Docker Hub only has `main` / `staging` / `docker_beta` — no semver tags. Upgrading means re-pinning `main` to its current digests (`APP_TAG` and `SERVER_TAG` in `.env` and `.env.local.example`; commands in `.env.example`) and adding a dated version note.
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
docker compose exec opensign-api sh

# Check MongoDB status (with auth)
docker compose exec db mongosh \
  --username opensign \
  --password "$(cat .secrets/db_root_pwd.txt)" \
  --authenticationDatabase admin \
  --eval "db.adminCommand('ping')"

# View API logs
docker compose logs opensign-api --follow
# Watch for: "parse-server-example running on port 8080"
```
