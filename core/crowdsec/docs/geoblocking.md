# Geoblocking

Opt-in country-level blocking for CrowdSec decisions.

---

## What geoblocking means here

CrowdSec makes decisions per IP address. Country-level decisions extend that: instead of
banning a single IP, a decision targets every IP that resolves to a given country code. Both
Phase 2 (Traefik bouncer) and Phase 3 (nftables bouncer) understand country-scope decisions
and enforce them the same way they enforce IP-scope bans.

**GeoIP enrichment is already active.** The `crowdsecurity/traefik` collection installed by
default includes the `crowdsecurity/geoip-enrich` parser. Every detected event is tagged with
country metadata automatically — no additional configuration is needed for enrichment to work.

**Country-based blocking is not enabled by default.** GeoIP enrichment and geoblocking are
separate things. The enrichment adds country tags to events; no decision is created unless you
explicitly add one. This document covers how to do that, the risks involved, and when it is
and is not appropriate.

Geoblocking is a blunt control. It does not replace behavior-based detection (CrowdSec's
normal mode), rate limiting, or AppSec. Those controls act on what an IP does; geoblocking
acts only on where it is located.

---

## When to consider it — and when not to

| Situation | Assessment |
|---|---|
| Your service is explicitly regional (e.g., a local business with no international users) | Reasonable — the false positive pool is small |
| You observe sustained attack traffic concentrated in specific countries | Reasonable as a temporary measure while investigating |
| You want to reduce scan noise from regions you have no legitimate users | Reasonable — accept that you will occasionally block a legitimate bot or VPN exit |
| Your users are global or unknown | Risky — false positive rate is unpredictable |
| Your users include people who travel or use VPNs | Risky — blocking a country blocks VPN exit nodes in that country regardless of who is using them |
| You host APIs that receive webhooks from third-party services | Risky — payment processors, OAuth providers, and CI/CD runners use globally distributed infrastructure |
| You rely on external monitoring (UptimeRobot, Freshping, StatusCake) | Risky — monitoring probes originate from nodes in many countries including commonly blocked ones |
| You depend on search engine indexing | Risky — Googlebot, Bingbot, and other crawlers use IPs in many countries; blocking can affect SEO |
| Phase 3 (nftables) is active | Requires extra caution — country blocks affect all ports including SSH, not just HTTP |

GeoIP databases are not perfect. IP block reassignments lag, VPN and proxy services route traffic
through many countries, and CDN edge nodes can appear in unexpected locations. A country decision
will affect every IP in the database that maps to that country, including legitimate users,
security researchers, and services you have not anticipated.

---

## Before enabling — self-lockout prevention

Country-level decisions enforced by Phase 3 (nftables) block traffic at the packet layer across
**all ports**. If you add a country decision and you are connecting to the server from an IP
that resolves to that country (including via a VPN exit node in that country), you will be
locked out of SSH.

Before enabling geoblocking:

1. **Confirm you have an out-of-band access path.** Tailscale, a cloud provider console (AWS
   EC2 Instance Connect, DigitalOcean console, Hetzner VNC), or IPMI are all sufficient.
   Any access path that does not depend on the blocked country routing working is acceptable.

2. **Check your own IP's country.** Before adding a country decision, verify that your current
   connection IP does not resolve to the country you intend to block.

   CrowdSec only tracks country metadata for IPs it has observed in logs or alerts — it does
   not know your admin IP's country unless it has appeared in traffic. Use one of these approaches:

   - **External lookup (recommended):** Check your current public IP's country using a trusted
     GeoIP lookup service (e.g., `curl https://ipinfo.io` from your admin machine, or any
     comparable tool). Do this before adding any country decision.
   - **CrowdSec alerts (if your IP has appeared in logs):** If your admin IP has ever been seen
     in Traefik access logs, its country metadata may appear in alert details:

     ```bash
     docker exec crowdsec cscli alerts list --ip <your-admin-ip>
     # If any alert exists, inspect it for country metadata:
     docker exec crowdsec cscli alerts inspect <ALERT_ID>
     ```

   Do not skip this step — if your IP resolves to a country you intend to block, you will lose
   SSH access as soon as Phase 3 picks up the decision.

3. **Whitelist your own IP or subnet first.** If you have a stable IP, add it to the
   permanent whitelist before adding any country decision. See
   [`docs/runbook.md`](runbook.md) § 3 Whitelisting for the whitelist file format.

4. **Start with short durations.** A 1–4 hour duration lets you confirm the decision is
   working as intended before committing to a longer block.

---

## Mechanism A — Manual country decisions

The simplest path. Use `cscli decisions add` with `--scope Country` to add a temporary
country-level decision. No config file changes. Fully reversible.

### Add a country decision

```bash
# Block a country for 24 hours
# Replace XX with the ISO 3166-1 alpha-2 country code (e.g., CN, RU, KP)
docker exec crowdsec cscli decisions add \
  --scope Country \
  --value XX \
  --duration 24h \
  --reason "geoblock-temporary"
```

Both bouncers pick up the decision on their next poll cycle:

- Phase 2 (Traefik): within ~60 s
- Phase 3 (nftables): within ~10 s

### Verify the decision is active

```bash
# List active country-scope decisions
docker exec crowdsec cscli decisions list --scope Country

# Expected output includes a row for the country code with the duration and reason
# Example:
#  ID  │ Source │ Scope   │ Value │ Action │ Country │ Expiration
#  ... │ manual │ Country │ XX    │ ban    │ ...     │ 24h

# Confirm Phase 3 enforcement (if nftables bouncer is active):
# Country-scope decisions generate a different rule type — verify the bouncer
# is still actively polling:
docker exec crowdsec cscli bouncers list
# Expected: firewall-bouncer and/or traefik-bouncer with a recent "Last API pull"
```

### Test before relying on it

To verify enforcement is working without using a real IP in the blocked country:

```bash
# Add a test IP-scope decision for an IP you can reach from:
docker exec crowdsec cscli decisions add \
  --ip <test-ip> \
  --duration 5m --reason "test-verify"

# Confirm Phase 2 returns 403 for that IP after ~60 s, then clean up:
docker exec crowdsec cscli decisions delete --ip <test-ip>
```

Country-scope decisions follow the same enforcement path — if IP-scope decisions are
being enforced, country-scope decisions will be too.

### Duration and renewal

Country decisions expire like IP decisions. CrowdSec does not auto-renew them.

```bash
# Check when active country decisions expire:
docker exec crowdsec cscli decisions list --scope Country

# Re-add with a new duration when needed, or switch to Mechanism B for persistence
```

For long-running blocks, Mechanism B (scenario-based) is more appropriate than
re-adding manual decisions repeatedly.

### Revert a country decision

```bash
# Remove a country decision
docker exec crowdsec cscli decisions delete \
  --scope Country \
  --value XX

# Confirm it is gone:
docker exec crowdsec cscli decisions list --scope Country
# Expected: empty output, or remaining rows for other countries only

# Phase 2 clears within ~60 s. Phase 3 clears within ~10 s.
```

---

## Mechanism B — Automated country blocking

The `crowdsecurity/countries-blacklist` scenario on the CrowdSec Hub generates decisions
automatically for IPs from a configured country list. Unlike Mechanism A, decisions are
created continuously — any new IP from a listed country receives a ban without manual
intervention.

This is the repeatable path for persistent geoblocking, but it requires more care:

- You must maintain a country list appropriate for your deployment
- Decisions are generated automatically — including for VPNs, monitoring services,
  and search engines originating from listed countries
- Hub upgrades may change scenario behaviour; review changelogs before upgrading
- There is no default country list provided here — choosing one requires deliberate
  assessment of your user base

### Install the scenario

```bash
# 1. Update the Hub index
docker exec crowdsec cscli hub update

# 2. Install the scenario
docker exec crowdsec cscli scenarios install crowdsecurity/countries-blacklist

# 3. Confirm it installed:
docker exec crowdsec cscli scenarios list | grep countries
# Expected: crowdsecurity/countries-blacklist  ✔  enabled
```

### Create the country list config

> **Verify the config schema before proceeding.** The expected config file path, file name,
> and YAML structure are defined by the scenario itself and may vary between Hub versions.
> Treat the example below as a template — confirm the actual schema against the installed
> scenario's documentation before writing any config file.
>
> After installing the scenario, inspect its source to find the expected config path and format:
>
> ```bash
> # View the scenario definition to find its configuration requirements:
> docker exec crowdsec cat /etc/crowdsec/hub/scenarios/crowdsecurity/countries-blacklist.yaml
> # Look for a 'data' section or 'filter' referencing a file — that identifies
> # the expected config file name, location, and key structure.
> ```

The scenario reads its country list from a file in the CrowdSec data directory.
Create the file at `volumes/data/` so it persists across container restarts:

```bash
# The data volume is mounted at ./volumes/data inside the container.
# Create the country list file on the host — adjust the file name and key
# to match what the installed scenario actually expects (see verification step above):
cat > volumes/data/crowdsec-blacklisted-countries.yaml << 'EOF'
countries:
  - XX    # Replace with ISO 3166-1 alpha-2 code — e.g., CN, RU, KP
  # Add one entry per line. Be deliberate — each entry blocks all IPs in that country.
EOF
```

> **No default country list is provided in this blueprint.** The right list depends
> entirely on where your legitimate users are located. Adding countries without
> assessing your traffic will cause false positives. Start with Mechanism A (manual,
> temporary decisions) to validate impact before committing to automated blocking.

### Activate the config and restart

```bash
# Restart the engine to load the new scenario config:
docker compose up -d --force-recreate crowdsec

# Confirm the scenario is running:
docker exec crowdsec cscli scenarios list | grep countries
docker exec crowdsec cscli metrics show scenarios | grep countries
```

### Remove the automated scenario

```bash
# 1. Remove existing country decisions generated by the scenario:
docker exec crowdsec cscli decisions delete --scenario crowdsecurity/countries-blacklist

# 2. Uninstall the scenario:
docker exec crowdsec cscli scenarios remove crowdsecurity/countries-blacklist

# 3. Delete the country list config file:
rm volumes/data/crowdsec-blacklisted-countries.yaml

# 4. Restart the engine:
docker compose up -d --force-recreate crowdsec
```

---

## Phase 2 vs Phase 3 — what each layer blocks

Country-scope decisions are enforced at both layers when both are active. The difference
is what traffic they cover.

| Layer | Scope | Blocks |
|---|---|---|
| Phase 2 — Traefik bouncer | HTTP traffic through Traefik only | Requests to services behind Traefik — returns HTTP 403 |
| Phase 3 — nftables bouncer | All ports, all protocols | Entire network connection — packet is dropped before any service sees it |

**Phase 3 blocks SSH.** A country decision enforced by Phase 3 drops every packet from
that country, including SSH connections. If you are administering the server from an IP
that resolves to a blocked country — including via a VPN exit node — you will be locked out.

If Phase 3 is active and you are considering geoblocking, re-read the
[self-lockout prevention](#before-enabling--self-lockout-prevention) section and confirm
your out-of-band access path before adding any country decision.

If you want HTTP-only country blocking without SSH risk, you can restrict the Traefik
bouncer's enforcement without enabling Phase 3 for country decisions. However, this requires
custom bouncer configuration and is out of scope for this blueprint.

---

## Trade-offs

| | |
|---|---|
| **Benefit** | Reduces attack surface from geographic regions with no legitimate users in your deployment |
| **Risk** | Blocks legitimate users, monitoring services, APIs, and VPN exit nodes in that country |
| **Operational impact** | Creates support burden when legitimate traffic is blocked; requires maintaining a country list for Mechanism B |
| **Mitigation** | Start with Mechanism A (short duration, manual); whitelist known good IPs before enabling; maintain an out-of-band access path; monitor false positive rate before extending duration or moving to automated blocking |

| | |
|---|---|
| **Benefit** | Drops attack traffic early (Phase 3) or at the proxy layer (Phase 2) before it consumes application resources |
| **Risk** | GeoIP databases are not 100% accurate — IPs are reassigned, CDN edge nodes appear in unexpected countries, cloud providers route through many regions |
| **Operational impact** | False positive rate is invisible until a legitimate user or service reports being blocked |
| **Mitigation** | Monitor `cscli decisions list --scope Country` and cross-reference with any access issues reported after enabling |

| | |
|---|---|
| **Benefit** | Reduces log noise and parser load from high-volume scan sources in specific countries |
| **Risk** | Scanning traffic originates from many countries and from compromised hosts worldwide — geoblocking shifts, not eliminates, the noise |
| **Operational impact** | Marginal improvement in signal-to-noise ratio at the cost of potential legitimate traffic loss |
| **Mitigation** | Behaviour-based detection (the default CrowdSec mode) is more precise — use geoblocking as a supplemental, not primary, control |

Geoblocking does not substitute for:

- CrowdSec's behaviour-based detection scenarios (already active)
- AppSec / WAF rules (`crowdsecurity/appsec-virtual-patching`, already active)
- Rate limiting middleware in Traefik
- Normal IP-level bans from detected attacks

---

## Emergency reversal

If geoblocking causes unexpected access loss:

```bash
# 1. Remove all country-scope decisions:
docker exec crowdsec cscli decisions delete --scope Country

# 2. Confirm all country decisions are gone:
docker exec crowdsec cscli decisions list --scope Country
# Expected: empty output

# 3. Phase 2 (Traefik) clears within ~60 s.
#    Phase 3 (nftables) clears within ~10 s.
#    If Phase 3 is not clearing, flush the chain directly:
sudo nft flush chain ip crowdsec crowdsec-chain

# 4. If Mechanism B (automated scenario) is active, the scenario will continue
#    generating new decisions. Remove it:
docker exec crowdsec cscli scenarios remove crowdsecurity/countries-blacklist
docker compose up -d --force-recreate crowdsec
```

Full emergency procedures: [`docs/runbook.md`](runbook.md) → §5 Emergency Procedures.

---

## What is not covered here

- No default country list is provided or recommended
- No changes to `docker-compose.yml`, `.env`, or CrowdSec config files are required
- GeoIP database customization (e.g., using a custom MaxMind account key) is not covered
- Country-weighted profiles (applying different ban durations based on country) are not covered
- IPv6 country blocking follows the same mechanism; Phase 3 handles both address families automatically
