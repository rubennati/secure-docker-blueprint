# Collabora Online (CODE)

LibreOffice-based online office server — the **lightweight** document-editing option: ~1 GB idle
(single stateless container) vs ~4 GB for OnlyOffice / Euro-Office (which bundle Postgres, RabbitMQ,
Redis, Nginx). Embedded via WOPI by Seafile / Nextcloud.

Pick per need: **OnlyOffice / [Euro-Office](../euro-office/)** for MS-Office-native fidelity, or
**Collabora** when you want a much smaller footprint (LibreOffice engine).

## Architecture

| Service | Image | Purpose |
|---------|-------|---------|
| `collabora-app` | `collabora/code:26.04.3.2.1` | Document editing server (port 9980, stateless) |

No database, no persistent volume. Embedded in iframes → `headers-application-owned` with the stack's own CSP
(`frame-ancestors`) instead of `headers-standard`, which sets `X-Frame-Options: DENY`. TLS is terminated at Traefik
(`ssl.termination=true`); the admin console is off by default. The image has no shell and no
`curl`: the healthcheck is coolwsd's own probe — a shell-based test never ran, the container stayed
`unhealthy`, and Traefik leaves an unhealthy container out of its routing (step 8 lab host).

## Setup

```bash
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, COLLABORA_ALIASGROUP (regex of the embedding host,
#       escape dots), COLLABORA_ALLOWED_ORIGINS (the same host(s), plain form)

docker compose up -d
# In Nextcloud: Office app → "Use your own server" → https://<APP_TRAEFIK_HOST>
```

## Try it locally

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
- [ ] Behind a closed access policy, Nextcloud hands Collabora its internal address
      (`wopi_callback_url`, the Nextcloud README, "Office servers behind a closed route")
- [ ] Admin console is not publicly reachable (kept off by default)

## Sandbox

What coolwsd 26.04.5.2.1 logged under this stack's settings (`cap_drop: ALL`, `MKNOD`,
`no-new-privileges:true`, Docker's default seccomp profile) on the step 8 lab host:

- It could not create a user namespace (`unshare` refused, EPERM; it names seccomp as the
  likely cause), and `coolmount` needs `CAP_SYS_ADMIN`, so no mount namespace.
- `coolforkit-caps`, which builds the chroot jails, could not start ("Operation not permitted").
- It started `coolforkit-ns`, ran LibreOffice from its template "without chroot jail setup",
  and logged "Landlock jail successfully created". Documents opened, edited and saved.
- It found no proof key (`/etc/coolwsd/proof_key`), so its WOPI requests carry no proof signature.

That is what was observed, not a security assessment: how the Landlock jail compares with the
chroot jail, and whether Nextcloud or Seafile would check a proof signature, were not examined.
The settings are unchanged.

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
- Alternatives: [`apps/onlyoffice/`](../onlyoffice/), [`apps/euro-office/`](../euro-office/)
