# Upstream Reference

## Source

- **Repo:** https://github.com/crowdsecurity/crowdsec
- **Docker:** https://hub.docker.com/r/crowdsecurity/crowdsec
- **Docs:** https://docs.crowdsec.net/
- **Hub (Collections):** https://hub.crowdsec.net/
- **Based on version:** v1.7.7
- **Last checked:** 2026-04-15

## Architecture

| Phase | Component | Where | Status |
|---|---|---|---|
| 1 | Security Engine | `core/crowdsec/` | Ready |
| 2 | Traefik Bouncer Plugin | `core/traefik/` config | TODO |
| 3 | Firewall Bouncer (nftables) | Host apt package | TODO |

## What we changed and why

| Change | Reason |
|--------|--------|
| Relative Traefik log path | `../traefik/volumes/logs` — works when both are in `core/` |
| LAPI on localhost only | `127.0.0.1:8080` — not exposed to network |
| `no-new-privileges` | Security hardening |
| Custom acquis.yaml + appsec.yaml | Mounted read-only for reproducibility |

## Upgrade checklist

1. Check [CrowdSec releases](https://github.com/crowdsecurity/crowdsec/releases)
2. Bump `APP_TAG` in `.env`
3. `docker compose pull` → `docker compose up -d`
4. Verify: `docker exec crowdsec cscli lapi status`
5. Update collections: `docker exec crowdsec cscli hub update`

## Useful commands

```bash
# Engine status
docker exec crowdsec cscli lapi status

# Metrics (parsed logs, active decisions)
docker exec crowdsec cscli metrics

# List installed collections
docker exec crowdsec cscli collections list

# List active bans
docker exec crowdsec cscli decisions list

# Manually ban an IP (test)
docker exec crowdsec cscli decisions add --ip 1.2.3.4 --duration 1h --reason "test"

# Remove a ban
docker exec crowdsec cscli decisions delete --ip 1.2.3.4

# Generate bouncer API key (for Phase 2/3)
docker exec crowdsec cscli bouncers add traefik-bouncer

# Update hub (parsers, scenarios, collections)
docker exec crowdsec cscli hub update
docker exec crowdsec cscli hub upgrade
```
