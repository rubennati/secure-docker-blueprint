# CrowdSec Dashboard

Visual visibility into alerts, decisions, and blocked IPs.

---

## What "dashboard" means here

The CrowdSec engine stores every detection event (alert) and every active ban (decision)
in its local database. Two paths exist to inspect that data:

- **CLI** — `cscli alerts list`, `cscli decisions list`, `cscli metrics` — covered in
  [`docs/runbook.md`](runbook.md). Sufficient for all operational tasks.
- **Web UI** — a visual interface showing the same data in graphs and tables, useful for
  at-a-glance status and historical trends without typing commands.

This document covers the web UI options. Neither is required — the CLI path is complete
on its own.

---

## Recommended option: CrowdSec Console

**What it is:** The official hosted dashboard from CrowdSec SAS at
[app.crowdsec.net](https://app.crowdsec.net). Free tier covers personal and homelab use
with no service limits that affect a single-server deployment.

**What it shows:**

- Active decisions and alert history with timeline graphs
- Blocked IP details: scenario that triggered the ban, duration, origin country
- Threat geography map
- Scenario and parser activity over time
- Community blocklist statistics (shared threat intelligence your engine contributes to
  and benefits from)

**What it does not replace:**

- Operational commands (unban, whitelist, emergency disable) — use the runbook
- Real-time log stream — `docker compose logs -f crowdsec`
- nftables enforcement state — `sudo nft list chain ip crowdsec crowdsec-chain`

### Opt-in — nothing is enabled by default

The CrowdSec engine does not enroll in the Console automatically. No data flows to
`app.crowdsec.net` until you run the enrollment command. The blueprint ships with
Console enrollment disabled.

### Privacy and external dependency

Enrolling the Console enables the CrowdSec Central API (CAPI). CAPI sends the following
to CrowdSec SAS servers (hosted in France, EU jurisdiction):

- Alert metadata: scenario name, triggered timestamp, source IP, country
- Decision metadata: ban duration, source IP
- Engine version and instance identifier

**What is not sent:** request bodies, response data, user credentials, application
content, or private file contents.

Note: if your engine is already registered with CAPI for community threat intel sharing
(the default after first start), this data already flows. The Console adds a visual
interface on top of what CAPI already receives — it does not introduce a new data
category.

If you prefer to keep all data local, skip enrollment and use the CLI path instead.

### Enrollment

**Prerequisites:** the CrowdSec engine container must be running.

```bash
# 1. Create a free account at https://app.crowdsec.net
#    (required to receive the enrollment key)

# 2. In the Console: Security Engines → Add → copy the enrollment key

# 3. Enroll from the host:
docker exec crowdsec cscli console enroll <your-enrollment-key>

# 4. Restart the engine to activate the Console connection
docker compose restart crowdsec

# 5. Back in the Console: accept the engine under Security Engines
#    The engine appears as pending until you confirm it there
```

Enrollment is persistent — it survives container restarts and engine upgrades. No
changes to `docker-compose.yml` or `.env` are required.

### Verify enrollment

```bash
# Check Console status
docker exec crowdsec cscli console status
# Expected: "You are enrolled in CrowdSec Console"
# and a list of enabled sharing options (alerts, decisions, etc.)

# Engine visible in Console?
# https://app.crowdsec.net → Security Engines
# Your engine should appear with a green status indicator
```

### Unenroll

```bash
docker exec crowdsec cscli console unenroll
docker compose restart crowdsec
```

After unenrolling, the Console connection is removed. The engine remains fully
functional: CAPI participation continues (community blocklist sharing is unaffected),
and Phase 2 and Phase 3 bouncers continue operating normally.

### Console tier limits

The free tier is sufficient for a single-server homelab. As of v1.7.7, there are no
alert or decision count limits that would affect this blueprint. Check the current
pricing page at [crowdsec.net/pricing](https://www.crowdsec.net/pricing) before
enrolling if your situation has changed.

---

## CLI alternative — no external dependency

If you do not want data leaving the server, the runbook provides complete operational
coverage via CLI. Every piece of information the Console shows is also available locally:

| Console view | CLI equivalent |
|---|---|
| Active decisions | `docker exec crowdsec cscli decisions list` |
| Alert history | `docker exec crowdsec cscli alerts list` |
| Scenario activity | `docker exec crowdsec cscli metrics show scenarios` |
| Blocked IP detail | `docker exec crowdsec cscli alerts inspect <ALERT_ID>` |
| nftables enforcement | `sudo nft list chain ip crowdsec crowdsec-chain` |

Full reference: [`docs/runbook.md`](runbook.md) → §2 Monitoring & Inspection.

The CLI path has no time-series history (metrics reset on container restart) and no
geography map. For a homelab these are informational gaps, not operational ones.

---

## Deferred options

### Prometheus + Grafana — deferred to v0.8.0 Monitoring

CrowdSec exposes a Prometheus metrics endpoint when enabled in the engine configuration.
An official Grafana dashboard template exists. This combination provides fully self-hosted,
time-series metrics with persistent history.

It is not implemented here because:

- It requires Prometheus and Grafana containers — meaningful infrastructure to add for
  one service's dashboard
- The v0.8.0 Monitoring pass already includes Beszel and Grafana for the whole stack;
  adding them now would pre-empt that work inconsistently
- The ROADMAP explicitly defers Grafana/Loki to a later pass

When v0.8.0 Monitoring is implemented, connecting CrowdSec's Prometheus endpoint to the
shared Grafana instance is the right integration point — not a separate dashboard here.

### Metabase — deprecated, do not use

CrowdSec previously shipped `crowdsecurity/crowdsec-metabase` as a self-hosted
dashboard. It has been deprecated since approximately v1.5 and is unmaintained. The
Docker image still exists but is not updated and is incompatible with the current
CrowdSec database schema. Do not use it.
