# Firewall Bouncer — Phase 3 Setup

Phase 3 is the host-level enforcement layer. The `crowdsec-firewall-bouncer-nftables`
package installs nftables rules on the host that drop packets from banned IPs before
they reach any service — Traefik, SSH, or anything else.

---

## Why host-level, not in Docker

The firewall bouncer runs on the host (installed via `apt`), not inside a container.

- It manipulates the host kernel's netfilter/nftables — a container cannot do this safely
- It must protect the whole host, not just one service
- It must see traffic that never reaches Traefik (SSH, directly-mapped ports)

The CrowdSec engine (Phase 1) still runs in Docker and makes all decisions. The
firewall bouncer only enforces those decisions at the network layer.

---

## Relationship to Phase 2 (Traefik bouncer)

The two enforcement layers are complementary, not alternatives.

| Attack type | Phase 2 catches it | Phase 3 catches it |
|---|---|---|
| HTTP brute force, CVE probes, path traversal | ✅ (inspects decrypted request) | ✅ (drops packet) |
| SSH brute force | ❌ (never reaches Traefik) | ✅ (drops packet) |
| Port scan across all ports | ❌ | ✅ |
| Direct connection to non-proxied service | ❌ | ✅ |

Phase 2 has higher fidelity for HTTP — it sees the decrypted payload and can return a
meaningful 403. Phase 3 has broader coverage (all ports, all protocols) and is more
efficient (packet drops, no TCP handshake completes).

Running both is defense in depth: Phase 3 drops the packet early; Phase 2 handles any
traffic from the same IP that arrives between bouncer polling windows.

---

## When to activate Phase 3

| Scenario | Recommendation |
|---|---|
| Server with public SSH (port 22 open to internet) | **Required** — SSH brute-force is constant and Traefik never sees it |
| Server with SSH on a non-standard port | **Recommended** — obscurity alone is not sufficient |
| Server reachable only via Tailscale / VPN, no public SSH | Nice-to-have — adds network-layer depth for HTTP traffic |
| Pure homelab behind NAT, only Traefik ports forwarded | Optional — meaningful only once SSH detection is also active |

---

## Setup

### 1. Install the bouncer package on the host

```bash
sudo apt install crowdsec-firewall-bouncer-nftables
```

This installs the bouncer and creates `/etc/crowdsec/bouncers/crowdsec-firewall-bouncer.yaml`.

### 2. Generate an API key

The bouncer authenticates against the CrowdSec LAPI running in the container:

```bash
docker exec crowdsec cscli bouncers add firewall-bouncer
```

Copy the key immediately — it is shown only once. If lost, delete the entry and
regenerate:

```bash
docker exec crowdsec cscli bouncers delete firewall-bouncer
docker exec crowdsec cscli bouncers add firewall-bouncer
```

### 3. Configure the bouncer

```bash
sudo nano /etc/crowdsec/bouncers/crowdsec-firewall-bouncer.yaml
```

Minimum working configuration:

```yaml
api_url: http://127.0.0.1:8080/
api_key: <key from step 2>
mode: nftables
```

Notes:

- `api_url` points to the CrowdSec LAPI. The container exposes it on `127.0.0.1:8080`
  by default (configurable via `CROWDSEC_LAPI_PORT` in `.env`).
- `mode: nftables` is correct for Debian 12+ and Ubuntu 22.04+. Use `iptables` on
  older systems.
- The bouncer polls the LAPI every 10 seconds. Decisions propagate within ~10 s of
  being created in the engine.

### 4. Enable and start

```bash
sudo systemctl enable --now crowdsec-firewall-bouncer
```

---

## Verify

Four checks in order — same structure as the Phase 2 verify.

```bash
# 1. Service running?
sudo systemctl status crowdsec-firewall-bouncer
# Expected: "active (running)"
# If failed: see Troubleshooting below

# 2. Bouncer registered with the engine?
docker exec crowdsec cscli bouncers list
# Expected: firewall-bouncer with a recent "Last API pull" timestamp (within ~10 s)

# 3. nftables chain created?
sudo nft list ruleset | grep -A3 crowdsec
# Expected (chain exists, empty if no active bans yet):
#   chain crowdsec-chain {
#   }
# No output: bouncer is not writing to nftables — check mode setting

# 4. Functional test (proves end-to-end enforcement)
docker exec crowdsec cscli decisions add \
  --ip 198.51.100.1 \
  --duration 5m --reason "phase3-verify"

# Wait ~15 s for the bouncer to pick up the decision:
sudo nft list chain ip filter crowdsec-chain
# Expected:
#   table ip filter {
#     chain crowdsec-chain {
#       ip saddr 198.51.100.1 drop
#     }
#   }

# Clean up after verifying:
docker exec crowdsec cscli decisions delete --ip 198.51.100.1
```

Use a documentation IP (192.0.2.x, 198.51.100.x, 203.0.113.x) for the test —
not an address you are connecting from.

---

## What active enforcement looks like

When bans are in effect, the nftables chain contains drop rules. Example with two
active bans:

```
table ip filter {
  chain crowdsec-chain {
    ip saddr 185.220.101.5 drop
    ip saddr 45.142.212.100 drop
  }
}
```

The chain is populated automatically as the engine creates decisions and emptied as
decisions expire. You do not manage the rules manually — the bouncer handles the full
lifecycle.

To see which decisions are currently feeding these rules:

```bash
docker exec crowdsec cscli decisions list
```

---

## SSH detection — making Phase 3 worth it

Without SSH detection, Phase 3 only enforces bans triggered by Traefik access logs —
the same decisions Phase 2 already covers. Phase 3 adds real value when it also catches
threats that never touch Traefik. SSH brute force is the primary case.

This is opt-in because not every deployment has a publicly reachable SSH port.

### When to enable

Enable if any of the following are true:

- Port 22 (or any SSH port) is reachable from the internet
- You have seen repeated failed logins in `/var/log/auth.log`
- You want to ban IPs that combine SSH probing with web attacks

Skip if SSH is accessible only via Tailscale or WireGuard and no unauthenticated path
to it exists from the internet.

### Step 1 — Add the sshd collection

In `.env`, extend `CROWDSEC_COLLECTIONS`:

```bash
# Before:
CROWDSEC_COLLECTIONS=crowdsecurity/traefik crowdsecurity/http-cve ...

# After — append crowdsecurity/sshd:
CROWDSEC_COLLECTIONS=crowdsecurity/traefik crowdsecurity/http-cve ... crowdsecurity/sshd
```

### Step 2 — Mount the SSH log into the container

Verify the log file exists on the host:

```bash
ls -la /var/log/auth.log
# If missing, SSH logs may live in /var/log/syslog — adjust the path in step 3
```

In `docker-compose.yml`, uncomment the SSH log volume mount:

```yaml
# Before (commented out):
# - /var/log/auth.log:/var/log/auth.log:ro

# After:
- /var/log/auth.log:/var/log/auth.log:ro
```

### Step 3 — Activate the acquisition source

In `config/acquis.yaml`, uncomment the SSH block:

```yaml
---
filenames:
  - /var/log/auth.log
labels:
  type: syslog
```

### Step 4 — Restart the engine

```bash
docker compose up -d --force-recreate crowdsec
```

Wait ~5 minutes for the collection to install and the parser to begin reading.

### Step 5 — Verify SSH detection

```bash
# 1. Is auth.log being parsed?
docker exec crowdsec cscli metrics show acquisition
# Expected: a row for file:/var/log/auth.log with lines_read > 0

# 2. Is the sshd collection installed?
docker exec crowdsec cscli collections list | grep sshd
# Expected: crowdsecurity/sshd  ✔  enabled

# 3. Are SSH scenarios active?
docker exec crowdsec cscli scenarios list | grep ssh
# Expected: crowdsecurity/ssh-bf, crowdsecurity/ssh-slow-bf (and others)
```

SSH bans appear automatically once brute-force patterns are detected. The threshold
is 5–10 failed attempts depending on the scenario. The firewall bouncer picks up new
decisions within ~10 seconds:

```bash
# Check for active SSH bans (look for reason "crowdsecurity/ssh-bf"):
docker exec crowdsec cscli decisions list
```

---

## Edge cases

### IPv6

If your host has an IPv6 address reachable from the internet, the firewall bouncer
covers IPv6 automatically — CrowdSec creates both `ip` (IPv4) and `ip6` (IPv6) chains.
Verify both exist after a ban:

```bash
sudo nft list ruleset | grep -E "chain crowdsec"
# Expected: entries under both `ip filter` and `ip6 filter`
```

No additional configuration is needed; the bouncer handles both address families.

### Docker bridge network

CrowdSec does not ban RFC 1918 addresses (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16).
Docker bridge networks fall within these ranges, so container-to-container traffic
cannot be accidentally blocked.

If you use non-standard ranges (custom Docker subnets, Tailscale addresses) that you
never want banned, add them to `safe_range` in the bouncer config:

```yaml
# /etc/crowdsec/bouncers/crowdsec-firewall-bouncer.yaml
deny_mode: drop
safe_range:
  - 10.0.0.0/8
  - 172.16.0.0/12
  - 192.168.0.0/16
  - 100.64.0.0/10    # Tailscale / CGNAT
```

### What happens if the bouncer service goes down

If `crowdsec-firewall-bouncer` stops, the nftables rules it created remain in place
(they are not automatically flushed on service stop). Existing bans stay enforced;
new decisions from the engine are not picked up until the service restarts.

To flush all rules manually (emergency only — removes all active bans immediately):

```bash
sudo nft flush chain ip filter crowdsec-chain
```

---

## Troubleshooting

| Problem | Likely cause | Resolution |
|---|---|---|
| Service fails to start | Config file syntax error or wrong API key | `sudo journalctl -u crowdsec-firewall-bouncer -f` |
| Bouncer not connecting to LAPI | Wrong `api_url` or port | `curl -s http://127.0.0.1:8080/v1/health` — expect `{"status":"ok"}` |
| LAPI unreachable from host | Port not exposed in Docker | Check `ports:` in `docker-compose.yml` and `CROWDSEC_LAPI_PORT` in `.env` |
| No nftables chain appears | Wrong `mode` setting | Use `nftables` on Debian 12+ / Ubuntu 22.04+, `iptables` on older |
| Chain exists but always empty | No active decisions | Normal — rules appear only when bans exist; use the Verify step 4 test |
| `auth.log` not being parsed | Volume not mounted or wrong path | `docker exec crowdsec ls /var/log/auth.log` — must exist in the container |
| SSH bans not appearing | `crowdsecurity/sshd` not installed | `docker exec crowdsec cscli collections list \| grep sshd` |

---

## Removal

```bash
# 1. Stop and disable the service
sudo systemctl disable --now crowdsec-firewall-bouncer

# 2. Flush the nftables chain (removes all active drop rules)
sudo nft flush chain ip filter crowdsec-chain 2>/dev/null || true

# 3. Uninstall the package
sudo apt remove crowdsec-firewall-bouncer-nftables

# 4. Remove the bouncer registration from the engine
docker exec crowdsec cscli bouncers delete firewall-bouncer
```

Phase 1 (engine) and Phase 2 (Traefik plugin) are unaffected by removal.
