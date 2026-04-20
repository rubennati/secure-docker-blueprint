# CrowdSec

Intrusion Detection and Prevention System (IDS/IPS) for the entire stack.

CrowdSec analyzes Traefik access logs, detects threats (brute force, CVE probes, aggressive crawling, path traversal), and stores security decisions. On its own it does **not block anything** — a separate "bouncer" enforces the decisions. You pick which enforcement layer you want.

---

## How it works — the three layers

Three independent components. The Engine is the brain; Phase 2 and Phase 3 are two different arms that actually block.

```
                      Internet
                         │
                         ▼
           ┌─────────────────────────────┐
   Phase 3 │  OS firewall (nftables)     │  drops packets at the host
           └─────────────┬───────────────┘  (before they reach Traefik)
                         ▼
           ┌─────────────────────────────┐
   Phase 2 │  Traefik Bouncer Plugin     │  rejects HTTP requests (403)
           └─────────────┬───────────────┘  at the proxy level
                         ▼
                    Your apps

           ┌─────────────────────────────┐
   Phase 1 │  CrowdSec Engine            │  reads Traefik logs,
           │  detect + decide            │  decides who's bad,
           └─────────────┬───────────────┘  stores decisions in its DB
                         │
             queried by Phase 2 + Phase 3
```

**Phase 1 is the only thing this directory runs.** Phase 2 configuration lives in `core/traefik/`; Phase 3 is an apt package on the host.

## Does Phase 1 alone do anything useful?

Yes — but it does **not** block. It:

- Shows you in real time who is probing your server (`cscli decisions list`)
- Builds a local threat database you can act on manually
- Optionally joins the CrowdSec community blocklist (downloads + contributes threat intel)
- Lets you tune scenarios before turning on enforcement (catches false positives before they bite legit users)

Phase 1 alone is **observability**. Attackers still reach your apps until you add Phase 2 or Phase 3.

## Which phases do you need?

| Goal | Setup |
|---|---|
| See who is attacking me | Phase 1 |
| Block HTTP attacks at Traefik | Phase 1 + Phase 2 |
| Block SSH brute force / non-HTTP at the firewall | Phase 1 + Phase 3 |
| Defense in depth (drop packets earlier + reject at HTTP) | Phase 1 + Phase 2 + Phase 3 |

Phase 3 is fully independent of Traefik — it operates at OS nftables level and will protect ports Traefik never sees (SSH, exposed database ports, etc.). Phase 2 is HTTP-only but gives richer feedback (403 with reason).

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

### Verify — first check after startup

Only two commands you need to see a green Phase 1:

```bash
# 1. Is the engine up?
docker exec crowdsec cscli lapi status
# Expected: "You can successfully interact with Local API (LAPI)"

# 2. Is Traefik's access log being parsed?
docker exec crowdsec cscli metrics | grep -A5 "Acquisition"
# Expected: file:/var/log/traefik/access.log  — lines read > 0, unparsed = 0
```

If both green, Phase 1 is done. Decisions may take a few minutes to appear — background internet scanners typically show up within the hour.

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

Turns Phase 1 decisions into actual HTTP-layer blocking. Configuration lives in `core/traefik/` — this directory only generates the bouncer API key.

### What you do here

```bash
# Generate the API key
docker exec crowdsec cscli bouncers add traefik-bouncer
# Save the key string that is printed — it's shown only once.
```

### What you do in core/traefik/

1. Paste the key as `CROWDSEC_BOUNCER_KEY=<key>` in `core/traefik/.env` (plain env var — the plugin reads it directly, no Docker Secret file needed)
2. Enable the plugin in `ops/templates/traefik.yml.tmpl` (static config — `experimental.plugins` block)
3. Uncomment the `sec-crowdsec` middleware in `ops/templates/dynamic/integrations.yml.tmpl`
4. Render + restart Traefik:
   ```bash
   cd ../traefik
   ./ops/scripts/render.sh
   docker compose restart traefik
   ```
5. Add `sec-crowdsec@file` to the middleware list of any router that should get the bouncer in front of it

The `core/traefik/README.md` section "CrowdSec Bouncer Plugin (optional)" has the full step-by-step.

---

## Phase 3: Firewall Bouncer (host-level, independent of Traefik)

Drops packets at the OS nftables level — runs before Traefik even sees the request. Useful for protecting non-HTTP ports (SSH, exposed databases) or for adding a pre-Traefik layer.

Phase 3 is an **apt package on the host**, not a Docker container, because it needs to manipulate host firewall rules.

```bash
# 1. Install on the host (not in a container)
sudo apt install crowdsec-firewall-bouncer-nftables

# 2. Generate a bouncer key from this CrowdSec container
docker exec crowdsec cscli bouncers add firewall-bouncer
# Save the printed key string.

# 3. Configure the host-side bouncer
sudo nano /etc/crowdsec/bouncers/crowdsec-firewall-bouncer.yaml
# Set:
#   api_url: http://127.0.0.1:8080/   (matches CROWDSEC_LAPI_PORT)
#   api_key: <the key from step 2>

# 4. Restart the service
sudo systemctl restart crowdsec-firewall-bouncer
```

The bouncer talks to CrowdSec's LAPI on `127.0.0.1:8080` (configurable via `CROWDSEC_LAPI_PORT` in this directory's `.env`). No Traefik involved.

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
