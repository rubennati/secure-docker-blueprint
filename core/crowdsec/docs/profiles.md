# CrowdSec Traefik Profiles — architecture

How CrowdSec HTTP enforcement is modelled in this blueprint: an **optional**
component, off as shipped, that an installation enables as **one decision for
the whole deployment** — placed on the reverse proxy's entrypoint in front of
every router, in two strengths: decisions only, or decisions plus AppSec
inspection — with a third strength and a geo mechanism deferred. Nothing here
assumes it is on, or that a server already runs it.

This document is the architecture and the roadmap. It defines the middleware
names, what each one does, what the underlying tooling can and cannot do per
app, and the whoami-first path to turning it on. **Nothing here is enabled by
default** — the Traefik plugin and the two middlewares exist only with
`CROWDSEC_BOUNCER_ENABLED=true` in `core/traefik/.env`. See
[§ Implemented vs deferred](#implemented-vs-deferred) for the exact status.

---

## Where CrowdSec sits — the entrypoint, not a router position

Every app router in this blueprint carries four middlewares from its own `.env`
(access, limit, headers, auth — [`docs/standards/traefik-security.md`](../../../docs/standards/traefik-security.md)).
Threat enforcement is none of them. `render.sh` places it on the `websecure`
entrypoint, where it runs before any router's list:

```text
entrypoint websecure:  threat-crowdsec@file, compress@file
router:                ${APP_TRAEFIK_ACCESS}@file, ${APP_TRAEFIK_LIMIT}@file, ${APP_TRAEFIK_HEADERS}@file, ${APP_TRAEFIK_AUTH}
                       └── reject banned IPs first ──┘ └─ who ─┘ └─ how fast ─┘ └─ headers ─┘ └─ gate ─┘
```

| Decision | Where | Answers | Values |
|------|--------|---------|----------|
| **Threat enforcement** | the entrypoint, by switch | *Which known-bad traffic is rejected?* — for every router at once | `threat-crowdsec`, `threat-crowdsec-appsec` |
| **Access** | router position 1, per stack | *Who* may reach this app? | `access-public`, `access-vpn`, `access-blocked`, … |

A banned address is rejected before any access check, counter, header or CSP
processing runs. The choice is a deployment's, not an application's: with the
switch on, every router on the entrypoint is behind the bouncer and none can
opt out; an address that must never be refused — the operator's own — is a
CrowdSec **AllowList** (`CROWDSEC_ALLOWLIST_ADMIN`, `ops/allowlist.sh`), which
holds against every decision the engine serves. That is what makes the bouncer
safe to put in front of everything: the exemption lives where the decisions
live. The same holds for AppSec: `CROWDSEC_APPSEC_ENABLED` inspects every
router's requests, so one application with known false positives (the table
in [appsec.md](appsec.md)) keeps the whole deployment at decisions only until
a path-scoped exclusion exists.

> This replaced the per-router slot (`APP_TRAEFIK_THREAT`) on 2026-10-22, with
> the middleware model (decision D1 of 2026-10-18): threat enforcement is a
> property of the deployment, and a per-router choice left most routers without
> it. The entrypoint list is static configuration — after a render that switches
> the bouncer off, recreate the Traefik container at once, or every router is
> disabled until then (the dynamic file is gone, the running list still names it).

---

## What belongs where

CrowdSec spans two directories and several distinct concerns. Knowing which knob
lives where prevents the most common mistakes (editing the wrong layer, or expecting
per-app behaviour from a global control).

| # | Concern | Lives in | Scope |
|---|---------|----------|-------|
| 1 | Traefik **static plugin** load (`experimental.plugins.bouncer`) | `core/traefik/ops/templates/traefik.yml.tmpl` | Loaded once per Traefik process. Requires a **restart** to change. |
| 2 | Traefik **dynamic middlewares** (`threat-crowdsec`, `threat-crowdsec-appsec`) | `core/traefik/ops/templates/dynamic/crowdsec.yml.tmpl`, rendered only with `CROWDSEC_BOUNCER_ENABLED=true` | Defined once. **Hot-reloaded**. Which of the two the entrypoint carries is `CROWDSEC_APPSEC_ENABLED`. |
| 3 | CrowdSec **LAPI / decisions** (bans) | `core/crowdsec/` engine | **Global** to the source IP. Every bouncer that polls LAPI enforces the same list. |
| 4 | **Parsers / scenarios / collections** | `core/crowdsec/` engine + Hub | Global. Detection logic; not per app. |
| 5 | **AppSec / WAF** engine + rules | `core/crowdsec/` (port `7422`) | Engine + rule sets are **global**; *invocation* is the deployment's switch (`CROWDSEC_APPSEC_ENABLED`). |
| 6 | **Geo enforcement** | CrowdSec country decisions (global) **or** an edge/geo mechanism (deferred) | See the `geo-*` profiles in [§ The middleware family](#the-middleware-family). Country decisions are global, not per app. |
| 7 | **Host-firewall remediation** (nftables bouncer) | Host apt package | Global, all ports. Not per app. See [firewall-bouncer.md](firewall-bouncer.md). |
| 8 | **Placement** | `entryPoints.websecure.http.middlewares` in `config/traefik.yml`, written by `render.sh` | The deployment. Static configuration: a change takes effect on a recreate of the Traefik container. |

The model controls axes **2** and **8**. Axes 3–7 are global engine behaviour
and cannot be made per-app by naming more middlewares — a constraint that shapes
the whole design below.

---

## Capability reality — per-app vs global

What the maxlerebourg CrowdSec Traefik plugin (`v1.7.1`) and the CrowdSec engine can
actually do, grounded in [appsec.md](appsec.md) and [geoblocking.md](geoblocking.md):

| Question | Answer | Consequence for the model |
|----------|--------|---------------------------|
| Can multiple CrowdSec middlewares exist with different names? | **Yes.** The plugin is loaded once; each `http.middlewares.<name>.plugin.bouncer` block is an independent instance with its own settings. | The two middlewares (`threat-crowdsec`, `threat-crowdsec-appsec`) are real and supported; the entrypoint carries one of them. |
| Can they share one bouncer key? | **Yes.** All instances may use the same `crowdsecLapiKey`; they appear as one bouncer in `cscli bouncers list` and each polls independently. | One key is the default. Use separate keys only if you want per-profile metrics. |
| Is AppSec per-middleware or global? | **Both.** `crowdsecAppsecEnabled` is a *per-middleware* toggle — but the AppSec **engine and rule sets are global** (single process at `crowdsec:7422`), and in this blueprint the invocation is a deployment switch, not a per-app choice. | `threat-crowdsec-appsec` (AppSec on) replaces `threat-crowdsec` (AppSec off) on the entrypoint when `CROWDSEC_APPSEC_ENABLED=true`. Per-app *rules* cannot exist — only path-scoped exclusions in the engine. |
| Can geo be a per-app middleware profile? | **No.** Geo is enforced through CrowdSec **decisions**, which are IP/country-scoped and **global** to every bouncer polling LAPI. | A per-app geo *profile* via the plugin is not possible. |
| Is geo blocking global to the source IP? | **Yes.** `cscli decisions add --scope Country --value XX` bans that country for the whole stack. | Geo today is stack-wide **blocklist**, never per-app **allowlist**. |
| Can DACH-only / EU-only be done safely per app with current tooling? | **No.** CrowdSec does country *blocklisting* (ban country X), not per-app *allowlisting* (allow only DACH/EU). | Deferred; needs a different mechanism (edge or a Traefik geo plugin). |
| Does the plugin support allowlist-style geo directly? | **No.** It is a decision-enforcement bouncer (+ optional AppSec forwarding). It has no GeoIP allowlist feature. | Geo allowlist is out of the CrowdSec axis entirely. |
| Safest minimal primitive to introduce first? | **`threat-crowdsec`** — stream mode, IP/decision bouncer only, AppSec off, fail-open. | This is what the bouncer switch places; validate it on whoami first. |

---

## The middleware family

Names use the **`threat-`** prefix of the model's entrypoint position. Geo is
named **`geo-*`** because it is *not* a CrowdSec-plugin mechanism — see below.

| Middleware | Blocks on | AppSec | Geo | Failure mode | Lockout risk | Status |
|---------|-----------|--------|-----|--------------|--------------|--------|
| `threat-crowdsec` | LAPI IP/country **decisions** | off | none | **fail-open** (stream cache; LAPI outage does not block) | **Low** | **Shipped** — placed by `CROWDSEC_BOUNCER_ENABLED` |
| `threat-crowdsec-appsec` | decisions **+ WAF** signatures | on | none | fail-open (AppSec error/unreachable → allow) | Medium (false positives) | **Shipped** — placed instead by `CROWDSEC_APPSEC_ENABLED` |
| `threat-crowdsec-strict` | decisions **+ WAF** signatures | on | none | **fail-closed** (AppSec error/unreachable → 403) | **High** | Deferred |
| `geo-dach` / `geo-eu` | country allowlist (edge/geo plugin) | n/a | allowlist | depends on mechanism | High | Deferred — not plugin-native |

### `threat-crowdsec`

- **Purpose:** reject IPs CrowdSec has already decided are malicious (scenario bans + community blocklist + any manual/country decisions).
- **Intended for:** a deployment that chooses to honour CrowdSec's ban list on its public routes, once validated on whoami. With the switch on it stands in front of every router, the VPN-only ones included — there it costs one lookup in the cached decision list and refuses nothing a closed access policy would not refuse anyway. A deployment without it is complete: the access policies, counters and headers do not depend on it.
- **Blocks:** requests from IPs with an active LAPI decision → HTTP 403. No request-body inspection.
- **AppSec:** no. **Geo:** none (though *global* country decisions, if the operator adds any, are enforced here too — that is a stack-wide engine choice).
- **Failure mode:** fail-open. Stream mode serves the last cached decision list; a CrowdSec outage does not block legitimate traffic.
- **The operator's own address:** an AllowList in the engine (`CROWDSEC_ALLOWLIST_ADMIN`), never a label — there is no per-router exemption.

### `threat-crowdsec-appsec`

- **Purpose:** `threat-crowdsec` **plus** synchronous WAF inspection of each request (SQLi, XSS, path traversal, virtual patches) via the AppSec engine.
- **Intended for:** a deployment whose public applications' traffic has been tested against the WAF and shown clean — after the engine is confirmed reachable from Traefik. It replaces `threat-crowdsec` on the entrypoint for every router at once (`CROWDSEC_APPSEC_ENABLED=true`).
- **Blocks:** banned IPs **and** individual requests matching a WAF rule. AppSec blocks the request without creating an IP ban (see [appsec.md](appsec.md)).
- **AppSec:** yes, **fail-open** (`crowdsecAppsecFailureBlock: false`, `crowdsecAppsecUnreachableBlock: false`).
- **When not to use:** while an application has known WAF false positives and no path-scoped exclusion for them — Nextcloud WebDAV, Paperless/Seafile/WordPress uploads, Authentik SAML, Invoice Ninja webhooks (full table in [appsec.md](appsec.md)). Because the switch is for every router, one such application holds the whole deployment at `threat-crowdsec`.

### `threat-crowdsec-strict` (deferred)

- **Purpose:** maximum HTTP enforcement — `threat-crowdsec-appsec` with **fail-closed** AppSec.
- **Intended for:** high-value apps where a failed WAF should be treated as an incident, **and only** with a proven out-of-band recovery path.
- **Failure mode:** **fail-closed** — if AppSec errors or is unreachable, every request returns 403. A CrowdSec restart race can cut all traffic on that router.
- **When not to use:** a deployment without a VPN/LAN/console recovery path; one not first run for days under `threat-crowdsec-appsec` (fail-open) without incident.

### `geo-dach` / `geo-eu` (deferred, not plugin-native)

- **Purpose:** restrict an app to DACH or EU client geographies (allowlist).
- **Why deferred:** the CrowdSec plugin cannot express a per-app geo allowlist. CrowdSec geo is global, IP/country-scoped, and **blocklist**-only (ban country X for the whole stack — [geoblocking.md](geoblocking.md)). Allowlisting "only DACH/EU" would mean blocklisting every other country, globally — impractical and not per app.
- **Candidate mechanisms (open decision):**
  1. **Cloudflare edge rules** — Cloudflare already fronts this stack; country allow/deny at the edge is the most natural and lowest-risk home for geo. Not a Traefik/CrowdSec change.
  2. **A dedicated Traefik GeoIP plugin** — a *separate* `experimental.plugins` entry + MaxMind DB; per-app middleware, but a new dependency to vet.
  3. **Global CrowdSec country blocklist** — available today ([geoblocking.md](geoblocking.md)) but stack-wide, not per app, and blunt.
- The `geo-*` name (not `crowdsec-*`) is deliberate: whichever mechanism wins, geo is a different layer from CrowdSec decision enforcement.

---

## Three-level enforcement model

The CrowdSec axis is a clean three-step ramp of **enforcement strength**. Geo is *not*
a level on this ramp — it is the orthogonal `geo-*` axis above.

| Level | Middleware | Adds | Gate to adopt |
|-------|---------|------|---------------|
| 1 | `threat-crowdsec` | IP/decision bouncer, fail-open | whoami validation passes |
| 2 | `threat-crowdsec-appsec` | + WAF, fail-open | AppSec reachable + false-positive testing of every public application |
| 3 | `threat-crowdsec-strict` | + WAF, fail-closed | days stable at level 2 + proven recovery path |

Move one level at a time, for the deployment. Most deployments stop at level 1;
level 2 is for one whose public applications have been WAF-tested; level 3 is
rare and deliberate.

---

## whoami-first validation

Always prove the path on `apps/whoami` — a throwaway fixture — before relying on
the bouncer for a real app. The switch places the middleware in front of every
router, so whoami is where the proof is read, not where the bouncer is attached;
the plugin's polling loop starts with the recreate that applies the entrypoint
list.

**All steps are operator-local. Rendered `config/` and `.env` are gitignored —
nothing here is committed.**

1. **Switch the integration on** (steps 3–4 of "How to enable" in
   [`core/traefik/README.md`](../../traefik/README.md)): in `core/traefik/.env` set
   `CROWDSEC_BOUNCER_ENABLED=true`, `CROWDSEC_BOUNCER_PLUGIN_VERSION` and
   `CROWDSEC_BOUNCER_KEY`, then `./ops/scripts/render.sh && ./ops/scripts/validate.sh
   && docker compose up -d --force-recreate traefik`. The plugin block, the
   entrypoint list and the `threat-crowdsec` / `threat-crowdsec-appsec`
   middlewares are rendered from
   [`crowdsec.yml.tmpl`](../../traefik/ops/templates/dynamic/crowdsec.yml.tmpl) and
   `traefik.yml.tmpl`; no template is edited.

   > `render.sh` runs `envsubst`. An unset `CROWDSEC_BOUNCER_KEY` renders an **empty**
   > key and the bouncer cannot authenticate. Set the key before rendering.

2. **Keep AppSec disabled** for first validation (`CROWDSEC_APPSEC_ENABLED=false`,
   the default — `threat-crowdsec` is what the entrypoint carries).
3. **Reach whoami.** Nothing is attached by hand: the entrypoint already puts the
   bouncer in front of whoami's router. whoami defaults to `access-vpn`, so the
   test request must actually reach it: test from a VPN-connected device, or set
   `APP_TRAEFIK_ACCESS=access-public` on whoami **for the test only**.
4. **Confirm the bouncer is live:** `docker exec crowdsec cscli bouncers list` shows
   a recent "Last API pull" (within ~60 s).
5. **Ban a test IP — never your admin IP.** Use a second device/IP you control
   (phone on cellular, a VPS) that is **not** your Tailscale/LAN admin path:

   ```bash
   docker exec crowdsec cscli decisions add --ip <TEST_IP> --duration 3m --reason whoami-validate
   sleep 65   # stream mode polls every 60 s
   # From <TEST_IP>, whoami must return 403. From your admin path, it must still load.
   docker exec crowdsec cscli decisions delete --ip <TEST_IP>
   ```

6. **Validate rollback:** restore `access-vpn` on whoami if it was changed and
   `docker compose up -d` there. The bouncer stays in front of every router; the
   way to switch it off is `CROWDSEC_BOUNCER_ENABLED=false`, a render and an
   immediate recreate of Traefik (`core/traefik/README.md`, "How to disable").

Only after this passes does the deployment rely on the bouncer.

> **If Traefik starts returning 403 everywhere:** you banned an IP covering your own
> path (`cscli decisions list` → `delete`), or a fail-closed AppSec profile was used
> while AppSec was unreachable (the shipped middlewares are fail-open). A `502` or
> "invalid middleware" instead of `403` means the plugin never loaded — check
> `experimental.plugins` and the `/plugins-storage` volume, not the bans.

---

## Cal.diy future placement

Recorded so the expectation is unambiguous — **nothing to attach: the bouncer
stands in front of Cal.diy's router as soon as the deployment switches it on.**

- **Strength:** `threat-crowdsec` — a public scheduling app should honour the ban
  list; its router carries `access-public`, `limit-standard`, `headers-standard`.
- **No AppSec initially** — Cal.diy traffic is untested against the WAF;
  `CROWDSEC_APPSEC_ENABLED` only after the [appsec.md](appsec.md) progression,
  which then covers every public application of the deployment.
- **No geo initially** — only if the operator deliberately decides, via a `geo-*`
  mechanism, not as a default.
- **Prerequisite:** the bouncer proven on whoami first (above).
- **Recovery:** a Tailscale/LAN path independent of the Cal.diy public router must
  exist before attaching.
- **Rollback:** the deployment's switch, not the stack — `CROWDSEC_BOUNCER_ENABLED=false`,
  render, recreate Traefik at once.

---

## Implemented vs deferred

| Item | State |
|------|-------|
| Traefik plugin block | Rendered into `config/traefik.yml` by `render.sh` when `CROWDSEC_BOUNCER_ENABLED=true` in `core/traefik/.env`; absent otherwise |
| The two middlewares | `threat-crowdsec` and `threat-crowdsec-appsec` are defined in `crowdsec.yml.tmpl` and rendered by the same switch into `config/dynamic/crowdsec.yml`; the file is removed when the switch is off |
| Placement | `render.sh` puts one of them on the `websecure` entrypoint, in front of every router: `threat-crowdsec`, or `threat-crowdsec-appsec` when `CROWDSEC_APPSEC_ENABLED=true`; `validate.sh` checks the list against the switches. The lab measured the entrypoint placement on 2026-10-18 (a forged `X-Forwarded-For` from an untrusted sender is deleted before the bouncer reads it); the per-router middleware was validated on a host on 2026-07-29 |
| `threat-crowdsec-strict` | Designed here; deferred behind the AppSec progression and a recovery-path gate |
| `geo-*` family | Deferred; mechanism undecided (edge vs Traefik geo plugin) |
| Per-app opt-in | Gone with the model: no slot, no label; the switch is the deployment's |
| `docs/standards/traefik-security.md` | Describes the entrypoint placement, both switches default-off |

Nothing in this batch enables runtime enforcement. This document is architecture and
roadmap only.

---

## Open design questions

1. **Per-app selection mechanism.** Settled twice: first as a per-router `.env`
   slot (2026-07), then, with the middleware model (D1, 2026-10-18), as the
   deployment's entrypoint switch — a per-router choice had left most routers
   without the bouncer, and the exemption an operator needs is an AllowList in
   the engine, not a label.
2. **Geo mechanism.** Cloudflare edge rules vs a Traefik GeoIP plugin vs global
   CrowdSec country blocklist — pick one before introducing any `geo-*` name.
3. **Bouncer key strategy.** One shared key (simple) vs per-profile keys (per-profile
   metrics). Default to one until metrics separation is actually needed.
4. **Naming migration.** Settled: `threat-crowdsec` and `threat-crowdsec-appsec`
   are the current names (the model's `threat-` position). Historical records —
   `CHANGELOG.md`, `docs/bugfixes/traefik-crowdsec-plugin-2026-04-20.md`, the
   verification records of 2026-07 and 2026-09 — keep the names of their time
   (`sec-crowdsec`, then `crowdsec-basic`) because they describe what was
   configured then.

---

## See also

- [README.md](../README.md) — CrowdSec engine: Core and the two remediation points
- [appsec.md](appsec.md) — WAF mechanics, per-app false positives, fail-open/closed
- [geoblocking.md](geoblocking.md) — why geo is global blocklist, not per-app allowlist
- [firewall-bouncer.md](firewall-bouncer.md) — host-firewall remediation, global rather than per app
- [`core/traefik/README.md`](../../traefik/README.md) — plugin enable/disable steps
- [`docs/standards/traefik-security.md`](../../../docs/standards/traefik-security.md) — the four router positions this stands in front of
