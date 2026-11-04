# Upstream Reference

## Source

- **Upstream GitHub:** https://github.com/euro-office/DocumentServer
- **Organization:** https://github.com/euro-office (Nextcloud, IONOS, XWiki, Proton, …)
- **Image registry:** `ghcr.io/euro-office/documentserver`
- **Forked from:** OnlyOffice Document Server (Ascensio System) — EU-governed, sovereignty-focused fork
- **License:** AGPL-3.0 (as OnlyOffice Document Server)
- **Decision facts checked:** not yet
- **Origin:** EU · euro-office consortium (Nextcloud, IONOS, XWiki, Proton) · EU
- **Domain:** Documents and e-signature
- **Role:** EU-governed fork of OnlyOffice, a drop-in document editing server
- **Based on version:** `v9.3.4-hotfix.1`
- **Last verified:** 2026-11-02 (v9.3.4-hotfix.1) — step 8 lab host on its edge network, after correcting the entrypoint and paths: DOCX, XLSX and PPTX opened, edited, saved and reopened through Nextcloud's OnlyOffice connector (`office.yml`) and Seafile CE and Pro, switched from OnlyOffice by settings alone; the command service and conversion refuse a missing or foreign token; the admin panel stays off; resources and timings measured — headless Chromium, no official client (docs/labs/ingress/2026-11-01-results.md)

## What we use

- `ghcr.io/euro-office/documentserver:v9.3.4-hotfix.1` — single container (bundles its own DB + queue)
- Custom `config/entrypoint.sh` to inject `JWT_SECRET` from a Docker Secret (no `_FILE` support)

## What we changed vs. upstream `docker run`

| Change | Reason |
|--------|--------|
| Modeled 1:1 on `apps/onlyoffice/` | Euro-Office is an OnlyOffice DS fork — drop-in, same integration |
| Custom entrypoint for JWT secret | No `_FILE` support; wrapper exports `JWT_SECRET`, creates the log directories the log volume hides, execs the image's `/entrypoint.sh` |
| Data and logs at `/var/www/euro-office/Data` and `/var/log/euro-office` | The fork's own paths — OnlyOffice's `/var/www/onlyoffice/Data` persisted nothing |
| `no-new-privileges:true` | Security baseline |
| Iframe-friendly Traefik middleware (CSP `frame-ancestors`) | Standard `sec-*` chains set `X-Frame-Options: DENY`, blocking Seafile/Nextcloud embedding |
| `X-Forwarded-Proto=https` middleware | DS behind Traefik TLS termination generates `http://` URLs otherwise (Mixed Content) |
| `EXAMPLE_ENABLED` left off | The demo server is an unauthenticated endpoint |

## Upgrade checklist

1. Watch [Euro-Office DocumentServer releases](https://github.com/euro-office/DocumentServer/releases)
2. Read the changelog (it tracks OnlyOffice DS versions — 9.x line)
3. Bump `APP_TAG` in `.env` (prefer a digest pin — see `apps/caldiy`)
4. `docker compose pull && docker compose up -d`
5. Re-check a consuming app (Seafile/Nextcloud) opens and saves a document

## Known limitations

- **Not OnlyOffice's file layout** — the image starts with `/entrypoint.sh` and keeps data and logs under `euro-office` paths; the stack copied OnlyOffice's and the container exited 127 in a restart loop until corrected (step 8 lab host, 2026-11-02)
- **Young project** — smaller release history than OnlyOffice; watch releases closely
