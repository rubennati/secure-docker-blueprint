# Upstream Reference

## Source

- **Repo:** https://github.com/crowdsecurity/crowdsec
- **Docker:** https://hub.docker.com/r/crowdsecurity/crowdsec
- **Docs:** https://docs.crowdsec.net/
- **Hub (Collections):** https://hub.crowdsec.net/
- **License:** MIT
- **Origin:** France · CrowdSec SAS · EU
- **Based on version:** v1.7.8
- **Last verified:** 2026-07-29 (v1.7.8) — engine, bouncer, an enforced ban and the AppSec layer all verified on a live host

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
| AppSec on `0.0.0.0:7422` | Upstream defaults to `127.0.0.1:7422`, which assumes the web server shares the host. Traefik is a separate container here, so a loopback bind is unreachable. Membership of `crowdsec-security` takes over the boundary the loopback bind provides upstream. |
| Engine on `crowdsec-security`, not `proxy-public` | Upstream states the AppSec component should be reachable from the web server or reverse proxy and from nowhere else. `proxy-public` carries every routed application, which is wider than that; `crowdsec-security` carries Traefik and this engine alone. The host publication on `127.0.0.1` is a separate mechanism and stays for the host-firewall remediation bouncer. |

## Firewall bouncer — verified package facts

The host-side enforcement component is a separate Debian package with its own schema.
These were established against the installed build and are the reason the blueprint owns
the DROP rule rather than delegating it.

- **Package:** `crowdsec-firewall-bouncer 0.0.25-5+b11` (Debian 13; upstream 0.0.25, the
  `-5` revision is packaging only)
- **`nftables.ipv4.set-only` and `nftables.ipv6.set-only` exist**, as do per-family
  `table` and `chain`. Set-only makes the bouncer maintain the blacklist sets and install
  no chain, which is what allows an interface-scoped rule to be owned elsewhere.
- **`safe_range` is not a configuration key.** Neither is `deny_mode`; the real option is
  `deny_action`. Both were previously documented here as working safeguards.
- **Unknown YAML keys pass `-t` validation**, which reports `config is valid`. A passing
  configuration test proves the file parses, not that an option in it has any effect.
- **Hook and priority are not configurable** in this version, so scoping enforcement to an
  interface is only possible by owning the rule.
- **Set-only does not create the tables.** Both must already exist; without the IPv4 table
  the bouncer exits `fatal: nftables: could not find ipv4 table 'crowdsec'`.
- **Set creation is asymmetric.** Given an existing table the bouncer creates a missing
  IPv4 set but never a missing IPv6 set, failing with `ENOENT` instead. The blueprint
  creates both, so no per-family special case survives into operation.
- **Set-only shutdown is asymmetric too, and leaves state behind.** In managed mode the
  bouncer removes its tables on stop. In set-only it clears IPv4 set membership, leaves
  IPv6 membership in place, and leaves both tables present. Cleaning up is the operator's
  job — an earlier claim here that stopping the service always removes the tables was true
  only of managed mode.
- **Interval sets are not supported.** nftables accepts `flags interval,timeout` and
  represents CIDR prefixes correctly, but the bouncer cannot populate such a set: every
  commit fails with `unable to commit add decisions … file exists` and the sets stay
  empty. The binary contains no `SetFlagInterval` reference. Consequently a `range`-scope
  decision inserted into the supported `flags timeout` set degrades silently to its
  network address — a `/24` becomes one address, reported as success.
- **A completion log line can be false.** After those failed netlink commits the bouncer
  still logged `N decisions added`, so that line alone cannot be used as a
  synchronisation-complete signal.
- **`ipv4.enabled: false` panics.** Disabling one family makes the current-state path
  dereference the absent IPv4 nftables connection
  (`nftables.go` → `GetSetElements` → nil `Conn`). Not a target configuration; recorded so
  nobody isolates a family that way.
- **Set-only logs a recurring metrics error.** `can't collect dropped packets … from nft`
  appears every collection interval because the collector expects a counter in a
  bouncer-owned chain that set-only never creates. `prometheus.enabled: false` removes it
  but disables the whole metrics endpoint; the blueprint keeps metrics on.
- **No newer package is offered.** `apt-cache policy` reports `0.0.25-5+b11` as both
  installed and candidate on Debian 13, so these are current limits rather than a pending
  upgrade.

Full architecture and the current verification status:
[`docs/firewall-bouncer.md`](docs/firewall-bouncer.md).

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

# Generate bouncer API key (for either remediation component)
docker exec crowdsec cscli bouncers add traefik-bouncer

# Update hub (parsers, scenarios, collections)
docker exec crowdsec cscli hub update
docker exec crowdsec cscli hub upgrade
```
