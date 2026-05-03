# Upstream Reference

## Source

- **Project:** https://www.opensignlabs.com
- **GitHub:** https://github.com/OpenSignLabs/OpenSign
- **Docker Hub:** https://hub.docker.com/r/opensignlabs/opensign
- **License:** AGPL-3.0
- **Origin:** India · OpenSign Inc · non-EU
- **Based on version:** `v2.38.0`
- **Last checked:** 2026-05-03

## What we use

- Two official images: `opensignlabs/opensignserver` (API) + `opensignlabs/opensign` (frontend SPA)
- MongoDB as backing database
- Docker Secrets for JWT secret and MongoDB credentials
- Traefik labels for HTTPS routing; frontend uses `sec-3-spa` (SPA with many parallel asset requests)

## What we changed vs. upstream examples

| Change from upstream | Reason |
|---|---|
| **Traefik labels instead of `-p` port mapping** | Blueprint routing standard |
| **Docker Secrets for JWT + DB credentials** | Security baseline |
| **`security_opt: no-new-privileges:true`** | Baseline hardening |
| **`sec-3-spa` on frontend router** | SPA fires 100+ parallel chunk requests on first load |

## Upgrade checklist

1. Check [OpenSign releases](https://github.com/OpenSignLabs/OpenSign/releases) — both images share the same version tag
2. Back up MongoDB:
   ```bash
   docker compose exec db mongodump --out /tmp/backup
   docker compose cp db:/tmp/backup ./opensign-backup-$(date +%Y%m%d)
   ```
3. Bump `APP_TAG` in `.env` (applies to both server and frontend images)
4. `docker compose pull && docker compose up -d`
5. Verify: log in, upload a document, send for signature

## Useful commands

```bash
# Shell into the API server
docker compose exec server sh

# Check MongoDB status
docker compose exec db mongosh --eval "db.adminCommand('ping')"
```
