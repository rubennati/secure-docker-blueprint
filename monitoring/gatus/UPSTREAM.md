# Upstream Reference

## Source

- **Project:** https://gatus.io
- **GitHub:** https://github.com/TwiN/gatus
- **Docker Hub:** https://hub.docker.com/r/twinproduction/gatus
- **License:** Apache-2.0
- **Origin:** Canada · TwinProduction · non-EU
- **Based on version:** `v5.34.0`
- **Last checked:** 2026-05-03

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
| **`acc-tailscale` default access** | Status page may expose internal service topology |

## Configuration

Gatus is config-file driven. Edit `config/config.yaml` for:
- **Endpoints**: services to monitor (HTTP, TCP, DNS, ICMP)
- **Alerting**: Slack, email, PagerDuty, Telegram integrations
- **Conditions**: response time, status codes, body content

See [Gatus config docs](https://github.com/TwiN/gatus#configuration) for the full reference.

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
