# Upstream Reference

## Source

- **Image:** https://hub.docker.com/r/onlyoffice/documentserver
- **Docs:** https://helpcenter.onlyoffice.com/docs/installation/docs-community-install-docker.aspx
- **GitHub (CE):** https://github.com/ONLYOFFICE/DocumentServer
- **Config reference:** https://github.com/ONLYOFFICE/DocumentServer/blob/master/Docker/README.md
- **License:** AGPL-3.0
- **Origin:** Latvia · Ascensio System SIA · EU
- **Based on version:** `9.3.1.2` (Document Server Community)
- **Last checked:** 2026-06-14

## What we use

- Official `onlyoffice/documentserver` image, pinned to `9.3.1.2`
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

`APP_TAG` is pinned to an exact patch release (`9.3.1.2`). Do not use floating tags such as `9.3`, `9`, or `latest` — they pick up upstream changes silently and make rollback ambiguous.

### Why 9.3.1.2 and not 9.4.x

9.4.0 (released 2026-05-19) consolidated all internal processes into a single Node.js process and **removed the bundled RabbitMQ and internal database**. This is a large architectural change. 9.3.1.2 uses the same internal stack as 8.3.x (PostgreSQL + Redis + RabbitMQ bundled) and is a well-settled release. Test 9.4.x separately before moving to it in production, paying particular attention to:

- Seafile and Nextcloud iframe embedding and JWT handshake
- First-boot behaviour (no RabbitMQ init messages expected in 9.4)
- Data volume compatibility (the internal DB format changes between 9.3 and 9.4)

## Upgrade checklist

Before upgrading, back up both volumes (documents/fonts and logs):

```bash
tar czf onlyoffice-data-$(date +%Y%m%d).tgz ./volumes/data
tar czf onlyoffice-logs-$(date +%Y%m%d).tgz ./volumes/logs
```

1. Read the release notes: https://github.com/ONLYOFFICE/DocumentServer/releases
2. If users are active, disconnect them first:
   ```bash
   docker exec ${CONTAINER_NAME_APP} documentserver-prepare4shutdown.sh
   # Wait up to 5 minutes for sessions to close
   ```
3. Bump `APP_TAG` in `.env`
4. `docker compose pull && docker compose up -d`
5. First start can take 1–5 minutes (PostgreSQL init or migration). Watch:
   ```bash
   docker compose logs app --follow
   # Look for: "ONLYOFFICE Document Server Community Edition vX.Y.Z is up and running"
   ```
6. Verify health:
   ```bash
   curl -fsSI https://<APP_TRAEFIK_HOST>/healthcheck   # expect 200
   curl -fsSI https://<APP_TRAEFIK_HOST>/web-apps/apps/api/documents/api.js   # expect 200
   ```
7. Open a `.docx` from Seafile (and Nextcloud if enabled) and confirm:
   - Editor loads in iframe — no `X-Frame-Options` error in the browser console
   - No `Token is invalid` JWT error in the browser console
   - Save and close — changes persist back to Seafile/Nextcloud
   - Multi-user: collaborative cursor visible when two sessions are open

### Rollback

Revert `APP_TAG` in `.env`, restore the volume backup, then `docker compose pull && docker compose up -d`:

```bash
tar xzf onlyoffice-data-YYYYMMDD.tgz
# edit .env: APP_TAG=<previous>
docker compose pull && docker compose up -d
```

Note: if an internal PostgreSQL schema migration ran, it is not automatically reversible — restoring the volume backup is required.

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
