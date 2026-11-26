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
- **Last verified:** 2026-11-08 (1.33.1) — over IPv4: moved from v1.33.0, a message sent with `mailpit sendmail` read through the API behind the UI password, kept after `down`/`up`, the refused client answered `403` (docs/labs/stack-refresh/2026-11-08-results.md)

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

- Moved to `v1.33.1` on 2026-11-08. A patch
  release; its notes name no configuration change.
- Moved to `v1.33.0` on 2026-11-05 (released 2026-10-31). No breaking change, removed option
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
- Moved to `v1.34.0` on 2026-11-23 (released 2026-11-17). It fixes GHSA-v887-64wg-qqc9 (medium):
  one message with an unparseable media type carrying an RFC 2231 parameter crashed the SMTP
  server, without authentication, from v1.33.1 on. It reaches this stack: port 1025 accepts any
  login from every container on `proxy-public`, so one sending stack could stop the sink for
  all. The release also hardens message, header, search, thumbnail and
  webhook handling against memory and CPU exhaustion. Breaking, checked against this stack:
  - Flags and variables deprecated for two years are removed (`MP_DATA_FILE`,
    `MP_UI_SSL_*`, `MP_SMTP_SSL_*`, `MP_SMTP_TLS_REQUIRED`, `MP_DISABLE_HTML_CHECK`,
    `MP_STRICT_RFC_HEADERS` and others) and a relay config with `recipient-allowlist` stops the
    start until renamed to `allowed-recipients`. Every `MP_*` variable this stack sets still
    exists, and it ships no relay config.
  - Ports, `return-path`, `--max-age`, integer variables and empty credentials are checked at
    start and refused if invalid; `MP_MAX_MESSAGES` is an integer, `MP_UI_AUTH_FILE` a
    populated htpasswd file.
  - The send API answers `400`, `413` and `503` in new cases; a message carries at most 100
    tags.
  With the database, the UI password file, an empty `MP_LABEL` and `MP_ALLOWED_HOSTS` set as
  in production, a message stored on v1.33.1 is still listed on v1.34.0, the API without the
  password answers `401`, and a message with an RFC 2231 media-type parameter is accepted
  (local stack with an override, 2026-11-23). Sources:
  https://github.com/axllent/mailpit/releases/tag/v1.34.0,
  https://github.com/axllent/mailpit/security/advisories/GHSA-v887-64wg-qqc9

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
