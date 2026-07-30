# Collabora Online (CODE)

LibreOffice-based online office server — the **lightweight** document-editing option: ~1 GB idle
(single stateless container) vs ~4 GB for OnlyOffice / Euro-Office (which bundle Postgres, RabbitMQ,
Redis, Nginx). Embedded via WOPI by Seafile / Nextcloud.

Pick per need: **OnlyOffice / [Euro-Office](../euro-office/)** for MS-Office-native fidelity, or
**Collabora** when you want a much smaller footprint (LibreOffice engine).

## Architecture

| Service | Image | Purpose |
|---------|-------|---------|
| `app` | `collabora/code:26.04.2.4.1` | Document editing server (port 9980, stateless) |

No database, no persistent volume. Embedded in iframes → an iframe-friendly middleware chain
(CSP `frame-ancestors`) replaces the standard `sec-*` chains. TLS is terminated at Traefik
(`ssl.termination=true`); the admin console is off by default.

## Setup

```bash
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, COLLABORA_ALIASGROUP (regex of the embedding host,
#       escape dots), COLLABORA_ALLOWED_ORIGINS (the same host(s), plain form)

docker compose up -d
# In Nextcloud: Office app → "Use your own server" → https://<APP_TRAEFIK_HOST>
```

## Local testing

```bash
cp .env.local.example .env.local
docker compose -f docker-compose.local.yml --env-file .env.local up -d
curl http://localhost:9980/   # → "OK"
```

## Verify on first deploy (Preview → Ready gate)

- [ ] Container starts; `http://<host>/` (or local `:9980/`) returns `OK`
- [ ] **LibreOffice sandbox starts** — if boot fails on the jail/chroot, relax security: the
      `MKNOD` cap is present; you may also need to drop `no-new-privileges:true` on some hosts
- [ ] `aliasgroup1` matches your Nextcloud/Seafile host exactly (regex, escaped dots, `:443`)
- [ ] A document opens and saves from Nextcloud/Seafile through Collabora
- [ ] Admin console is not publicly reachable (kept off by default)

## Backup

| | |
|---|---|
| **Database** | None. |
| **State** | None. Configuration comes from `.env` and the entrypoint; documents live in the application that embeds this server, never here. |
| **Reproducible** | everything — the container is disposable |
| **Quiescing** | Not applicable. |

Nothing to back up. Restoring means starting the container again with the same
`.env`, including the JWT secret shared with the embedding application — if that
value changes, the integration stops working until both sides agree again.

## Details

- [UPSTREAM.md](UPSTREAM.md) — source, upgrade checklist, deviations
- Alternatives: [`core/onlyoffice/`](../onlyoffice/), [`core/euro-office/`](../euro-office/)
