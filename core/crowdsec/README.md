# CrowdSec

Intrusion Detection and Prevention System (IDS/IPS) for the entire stack.

CrowdSec analyzes Traefik access logs and produces security decisions (ban, captcha) based on community-maintained threat intelligence and local log analysis.

## Architecture

CrowdSec is deployed in three phases:

| Phase | Component | Scope | Status |
|-------|-----------|-------|--------|
| 1 | **Security Engine** (this service) | Detection — analyzes logs, produces decisions | Ready |
| 2 | **Traefik Bouncer Plugin** | HTTP enforcement — blocks malicious requests | Requires Traefik changes |
| 3 | **Firewall Bouncer** | IP-level enforcement — nftables rules on host | Host-level install |

```
Internet
   |
Traefik + CrowdSec Plugin    <-- Phase 2: HTTP enforcement
   |
Docker Services
   |
Host nftables                 <-- Phase 3: IP-level enforcement
   |
CrowdSec Engine               <-- Phase 1: Detection (logs -> decisions)
```

## Phase 1: Security Engine (this setup)

The engine collects and analyzes logs, detects threats, and stores decisions. It doesn't block anything on its own — it needs a bouncer (Phase 2 or 3) to enforce decisions.

What it does right now:
- Parses Traefik access logs in real-time
- Detects: brute force, aggressive crawling, CVE probes, suspicious HTTP patterns
- Stores ban decisions in its local database
- Shares threat intelligence with the CrowdSec community network
- Provides AppSec / WAF analysis on port 7422

### Setup

```bash
# 1. Create .env
cp .env.example .env
# Edit: TIMEZONE, TRAEFIK_LOG_PATH, CROWDSEC_LOG_GID

# 2. Start the engine
docker compose up -d
```

No secrets needed — the engine generates its own internal credentials on first start.

### Prerequisites

Traefik must write access logs in **JSON format**. Add to your Traefik static config:

```yaml
accessLog:
  filePath: /var/log/traefik/access.log
  format: json
```

The `TRAEFIK_LOG_PATH` in `.env` defaults to `../traefik/volumes/logs` (relative).
Override with absolute path if Traefik is elsewhere.

### Verify

```bash
# Check engine status
docker exec crowdsec cscli lapi status

# View metrics (parsed logs, active decisions)
docker exec crowdsec cscli metrics

# List installed collections
docker exec crowdsec cscli collections list

# List active decisions (bans)
docker exec crowdsec cscli decisions list

# List all alerts (detected threats)
docker exec crowdsec cscli alerts list

# Check if Traefik logs are being parsed
docker exec crowdsec cscli metrics | grep -A5 "Acquisition"
```

### Monitoring

```bash
# Live logs (real-time detection)
docker compose logs -f crowdsec

# Test: manually ban an IP
docker exec crowdsec cscli decisions add --ip 1.2.3.4 --duration 1h --reason "test ban"

# Remove a test ban
docker exec crowdsec cscli decisions delete --ip 1.2.3.4

# Update threat intelligence
docker exec crowdsec cscli hub update && docker exec crowdsec cscli hub upgrade

# Generate bouncer API key (needed for Phase 2)
docker exec crowdsec cscli bouncers add traefik-bouncer
```

### What to expect

- **No alerts initially** — normal, CrowdSec only alerts on suspicious patterns
- **Empty decisions list** — normal without Phase 2 (Bouncer), engine detects but doesn't block
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

## Phase 2: Traefik Bouncer Plugin (future)

Requires changes to `core/traefik/`:
- CrowdSec plugin in Traefik static config
- CrowdSec middleware in Traefik dynamic config
- Bouncer API key generated from this engine

Generate the bouncer key:

```bash
docker exec crowdsec cscli bouncers add traefik-bouncer
```

This outputs an API key that the Traefik plugin uses to query the engine. Details will be documented when Phase 2 is implemented.

## Phase 3: Firewall Bouncer (future)

Host-level IP blocking via nftables. This is an **apt package on the host**, not a Docker container.

```bash
# Install on the host
sudo apt install crowdsec-firewall-bouncer-nftables

# Generate bouncer key
docker exec crowdsec cscli bouncers add firewall-bouncer

# Configure: /etc/crowdsec/bouncers/crowdsec-firewall-bouncer.yaml
# Set api_url and api_key, then restart the service
```

The firewall bouncer connects to the LAPI port exposed on `127.0.0.1:8080` (configurable via `CROWDSEC_LAPI_PORT`).

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

Mount the additional log file in `docker-compose.yml` and add the corresponding collection.

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
