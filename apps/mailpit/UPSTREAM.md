# Upstream Reference

## Source

- **Image:** https://hub.docker.com/r/axllent/mailpit
- **GitHub:** https://github.com/axllent/mailpit
- **Docs:** https://mailpit.axllent.org/docs/
- **License:** MIT
- **Decision facts checked:** not yet
- **Origin:** New Zealand · Ralph Slooten (axllent) · non-EU
- **Domain:** Developer tools
- **Role:** SMTP sink that catches every outgoing message and shows it, delivering nothing
- **Last verified:** 2026-11-08 (1.33.1) — lab host (VM), IPv4 LAN: moved from v1.33.0, a message sent with `mailpit sendmail` read through the API behind the UI password, kept after `down`/`up`, the refused client answered `403`; the README's password step corrected (docs/labs/stack-refresh/2026-11-08-results.md)

## What we use

- Official image, pinned tag
- Configuration entirely through `MP_*` environment variables, the documented
  equivalents of the CLI flags (`mailpit --help`)

## Architecture

```text
VPN client → Traefik (TLS, 443) → mailpit :8025  (web UI, API)
any stack on proxy-public ────────→ mailpit :1025  (SMTP)
```

## What we changed and why

| Change | Reason |
|--------|--------|
| `user: USERMAP_UID`, `read_only: true`, `cap_drop: ALL` | The image starts as root but needs nothing from it — both ports are above 1024 and the only write goes to `/data` |
| `MP_SMTP_AUTH_ACCEPT_ANY` + `MP_SMTP_AUTH_ALLOW_INSECURE` | Applications refuse to boot without SMTP credentials; the sink accepts whatever they send, over plaintext |
| `MP_SMTP_DISABLE_RDNS` | Reverse lookups on Docker-internal addresses only add latency |
| `MP_DISABLE_VERSION_CHECK` | Upstream asks the GitHub API for newer releases; version tracking is the operator's job here — `docs/sovereignty/data-egress.md` |
| `MP_ALLOWED_HOSTS` = the Traefik hostname | The API and UI refuse requests from other containers by Host header; Traefik and the localhost healthcheck pass |
| Traefik labels, `access-vpn`, `limit-standard` | The UI shows every message the stacks send, including password-reset links; a first load is about ten requests |
| Healthcheck repeated in the compose file | The image declares `/mailpit readyz` itself; repeating it makes "healthy" visible |
| `memory: 128m` | Idles at 13 MB with a thousand messages stored; the store is on disk |

## Version notes

- Moved to `v1.33.1` on 2026-11-08 and run on a host. A patch
  release; its notes name no configuration change.
- Moved to `v1.33.0` on 2026-11-05 (released 2026-10-31), not run on a host at
  this tag; `Last verified` stays at v1.31.1. No breaking change, removed option
  or migration in v1.31.2 to v1.33.0. Security: v1.31.2 limits thumbnail
  decoding to one frame (GHSA-2vgv-6hcp-mf43, memory exhaustion through animated
  images); v1.32.0 replaces the EXIF library whose crafted images could hang the
  thumbnail generator (GHSA-379p-g4f4-hq5h), strips `<base>` and meta-refresh
  tags from the HTML view, and caps SMTP, POP3 and HTTP at 1000 concurrent
  connections each. v1.31.5 tightens SMTP parsing (AUTH in `MAIL FROM`,
  parameter spacing), which a sender with a malformed command now sees refused.
  New in v1.33.0 and off unless set: a Subject prefix for relay and forward, and
  an Rspamd spam check. `MP_ALLOWED_HOSTS` and the other `MP_*` settings here
  are unchanged. https://github.com/axllent/mailpit/releases

## Upgrade checklist

1. Read the release notes: https://github.com/axllent/mailpit/releases
2. Bump `APP_TAG` in `.env.example` and `.env`
3. `docker compose pull && docker compose up -d`
4. Send a message from any stack and confirm it appears in the UI

No data migration: the store is disposable.

## Useful commands

```bash
docker compose logs mailpit --follow
# API: newest messages
docker compose exec mailpit wget -qO- http://127.0.0.1:8025/api/v1/messages
# Empty the inbox
docker compose exec mailpit wget -qO- --method=DELETE http://127.0.0.1:8025/api/v1/messages
```
