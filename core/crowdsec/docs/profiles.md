# CrowdSec Traefik Profiles — architecture

How CrowdSec HTTP enforcement is modelled in this blueprint: a small family of
**named, per-app middleware profiles** instead of one generic `sec-crowdsec`
applied everywhere.

This document is the architecture and the roadmap. It defines the profile names,
what each one does, what the underlying tooling can and cannot do per app, and the
whoami-first path to turning any of it on. **Nothing here is enabled yet** — the
Traefik plugin and every profile middleware remain commented out in the templates.
See [§ Implemented vs deferred](#implemented-vs-deferred) for the exact status.

---

## Where CrowdSec sits — three orthogonal axes

Every app router in this blueprint composes its middleware from independent layers.
Two exist today and are set per app via `.env`:

```text
traefik.http.routers.<app>.middlewares = ${APP_TRAEFIK_ACCESS}@file,${APP_TRAEFIK_SECURITY}@file
                                          └─── WHO ───┘            └──── WHAT ────┘
```

| Axis | Prefix | Answers | Examples |
|------|--------|---------|----------|
| **Access** | `acc-*` | *Who* may reach this app? | `acc-public`, `acc-tailscale`, `acc-deny` |
| **Security chain** | `sec-N` | *What* headers / rate limit / CSP? | `sec-2`, `sec-3`, `sec-4`, `sec-5` |
| **Threat enforcement** | `crowdsec-*` | *Which known-bad traffic is rejected?* | `crowdsec-basic` (+ deferred profiles) |

CrowdSec is a **third, independent axis** — not a new `sec-N` level and not part of
the `acc-*` policy. A protected public app composes all three:

```text
crowdsec-basic@file, acc-public@file, sec-3@file
└── reject banned IPs ──┘ └─ access ─┘ └─ headers/rl ─┘
```

CrowdSec goes **first** so a banned IP is rejected before any rate-limit, header, or
CSP processing runs. Picking a CrowdSec profile is therefore an explicit, per-app
choice that is orthogonal to who can reach the app and which header chain it uses.

> This is the core correction to the earlier "one `sec-crowdsec` everywhere" model:
> the *access* decision (acc-\*) and the *enforcement strength* decision (crowdsec-\*)
> are separate questions and must be chosen separately per app.

---

## What belongs where

CrowdSec spans two directories and several distinct concerns. Knowing which knob
lives where prevents the most common mistakes (editing the wrong layer, or expecting
per-app behaviour from a global control).

| # | Concern | Lives in | Scope |
|---|---------|----------|-------|
| 1 | Traefik **static plugin** load (`experimental.plugins.bouncer`) | `core/traefik/ops/templates/traefik.yml.tmpl` | Loaded once per Traefik process. Requires a **restart** to change. |
| 2 | Traefik **dynamic middleware profiles** (`crowdsec-*`) | `core/traefik/ops/templates/dynamic/integrations.yml.tmpl` | Per-router. **Hot-reloaded**. This is where profiles are defined. |
| 3 | CrowdSec **LAPI / decisions** (bans) | `core/crowdsec/` engine | **Global** to the source IP. Every bouncer that polls LAPI enforces the same list. |
| 4 | **Parsers / scenarios / collections** | `core/crowdsec/` engine + Hub | Global. Detection logic; not per app. |
| 5 | **AppSec / WAF** engine + rules | `core/crowdsec/` (port `7422`) | Engine + rule sets are **global**; *invocation* is per-middleware (axis 2). |
| 6 | **Geo enforcement** | CrowdSec country decisions (global) **or** an edge/geo mechanism (deferred) | See the `geo-*` profiles in [§ The profile family](#the-profile-family). Country decisions are global, not per app. |
| 7 | **Firewall bouncer** (Phase 3, nftables) | Host apt package | Global, all ports. Not per app. See [firewall-bouncer.md](firewall-bouncer.md). |
| 8 | **App-level profile selection** | the app's router middleware label | Per app. Operator prepends the chosen `crowdsec-*@file`. |

The profile model only controls axes **2** and **8**. Axes 3–7 are global engine
behaviour and cannot be made per-app by naming more middlewares — a constraint that
shapes the whole design below.

---

## Capability reality — per-app vs global

What the maxlerebourg CrowdSec Traefik plugin (`v1.4.5`) and the CrowdSec engine can
actually do, grounded in [appsec.md](appsec.md) and [geoblocking.md](geoblocking.md):

| Question | Answer | Consequence for the model |
|----------|--------|---------------------------|
| Can multiple CrowdSec middlewares exist with different names? | **Yes.** The plugin is loaded once; each `http.middlewares.<name>.plugin.bouncer` block is an independent instance with its own settings. | Named profiles (`crowdsec-basic`, `crowdsec-appsec`, …) are real and supported. |
| Can they share one bouncer key? | **Yes.** All instances may use the same `crowdsecLapiKey`; they appear as one bouncer in `cscli bouncers list` and each polls independently. | One key is the default. Use separate keys only if you want per-profile metrics. |
| Is AppSec per-middleware or global? | **Both.** `crowdsecAppsecEnabled` is a *per-middleware* toggle, so you choose per app whether requests are sent to AppSec — but the AppSec **engine and rule sets are global** (single process at `crowdsec:7422`). | `crowdsec-appsec` (AppSec on) and `crowdsec-basic` (AppSec off) can coexist. Per-app *rules* cannot — only per-app *invocation* + path-scoped exclusions. |
| Can geo be a per-app middleware profile? | **No.** Geo is enforced through CrowdSec **decisions**, which are IP/country-scoped and **global** to every bouncer polling LAPI. | A per-app geo *profile* via the plugin is not possible. |
| Is geo blocking global to the source IP? | **Yes.** `cscli decisions add --scope Country --value XX` bans that country for the whole stack. | Geo today is stack-wide **blocklist**, never per-app **allowlist**. |
| Can DACH-only / EU-only be done safely per app with current tooling? | **No.** CrowdSec does country *blocklisting* (ban country X), not per-app *allowlisting* (allow only DACH/EU). | Deferred; needs a different mechanism (edge or a Traefik geo plugin). |
| Does the plugin support allowlist-style geo directly? | **No.** It is a decision-enforcement bouncer (+ optional AppSec forwarding). It has no GeoIP allowlist feature. | Geo allowlist is out of the CrowdSec axis entirely. |
| Safest minimal primitive to introduce first? | **`crowdsec-basic`** — stream mode, IP/decision bouncer only, AppSec off, fail-open. | This is the one profile to implement and validate first. |

---

## The profile family

Names use a dedicated **`crowdsec-*`** prefix (clearer than overloading `sec-*`, and
distinct from the `sec-N` header chains). Geo is named **`geo-*`** because it is *not*
a CrowdSec-plugin mechanism — see below.

| Profile | Blocks on | AppSec | Geo | Failure mode | Lockout risk | Status |
|---------|-----------|--------|-----|--------------|--------------|--------|
| `crowdsec-basic` | LAPI IP/country **decisions** | off | none | **fail-open** (stream cache; LAPI outage does not block) | **Low** | **Ready to implement** |
| `crowdsec-appsec` | decisions **+ WAF** signatures | on | none | fail-open (AppSec error/unreachable → allow) | Medium (false positives) | Deferred |
| `crowdsec-strict` | decisions **+ WAF** signatures | on | none | **fail-closed** (AppSec error/unreachable → 403) | **High** | Deferred |
| `geo-dach` / `geo-eu` | country allowlist (edge/geo plugin) | n/a | allowlist | depends on mechanism | High | Deferred — not plugin-native |

### `crowdsec-basic`

- **Purpose:** reject IPs CrowdSec has already decided are malicious (scenario bans + community blocklist + any manual/country decisions).
- **Intended for:** any public-facing app once validated on whoami — the standard first production profile. Pairs naturally with `acc-public` + `sec-3`.
- **Blocks:** requests from IPs with an active LAPI decision → HTTP 403. No request-body inspection.
- **AppSec:** no. **Geo:** none (though *global* country decisions, if the operator adds any, are enforced here too — that is a stack-wide engine choice, not part of this profile).
- **Failure mode:** fail-open. Stream mode serves the last cached decision list; a CrowdSec outage does not block legitimate traffic.
- **Example use:** Cal.diy (later), Ghost, Nextcloud, WordPress — public apps that should honour the ban list.
- **When not to use:** VPN-only apps (`acc-tailscale`) gain little — the access policy already restricts the source to trusted peers.

### `crowdsec-appsec` (deferred)

- **Purpose:** `crowdsec-basic` **plus** synchronous WAF inspection of each request (SQLi, XSS, path traversal, virtual patches) via the AppSec engine.
- **Intended for:** public apps whose traffic has been tested against the WAF and shown clean — after the engine is confirmed reachable from Traefik.
- **Blocks:** banned IPs **and** individual requests matching a WAF rule. AppSec blocks the request without creating an IP ban (see [appsec.md](appsec.md)).
- **AppSec:** yes, **fail-open** (`crowdsecAppsecFailureBlock: false`, `crowdsecAppsecUnreachableBlock: false`).
- **When not to use:** apps with known WAF false positives until per-path exclusions are written — Nextcloud WebDAV, Paperless/Seafile/WordPress uploads, Authentik SAML, Invoice Ninja webhooks (full table in [appsec.md](appsec.md)).

### `crowdsec-strict` (deferred)

- **Purpose:** maximum HTTP enforcement — `crowdsec-appsec` with **fail-closed** AppSec.
- **Intended for:** high-value apps where a failed WAF should be treated as an incident, **and only** with a proven out-of-band recovery path.
- **Failure mode:** **fail-closed** — if AppSec errors or is unreachable, every request returns 403. A CrowdSec restart race can cut all traffic on that router.
- **When not to use:** anything without a Tailscale/LAN/console recovery path; any app not first run for days under `crowdsec-appsec` (fail-open) without incident.

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

| Level | Profile | Adds | Gate to adopt |
|-------|---------|------|---------------|
| 1 | `crowdsec-basic` | IP/decision bouncer, fail-open | whoami validation passes |
| 2 | `crowdsec-appsec` | + WAF, fail-open | AppSec reachable + per-app false-positive testing |
| 3 | `crowdsec-strict` | + WAF, fail-closed | days stable at level 2 + proven recovery path |

Move one level at a time, per app. Most public apps should stop at level 1; level 2
is for apps you have WAF-tested; level 3 is rare and deliberate.

---

## whoami-first validation

Always prove the path on `core/whoami` — a throwaway fixture — before attaching any
profile to a real app. Defining a profile makes it *available*; it protects nothing
until a router uses it, and the plugin's polling loop does not even start until then.

**All steps are operator-local. Rendered `config/` and `.env` are gitignored —
nothing here is committed.**

1. **Enable the plugin + the `crowdsec-basic` middleware locally** (steps 3–6 of
   "How to enable" in [`core/traefik/README.md`](../../traefik/README.md)): set
   `CROWDSEC_BOUNCER_KEY` in `core/traefik/.env`, uncomment `experimental.plugins`
   in `traefik.yml.tmpl`, uncomment the profile block in
   [`integrations.yml.tmpl`](../../traefik/ops/templates/dynamic/integrations.yml.tmpl),
   then `./ops/scripts/render.sh && docker compose restart traefik`.

   > `render.sh` runs `envsubst`. An unset `CROWDSEC_BOUNCER_KEY` renders an **empty**
   > key and the bouncer cannot authenticate. Set the key before rendering.

2. **Keep AppSec disabled** for first validation (`crowdsec-basic` already does).
3. **Attach `crowdsec-basic@file` to the whoami router only**, as the **first**
   middleware — a local label edit, not committed:

   ```text
   ...middlewares=crowdsec-basic@file,${APP_TRAEFIK_ACCESS}@file,${APP_TRAEFIK_SECURITY}@file
   ```

   whoami defaults to `acc-tailscale`, so the test request must actually reach it:
   test from a Tailscale-connected device, or set `APP_TRAEFIK_ACCESS=acc-public`
   on whoami **for the test only**.
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

6. **Validate rollback:** remove `crowdsec-basic@file` from whoami (and restore
   `acc-tailscale` if changed), `docker compose up -d --force-recreate`. The plugin
   and profile stay loaded; whoami simply stops using them.

Only after this passes is attaching a profile to a real app on the table.

> **If Traefik starts returning 403 everywhere:** you banned an IP covering your own
> path (`cscli decisions list` → `delete`), or a fail-closed AppSec profile was used
> while AppSec was unreachable (use `crowdsec-basic`, which is fail-open). A `502` or
> "invalid middleware" instead of `403` means the plugin never loaded — check
> `experimental.plugins` and the `/plugins-storage` volume, not the bans.

---

## Cal.diy future placement

Recorded so the eventual attachment is unambiguous — **not implemented; do not edit
`apps/caldiy/docker-compose.yml` or attach anything yet.**

- **Likely profile:** `crowdsec-basic` — a public scheduling app that should honour
  the ban list, composed as `crowdsec-basic@file, acc-public@file, sec-3@file`.
- **No AppSec initially** — Cal.diy traffic is untested against the WAF; `crowdsec-appsec`
  only after the [appsec.md](appsec.md) progression.
- **No geo initially** — only if the operator deliberately decides, via a `geo-*`
  mechanism, not as a default.
- **Prerequisite:** the bouncer proven on whoami first (above).
- **Recovery:** a Tailscale/LAN path independent of the Cal.diy public router must
  exist before attaching.
- **Rollback:** remove the one `crowdsec-basic@file` token from the router label and
  recreate the app — Traefik hot-reloads within seconds.

---

## Implemented vs deferred

| Item | State |
|------|-------|
| Traefik plugin block | Commented in `traefik.yml.tmpl` (operator enables locally) |
| `crowdsec-*` profile middlewares | `crowdsec-basic` and `crowdsec-appsec` are defined in `integrations.yml.tmpl`, commented out — the operator uncomments one locally |
| `crowdsec-basic` | Designed here; lowest-risk primitive; implement + whoami-validate next |
| `crowdsec-appsec`, `crowdsec-strict` | Designed here; deferred behind AppSec testing / recovery-path gates |
| `geo-*` family | Deferred; mechanism undecided (edge vs Traefik geo plugin) |
| Any app attachment (incl. Cal.diy) | None — whoami-first, then per-app opt-in |
| `docs/standards/traefik-security.md` Integrations rows | List `crowdsec-basic` and `crowdsec-appsec` as supported optional middlewares, both default-off |

Nothing in this batch enables runtime enforcement. This document is architecture and
roadmap only.

---

## Open design questions

1. **Per-app selection mechanism.** Settled: the router label carries a third `.env`
   slot, `APP_TRAEFIK_THREAT`, which the operator sets to `crowdsec-basic@file,`
   including the trailing comma. It defaults to empty, so a stack that does not set it
   renders the same middleware list as before. `apps/_reference` and `core/whoami`
   carry the slot; the dangling-comma problem is handled by keeping the comma inside
   the value rather than in the label.
2. **Geo mechanism.** Cloudflare edge rules vs a Traefik GeoIP plugin vs global
   CrowdSec country blocklist — pick one before introducing any `geo-*` name.
3. **Bouncer key strategy.** One shared key (simple) vs per-profile keys (per-profile
   metrics). Default to one until metrics separation is actually needed.
4. **Naming migration.** Settled: the `crowdsec-*` names are the current ones, and
   current-state documentation uses them. Historical records — `CHANGELOG.md` and
   `docs/bugfixes/traefik-crowdsec-plugin-2026-04-20.md` — keep the old `sec-crowdsec`
   name because they describe what was configured at the time.

---

## See also

- [README.md](../README.md) — CrowdSec engine + the three-phase model
- [appsec.md](appsec.md) — WAF mechanics, per-app false positives, fail-open/closed
- [geoblocking.md](geoblocking.md) — why geo is global blocklist, not per-app allowlist
- [firewall-bouncer.md](firewall-bouncer.md) — Phase 3 host-level (global) enforcement
- [`core/traefik/README.md`](../../traefik/README.md) — plugin enable/disable steps
- [`docs/standards/traefik-security.md`](../../../docs/standards/traefik-security.md) — the `acc-*` / `sec-N` axes this composes with
