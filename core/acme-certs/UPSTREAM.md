# Upstream Reference

## Source

- **Repo:** https://github.com/acmesh-official/acme.sh
- **Docker:** https://hub.docker.com/r/neilpang/acme.sh
- **Based on version:** 3.1.2
- **Last checked:** 2026-04-14

## What we changed and why

| Change | Reason |
|--------|--------|
| `crond -f` without `-d` | BusyBox crond in 3.1.2+ doesn't support `-d` (debug level) |
| Custom entrypoint wrapper | Loads CF_TOKEN from Docker Secret |
| Scripts in `./scripts/` | Wizard, issue, renew, PFX conversion |
| Output to `./volumes/output/` | Standard volume path |

## Known issues

- **`crond -d` crash**: Fixed — removed unsupported `-d` flag
- **Script permissions**: Scripts may lose +x after copy. Fix: `chmod +x scripts/*.sh`

## Upgrade checklist

1. Check [acme.sh releases](https://github.com/acmesh-official/acme.sh/releases)
2. Bump `APP_TAG` in `.env`
3. `docker compose pull` → `docker compose up -d`
4. Test: `docker compose exec acme-certs acme.sh --version`
