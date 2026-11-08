# Upstream Reference

## Source

- **Project:** https://gatus.io
- **GitHub:** https://github.com/TwiN/gatus
- **Docker Hub:** https://hub.docker.com/r/twinproduction/gatus
- **License:** Apache-2.0
- **Decision facts checked:** not yet
- **Origin:** Canada · TwinProduction · non-EU
- **Domain:** Monitoring
- **Role:** Uptime and status page defined as YAML
- **Last verified:** 2026-11-08 (v5.38.0) — lab host (VM), IPv4 LAN, run in a parallel batch: the status API answering for the configured endpoints before and after `down`/`up`, the refused client answered `403` (docs/labs/stack-refresh/2026-11-08-results.md)

## What we use

- Official `twinproduction/gatus` image
- File-based configuration (`config/config.yaml`) — no database for basic use
- Optional PostgreSQL backing for historical data persistence (not enabled by default)
- Traefik labels for HTTPS routing

## What we changed vs. upstream examples

| Change from upstream | Reason |
|---|---|
| **Traefik labels instead of `-p 8080:8080`** | Blueprint routing standard |
| **`security_opt: no-new-privileges:true`** | Baseline hardening |
| **Config mounted as read-only (`:ro`)** | Container should not modify its own config |
| **`access-vpn` default access** | Status page may expose internal service topology |

## Configuration

Gatus is config-file driven. Edit `config/config.yaml` for:

- **Endpoints**: services to monitor (HTTP, TCP, DNS, ICMP)
- **Alerting**: Slack, email, PagerDuty, Telegram integrations
- **Conditions**: response time, status codes, body content

See [Gatus config docs](https://github.com/TwiN/gatus#configuration) for the full reference.

## Version notes

- Moved `twinproduction/gatus` to `v5.38.0` on 2026-11-05 (released 2026-10-28),
  across v5.37.0, not run on a host at this tag. No breaking change is listed.
  v5.38.0 now validates maintenance windows on external, DNS and SSH endpoints, so a
  configuration with an invalid window there is refused at start instead of being
  ignored (`config.example.yaml` sets none); it redacts the Telegram token from send
  errors, applies the client timeout to WebSocket reads and writes, and adds OIDC
  diagnostics logging and a Resend alerting provider. v5.37.0 adds the DNS `TXT`
  query type, configurable client cookie storage and a Zulip alert topic. No
  compose change. Sources: https://github.com/TwiN/gatus/releases/tag/v5.38.0,
  https://github.com/TwiN/gatus/releases/tag/v5.37.0

## Upgrade checklist

1. Check [Gatus releases](https://github.com/TwiN/gatus/releases) — config schema rarely changes between v5.x releases
2. Bump `APP_TAG` in `.env`
3. `docker compose pull && docker compose up -d`
4. Verify: dashboard loads, all endpoints show correct status

## Useful commands

```bash
# Validate config syntax (check logs on startup)
docker compose logs app | head -30

# Reload config without restart (Gatus watches config file automatically)
# No command needed — Gatus hot-reloads config.yaml on change
```
