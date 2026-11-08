# Collabora Online (CODE)

LibreOffice-based online office server — the **lightweight** document-editing option: a single
stateless container, measured at about 400 MiB idle and 650 MiB with three editors open, against
about 1.5–2 GB for OnlyOffice and Euro-Office, which bundle Postgres, RabbitMQ, Redis and nginx
(lab host, `docs/labs/ingress/2026-11-01-results.md`, "Office servers"). Embedded via WOPI
by Nextcloud's `richdocuments`; Seafile supports it too, with settings this blueprint does not ship.

Pick per need: **OnlyOffice / [Euro-Office](../euro-office/)** for MS-Office-native fidelity, or
**Collabora** when you want a much smaller footprint (LibreOffice engine).

Project, source, licence and origin: [`UPSTREAM.md`](UPSTREAM.md).

## Architecture

| Service | Image | Purpose |
|---------|-------|---------|
| `collabora-app` | `collabora/code:26.04.5.2.1` | Document editing server (port 9980, stateless) |

No database, no persistent volume. Embedded in iframes → `headers-application-owned` with the stack's own CSP
(`frame-ancestors`) instead of `headers-standard`, which sets `X-Frame-Options: DENY`. TLS is terminated at Traefik
(`ssl.termination=true`); the admin console is off by default. The image has no shell and no
`curl`: the healthcheck is coolwsd's own probe — a shell-based test never ran, the container stayed
`unhealthy`, and Traefik leaves an unhealthy container out of its routing (lab host).

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

- [x] Container starts and reports healthy through coolwsd's own probe (lab host)
- [x] **LibreOffice sandbox starts** with `MKNOD` and `no-new-privileges:true` — not the chroot jail: coolwsd
      falls back to a Landlock jail and editing works (lab host; "Sandbox" below)
- [x] `aliasgroup1` matches the Nextcloud host exactly (regex, escaped dots, `:443`); a host outside the groups is refused
- [x] A document opens and saves from Nextcloud through Collabora — only while Nextcloud's public name is
      reachable from the container: behind its closed route the document does not open (open finding)
- [ ] Behind a closed access policy, Nextcloud hands Collabora its internal address
      (`occ richdocuments:activate-config --callback-url=http://<nginx>`) and joins this stack's edge network
      with its `office.yml`; `aliasgroup1` admits that callback host as well (the Nextcloud README, "Office
      servers behind a closed route") — the WOPI calls take it, but a template preset is fetched at Nextcloud's public
      name and refused, and the document does not open (lab host; open)
- [x] Admin console answers 401 (off by default)

## Sandbox

What coolwsd 26.04.5.2.1 logged under this stack's settings (`cap_drop: ALL`, `MKNOD`,
`no-new-privileges:true`, Docker's default seccomp profile) on the lab host:

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

## Open findings

The image, `collabora/code:26.04.5.2.1`, carries one CRITICAL finding in the DOMPurify copy bundled with the browser editor (GHSA-cg2g-xh64-v4q7). It is the newest release.

**Risk:** the flaw only applies to a specific sanitizer mode; whether the editor uses it has not been checked. Move to the next release.

## Details

- [UPSTREAM.md](UPSTREAM.md) — source, upgrade checklist, deviations
- Alternatives: [`apps/onlyoffice/`](../onlyoffice/), [`apps/euro-office/`](../euro-office/)
