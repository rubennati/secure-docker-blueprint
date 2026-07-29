# Upstream Reference

## Source

- **Upstream GitHub:** https://github.com/euro-office/DocumentServer
- **Organization:** https://github.com/euro-office (Nextcloud, IONOS, XWiki, Proton, …)
- **Image registry:** `ghcr.io/euro-office/documentserver`
- **Forked from:** OnlyOffice Document Server (Ascensio System) — EU-governed, sovereignty-focused fork
- **License:** AGPL-3.0 (as OnlyOffice Document Server)
- **Based on version:** `v9.3.2`
- **Last verified:** — (config authored 2026-07-26; not yet run on a live server)

## What we use

- `ghcr.io/euro-office/documentserver:v9.3.2` — single container (bundles its own DB + queue)
- Custom `config/entrypoint.sh` to inject `JWT_SECRET` from a Docker Secret (no `_FILE` support)

## What we changed vs. upstream `docker run`

| Change | Reason |
|--------|--------|
| Modeled 1:1 on `core/onlyoffice/` | Euro-Office is an OnlyOffice DS fork — drop-in, same integration |
| Custom entrypoint for JWT secret | No `_FILE` support; wrapper exports `JWT_SECRET`, execs `/app/ds/run-document-server.sh` |
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

- **Not yet live-verified** — see the README "Verify on first deploy" gate before marking ✅
- **Entrypoint path assumes upstream parity** — `/app/ds/run-document-server.sh` (OnlyOffice path); confirm on the fork image
- **Young project** — smaller release history than OnlyOffice; watch releases closely
