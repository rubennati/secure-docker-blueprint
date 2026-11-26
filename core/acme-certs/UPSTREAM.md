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
| `crond -f` without `-d` | BusyBox crond in 3.1.2+ doesn't support `-d` (debug level) |
| Custom entrypoint wrapper | Loads CF_TOKEN from Docker Secret |
| Scripts in `./scripts/` | Wizard, issue, renew, PFX conversion |
| Output to `./volumes/output/` | Standard volume path |

## Known issues

- **`crond -d` crash**: Fixed — removed unsupported `-d` flag
- **Script permissions**: Scripts may lose +x after copy. Fix: `chmod +x scripts/*.sh`
- **SAN default leak**: Old wizard used .env SAN default when input was empty, causing wrong wildcard domain. Fixed in wizard rewrite.
- **CF_Token not in exec**: `docker compose exec` bypasses entrypoint. Fixed: `issue.sh` loads secret directly.

## Version notes

- Moved `ghcr.io/rubennati/cert-ops-tool` from `0.2.1` to `0.3.0` on 2026-11-23
  (released 2026-11-11), a security release. Images up to `0.2.1` are built on
  `neilpang/acme.sh:3.1.2` (Alpine 3.22) and carry known vulnerabilities in OpenSSL,
  curl, OpenSSH, BIND tools and socat; `0.3.0` is built on `neilpang/acme.sh:3.1.6`
  (Alpine 3.23), pinned by digest, with Alpine security updates applied at build time.
  The scripts run under `umask 077`, so private keys and PFX files are owner-only from
  creation; `issue.sh`, `renew.sh`, `convert-to-pfx.sh` and the wizard reject domain
  values that are not host names, since the value becomes a path under `/output`.
  `convert-to-pfx.sh` takes the password from a prompt or `PFX_PASSWORD`; the second
  argument still works, prints a deprecation warning and leaves the password in the
  process list. acme.sh 3.1.6 renews by ACME Renewal Information (ARI) by default, the
  cron job runs every six hours; `NO_ARI=1` disables it. Upstream acme.sh removed the
  `dns_hetzner` and `dns_linode` (v3) hooks in favour of `dns_hetznercloud` and
  `dns_linode_v4`; this stack uses Cloudflare DNS-01 only, so neither applies. No
  compose change. Sources: https://github.com/rubennati/cert-ops-tool/releases/tag/v0.3.0,
  https://github.com/acmesh-official/acme.sh/releases

## Upgrade checklist

1. Check [acme.sh releases](https://github.com/acmesh-official/acme.sh/releases)
2. Bump `APP_TAG` in `.env`
3. `docker compose pull` → `docker compose up -d`
4. Test: `docker compose exec acme-certs acme.sh --version`
