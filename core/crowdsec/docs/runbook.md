# CrowdSec Operations Runbook

Day-to-day operations and incident response for the CrowdSec stack: Core and its two
remediation points.

**Components this runbook covers:**

| Component | Where it runs |
|---|---|
| Core — engine, detection and decisions | Docker container (`core/crowdsec/`) |
| Reverse-Proxy Remediation — Traefik bouncer plugin | Inside the Traefik container (`core/traefik/`) |
| Host-Firewall Remediation — nftables bouncer | Host service (`crowdsec-firewall-bouncer`) |

Run all `docker exec` and `docker compose` commands from `core/crowdsec/` unless otherwise noted.

---

## 1. Health Checks

### Quick triage — all phases in ~30 seconds

Run this sequence when something seems wrong or after any change to the stack.

```bash
# Core — engine up and talking to LAPI?
docker exec crowdsec cscli lapi status
# Expected: "You can successfully interact with Local API (LAPI)"

# Core — log sources being parsed?
docker exec crowdsec cscli metrics show acquisition
# Expected: rows for each active log source, lines_read > 0, lines_unparsed = 0

# Reverse-proxy remediation — bouncer connected and polling?
docker exec crowdsec cscli bouncers list
# Expected: traefik-bouncer row with a "Last API pull" timestamp within the last 60 s

# Host-firewall remediation — bouncer service running?
sudo systemctl status crowdsec-firewall-bouncer
# Expected: "active (running)"

# Host-firewall remediation — the set the bouncer fills, and the scoped rule
sudo nft list set ip crowdsec crowdsec-blacklists
# Expected: the set, one element per active ban (empty is normal)
sudo nft list chain ip crowdsec cs-public-forward
# Expected: one rule — iifname "<public interface>" ct original ip saddr @crowdsec-blacklists counter drop
```

### Core — Engine

```bash
# Container running?
docker ps --filter name=crowdsec --format "{{.Names}}\t{{.Status}}"

# Engine log stream (live)
docker compose logs -f crowdsec

# Engine errors only
docker compose logs crowdsec 2>&1 | grep -i "error\|fatal\|panic" | tail -20

# LAPI reachable?
docker exec crowdsec cscli lapi status

# All metrics (parsers, scenarios, bouncers, LAPI)
docker exec crowdsec cscli metrics
```

### Reverse-Proxy Remediation — Traefik bouncer

```bash
# Is the bouncer registered and polling?
docker exec crowdsec cscli bouncers list
# Healthy: "Last API pull" within last 60 s, IP address populated

# Plugin loaded in Traefik?
docker compose -f ../traefik/docker-compose.yml logs traefik 2>&1 \
  | grep -iE "plugin|bouncer" | tail -5
# Healthy: "Plugin bouncer loaded" with no "Plugins are disabled" lines

# crowdsec-basic middleware status: Traefik dashboard
# https://<traefik-host>/dashboard/#/http/middlewares
# crowdsec-basic@file must show green "Success"
```

### Host-Firewall Remediation — nftables bouncer

```bash
# Service status
sudo systemctl status crowdsec-firewall-bouncer

# Recent bouncer logs
sudo journalctl -u crowdsec-firewall-bouncer -n 50

# Active bans at the host — the elements of the set the bouncer maintains
sudo nft list set ip crowdsec crowdsec-blacklists

# Bouncer registered with engine?
docker exec crowdsec cscli bouncers list
# Healthy: firewall-bouncer row with recent "Last API pull" (within ~10 s)
```

---

## 2. Monitoring & Inspection

### Active alerts and decisions

```bash
# All alerts (detection events — may not all become bans)
docker exec crowdsec cscli alerts list

# Active bans only
docker exec crowdsec cscli decisions list

# Bans in the last hour
docker exec crowdsec cscli decisions list --since 1h

# Decisions for a specific IP
docker exec crowdsec cscli decisions list --ip 1.2.3.4

# Drill into a specific alert (get ALERT_ID from alerts list)
docker exec crowdsec cscli alerts inspect <ALERT_ID>

# Decision count summary
docker exec crowdsec cscli decisions list | wc -l
```

### Metrics

```bash
# Log acquisition (lines read, parsed, poured to scenarios)
docker exec crowdsec cscli metrics show acquisition

# Parser hit counts — useful for confirming a log source is being processed
docker exec crowdsec cscli metrics show parsers

# Scenario activity — how many events each scenario has seen
docker exec crowdsec cscli metrics show scenarios

# Bouncer polling stats
docker exec crowdsec cscli metrics show bouncers

# LAPI request counts
docker exec crowdsec cscli metrics show lapi
```

**Healthy acquisition metrics (once traffic is flowing):**

| Metric | Healthy value |
|---|---|
| `lines_read` | > 0, increasing over time |
| `lines_parsed` | Equal to `lines_read` |
| `lines_unparsed` | 0 or absent |
| `lines_poured` | > 0 (scenarios are evaluating events) |

If `lines_parsed` < `lines_read`, the log format is not matching the configured parser.
Check that Traefik writes JSON-format access logs and that `type: traefik` is set in
`config/acquis.yaml`.

### Active nftables bans (host-firewall remediation)

In `set-only` mode the bouncer maintains the two blacklist sets and nothing else. The
DROP rule that consumes them is the blueprint's, in chain `cs-public-forward` of each
table ([`firewall-bouncer.md`](firewall-bouncer.md#set-only-architecture)).

```bash
# IPv4 bans — one element per decision, each with its timeout
sudo nft list set ip crowdsec crowdsec-blacklists

# IPv6 bans
sudo nft list set ip6 crowdsec6 crowdsec6-blacklists

# Count of banned IPv4 addresses
sudo nft list set ip crowdsec crowdsec-blacklists | grep -o 'expires' | wc -l

# The scoped rule, one per family — no output means nothing is enforced
sudo nft list chain ip crowdsec cs-public-forward
sudo nft list chain ip6 crowdsec6 cs-public-forward
```

### Log locations

| Log | How to access |
|---|---|
| CrowdSec engine (stdout) | `docker compose logs crowdsec` |
| Traefik access logs | `../traefik/volumes/logs/access.log` (default path; set via `TRAEFIK_LOG_PATH` in `.env`) |
| Firewall bouncer | `sudo journalctl -u crowdsec-firewall-bouncer` |

---

## 3. Whitelisting

Three tools, three questions:

| Question | Tool |
|---|---|
| Lift one ban now; the address may be banned again | `cscli decisions delete --ip …` |
| This address must never be served a decision — whatever produced it, the community blocklist included | LAPI AllowList — `ops/allowlist.sh`, the same procedure as README step 5 |
| The engine must not derive detections from this traffic of mine — a monitoring probe, a known crawler — but a decision from elsewhere may still apply | parser whitelist |

The second and the third look alike and are not: a parser whitelist sits in the engine's
own log path, and a decision pulled from the central API never travels through it
([`firewall-bouncer.md`](firewall-bouncer.md#a-parser-whitelist-is-not-a-universal-exclusion)).
For an address that must stay reachable, the AllowList is the tool.

### Remove an active ban (temporary — IP can be re-banned)

`cscli decisions delete --ip X` removes decisions for that IP from the local origin
(manually added or locally triggered decisions). `cscli decisions delete --ip X --all`
removes matching decisions across all origins — including the CrowdSec community
blocklist and any other source that may have contributed a decision. Use `--all` when
you need to fully unblock an IP and are sure this is intentional — without it, a
decision from a non-local origin may persist and keep the IP banned.

```bash
# Remove locally-originated decisions for an IP
docker exec crowdsec cscli decisions delete --ip 1.2.3.4

# Remove decisions across all origins (use when you need a complete unblock)
docker exec crowdsec cscli decisions delete --ip 1.2.3.4 --all

# Verify the ban is gone
docker exec crowdsec cscli decisions list --ip 1.2.3.4
# Expected: empty output
```

Host-firewall enforcement clears within ~10 seconds. Reverse-proxy enforcement clears within ~60 seconds
(Traefik bouncer polling interval).

### Exempt an address from every decision — the AllowList

The administrative devices go into `CROWDSEC_ALLOWLIST_ADMIN` in `.env` and
`ops/allowlist.sh apply` carries them into the LAPI AllowList `admin-devices` — README,
step 5, which also says what the exemption costs. `apply` never removes an entry;
`ops/allowlist.sh remove <value>` does, one at a time. A temporary exemption, for an
investigation, goes straight to the engine with an expiry:

```bash
docker exec crowdsec cscli allowlists add admin-devices 203.0.113.10 -e 2h -d "investigating a false positive"
docker exec crowdsec cscli allowlists inspect admin-devices
docker exec crowdsec cscli allowlists check 203.0.113.10
```

Adding an entry also removes the decisions it covers — measured on v1.7.8
(`firewall-bouncer.md`). Whether a decision added by hand with `cscli decisions add`
is withheld, and whether `--bypass-allowlist` overrides the list, is a host test this
repository has not run yet; until it has, lift an existing ban explicitly as well
(above).

### Suppress detections from your own traffic — the parser whitelist

For traffic the engine should not even count — a monitoring probe, a known crawler —
and only that. A decision from the community blocklist still applies to an address
listed here; for an address that must stay reachable, use the AllowList above.

Create a whitelist parser file in the persistent config volume. The file survives container
restarts because `volumes/config` maps to `/etc/crowdsec`.

```bash
# Create the local parsers directory if it doesn't exist
mkdir -p volumes/config/parsers/s02-enrich
```

Create `volumes/config/parsers/s02-enrich/whitelist-trusted.yaml`:

```yaml
name: whitelist-trusted
description: "Traffic the engine does not derive detections from"
whitelist:
  reason: "own monitoring"
  ip:
    - 203.0.113.10       # example: your monitoring server
```

Apply the whitelist (requires container restart to load the new parser):

```bash
docker compose restart crowdsec
```

Verify the whitelist file is present and readable inside the container:

```bash
# Confirm the file exists at the expected path inside the container
docker exec crowdsec ls -la /etc/crowdsec/parsers/s02-enrich/whitelist-trusted.yaml

# Inspect its contents to confirm the IPs/CIDRs are correct
docker exec crowdsec cat /etc/crowdsec/parsers/s02-enrich/whitelist-trusted.yaml
```

> **Note:** Local parser files placed directly in `volumes/config/` are not managed
> through the Hub index and may not appear in `cscli parsers list`. The filesystem
> checks above are the reliable way to confirm the file loaded correctly.

### Temporary troubleshooting whitelist

When investigating a suspected false positive, temporarily remove the ban and monitor
while you investigate:

```bash
# 1. Remove the current ban
docker exec crowdsec cscli decisions delete --ip 1.2.3.4 --all

# 2. Watch for re-banning in real time
docker compose logs -f crowdsec | grep 1.2.3.4

# 3. Check what scenario triggered it
docker exec crowdsec cscli alerts list --ip 1.2.3.4
docker exec crowdsec cscli alerts inspect <ALERT_ID>
```

If the IP keeps getting re-banned and it's legitimate traffic, decide which of the two
tools above it needs: the AllowList when the address must stay reachable, the parser
whitelist when only your own traffic should stop counting.

### Locked out over the VPN

The engine served a decision against your own address — both families, if both were
in use — and the host-firewall bouncer or the Traefik bouncer enforces it. The way back
must not depend on the VPN, because the VPN is what closed.

1. **Reach the host another way.** The other address family, if only one is banned; the
   LAN; otherwise the hoster's console (VNC or serial). An SSH session that was already
   open stays open — conntrack passes an established flow — and is the first thing to
   use before it closes.
2. **Stop the enforcement that closed the path, not the engine.** For SSH over the
   management interface that is the host-firewall bouncer:

   ```bash
   sudo systemctl stop crowdsec-firewall-bouncer
   ```

   The Traefik bouncer concerns HTTPS routes only; it fails open when the engine is
   unreachable, and a ban it enforces clears within its polling interval once the
   decision is gone.
3. **Lift the one decision, and no other:**

   ```bash
   docker exec crowdsec cscli decisions list --ip <your address>
   docker exec crowdsec cscli decisions delete --ip <your address> --all   # this address only
   ```

   `--all` reaches every origin for that address — the community blocklist included —
   and nothing else. Do not delete decisions wholesale; every other ban is doing its job.
4. **Exempt the device**, so the next detection does not repeat this: README step 5,
   both families.
5. **Start the enforcement again** and watch it: `sudo systemctl start
   crowdsec-firewall-bouncer`, then a *new* connection from the device over the
   management interface — an existing one proves nothing.

### Verify a parser whitelist is effective

Parser whitelists prevent the engine from automatically creating decisions based on
log events. They do **not** prevent manual decisions added via `cscli decisions add`
— those are always enforced regardless of any whitelist.

To confirm the whitelist is working:

```bash
# 1. Confirm the file is loaded (see above)
docker exec crowdsec ls /etc/crowdsec/parsers/s02-enrich/whitelist-trusted.yaml

# 2. Remove any existing ban for the whitelisted IP
docker exec crowdsec cscli decisions delete --ip <whitelisted-ip> --all

# 3. Monitor the decision list while the IP generates normal traffic
#    If the whitelist is working, no automatic decision should reappear:
watch -n 10 "docker exec crowdsec cscli decisions list --ip <whitelisted-ip>"
```

The whitelist can only be fully confirmed by observing that the IP is not automatically
re-banned when traffic resumes. There is no dry-run test that proves scenario-based
auto-banning will not occur.

---

## 4. False Positive Handling

A false positive is a legitimate request or IP that triggered a CrowdSec scenario and
received a ban decision.

### Investigation workflow

```bash
# 1. Identify the alert that caused the ban
docker exec crowdsec cscli alerts list --ip <affected-ip>
# Note the ALERT_ID

# 2. Inspect the alert details
docker exec crowdsec cscli alerts inspect <ALERT_ID>
# Shows: scenario name, trigger event, context (URL, user-agent, timestamps)

# 3. Check all active decisions for this IP
docker exec crowdsec cscli decisions list --ip <affected-ip>

# 4. Review the raw log events that triggered the scenario
# The alert inspect output shows the original log lines
# Cross-reference with Traefik access logs (default path — adjust if TRAEFIK_LOG_PATH
# was changed in .env):
grep <affected-ip> ../traefik/volumes/logs/access.log | tail -20
```

### Remove the decision

```bash
# Remove all decisions for the IP
docker exec crowdsec cscli decisions delete --ip <affected-ip> --all

# Confirm cleared
docker exec crowdsec cscli decisions list --ip <affected-ip>
```

### Prevent recurrence

Based on the investigation, choose the appropriate remediation:

| Root cause | Remediation |
|---|---|
| Legitimate IP being flagged repeatedly | Add to permanent whitelist (see §3) |
| App generating patterns that look like attacks | Review app behaviour; consider path-specific whitelist expressions |
| Scenario threshold too aggressive | Adjust via a custom profile (see `README.md` → Custom Profiles) |
| Your own monitoring/uptime tool | Add the monitoring service IP to whitelist |

### Verification

```bash
# Confirm no active decisions remain for the IP
docker exec crowdsec cscli decisions list --ip <affected-ip>

# If a whitelist was added, confirm the file is present inside the container
docker exec crowdsec ls /etc/crowdsec/parsers/s02-enrich/

# Monitor for re-banning (run for a few minutes)
docker compose logs -f crowdsec | grep <affected-ip>
```

---

## 5. Emergency Procedures

### Clear all active bans immediately (affects all enforcement layers)

Removes every active decision from the LAPI. Both remediation points
(firewall bouncer) read from the same decision list — this clears protection at both
layers simultaneously.

> **Warning:** Do not use this during an active attack unless you are intentionally
> accepting the exposure window. All enforcement drops until CrowdSec re-bans the
> sources from new log events.

```bash
docker exec crowdsec cscli decisions delete --all
```

Reverse-proxy remediation clears within ~60 s, host-firewall remediation within ~10 s.

### Disable host-firewall remediation (nftables only)

Stops network-layer enforcement without affecting Core or reverse-proxy remediation.

Stopping the service removes the enforcement with it: the companion unit
(`crowdsec-fw-scope.service`, bound to the bouncer) removes the scoped chains, and the
bouncer's `ExecStopPost=cs-fw-cleanup` destroys both CrowdSec tables. Without that
drop-in installed, the bouncer in `set-only` mode leaves both tables in place, clears the
IPv4 set and leaves the IPv6 set populated
([`firewall-bouncer.md`](firewall-bouncer.md#service-lifecycle)).

```bash
# 1. Stop the bouncer — the companion stops with it
sudo systemctl stop crowdsec-firewall-bouncer

# 2. Confirm both tables are gone
sudo nft list tables | grep -E 'crowdsec6?$'
# Expected: no output

# 3. Only on a host without the cleanup drop-in: remove what the bouncer left behind
sudo nft destroy table ip  crowdsec
sudo nft destroy table ip6 crowdsec6
```

Core (detection) and reverse-proxy remediation (HTTP blocking) continue running.

To re-enable:

```bash
sudo systemctl start crowdsec-firewall-bouncer
# ExecStartPre rebuilds both tables with empty sets, the bouncer syncs the active
# decisions within ~10 s, and the companion installs the scoped chains once the
# readiness gate confirms both sets are populated.
```

### Disable reverse-proxy remediation

There is no single command that disables only reverse-proxy remediation without affecting the host-firewall side.

**Option A — Remove specific decisions causing problems (targeted):**

```bash
# Remove bans only for the IPs that are being incorrectly blocked
docker exec crowdsec cscli decisions delete --ip <ip> --all
# host-firewall nftables rules are updated accordingly within ~10 s
```

**Option B — Clear all decisions (also affects host-firewall remediation):**

```bash
# Clears ALL bans across both remediation points — see warning above
docker exec crowdsec cscli decisions delete --all
```

**Option C — Disable the Traefik bouncer plugin entirely (config change required):**

Remove `crowdsec-basic@file` (or `crowdsec-appsec@file`) from the router middleware
lists in Traefik config, then reload Traefik. The host-firewall nftables rules remain active. See `core/traefik/README.md`
for the configuration location. This is the only approach that truly isolates reverse-proxy remediation.

### Disable CrowdSec entirely — engine + all enforcement

Use when CrowdSec itself is causing a problem (false positives at scale, broken update,
configuration error).

```bash
# 1. Stop host-firewall remediation — the cleanup destroys both CrowdSec tables,
#    chains and sets included; the destroy lines cover a host without the drop-in
sudo systemctl stop crowdsec-firewall-bouncer
sudo nft destroy table ip  crowdsec
sudo nft destroy table ip6 crowdsec6

# 2. Stop the CrowdSec engine (Core)
#    the reverse-proxy bouncer loses its decision source — it will continue
#    enforcing its last cached decision list until the cache clears
docker compose down

# 3. (Optional) Clear the reverse-proxy bouncer's cached decisions by restarting Traefik
#    Only needed if you want immediate HTTP access restored
docker compose -f ../traefik/docker-compose.yml restart traefik
```

**Effect on each component:**

| Component | After engine stops |
|---|---|
| Core | Down — no new detections or decisions |
| Reverse-proxy remediation | Continues enforcing last cached decision list (~60 s cache window), then fails open |
| Host-firewall remediation | Keeps enforcing the set membership it last synced, until each element's timeout expires or the service is stopped — the stop destroys both tables through the blueprint's cleanup |

### Restore after emergency

```bash
# 1. Start Core (engine)
docker compose up -d

# 2. Wait for startup (~5 min for full parser init)
docker exec crowdsec cscli lapi status

# 3. Start host-firewall remediation
sudo systemctl start crowdsec-firewall-bouncer

# 4. Confirm all components healthy (see §1 Quick triage)
```

Reverse-proxy remediation recovers automatically once the engine is reachable and the Traefik container
has restarted or its cache has refreshed.

---

## 6. Maintenance

### Update collections, parsers, and scenarios

Run monthly or after a significant CrowdSec Hub update.

```bash
# 1. Pull latest metadata from the Hub
docker exec crowdsec cscli hub update

# 2. Review what has updates available
docker exec crowdsec cscli collections list | grep update
docker exec crowdsec cscli parsers list | grep update
docker exec crowdsec cscli scenarios list | grep update

# 3. Apply all updates
docker exec crowdsec cscli hub upgrade

# 4. Verify the engine is healthy after upgrade
docker exec crowdsec cscli lapi status
docker exec crowdsec cscli metrics show acquisition
```

Hub upgrades apply immediately — no container restart required.

### Verify updates

```bash
# Confirm installed versions match Hub versions
docker exec crowdsec cscli collections list
docker exec crowdsec cscli parsers list
docker exec crowdsec cscli scenarios list

# Check for any failed or disabled items
docker exec crowdsec cscli hub list --all | grep -i "fail\|disabled"
```

### Rollback considerations

CrowdSec Hub upgrades are not trivially reversible. If an update causes problems:

1. Identify the affected collection or scenario:

   ```bash
   docker exec crowdsec cscli alerts list
   # Look for a sudden spike or unexpected scenario triggering
   ```

2. Remove (uninstall) a specific scenario:

   ```bash
   docker exec crowdsec cscli scenarios remove crowdsecurity/<scenario-name>
   # To reinstall later: docker exec crowdsec cscli scenarios install crowdsecurity/<scenario-name>
   ```

3. Or pin the collection at its current version and skip future updates until the
   upstream issue is resolved. File a bug report against the collection on the
   [CrowdSec Hub GitHub](https://github.com/crowdsecurity/hub).

### CrowdSec engine version upgrade

See `UPSTREAM.md` for the upgrade checklist. Summary:

```bash
# 1. Bump APP_TAG in .env
# 2. Pull and restart
docker compose pull
docker compose up -d

# 3. Verify
docker exec crowdsec cscli lapi status
docker exec crowdsec cscli hub update
```

---

## 7. Troubleshooting

### No alerts detected

Alerts require traffic + matching scenarios. This is expected on a quiet server.

```bash
# Is the acquisition source running?
docker exec crowdsec cscli metrics show acquisition
# If no rows or lines_read = 0: log file not being parsed

# Is the log file reachable inside the container?
docker exec crowdsec ls -la /var/log/traefik/access.log

# Are scenarios installed?
docker exec crowdsec cscli scenarios list

# Generate a test event by making a suspicious-looking request:
# (from an external machine or curl on the server)
# Access a path CrowdSec considers sensitive:
curl https://<your-domain>/.env
# Then wait 30 s and check:
docker exec crowdsec cscli alerts list
```

If lines are being read but no alerts appear, traffic may not yet match any scenario
thresholds — this is normal for low-traffic periods.

---

### No decisions generated

Alerts do not always produce decisions. A decision is created when a scenario threshold
is reached (typically 5–10 events within a time window).

```bash
# Check alert count vs decision count
docker exec crowdsec cscli alerts list | wc -l
docker exec crowdsec cscli decisions list | wc -l
# Low alert count with no decisions is normal

# What thresholds are configured?
docker exec crowdsec cscli scenarios list
# Review the scenario name, then check its definition on https://hub.crowdsec.net/
```

---

### Decisions not enforced

**Reverse-proxy remediation not enforcing:**

```bash
# Is the bouncer polling?
docker exec crowdsec cscli bouncers list
# Look for traefik-bouncer — is "Last API pull" recent?

# Is the plugin loaded in Traefik?
docker compose -f ../traefik/docker-compose.yml logs traefik 2>&1 \
  | grep -iE "plugin|bouncer" | tail -5
# Must show "Plugin bouncer loaded"

# Is crowdsec-basic@file attached to the router?
# Check the router's middleware list in the Traefik dashboard or compose file
```

**Host-firewall remediation not enforcing:**

```bash
# Is the bouncer service running?
sudo systemctl status crowdsec-firewall-bouncer

# Is the set populated, and is the scoped rule in place?
sudo nft list set ip crowdsec crowdsec-blacklists
sudo nft list chain ip crowdsec cs-public-forward

# Are there active decisions the bouncer should be enforcing?
docker exec crowdsec cscli decisions list

# Check bouncer logs for errors
sudo journalctl -u crowdsec-firewall-bouncer -n 50
```

---

### LAPI unavailable

```bash
# Is the container running?
docker ps --filter name=crowdsec

# Can the host reach the LAPI port?
docker exec crowdsec cscli lapi status

# What port is configured?
grep CROWDSEC_LAPI_PORT .env
# Default: CROWDSEC_LAPI_PORT=8080

# Is the LAPI port exposed on the host?
# Replace 8080 with the value from CROWDSEC_LAPI_PORT if changed
ss -tlnp | grep "$(grep CROWDSEC_LAPI_PORT .env | cut -d= -f2)"
# Expected: 127.0.0.1:<port> listening
```

If the container is up but LAPI is unreachable, check the engine logs for startup errors:

```bash
docker compose logs crowdsec | grep -i "error\|fatal" | tail -20
```

If the engine fails to start with a database error (e.g., "unable to open database",
"database is malformed"), the `volumes/data` directory may be corrupted:

```bash
# Check for database errors at startup
docker compose logs crowdsec | grep -i "database\|db\|sqlite" | tail -20
```

> **Recovery:** Stopping the engine and deleting `volumes/data/` forces a clean start.
> **This permanently loses all decision history and alert history.**
> All registered bouncers will lose their API keys — regenerate
> with `cscli bouncers add` and update the keys in `core/traefik/.env`
> (`CROWDSEC_BOUNCER_KEY`, then `render.sh`) and in
> `/etc/crowdsec/bouncers/crowdsec-firewall-bouncer.yaml.local` before restarting those services.

---

### Traefik bouncer unhealthy

Symptoms: `cscli bouncers list` shows no recent pull, or the Traefik dashboard shows
`crowdsec-basic@file` as red / missing.

```bash
# 1. Is the plugin loaded?
docker compose -f ../traefik/docker-compose.yml logs traefik 2>&1 \
  | grep -iE "plugin|bouncer|disabled" | tail -10

# 2. Is the bouncer API key valid?
docker exec crowdsec cscli bouncers list
# If traefik-bouncer is not listed, the key was never registered or was deleted
# Regenerate: docker exec crowdsec cscli bouncers add traefik-bouncer
# Then update CROWDSEC_BOUNCER_KEY in core/traefik/.env and re-render templates

# 3. Can Traefik reach CrowdSec?
# Both containers must be on the same Docker network (crowdsec-security)
docker inspect crowdsec | grep -A5 '"Networks"'
docker inspect traefik | grep -A5 '"Networks"'
```

---

### nftables bouncer unhealthy

```bash
# 1. Service status and last error
sudo journalctl -u crowdsec-firewall-bouncer -n 30

# 2. Can the bouncer reach the LAPI?
docker exec crowdsec cscli lapi status
ss -tlnp | grep "$(grep CROWDSEC_LAPI_PORT .env | cut -d= -f2)"
# Default port is 8080 — check .env if different

# 3. API key still valid?
docker exec crowdsec cscli bouncers list
# If firewall-bouncer is absent: key was deleted
# Regenerate: docker exec crowdsec cscli bouncers add firewall-bouncer
# Update api_key in /etc/crowdsec/bouncers/crowdsec-firewall-bouncer.yaml.local
# (the package-managed .yaml is never edited)

# 4. Mode mismatch?
grep "^mode:" /etc/crowdsec/bouncers/crowdsec-firewall-bouncer.yaml.local
# Must be "nftables" on Debian 12+ / Ubuntu 22.04+
# Verify nftables is active: sudo nft list ruleset
```

Full host-firewall troubleshooting table: [`firewall-bouncer.md`](firewall-bouncer.md).

---

### SSH detection not working

Prerequisites: host-firewall remediation installed, SSH log volume mounted, `crowdsecurity/sshd`
collection added, container restarted.

```bash
# 1. Is auth.log being parsed?
docker exec crowdsec cscli metrics show acquisition
# Expected: row for file:/var/log/auth.log

# 2. Is the file accessible inside the container?
docker exec crowdsec ls -la /var/log/auth.log
# If "No such file": volume not mounted — uncomment in docker-compose.yml and restart

# 3. Is the collection installed?
docker exec crowdsec cscli collections list | grep sshd

# 4. Are SSH scenarios active?
docker exec crowdsec cscli scenarios list | grep ssh

# 5. Is the GID correct?
# auth.log group on the host:
stat -c '%G %a' /var/log/auth.log
# CrowdSec GID in .env:
grep CROWDSEC_LOG_GID .env
```

Full SSH detection activation steps: [`firewall-bouncer.md`](firewall-bouncer.md)
→ "SSH detection — what makes host-firewall remediation worth it".
