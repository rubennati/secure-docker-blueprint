# Firewall Bouncer — Phase 3 Setup

Phase 3 is the host-level enforcement layer. A firewall bouncer package installs
nftables rules on the host that drop packets from banned IPs before they reach any
service — Traefik, SSH, or anything else.

> **Debian 13 / Trixie note:** The package name changed. Use `crowdsec-firewall-bouncer`
> (from Debian main). Upstream/packagecloud docs and older guides refer to
> `crowdsec-firewall-bouncer-nftables` — that package is not available in Debian 13.

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

**Debian 13 / Trixie:**

```bash
sudo apt install crowdsec-firewall-bouncer
```

**Older Debian / Ubuntu / upstream packagecloud:**

```bash
sudo apt install crowdsec-firewall-bouncer-nftables
```

The Debian 13 package installs with nftables configured by default. During installation
you will see:

```
W: cscli not found, no automatic registration
I: Configuring nftables [see README.Debian]
To adjust the config: editor /etc/crowdsec/bouncers/crowdsec-firewall-bouncer.yaml.local && systemctl restart crowdsec-firewall-bouncer
```

The `cscli not found` warning is expected — the CrowdSec engine runs in Docker, not on
the host. Registration is done manually in the next step.

The Debian package creates two files:

- `/etc/crowdsec/bouncers/crowdsec-firewall-bouncer.yaml` — base config managed by the
  package; **do not edit this directly**
- `/etc/crowdsec/bouncers/crowdsec-firewall-bouncer.yaml.local` — your local overrides;
  edit this file

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

**Debian 13 / Trixie** — edit the `.yaml.local` override file only:

```bash
sudo editor /etc/crowdsec/bouncers/crowdsec-firewall-bouncer.yaml.local
```

The base config (`crowdsec-firewall-bouncer.yaml`) uses variable placeholders
(`${API_KEY}`, `${BACKEND}`). The `.yaml.local` file supplies the concrete values that
override those placeholders. Set:

```yaml
api_url: http://127.0.0.1:8080/
api_key: <key from step 2>
mode: nftables
```

Do not edit the base `.yaml` file — it is managed by the Debian package and may be
reset on upgrade.

**Upstream/packagecloud install** — edit the main config directly:

```bash
sudo nano /etc/crowdsec/bouncers/crowdsec-firewall-bouncer.yaml
```

Update only these fields; leave all other installer-generated settings in place:

```yaml
api_url: http://127.0.0.1:8080/
api_key: <key from step 2>
mode: nftables
```

Notes:

- `api_url` points to the CrowdSec LAPI. The container exposes it on `127.0.0.1:8080`
  by default (configurable via `CROWDSEC_LAPI_PORT` in `.env`).
- `mode: nftables` is correct for Debian 12+ and Ubuntu 22.04+. Use `iptables` on
  older systems. The Debian 13 package defaults to nftables automatically.
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
sudo nft list chain ip crowdsec crowdsec-chain
# Expected:
#   table ip crowdsec {
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
table ip crowdsec {
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

First confirm where SSH authentication events are written on your system:

```bash
ls -l /var/log/auth.log
# Debian 12, Ubuntu 22.04+: auth.log exists → use /var/log/auth.log
# If "No such file or directory":
#   Ubuntu with systemd-journald only: check journalctl -u ssh
#   Some systems write to /var/log/syslog instead → use /var/log/syslog
#   Rocky/AlmaLinux: /var/log/secure
```

The file must exist **before** the CrowdSec container starts and must be readable by
the GID configured in `.env` (`CROWDSEC_LOG_GID`). Verify the file is readable:

```bash
stat -c '%G %a' /var/log/auth.log
# Note the group name and check that CROWDSEC_LOG_GID matches that group's GID:
getent group <group-name>
```

> **Note on journald-only systems:** If your distro writes SSH logs exclusively to the
> systemd journal (no flat log file), CrowdSec cannot read them via file acquisition.
> Enable traditional syslog forwarding (`ForwardToSyslog=yes` in
> `/etc/systemd/journald.conf`) or use the CrowdSec journald acquisition source instead
> — which requires additional configuration not covered here.

In `docker-compose.yml`, uncomment the SSH log volume mount (adjust the path if your
system uses `/var/log/syslog` or `/var/log/secure`):

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

### Optional: verify the full detection chain end-to-end

This confirms that the complete path works: auth.log event → parser → engine decision
→ firewall bouncer rule. It does not require brute-forcing a real SSH service.

**Method:** inject a synthetic failed-login line directly into the log file that
CrowdSec is monitoring, then check whether the engine parses it and produces an alert.

```bash
# 1. Note the current alert count (baseline)
docker exec crowdsec cscli alerts list | wc -l

# 2. Write a single synthetic failed-login line in the format sshd uses.
#    Use a documentation IP (203.0.113.x range) — never a real address.
#    The exact format must match what your sshd version writes.
echo "$(date '+%b %d %H:%M:%S') $(hostname) sshd[99999]: Failed password for invalid user testuser from 203.0.113.99 port 54321 ssh2" \
  | sudo tee -a /var/log/auth.log

# 3. Wait ~30 s for CrowdSec to parse the new line, then check:
docker exec crowdsec cscli metrics show acquisition
# Expected: lines_read for auth.log has increased by 1

# 4. A single line will not trigger a ban (threshold is 5–10 events).
#    To confirm parsing without triggering a scenario, check the parser hit count:
docker exec crowdsec cscli metrics show parsers
# Expected: crowdsecurity/sshd-logs shows a hit for the injected line

# 5. Clean up — the synthetic line is harmless but tidy to remove:
sudo sed -i '/testuser.*203\.0\.113\.99/d' /var/log/auth.log
```

> **What a real SSH ban looks like once traffic flows:**
> After genuine brute-force attempts accumulate, `cscli decisions list` will show an
> entry with `reason: crowdsecurity/ssh-bf`. Within ~10 s, the nftables chain will
> contain the corresponding drop rule — verifiable with
> `sudo nft list chain ip crowdsec crowdsec-chain`.

---

## Edge cases

### IPv6

If your host has an IPv6 address reachable from the internet, the firewall bouncer
covers IPv6 automatically — CrowdSec creates both `ip` (IPv4) and `ip6` (IPv6) chains.
Verify both exist after a ban:

```bash
sudo nft list ruleset | grep -E "table ip"
# Expected: entries for both `ip crowdsec` and `ip6 crowdsec`
```

No additional configuration is needed; the bouncer handles both address families.

### Docker bridge network and private ranges

CrowdSec's detection scenarios don't typically trigger on RFC 1918 addresses
(10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16) — internet scanners and brute-force
sources almost never originate from private ranges. In practice, Docker bridge traffic
is safe.

However, the firewall bouncer enforces **any active decision**, including decisions for
private IPs. A manual `cscli decisions add --ip 192.168.1.x` would be enforced at the
network layer. If you want a hard guarantee that certain ranges are never dropped,
configure `safe_range` in the bouncer config:

```yaml
# /etc/crowdsec/bouncers/crowdsec-firewall-bouncer.yaml.local  (Debian 13)
# /etc/crowdsec/bouncers/crowdsec-firewall-bouncer.yaml        (upstream install)
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
sudo nft flush chain ip crowdsec crowdsec-chain
```

### Reboot behavior

On reboot, nftables rules are **not** persistent — the kernel starts with an empty
ruleset. The firewall bouncer re-establishes the rules by syncing decisions from the
LAPI as soon as the service starts. Because `systemctl enable` is part of the setup,
the bouncer starts automatically on boot.

There is a brief window between kernel start and when the bouncer service is fully up
during which no drop rules are active. In most deployments this window is a few seconds
and poses no meaningful risk. If you require zero-gap enforcement at boot, configure
`nftables.service` persistence separately (out of scope for this blueprint).

---

## Troubleshooting

| Problem | Likely cause | Resolution |
|---|---|---|
| Service fails to start | Config file syntax error or wrong API key | `sudo journalctl -u crowdsec-firewall-bouncer -f` |
| Bouncer not connecting to LAPI | Wrong `api_url` or port | `docker exec crowdsec cscli lapi status` — expect "You can successfully interact with Local API" |
| LAPI unreachable from host | Port not exposed in Docker | Check `ports:` in `docker-compose.yml` and `CROWDSEC_LAPI_PORT` in `.env` |
| No nftables chain appears | Wrong `mode` setting | Use `nftables` on Debian 12+ / Ubuntu 22.04+; Debian 13 package sets this automatically — check `.yaml.local` wasn't inadvertently set to `iptables` |
| Chain exists but always empty | No active decisions | Normal — rules appear only when bans exist; use the Verify step 4 test |
| `auth.log` not being parsed | Volume not mounted or wrong path | `docker exec crowdsec ls /var/log/auth.log` — must exist in the container |
| SSH bans not appearing | `crowdsecurity/sshd` not installed | `docker exec crowdsec cscli collections list \| grep sshd` |

---

## Removal

```bash
# 1. Stop and disable the service
sudo systemctl disable --now crowdsec-firewall-bouncer

# 2. Flush the nftables chain (removes all active drop rules)
sudo nft flush chain ip crowdsec crowdsec-chain 2>/dev/null || true

# 3. Uninstall the package
# Debian 13 / Trixie:
sudo apt remove crowdsec-firewall-bouncer
# Upstream/packagecloud install:
# sudo apt remove crowdsec-firewall-bouncer-nftables

# 4. Remove the bouncer registration from the engine
docker exec crowdsec cscli bouncers delete firewall-bouncer
```

Phase 1 (engine) and Phase 2 (Traefik plugin) are unaffected by removal.
