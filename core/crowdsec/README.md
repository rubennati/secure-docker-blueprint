# CrowdSec

Intrusion Detection and Prevention System (IDS/IPS) for the entire stack.

CrowdSec analyzes Traefik access logs, detects threats (brute force, CVE probes, aggressive crawling, path traversal), and stores security decisions. On its own it does **not block anything** — a separate "bouncer" enforces the decisions. You pick which enforcement layer you want.

---

## Architecture

Three independent components. The Engine parses logs and decides; the two bouncers enforce at different network layers.

```text
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

**If the acquisition table is empty (no row at all) even after the 5-minute startup window**, this is usually not a broken install — two things commonly delay it:

1. **CrowdSec tails from the end of the file, not the beginning** (`Starting tail (offset: 0, whence: 2)` in the engine log). Any Traefik traffic that happened *before* the CrowdSec container started is invisible to it — only new lines written after that point count.
2. **`TRAEFIK_ACCESSLOG_BUFFER`** (default `100` in `core/traefik/.env`) batches access-log writes — on a quiet server, a handful of requests may not be enough to trigger a flush to disk yet.

To force a flush and confirm ingestion actually works, generate enough local traffic directly against Traefik (no DNS needed, works even if the only reachable app uses `acc-tailscale` and blocks self-curls with 403 — the access-log line is written either way):

```bash
for i in $(seq 1 110); do
  curl -sk -o /dev/null -H "Host: <any-app-domain-with-a-router>" https://127.0.0.1/
done
docker exec crowdsec cscli metrics show acquisition
```

Expect `lines_read`/`lines_parsed` to jump to the request count. A `lines_whitelisted` count equal to `lines_read` is normal here too — CrowdSec's built-in whitelists recognize private/loopback-range source IPs (like the `172.x.x.x` Docker-gateway address a self-curl produces — see [`docs/standards/troubleshooting.md`](../../docs/standards/troubleshooting.md) "Common IP problems") as non-threatening test traffic, not a sign anything is misconfigured.

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

## The community blocklist — what you get, what you send

The engine registers with CrowdSec's Central API on first start and both pulls and
pushes. It is on by default, and it is a trade rather than a subscription.

**What arrives.** Measured on a host running this blueprint: **15,880 active
decisions**, essentially all of them `Source: CAPI`. Addresses other installations
detected attacking them.

**What leaves.** The address that triggered, which scenario fired, a timestamp.
Not the request — `context` is off by default, so URLs, headers and bodies stay
on your host. Check yours:

```bash
docker exec crowdsec cscli console status   # what is forwarded
docker exec crowdsec cscli capi status      # registration and sharing
```

**Whether it is worth it.** Over fourteen hours this host's own engine produced
two genuine detections — probes for a Jira CVE, against software it does not
even run. The community list supplied 15,880. That is not a close comparison,
and the imbalance is structural: local detection can only see what reaches you,
while the list is what reached everyone else first.

Turning sharing off also ends the pull; the two are one arrangement. CrowdSec is
a French company, so for EU deployments the data leaving is at least staying
inside that jurisdiction — but it is a data flow, and it should be a decision, not
a default.

**The cost is not security, it is diagnosis.** A packet dropped by the firewall
bouncer produces no log line anywhere — not in the proxy's access log, not in the
application. Same blind spot as an access policy, except these addresses were
chosen by somebody else.

The scenario to be ready for: a client sits behind an address that reached the
list — shared CGNAT, a compromised neighbour, a VPN exit. For them the site does
not load, and nothing anywhere says why. One command answers it:

```bash
docker exec crowdsec cscli decisions list --ip <address>
```

That belongs at the *start* of "the site does not work for me", not at the end.
To clear one:

```bash
docker exec crowdsec cscli decisions delete --ip <address>
```

Note that the firewall bouncer cannot filter by origin — it enforces every
decision or none. Keeping community decisions at the proxy layer only, where a
403 at least leaves a log line, is not something the current tooling offers.

## Phase 2: Traefik Bouncer Plugin

HTTP-layer enforcement. Configuration spans two directories: the bouncer API key is generated here, and the plugin itself is declared in `core/traefik/`.

> **Before attaching the bouncer to anything, read [docs/profiles.md](docs/profiles.md).**
> HTTP enforcement is modelled as a small family of named, per-app profiles
> (`crowdsec-basic` → `crowdsec-appsec` → `crowdsec-strict`), chosen independently of
> the `acc-*` access and `sec-N` header axes — not one generic `sec-crowdsec` applied
> everywhere. That document also defines the whoami-first validation path, what is
> per-app vs global, and why geo is a deferred, separate mechanism. The steps below are
> the raw plugin enablement those profiles build on.

### Generate the bouncer key

```bash
docker exec crowdsec cscli bouncers add traefik-bouncer
```

The command prints the key once — save it immediately.

### Wire the plugin in core/traefik/

1. Add the key to `core/traefik/.env` as `CROWDSEC_BOUNCER_KEY=<key>`.
2. Declare the plugin in `ops/templates/traefik.yml.tmpl` under `experimental.plugins`.
3. Uncomment the `crowdsec-basic` middleware block in `ops/templates/dynamic/integrations.yml.tmpl`.
4. Render the templates and restart Traefik:

   ```bash
   cd ../traefik
   ./ops/scripts/render.sh
   docker compose up -d --force-recreate traefik
   ```

5. **Required, not optional — do this before verifying.** Add `crowdsec-basic@file` as the **first** middleware on the router. The plugin loading successfully (steps 1–4) does not make the bouncer do anything by itself: its polling loop only starts once the middleware is actually attached to a router's request path. Skip this step and `cscli bouncers list` will never show a `Last API pull` — no error anywhere, it just silently never starts. See [`docs/bugfixes/traefik-crowdsec-plugin-2026-04-20.md`](../../docs/bugfixes/traefik-crowdsec-plugin-2026-04-20.md) "Bug #3" if this happens. Start with `core/whoami` — see [docs/profiles.md](docs/profiles.md) "whoami-first validation". Example label:

   ```yaml
   - "traefik.http.routers.${COMPOSE_PROJECT_NAME}.middlewares=crowdsec-basic@file,${APP_TRAEFIK_ACCESS}@file,${APP_TRAEFIK_SECURITY}@file"
   ```

   ```bash
   cd ../whoami   # or whichever app you edited
   docker compose up -d --force-recreate
   ```

Full reference including the exact plugin block: `core/traefik/README.md`, section "CrowdSec Bouncer Plugin".

### Phase 2 verify

Four checks, in order. Run after **step 5** (not just step 4) — check #2 depends on at least one router actually using the middleware.

```bash
# 1. Plugin loaded successfully in Traefik?
docker compose -f ../traefik/docker-compose.yml logs traefik 2>&1 \
  | grep -iE "plugin|bouncer" | tail -5
# Expected: "Plugin bouncer loaded" — no "Plugins are disabled"
# If "Plugins are disabled because an error has occurred":
# read-only FS is blocking /plugins-storage. See
# docs/bugfixes/traefik-crowdsec-plugin-2026-04-20.md.

# 2. Bouncer actively pulls from CrowdSec?
docker exec crowdsec cscli bouncers list
# Expected: traefik-bouncer with a non-empty IP Address and a
# recent "Last API pull" timestamp (within ~60 s).

# 3. Middleware visible in Traefik dashboard?
# https://<traefik-host>/dashboard/#/http/middlewares
# Find crowdsec-basic@file — Status must be green "Success".
# If "invalid middleware type or middleware does not exist":
# plugin did not load (check 1).

# 4. Functional ban test — proves end-to-end enforcement
docker exec crowdsec cscli decisions add \
  --ip <an-IP-you-can-reach-the-app-from> \
  --duration 3m --reason "phase2-verify"

# Wait for the plugin to pull the new decision (stream mode polls
# every 60 s — do not test before that window elapses, or you will
# still see the cached empty list and assume the ban is not enforced).
sleep 65

# From that IP, the protected app must now return HTTP 403.
# After verifying, clean up:
docker exec crowdsec cscli decisions delete \
  --ip <an-IP-you-can-reach-the-app-from>
```

Do not ban the IP you administer the server from (Tailscale, LAN admin subnet) unless you have a separate path back in — the ban also blocks the Traefik dashboard, Dockhand, Portainer, etc.

---

## Phase 3: Firewall Bouncer

Host-level enforcement via nftables. Installed as a system package (`apt`) on the host
— not inside any container — because it manipulates host kernel firewall rules directly.

The bouncer polls the CrowdSec LAPI on `127.0.0.1:8080` and translates active decisions
into nftables drop rules. Traffic from banned IPs is dropped before any service sees it
— Traefik, SSH, or otherwise. Phase 3 is the only enforcement layer that covers ports
Traefik does not terminate.

**Full setup, SSH detection, verify steps, edge cases, and troubleshooting:**
→ [`docs/firewall-bouncer.md`](docs/firewall-bouncer.md)

---

## Configuration Reference

### Log Acquisition (`config/acquis.yaml`)

Defines which log files CrowdSec monitors. Default: Traefik access logs in JSON format.

The file ships with a commented-out SSH block. Uncomment it to enable SSH brute-force
detection alongside Phase 3 — see [`docs/firewall-bouncer.md`](docs/firewall-bouncer.md)
→ "SSH detection" for the full activation steps (volume mount + collection + restart).

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

## Backup

| | |
|---|---|
| **Database** | SQLite inside `./volumes/data` — no database server, and no dump hook |
| **State** | `./volumes/data` (decisions, alerts, machine and bouncer credentials) · `./volumes/config` (installed collections, parsers, local API credentials) |
| **Reproducible** | the acquisition config in `./config/` — versioned in git, not on the host |
| **Quiescing** | **Required.** A file-level copy of a live SQLite database can capture a torn state that restores as a corrupt file. Stop the container, or snapshot the filesystem, before copying `volumes/data`. |

No database hook: borgmatic's SQLite support addresses a file, and this one lives
inside the data directory rather than being declared separately. Back the
directory up as a source directory and quiesce it.

**The bouncer credentials are the operational part.** They live in
`volumes/config` and are registered against the local API in `volumes/data`. Restoring
one without the other leaves bouncers that authenticate against an API that has
never heard of them — Traefik then fails open or closed depending on its own
configuration, and neither is what you intended.

Losing the decision list itself is survivable: bans rebuild from live traffic.
Losing the credentials means re-enrolling every bouncer by hand.

## Details

- [UPSTREAM.md](UPSTREAM.md) — Upstream reference, upgrade checklist
- [docs/profiles.md](docs/profiles.md) — Traefik bouncer profile architecture: the `crowdsec-*` per-app profile family, what is per-app vs global, three-level enforcement model, geo/AppSec feasibility, whoami-first validation
- [docs/runbook.md](docs/runbook.md) — Day-to-day operations: health checks, whitelisting, false positive handling, emergency procedures, maintenance, troubleshooting
- [docs/firewall-bouncer.md](docs/firewall-bouncer.md) — Phase 3 setup, SSH detection, verify steps, edge cases
- [docs/dashboard.md](docs/dashboard.md) — Visual dashboard options: CrowdSec Console (opt-in), CLI alternative, deferred Prometheus/Grafana path
- [docs/geoblocking.md](docs/geoblocking.md) — Country-level blocking: GeoIP enrichment, manual country decisions, automated scenario, Phase 2/3 interaction, self-lockout prevention, trade-offs
- [docs/appsec.md](docs/appsec.md) — AppSec / WAF: how request-level inspection works, enabling safely, failure mode trade-offs, application-specific false positives, exclusions, emergency disable
