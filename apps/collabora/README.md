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
| `collabora-app` | `collabora/code:26.04.6.1.1` | Document editing server (port 9980, stateless) |

No database, no persistent volume. Embedded in iframes → `headers-application-owned` with the stack's own CSP
(`frame-ancestors`) instead of `headers-standard`, which sets `X-Frame-Options: DENY`. TLS is terminated at Traefik
(`ssl.termination=true`); the admin console is off by default. The image has no shell and no
`curl`: the healthcheck is coolwsd's own probe — a shell-based test never ran, the container stayed
`unhealthy`, and Traefik leaves an unhealthy container out of its routing (lab host).

**`/cool/convert-to` is closed on the public route.** It converts any uploaded file and asks for
no WOPI token, and Collabora admits it from private addresses — which includes Traefik, so on an
`access-public` route it would be a conversion service for anyone. A second router of higher
priority answers the path with `access-blocked`. The editor does not use it; Nextcloud's previews
of office files do, and they reach Collabora by its internal address instead (the Nextcloud
README, "Office servers behind a closed route", `office-collabora.yml`).

## Setup

```bash
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, COLLABORA_ALIASGROUP (regex of the embedding host,
#       escape dots), COLLABORA_ALLOWED_ORIGINS (the same host(s), plain form)

docker compose up -d
# In Nextcloud: the connector settings in its README, "Office servers behind a closed route"
```

## Try it locally

```bash
cp .env.local.example .env.local
docker compose -f docker-compose.local.yml --env-file .env.local up -d
curl http://localhost:9980/   # → "OK"
docker compose -f docker-compose.local.yml --env-file .env.local down
```

## Verify on first deploy

- [x] Container starts and reports healthy through coolwsd's own probe (lab host)
- [x] **LibreOffice sandbox starts** with `MKNOD` and `no-new-privileges:true` — not the chroot jail: coolwsd
      falls back to a Landlock jail and editing works (lab host; "Sandbox" below)
- [x] `aliasgroup1` matches the Nextcloud host exactly (regex, escaped dots, `:443`); a host outside the groups is refused
- [x] Behind Nextcloud's closed access policy, a `.docx` opens, is edited, saves and reopens through
      Collabora: `office.yml` and `office-collabora.yml`, the callback and the internal address set with
      `occ richdocuments:activate-config`, `NC_OVERWRITECONDADDR` so the template presets are fetched over
      nginx, and `aliasgroup1` admitting the callback host (the Nextcloud README, "Office servers behind a
      closed route"; lab host)
- [x] `/cool/convert-to` answers `403` on the public route, also to a trusted client; Nextcloud's `.docx`
      previews are rendered through the internal address (lab host)
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

<!-- findings:start — generated by scripts/ci/lifecycle-report.py from upstream-status.json; edit the text around it -->

**Findings in the upstream images** at the pin `26.04.6.1.1` — the newest upstream release. Scanned 2026-11-09; counted are findings with a published fix, as CRITICAL · HIGH. They come with the images as upstream publishes them.

| Image | Base system | Libraries | Programs |
|---|---|---|---|
| `collabora/code:26.04.6.1.1` | — | 1 · 1 | — |

<!-- findings:end -->

The image, `collabora/code:26.04.6.1.1`, carries one CRITICAL finding in the DOMPurify copy bundled with the browser editor (GHSA-cg2g-xh64-v4q7). It is the newest release.

**Risk:** the flaw only applies to a specific sanitizer mode; whether the editor uses it has not been checked. Move to the next release.

## Details

- [UPSTREAM.md](UPSTREAM.md) — source, upgrade checklist, deviations
- Alternatives: [`apps/onlyoffice/`](../onlyoffice/), [`apps/euro-office/`](../euro-office/)
