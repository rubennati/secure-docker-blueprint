# Upstream Reference

## Source

- **Image:** https://hub.docker.com/r/axllent/mailpit
- **GitHub:** https://github.com/axllent/mailpit
- **Docs:** https://mailpit.axllent.org/docs/
- **License:** MIT
- **Origin:** New Zealand · Ralph Slooten (axllent) · non-EU
- **Based on version:** `v1.31.1`
- **Last verified:** 2026-09-07 (v1.31.1)

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
| Traefik labels, `acc-tailscale`, `sec-3` | The UI shows every message the stacks send, including password-reset links; a first load is about ten requests |
| Healthcheck repeated in the compose file | The image declares `/mailpit readyz` itself; repeating it makes "healthy" visible |
| `memory: 128m` | Idles at 13 MB with a thousand messages stored; the store is on disk |

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
