# Upstream Reference

## Source

- **Image:** https://hub.docker.com/r/onlyoffice/documentserver
- **Docs:** https://helpcenter.onlyoffice.com/docs/installation/docs-community-install-docker.aspx
- **GitHub (CE):** https://github.com/ONLYOFFICE/DocumentServer
- **Config reference:** https://github.com/ONLYOFFICE/DocumentServer/blob/master/Docker/README.md
- **License:** AGPL-3.0
- **Origin:** Latvia · Ascensio System SIA · EU
- **Based on version:** `8.3` (Document Server Community)
- **Last checked:** 2026-04-16

## What we use

- Official `onlyoffice/documentserver` image, pinned to major version `8.3`
- Single-container deployment — the image bundles PostgreSQL + Redis + RabbitMQ internally
- `config/entrypoint.sh` wrapper to inject the JWT secret from Docker Secrets

## What we changed and why

| Change | Reason |
|--------|--------|
| Entrypoint wrapper reading `/run/secrets/ONLYOFFICE_JWT_SECRET` | Upstream reads `JWT_SECRET` from env only — no `_FILE` support. The wrapper exports it, then execs the original `run-document-server.sh`. |
| Custom Traefik middleware chain (`-proto`, `-headers`) | Standard `sec-*` chains set `X-Frame-Options: DENY`; OnlyOffice must be embeddable in an iframe by Seafile/Nextcloud. The custom chain replaces DENY with a scoped CSP `frame-ancestors` allowlist. |
| `X-Forwarded-Proto: https` + `X-Forwarded-Host` custom request headers | OnlyOffice uses these to generate absolute URLs for assets; without them the client gets Mixed Content errors because the editor tries to load `http://…` resources inside an `https://` page. |
| `WOPI_ENABLED: "true"` | Enables the WOPI protocol on top of the standard OnlyOffice API — required by Nextcloud's integration and optionally used by other clients. |
| Volumes `/var/www/onlyoffice/Data` and `/var/log/onlyoffice` | Persist uploaded fonts/templates and server logs across container restarts. |
| `no-new-privileges:true` | Blueprint baseline; the upstream image doesn't need privilege escalation at runtime. |
| Single `app` service name (instead of `onlyoffice`) | Blueprint convention — `app` is the primary service of the compose project; the project name disambiguates when stacks are merged. |

## Tag pinning

`APP_TAG=8.3` pins to the 8.3 line. Within the line, patches are rolled out by the upstream and picked up on `docker compose pull` — acceptable for non-critical content. Pin to a specific digest (`docker image inspect <image> --format '{{index .RepoDigests 0}}'`) for reproducible deployments.

## Upgrade checklist

Major-version upgrades (`8.x` → `9.x`) carry schema migrations inside the internal PostgreSQL.

1. Read the release notes: https://github.com/ONLYOFFICE/DocumentServer/releases
2. Back up the data volume:
   ```bash
   tar czf onlyoffice-data-$(date +%Y%m%d).tgz ./volumes/data
   ```
3. Bump `APP_TAG` in `.env`
4. `docker compose pull && docker compose up -d`
5. First start after a major version bump can take several minutes while the internal PostgreSQL migrates. Watch:
   ```bash
   docker compose logs app --follow
   ```
6. Verify: `curl -fsSI https://<APP_TRAEFIK_HOST>/healthcheck` returns 200, and open an editor from a connected app.

### Rollback

The internal PostgreSQL migration is not reversible. Rollback = restore `onlyoffice-data-*.tgz` and revert `APP_TAG`.

## Useful commands

```bash
# Shell
docker compose exec app bash

# Check the resolved JWT secret inside the container (sanity check for the wrapper)
docker compose exec app sh -c 'echo "${JWT_SECRET:0:6}... (length $#)"'

# OnlyOffice version
docker compose exec app cat /var/www/onlyoffice/documentserver/VERSION

# Tail logs (container stderr + on-disk logs)
docker compose logs app --follow
tail -f volumes/logs/documentserver/docservice/out.log

# Clear the internal document cache (rarely needed; only for troubleshooting
# "locked for editing" states after a crash)
docker compose exec app bash -c 'supervisorctl restart all'
```
