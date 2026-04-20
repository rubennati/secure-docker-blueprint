# Firewall Bouncer — Phase 3 Setup Guide

This is the **host-level** CrowdSec bouncer that enforces ban decisions at the network layer (`nftables` / `iptables`), as opposed to the Traefik plugin bouncer which works at the HTTP layer.

## Why host-level, not Docker

Recommended approach on Debian/Ubuntu: **install the firewall bouncer on the host, not in Docker**.

Reasons:

- it needs direct control over `nftables` / `iptables`
- it should protect the whole host, not just one container
- it must see traffic that never reaches Traefik (SSH, DNS, direct ports)

This is why the firewall bouncer is explicitly **not** part of the Docker Compose setup in `core/crowdsec/`.

## When to activate this phase

See the decision matrix in [`../../../ROADMAP.md`](../../../ROADMAP.md#crowdsec-integration) and [`../README.md`](../README.md). Short version:

| Scenario | Firewall bouncer needed? |
|---|---|
| Server only reachable via Tailscale, no public SSH | Nice-to-have |
| Server with public SSH + public web | **Recommended** — SSH brute-force is constant |
| Pure homelab behind NAT, only Traefik port-forwarded | Unnecessary |
| Production / customer-facing | **Required** — defense in depth |

## Relationship to the Traefik plugin bouncer

The two bouncers are **complementary**, not alternatives:

- **Traefik plugin** (Phase 2) protects your web apps at HTTP layer, also does WAF (inspects request bodies for SQL injection, XSS, CVE probes).
- **Firewall bouncer** (Phase 3) protects your entire host at network layer. Blocks with packet drops (attacker sees nothing).

If an attacker tries to brute-force SSH on port 22, the Traefik plugin doesn't help — the traffic never reaches Traefik. Firewall bouncer catches it.

If an attacker sends a SQL-injection payload to your WordPress site, the firewall bouncer doesn't help — the traffic is encrypted HTTPS. Traefik plugin inspects the decrypted request and blocks it.

## Install procedure (Debian / Ubuntu with nftables)

### 1. Install the bouncer package on the host

```bash
sudo apt install crowdsec-firewall-bouncer-nftables
```

### 2. Generate an API key from the CrowdSec container

```bash
docker exec -it crowdsec cscli bouncers add firewall-bouncer
```

Copy the generated key. It cannot be retrieved again — if lost, delete the bouncer entry (`cscli bouncers delete firewall-bouncer`) and recreate.

### 3. Configure the bouncer

Edit the host config file:

```bash
sudo nano /etc/crowdsec/bouncers/crowdsec-firewall-bouncer.yaml
```

Minimal configuration:

```yaml
api_url: http://127.0.0.1:8080/
api_key: <paste_generated_key_here>
mode: nftables
```

Notes:

- `api_url` points to the CrowdSec Local API. If the engine runs in Docker with port `8080` exposed on the host, this is correct. If not, use the container IP or expose the LAPI port.
- `mode: nftables` is the Debian 12+ / Ubuntu 22.04+ default. Use `iptables` on older systems.

### 4. Enable and start the service

```bash
sudo systemctl enable --now crowdsec-firewall-bouncer
```

## Verification

From the CrowdSec container:

```bash
docker exec -it crowdsec cscli bouncers list
```

The `firewall-bouncer` should appear with a recent heartbeat timestamp.

From the host:

```bash
sudo systemctl status crowdsec-firewall-bouncer
sudo nft list ruleset | grep crowdsec
```

You should see a `crowdsec` chain in the `nft` ruleset. It will be empty until the first ban.

## Testing

Generate a test ban:

```bash
docker exec crowdsec cscli decisions add --ip 1.2.3.4 --duration 1h --reason "firewall-bouncer test"
```

Within ~30 seconds the firewall bouncer should pick up the decision:

```bash
sudo nft list chain ip filter crowdsec-chain
```

You should see the IP in the drop list.

Remove the test ban:

```bash
docker exec crowdsec cscli decisions delete --ip 1.2.3.4
```

## Troubleshooting

| Problem | Check |
|---|---|
| Bouncer not connecting | API URL reachable from host? `curl http://127.0.0.1:8080/v1/decisions/stream` |
| No rules appearing | `sudo journalctl -u crowdsec-firewall-bouncer -f` for connection errors |
| Bans not enforced | `mode` setting matches your firewall backend (`nftables` vs `iptables`) |
| Performance impact | Switch to `iptables` if nftables causes issues; usually not needed |

## Removal

```bash
sudo systemctl disable --now crowdsec-firewall-bouncer
sudo apt remove crowdsec-firewall-bouncer-nftables
docker exec crowdsec cscli bouncers delete firewall-bouncer
```
