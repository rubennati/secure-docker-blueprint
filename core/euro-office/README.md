# Euro-Office

> **Status: 🚧 Preview** — v9.3.2 · 2026-07-26 · modeled on `core/onlyoffice/`, **not yet verified on a live server**

EU-governed, open-source **fork of OnlyOffice Document Server** — in-browser editing of
docx / xlsx / pptx / pdf / odt for Seafile, Nextcloud, or any WOPI-compatible app. Backed by
**Nextcloud, IONOS, XWiki, Proton** and others for digital sovereignty; created over concerns
about Russian influence on upstream OnlyOffice.

Because it forks the same Document Server, it is a **drop-in replacement** for
[`core/onlyoffice/`](../onlyoffice/) — same JWT + iframe integration, same API path. Run one or the
other, not both, per consuming app.

## Architecture

| Service | Image | Purpose |
|---------|-------|---------|
| `app` | `ghcr.io/euro-office/documentserver:v9.3.2` | Document editing server (port 80, bundles its own DB/queue) |

No `_FILE` support (OnlyOffice lineage) → `config/entrypoint.sh` injects `JWT_SECRET` from a Docker
Secret, then execs the DS start script. Embedded in iframes → an iframe-friendly middleware chain
(CSP `frame-ancestors`) replaces the standard `sec-*` chains (which set `X-Frame-Options: DENY`).

## Setup

```bash
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, EURO_OFFICE_ALLOWED_ORIGINS (the apps that embed it), TZ

mkdir -p .secrets
openssl rand -base64 30 | tr -d '\n' > .secrets/jwt_secret.txt

docker compose up -d
# Consuming app (Seafile/Nextcloud) uses the SAME jwt_secret and:
#   https://<APP_TRAEFIK_HOST>/web-apps/apps/api/documents/api.js
```

## Local testing

```bash
cp .env.local.example .env.local
docker compose -f docker-compose.local.yml --env-file .env.local up -d
# http://localhost:8080/healthcheck → "true"   (JWT disabled locally — never in prod)
```

## Verify on first deploy (Preview → Ready gate)

Modeled on the proven OnlyOffice config, but the fork image has not been run here. Confirm:

- [ ] `docker compose up -d` — container healthy; `GET /healthcheck` returns `true`
- [ ] Entrypoint path parity — the image still starts via `/app/ds/run-document-server.sh` (fork of OnlyOffice; verify if boot fails)
- [ ] `JWT_SECRET` injected — no JWT value in `docker inspect euro-office-app`; JWT enforced (requests without a valid token are rejected)
- [ ] End-to-end — a document opens and saves from Seafile/Nextcloud using the shared secret
- [ ] `EXAMPLE_ENABLED` is off — `https://<host>/example/` is not reachable

## Backup

| | |
|---|---|
| **Database** | None in this stack. |
| **State** | `.secrets/jwt_secret.txt` — shared with the embedding application |
| **Reproducible** | `./volumes/data` (document cache) · `./volumes/logs` |
| **Quiescing** | Not applicable. |

Documents live in the application that embeds this document server — Nextcloud,
Seafile — and are backed up there. What is cached here is a working copy.

The JWT secret is the only thing whose loss is felt: both sides have to hold the
same value, so regenerating it means updating the embedding application too.
Editing stays broken until they match, and the error surfaces there rather than
here.

## Details

- [UPSTREAM.md](UPSTREAM.md) — source, upgrade checklist, deviations
- Alternative: [`core/onlyoffice/`](../onlyoffice/) — the upstream OnlyOffice Document Server
