# Upstream Reference

## Source

- **Image:** https://hub.docker.com/r/onlyoffice/documentserver
- **Docs:** https://helpcenter.onlyoffice.com/docs/installation/docs-community-install-docker.aspx
- **GitHub (CE):** https://github.com/ONLYOFFICE/DocumentServer
- **Config reference:** https://github.com/ONLYOFFICE/DocumentServer/blob/master/Docker/README.md
- **License:** AGPL-3.0
- **Decision facts checked:** not yet
- **Origin:** Latvia · Ascensio System SIA · EU
- **Domain:** Documents and e-signature
- **Role:** Document editing server for Nextcloud, Seafile and similar
- **Based on version:** `10.0.0` (Document Server Community)
- **Last verified:** 2026-11-02 (9.4.0) — step 8 lab host on its edge network: DOCX, XLSX and PPTX opened, edited, saved and reopened through Nextcloud (`office.yml`) and Seafile CE and Pro (`onlyoffice-callback.yml`), and from a JWT-signed editor page; the command service and conversion refuse a missing or foreign token; resources and timings measured — headless Chromium, no official client (docs/labs/ingress/2026-11-01-results.md). Earlier: `Last checked` 2026-06-14

## What we use

- Official `onlyoffice/documentserver` image, pinned to `10.0.0`
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

## Operational notes

### Updating `ONLYOFFICE_ALLOWED_ORIGINS`

`ONLYOFFICE_ALLOWED_ORIGINS` is used in a Traefik label to build the `frame-ancestors`
CSP directive. Labels are applied at container creation time, not on restart.

After changing `ONLYOFFICE_ALLOWED_ORIGINS` in `.env`:

```bash
# On the OnlyOffice server — restart alone is NOT sufficient:
docker compose up -d --force-recreate
```

A plain `docker compose restart` leaves the old Traefik label (and therefore the old CSP)
in place. The browser will continue to block the iframe embed for any origin not in the
original CSP until the container is recreated.

## Tag pinning

`APP_TAG` is pinned to an exact patch release (`10.0.0`). Do not use floating tags such as `10.0`, `10`, or `latest` — they pick up upstream changes silently and make rollback ambiguous.

### Why 9.3.1.2 and not 9.4.x

9.4.0 (released 2026-05-19) consolidated all internal processes into a single Node.js process and **removed the bundled RabbitMQ and internal database**. This is a large architectural change. 9.3.1.2 uses the same internal stack as 8.3.x (PostgreSQL + Redis + RabbitMQ bundled) and is a well-settled release. Test 9.4.x separately before moving to it in production, paying particular attention to:

- Seafile and Nextcloud iframe embedding and JWT handshake
- First-boot behaviour (no RabbitMQ init messages expected in 9.4)
- Data volume compatibility (the internal DB format changes between 9.3 and 9.4)

## Version notes

- Moved `onlyoffice/documentserver` to `10.0.0` on 2026-11-05 (released 2026-10-12;
  `10.0.0.1` is the same release with the build number), a major release, not run on
  a host at this tag. Security: the release fixes a long list of vulnerabilities,
  among them SSRF in the WOPI endpoints, co-editing session hijacking over WOPI,
  path traversal in the WOPI new-file template handler, arbitrary file write when
  extracting archives during conversion, local file read during EPUB conversion,
  creating `runtime.json` through Document Builder (CVE-2026-110385), an editor
  token being usable for Document Builder, several XSS and macro-sandbox bypasses,
  memory-safety bugs in the DOC, XLS, PPT, PDF, WMF and EMF+ converters, and
  privilege escalation through `documentserver-flush-cache`. Behaviour changes that
  touch this stack: (1) WOPI now needs an explicit `allow <host>` rule per WOPI host
  in the IP filter, `allow *` is not enough; the image sets it from
  `IP_FILTER_RULES` (semicolon-separated `allow <address>` / `deny <address>`, no
  CIDR, replaces the existing rules when set). `WOPI_ENABLED` stays `true`, but no
  rule is set, so WOPI clients are refused until one is added; the Nextcloud and
  Seafile integrations this blueprint was verified with use the Document Server API
  with the JWT secret, not WOPI, so they are not affected. (2) `/converter`,
  `/docbuilder` and `/command` no longer accept a token taken from an editor
  configuration; integrators must sign these requests with the shared secret, as
  the Nextcloud connector does. (3) Only the `log4js` level can be changed through
  `runtime.json`. (4) The deprecated `editorConfig.customization` parameters
  `reviewDisplay`, `trackChanges` and `showReviewChanges` are ignored. (5) The image's
  helper commands drop the `.sh` suffix (`documentserver-prepare4shutdown`,
  `documentserver-jwt-status`); the checklist below uses the new name. (6) Service
  stderr is merged into stdout instead of a separate `err.log`. The entrypoint
  `/app/ds/run-document-server.sh`, port 80, `JWT_SECRET`, `JWT_ENABLED` and
  `/healthcheck` are unchanged, so `config/entrypoint.sh` and the compose files keep
  their configuration. Upstream's Docker repository has no release tags; the image
  details above were read from its default branch, whose changes up to the release
  date are in this tag. Back up both volumes before the first start. Sources:
  https://github.com/ONLYOFFICE/DocumentServer/blob/master/CHANGELOG.md#1000,
  https://github.com/ONLYOFFICE/Docker-DocumentServer (README, `run-document-server.sh`)

## Upgrade checklist

Before upgrading, back up both volumes (documents/fonts and logs):

```bash
tar czf onlyoffice-data-$(date +%Y%m%d).tgz ./volumes/data
tar czf onlyoffice-logs-$(date +%Y%m%d).tgz ./volumes/logs
```

1. Read the release notes: https://github.com/ONLYOFFICE/DocumentServer/releases
2. If users are active, disconnect them first:

   ```bash
   docker exec ${CONTAINER_NAME_APP} documentserver-prepare4shutdown
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
