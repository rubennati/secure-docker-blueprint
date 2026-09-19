# Upstream Reference

## Source

- **Image:** https://github.com/rubennati/cert-ops-tool — `ghcr.io/rubennati/cert-ops-tool`,
  a thin wrapper that runs `acme.sh` under `crond` and exports PEM files. Operator-owned:
  this repository publishes it, so no upstream release feed applies.
- **Bundled tool:** https://github.com/acmesh-official/acme.sh — the certificate client the
  image wraps. Its version follows whatever the image was built against; read it with
  `docker compose exec acme-certs acme.sh --version`.
- **License:** GPL-3.0 (acme.sh)
- **Origin:** Austria · maintained in this project · EU (the bundled acme.sh is independent, original author Neil Pang)
- **Domain:** Infrastructure
- **Role:** Certificates for devices that never pass through the reverse proxy: NAS, routers, mail servers
- **Based on version:** `0.2.1` (cert-ops-tool)
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
- **SAN default leak**: Old wizard used .env SAN default when input was empty, causing wrong wildcard domain. Fixed in wizard rewrite.
- **CF_Token not in exec**: `docker compose exec` bypasses entrypoint. Fixed: `issue.sh` loads secret directly.

## Upgrade checklist

1. Check [acme.sh releases](https://github.com/acmesh-official/acme.sh/releases)
2. Bump `APP_TAG` in `.env`
3. `docker compose pull` → `docker compose up -d`
4. Test: `docker compose exec acme-certs acme.sh --version`
