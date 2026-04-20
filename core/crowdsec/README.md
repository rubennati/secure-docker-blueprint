# CrowdSec

Intrusion Detection and Prevention System (IDS/IPS) for the entire stack.

CrowdSec analyzes Traefik access logs, detects threats (brute force, CVE probes, aggressive crawling, path traversal), and stores security decisions. On its own it does **not block anything** — a separate "bouncer" enforces the decisions. You pick which enforcement layer you want.

---

## Architecture

Three independent components. The Engine parses logs and decides; the two bouncers enforce at different network layers.

```
                      Internet
                         │
                         ▼
           ┌─────────────────────────────┐
   Phase 3 │  Firewall Bouncer           │  nftables rules on the host
           └─────────────┬───────────────┘  drop packets before Traefik
                         ▼
           ┌─────────────────────────────┐
   Phase 2 │  Traefik Bouncer Plugin     │  reject HTTP requests (403)
           └─────────────┬───────────────┘  at the proxy layer
                         ▼
                    Your apps

           ┌─────────────────────────────┐
   Phase 1 │  Security Engine            │  parses Traefik logs,
           │                             │  runs scenarios,
           └─────────────┬───────────────┘  stores ban decisions
                         │
             queried by Phase 2 + Phase 3
```

The Engine is the only component that runs from this directory. Phase 2 lives in `core/traefik/` (Traefik static + dynamic config plus an env var for the bouncer key). Phase 3 is an apt package installed on the host — it never enters a container.

### Phase roles

- **Phase 1 — Security Engine.** Detection and decision. Reads logs, matches scenarios (brute force, CVE probes, path traversal, aggressive crawling), produces ban decisions. Stores decisions in a local database. On its own, enforces nothing.
- **Phase 2 — Traefik Bouncer Plugin.** HTTP-layer enforcement. The plugin polls the Engine every 60 s, caches the current decision list, and rejects matching requests with HTTP 403 before they reach any app. Works only for traffic that goes through Traefik.
- **Phase 3 — Firewall Bouncer.** Network-layer enforcement. Sets nftables rules on the host, dropping packets from flagged IPs regardless of destination port. Protects services Traefik does not terminate (SSH, exposed database ports, directly mapped containers) and drops attack traffic earlier in the request path.

Phases 2 and 3 are independent: either can run without the other, or both together for defense in depth.

### Typical deployments

| Deployment | Components | Outcome |
|---|---|---|
| Detection only | Phase 1 | Visibility into attacks; no blocking. Useful for tuning before enabling enforcement. |
| HTTP protection | Phase 1 + Phase 2 | Traefik rejects requests from flagged IPs. Blocks web attacks, leaves non-HTTP ports untouched. |
| Network protection | Phase 1 + Phase 3 | Host firewall drops packets from flagged IPs across all ports. Covers SSH and non-HTTP services; drops traffic earlier. |
| Defense in depth | Phase 1 + Phase 2 + Phase 3 | Network-layer drop for all protocols; HTTP-layer reject with richer feedback when packets do reach Traefik. |

---

## Phase 1: Security Engine — setup

This directory's `docker-compose.yml` runs the engine. It collects logs, parses them, runs scenarios, stores decisions.

### Prerequisites

Traefik must write access logs in **JSON format** to a file CrowdSec can read. In the blueprint's `core/traefik/` this is the default — no change needed if you haven't touched Traefik's `.env`.

The `.env` vars that matter:

- Traefik side (`core/traefik/.env`): `TRAEFIK_ACCESSLOG_FORMAT=json` and `TRAEFIK_ACCESSLOG_FILE=/var/log/traefik/access.log`
- CrowdSec side (`core/crowdsec/.env`): `TRAEFIK_LOG_PATH=../traefik/volumes/logs` (relative path — override with absolute if Traefik lives elsewhere)

### Setup

```bash
# 1. Create .env
cp .env.example .env
# Review: TZ, TRAEFIK_LOG_PATH, CROWDSEC_LOG_GID

# 2. Start the engine
docker compose up -d
```

No secrets needed — the engine generates its own internal credentials on first start.

### Verify

**First-boot takes ~5 minutes** before acquisition starts parsing. On startup the container runs `cscli hub update`, installs collections, loads parsers, then begins tailing the log file. During that window `cscli metrics` shows only `Local API Metrics` and `Local API Machines Metrics` — no Acquisition / Parser / Bucket tables. That is normal startup state, not a broken install. Wait about 5 minutes before running the verify commands.

```bash
# 1. Is the engine up?
docker exec crowdsec cscli lapi status
# Expected: "You can successfully interact with Local API (LAPI)"

# 2. Is Traefik's access log being parsed?
docker exec crowdsec cscli metrics show acquisition
# Expected: a row for file:/var/log/traefik/access.log
# with lines_read > 0 and lines_unparsed = 0 (or empty)
```

If both green, Phase 1 is done. The `cscli metrics show acquisition` form is preferred over grepping the full `cscli metrics` output — it returns a meaningful "no acquisition source running" message while startup is still in progress, instead of silently empty output.

Decisions may take additional minutes to appear — background internet scanners typically show up within the hour.

**What the metrics should look like once traffic is flowing:**

| Metric | Healthy value |
|--------|---------------|
| Lines read | > 0 (increases with traffic) |
| Lines parsed | = Lines read (no unparsed) |
| Lines poured to bucket | > 0 (scenarios are evaluating) |
| Alerts | Appear when suspicious patterns detected |
| Decisions | Appear when scenarios overflow (ban threshold reached) |

### Watching detection in production

Day-to-day monitoring once Phase 1 is running:

```bash
# Live detection stream
docker compose logs -f crowdsec

# All detected threats so far
docker exec crowdsec cscli alerts list

# Active bans (kept even without a bouncer — Phase 2/3 enforces them)
docker exec crowdsec cscli decisions list

# Drill into a specific alert
docker exec crowdsec cscli alerts inspect <ALERT_ID>
```

### Ad-hoc commands — only when you need them

Most of the time you won't touch these. Useful for false positives (unban) or manual testing.

```bash
# Manually ban an IP (e.g., one you've identified outside CrowdSec)
docker exec crowdsec cscli decisions add --ip 1.2.3.4 --duration 1h --reason "manual"

# Remove a specific ban (false positive / your own IP got caught)
docker exec crowdsec cscli decisions delete --ip 1.2.3.4

# Remove ALL decisions for an IP (captured-by-different-scenarios too)
docker exec crowdsec cscli decisions delete --ip 1.2.3.4 --all
```

### Maintenance — monthly or as needed

```bash
# Pull latest parsers / scenarios / collections from the Hub
docker exec crowdsec cscli hub update
docker exec crowdsec cscli hub upgrade

# Add a new data source (e.g., if you later add Nginx logs)
docker exec crowdsec cscli collections install crowdsecurity/nginx

# Inventory what's currently installed
docker exec crowdsec cscli parsers list
docker exec crowdsec cscli scenarios list
docker exec crowdsec cscli collections list
```

> **Bouncer setup** — the commands for generating bouncer API keys
> (`cscli bouncers add/list/delete`) belong to Phase 2 and Phase 3.
> See those sections below when you are ready to turn detection
> into enforcement.

### What to expect

- **Alerts appear** when CrowdSec detects suspicious patterns (probing, brute force, CVE attempts)
- **Decisions (bans)** are created when a scenario threshold is reached
- **Without a bouncer** (Phase 2/3), decisions are stored but not enforced — detection only
- **Community blocklist** downloads automatically after CAPI registration
- **Parsed lines** increase over time as Traefik processes requests

### Installed Collections

Collections are sets of parsers and scenarios for specific services. Configured via `CROWDSEC_COLLECTIONS` in `.env`:

| Collection | What it detects |
|------------|-----------------|
| `crowdsecurity/traefik` | Traefik log parser + HTTP attack scenarios |
| `crowdsecurity/http-cve` | Known CVE exploit attempts |
| `crowdsecurity/appsec-generic-rules` | Generic WAF rules (SQL injection, XSS, etc.) |
| `crowdsecurity/appsec-virtual-patching` | Virtual patches for known vulnerabilities |

Add more collections from the [CrowdSec Hub](https://hub.crowdsec.net/).

### Detected Scenarios

Scenarios that trigger on Traefik traffic:

| Scenario | What it detects |
|----------|-----------------|
| `crowdsecurity/http-probing` | Scanning for open ports and services |
| `crowdsecurity/http-sensitive-files` | Access attempts to `.env`, `.git`, `wp-config`, etc. |
| `crowdsecurity/http-admin-interface-probing` | Scanning for admin panels (`/admin`, `/wp-admin`) |
| `crowdsecurity/http-crawl-non_statics` | Aggressive crawling of dynamic pages |
| `crowdsecurity/http-path-traversal-probing` | `../` path traversal attempts |

---

## Phase 2: Traefik Bouncer Plugin

HTTP-layer enforcement. Configuration spans two directories: the bouncer API key is generated here, and the plugin itself is declared in `core/traefik/`.

### Generate the bouncer key

```bash
docker exec crowdsec cscli bouncers add traefik-bouncer
```

The command prints the key once — save it immediately.

### Wire the plugin in core/traefik/

1. Add the key to `core/traefik/.env` as `CROWDSEC_BOUNCER_KEY=<key>`.
2. Declare the plugin in `ops/templates/traefik.yml.tmpl` under `experimental.plugins`.
3. Uncomment the `sec-crowdsec` middleware block in `ops/templates/dynamic/integrations.yml.tmpl`.
4. Render the templates and restart Traefik:
   ```bash
   cd ../traefik
   ./ops/scripts/render.sh
   docker compose restart traefik
   ```
5. Add `sec-crowdsec@file` to the middleware list of routers that should be gated by the bouncer.

Full reference including the exact plugin block: `core/traefik/README.md`, section "CrowdSec Bouncer Plugin".

---

## Phase 3: Firewall Bouncer

Host-level enforcement via nftables. Installed as a system package (apt) and configured on the host — not inside any container — because it manipulates host firewall rules.

```bash
# Install the bouncer (on the host, not in a container)
sudo apt install crowdsec-firewall-bouncer-nftables

# Generate an API key from the CrowdSec Engine
docker exec crowdsec cscli bouncers add firewall-bouncer

# Configure the bouncer
sudo nano /etc/crowdsec/bouncers/crowdsec-firewall-bouncer.yaml
# Set:
#   api_url: http://127.0.0.1:8080/   (matches CROWDSEC_LAPI_PORT)
#   api_key: <key from the previous command>

# Apply
sudo systemctl restart crowdsec-firewall-bouncer
```

The bouncer polls CrowdSec's LAPI on `127.0.0.1:8080` (configurable via `CROWDSEC_LAPI_PORT`). Traefik is not in the path; the bouncer operates at the kernel firewall layer and covers every port on the host.

---

## Configuration Reference

### Log Acquisition (`config/acquis.yaml`)

Defines which log files CrowdSec monitors. Default: Traefik access logs.

To add more log sources (e.g. SSH):

```yaml
filenames:
  - /var/log/auth.log
labels:
  type: syslog
```

Mount the additional log file in `docker-compose.yml` and install the corresponding collection with `cscli collections install`.

### AppSec (`config/appsec.yaml`)

Application-level security analysis. The AppSec component listens on port 7422 and inspects HTTP requests forwarded by the Traefik bouncer plugin (Phase 2).

### Custom Profiles

To customize ban durations or remediation types, create `config/profiles.yaml` and mount it:

```yaml
# Example: ban for 4 hours instead of default
name: default_ip_remediation
filters:
  - Alert.Remediation == true && Alert.GetScope() == "Ip"
decisions:
  - type: ban
    duration: 4h
on_success: break
```

## Details

- [UPSTREAM.md](UPSTREAM.md) — Upstream reference, upgrade checklist
