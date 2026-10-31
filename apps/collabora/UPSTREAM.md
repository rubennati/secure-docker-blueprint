# Upstream Reference

## Source

- **Upstream GitHub:** https://github.com/CollaboraOnline/online
- **Image registry:** `collabora/code` (Docker Hub)
- **Docs:** https://sdk.collaboraonline.com/docs/installation/CODE_Docker_image.html
- **Vendor:** Collabora Productivity (Cambridge, UK) — LibreOffice-based
- **License:** MPL-2.0
- **Decision facts checked:** not yet
- **Origin:** UK · Collabora Productivity Ltd · non-EU
- **Domain:** Documents and e-signature
- **Role:** Office document editing server based on LibreOffice
- **Based on version:** `26.04.5.2.1`
- **Last verified:** — (config authored 2026-07-26; not yet run on a live server)

## What we use

- `collabora/code:26.04.3.2.1` — single stateless container (no DB, no volume)
- TLS terminated at Traefik (`ssl.termination=true`, `ssl.enable=false`)

## What we changed vs. upstream `docker run`

| Change | Reason |
|--------|--------|
| `cap_drop: ALL` + `cap_add: MKNOD` | Baseline drop; MKNOD is required for Collabora's per-document LibreOffice jail |
| `no-new-privileges:true` | Baseline — flagged in README as the first thing to relax if the sandbox fails |
| Iframe-friendly Traefik middleware (CSP `frame-ancestors`) | Standard `sec-*` chains set `X-Frame-Options: DENY`, blocking WOPI embedding |
| `X-Forwarded-Proto=https` middleware | Required with `ssl.termination=true` |
| Admin console left OFF | The `/browser/.../admin` console is an attack surface; enable + restrict deliberately |
| `deploy.resources` (memory/cpus/pids) | Bound the container; ~50–100 MB per open document above idle |
| TCP healthcheck on 9980 (bash `/dev/tcp`) | No guaranteed curl in the image |

## Version notes

- Moved to `26.04.5.2.1` on 2026-10-31, not run at this tag. The 26.04 line's
  update notes on collaboraoffice.com were not reachable from the session that
  moved the pin; what was read is the Helm chart's tag history (26.04.4.2.1 on
  2026-09-24, 26.04.5.1.1 on 2026-10-09, 26.04.5.2.1 on 2026-10-23) and Docker
  Hub, which carries the tag. Breaking changes, `coolwsd.xml` changes and
  advisories in the range are therefore not checked — read
  https://www.collaboraonline.com/release-notes/ before a host run.

## Upgrade checklist

1. Check current tags: https://hub.docker.com/r/collabora/code/tags
2. Bump `APP_TAG` in `.env` (prefer a digest pin — see `apps/caldiy`)
3. `docker compose pull && docker compose up -d`
4. Re-check a consuming app (Nextcloud/Seafile) opens and saves a document

## Known limitations

- **Not yet live-verified** — see the README "Verify on first deploy" gate before marking ✅
- **Sandbox vs hardening** — `no-new-privileges` may need relaxing depending on host kernel/seccomp
- **LibreOffice format fidelity** — differs from OnlyOffice's MS-native rendering (by design)
