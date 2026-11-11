# Upstream Reference

## Source

- **Image:** https://github.com/rubennati/cert-ops-tool — `ghcr.io/rubennati/cert-ops-tool`,
  a thin wrapper that runs `acme.sh` under `crond` and exports PEM files. Operator-owned:
  this repository publishes it, so no upstream release feed applies.
- **Bundled tool:** https://github.com/acmesh-official/acme.sh — the certificate client the
  image wraps. Its version follows whatever the image was built against; read it with
  `docker compose exec acme-certs acme.sh --version`.
- **License:** GPL-3.0 (acme.sh)
- **Decision facts checked:** not yet
- **Origin:** Austria · maintained in this project · EU (the bundled acme.sh is independent, original author Neil Pang)
- **Domain:** Infrastructure
- **Role:** Certificates for devices that never pass through the reverse proxy: NAS, routers, mail servers
- **Last verified:** 2026-11-08 (0.2.1) — over IPv4: a Let's Encrypt certificate issued over Cloudflare DNS-01 with a zone-scoped token and exported as `fullchain.pem`/`privkey.pem`, then used by both mail servers (docs/labs/stack-refresh/2026-11-08-results.md)

## What we changed and why

| Change | Reason |
|--------|--------|
| `crond -f` without `-d` | BusyBox crond in acme.sh 3.1.2+ doesn't support `-d` (debug level) |
| Custom entrypoint wrapper | Loads CF_TOKEN from Docker Secret |
| Scripts in `./scripts/` | Wizard, issue, renew, PFX conversion |
| Output to `./volumes/output/` | Standard volume path |

## Known issues

- **`crond -d` crash**: Fixed — removed unsupported `-d` flag
- **Script permissions**: Scripts may lose +x after copy. Fix: `chmod +x scripts/*.sh`
- **SAN default leak**: Old wizard used .env SAN default when input was empty, causing wrong wildcard domain. Fixed in wizard rewrite.
- **CF_Token not in exec**: `docker compose exec` bypasses entrypoint. Fixed: `issue.sh` loads secret directly.

## Version notes

- **0.3.0** (pinned since 2026-11-11, not yet run on a host): rebuilt on `acme.sh` 3.1.6 and
  Alpine 3.23; the image scans without a fixable CRITICAL or HIGH finding. Renewal follows
  ACME Renewal Information: the cron job runs every six hours and renews inside the window
  the CA suggests; `NO_ARI=1` in the container environment restores the fixed schedule.
  `convert-to-pfx.sh` asks for the password or reads `PFX_PASSWORD`; the password as a
  second argument still works and prints a warning. `issue.sh`, `renew.sh` and
  `convert-to-pfx.sh` refuse a domain that is not a host name. No migration step:
  `volumes/acme` and `volumes/output` are used as they are.

## Upgrade checklist

1. Check the [cert-ops-tool releases](https://github.com/rubennati/cert-ops-tool/releases) and, for the bundled client, the [acme.sh releases](https://github.com/acmesh-official/acme.sh/releases)
2. Bump `APP_TAG` in `.env`
3. `docker compose pull` → `docker compose up -d`
4. Test: `docker compose exec acme-certs acme.sh --version`
