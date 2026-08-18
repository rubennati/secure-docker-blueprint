# Cal.diY — Hardening Roadmap

> **Status: 📋 Plan** — phased roadmap · 2026-07-26
>
> **Progress:** Phase 0 (release hygiene) and Phase 1 (surface reduction) config has **landed in
> the repo** (`.env.example`, `docker-compose.yml`, `UPSTREAM.md`, `README.md`); their live-host
> acceptance checks are still open. Phase 2 (CrowdSec) and Phase 3 (geo) not started. Cloudflare
> is the **recommended** edge layer for the internet-facing deployment — see
> [cloudflare.md](cloudflare.md).

Post-incident hardening plan for Cal.diY on the secure-docker-blueprint. Written after an
incident on a live server in which the **SMTP credential was exfiltrated**. This document is the
"why" and the "in what order"; the operational steps live in
[`ops-runbook.md`](ops-runbook.md) and the CrowdSec architecture in
[`core/crowdsec/docs/profiles.md`](../../../core/crowdsec/docs/profiles.md).

The phases are ordered **0 → 1 → 2 → 3** and each is gated on the previous one working. Do not
skip ahead.

---

## 0. Threat model — what the incident actually means

The SMTP password is already a Docker Secret, yet it was stolen. That is not a contradiction:

> A Docker Secret protects the value from `docker inspect` and from ending up in `.env` or git.
> It does **not** protect it from an attacker with **code execution inside the app container**,
> or an **SSRF/LFI that reads `/proc/self/environ`**. `config/entrypoint.sh` exports
> `EMAIL_SERVER_PASSWORD` as an **environment variable in the Node process** — anyone who is
> *inside* that process sees it.

So the stolen SMTP key is a **symptom**, not the root cause. The realistic vectors for a
Cal.com-class app are:

1. **RCE** via a vulnerable dependency or API endpoint → attacker reads `process.env`.
2. **SSRF / LFI** → reads `/proc/self/environ` or internal endpoints.
3. **Exposed admin / debug / Prisma surface** or an open `/api` path.
4. **Leaked `.env` / backup** outside the container.
5. **Open self-registration** as an initial foothold.

This reframes where hardening pays off. The storage of the secret is already good; the three
real levers are:

| Lever | Goal | Phases |
|-------|------|--------|
| **A — Reduce RCE/SSRF likelihood** | Fewer ways in | WAF/AppSec (P2), surface reduction (P1), patched image (P0 — the cal.forte fork exists for this) |
| **B — Contain blast radius** | A break-in leaks less | Provider-side SMTP caps (runbook §4), no extra creds in the same env, egress awareness (P1) |
| **C — Reduce attack traffic** | Fewer attempts reach the app at all | CrowdSec (P2) + Geo allowlist (P3) |

---

## Phase 0 — Release hygiene (blocks the release)

The blueprint currently points at a fork model that no longer exists. Reconcile before cutting
a release.

| Item | Current state | Target |
|------|---------------|--------|
| Fork model in `UPSTREAM.md` | Describes "1:1 mirror + develop + release", upstream `calcom/cal.diy` | The fork is now **cal.forte** — security-first, review-gated: `main` = untouched mirror (not deployable), `develop` = integration/review, `release` = reviewed source for image builds. Governance docs: `FORK_PROCESS.md`, `UPSTREAM_SYNC.md`, `SECURITY_REVIEW.md`, `IMAGE_BUILD.md`, `RELEASE_PROCESS.md` |
| `APP_TAG` | `v6.2.0` (a tag that does not exist yet on the fork) | Pin to the **first reviewed release tag or, better, the image digest** — never `latest`. The fork's own guidance: "reviewed tag or digest from the `release` branch" |
| "live testing" phrasing in `UPSTREAM.md` | "Gotchas found during live testing (v6.2.0)" | Neutral phrasing (e.g. "Known gotchas (v6.2.0)") per repo status-language convention |

**Acceptance:**

- [ ] `UPSTREAM.md` matches the cal.forte branch/governance model, no stale `calcom/cal.diy` upstream naming
- [ ] `APP_TAG` pinned to a reviewed tag/digest that actually exists; `.env.example` + `README.md` consistent
- [ ] `docker compose config` clean

---

## Phase 1 — Reduce the app's attack surface (env / compose)

Cheap, high-leverage, no new infrastructure. Flags verified against the Cal.com source unless
noted; re-confirm against the cal.forte fork before applying (some may be stripped in the
community edition).

### 1.1 Disable public self-registration

```env
# apps/caldiy/.env
NEXT_PUBLIC_DISABLE_SIGNUP=true
```

On a scheduling instance **you** operate, nobody outside needs to create an account. Open signup
is both an attack foothold (vector 5) and a spam surface. Confirmed present in Cal.com's
`.env.example` ("Set this to true to disable new signups").

### 1.2 Resource limits (blast-radius cap)

The runbook already flags `deploy.resources` as unset. After a break-in, an unbounded container
is a free cryptominer/DoS host. Add conservative interim caps now, tighten after measuring:

```yaml
# per service in docker-compose.yml — measure with `docker stats` and set ~2× peak
deploy:
  resources:
    limits:
      memory: <measured>
```

### 1.3 Surface inventory — classify what must be reachable

Produce a short table of the app's externally-reachable paths and mark each **public /
webhook-only / should-be-restricted**. Feeds the Phase 3 geo split. Categories to classify:

| Surface | Reachability needed | Notes |
|---------|--------------------|-------|
| Public booking pages (`/`, `/[user]`, `/[user]/[type]`) | Public (geo-limited in P3) | Human-facing |
| Login / setup / settings / admin | Restricted (geo or VPN in P3) | Human-facing, high value |
| `/api/cron/*` | Token only | Already protected by `CRON_API_KEY` |
| `/api/integrations/*/webhook` (calendar push, conferencing callbacks) | **Public — leave open** | Server-to-server from Google/MS/Zoom infra; protected by provider signatures + CrowdSec/AppSec |
| `/api/auth/*` (NextAuth) | Public | Needed for login flow |
| Other `/api/*` (public API v1/v2) | Classify | Disable/restrict if unused |

### 1.4 Egress awareness (documented residual risk)

DB and Redis are already on `app-internal` (`internal: true`) — no egress. The **app** container
needs outbound internet (calendars, SMTP, OAuth), so a full egress lockdown would break the
integrations you want to keep. Decision: **document the residual risk** (an attacker with RCE can
exfiltrate outbound) rather than break integrations. An egress allowlist proxy is a possible
later step, out of scope for this phase.

**Acceptance:**

- [ ] Signup disabled, verified in the UI (registration returns disabled/404)
- [ ] Memory limits set on all three services; app stable for 24–48h
- [ ] Surface inventory table filled in and committed
- [ ] Integrations (calendars, Teams/Zoom/Signal meeting creation) still work

---

## Phase 2 — Turn CrowdSec on (follow `profiles.md` exactly)

This is lever A + C. Nothing here deviates from the existing architecture — it just switches it
on. Full steps: [`core/crowdsec/docs/profiles.md`](../../../core/crowdsec/docs/profiles.md)
"whoami-first validation".

### 2.1 `crowdsec-basic` (IP/decision bouncer, fail-open)

1. Load the plugin: uncomment `experimental.plugins.bouncer` in
   `core/traefik/ops/templates/traefik.yml.tmpl`, set `CROWDSEC_BOUNCER_KEY` in
   `core/traefik/.env`, `./ops/scripts/render.sh && docker compose restart traefik`.
2. Define the `crowdsec-basic` middleware in
   `core/traefik/ops/templates/dynamic/integrations.yml.tmpl` (block already scaffolded).
3. **Validate on `core/whoami` first** — ban a test IP (never your admin IP), confirm 403, roll
   back. Do not touch the Cal.diY router until this passes.
4. Attach to the Cal.diY router as the **first** middleware:
   `crowdsec-basic@file, acc-public@file, sec-3@file`.

### 2.2 `crowdsec-appsec` (WAF, fail-open) — the layer that most directly addresses the incident

`crowdsec-basic` blocks known-bad **IPs**; it does not inspect request bodies. The WAF
(`crowdsec-appsec`) inspects each request for SQLi / XSS / path traversal / virtual-patched CVEs —
i.e. exactly the RCE/SSRF class (vectors 1–3) that most plausibly caused the incident.

Deferred behind its gates (per `profiles.md` / `appsec.md`): AppSec engine confirmed reachable
from Traefik, then per-path false-positive testing, **fail-open** (`crowdsecAppsecFailureBlock:
false`, `crowdsecAppsecUnreachableBlock: false`). Never fail-closed without a proven out-of-band
recovery path.

**Acceptance:**

- [ ] `cscli bouncers list` shows a recent pull; whoami ban test passes and rolls back cleanly
- [ ] `crowdsec-basic` attached to Cal.diY; end-to-end ban test returns 403 from a test IP, admin path unaffected
- [ ] (later) AppSec reachable, false-positive-tested on Cal.diY traffic, fail-open confirmed

---

## Phase 3 — Geo allowlist (human-facing surface only)

Goal: only DACH/EU clients can reach the **interactive** surface, while provider webhooks stay
open so calendars/Teams/Zoom keep syncing. Chosen scope: **human-facing paths only** (P1.3
inventory), leaving `/api/integrations/*/webhook` and `/api/auth/*` open.

### 3.1 Why not CrowdSec for this

Per `profiles.md` / `geoblocking.md`: CrowdSec does country **blocklisting** (ban country X),
**global** to every bouncer — it cannot express a per-app **allowlist** ("only DACH/EU"). So geo
is a separate `geo-*` axis, not a `crowdsec-*` profile.

### 3.2 Two mechanisms — pick by what is actually at the edge

**This depends on a fact about the deployment, not the repo:** the blueprint runs *with or
without* Cloudflare (`cloudflare-dns` DNS-01 vs `httpResolver` HTTP-01, "no Cloudflare
dependency"). Confirm which is true before building the rule.

| | Path A — Cloudflare edge | Path B — Traefik GeoIP plugin |
|-|--------------------------|-------------------------------|
| **Precondition** | Cloudflare **proxy** (orange cloud) actually in front — not DNS-only | Any/none — portable, repo-native |
| **Where** | CF WAF custom rule: `country` + URI-path exception | New `geo-*` Traefik middleware (`experimental.plugins` + MaxMind GeoLite2 DB) |
| **Blocks** | Before your server (best) | At Traefik, after TLS |
| **Cost** | Free (incl. free plan) | New dependency to vet + DB refresh |
| **Human-only scope** | One rule: block if `country ∉ {allow}` AND path ∉ {`/api/integrations`, `/api/auth`} | Split routers: geo middleware on the human router, webhook paths on a separate router without it |
| **Fits** | If you run CF proxy anyway | The blueprint's "portable, no host-specific assumptions" goal |

**Decision (Cal.diy):** the internet-facing deployment runs behind the Cloudflare proxy (see
[README](../README.md) + [cloudflare.md](cloudflare.md)), so geo is implemented as **Path A** — a
Cloudflare WAF custom rule (country + path exception). Full settings live in
[cloudflare.md](cloudflare.md) §3. Path B (Traefik GeoIP plugin as a `geo-*` profile) is retained
as the fallback concept for a deployment without Cloudflare; its implementation is
not covered here.

### 3.3 Scope caveat (why "human-only")

Geo-blocking the whole host to DACH breaks the integrations you want to keep: Google Calendar
push, Microsoft Graph and Zoom webhooks are **server-to-server from US/global provider infra**
and would get 403 → sync falls back to polling or breaks. Keep webhook/callback paths open
(protected by provider signatures + CrowdSec + AppSec). Also keep an admin path (VPN/Tailscale)
that does not depend on the geo rule, so you are never locked out from abroad.

**Acceptance:**

- [ ] Cloudflare proxy confirmed in front (cloudflare.md §0); origin locked to Cloudflare (cloudflare.md §1)
- [ ] Human paths return 403/challenge from a non-allowed country (test via VPN exit); booking + login work from DACH/EU
- [ ] A provider webhook (e.g. calendar push) still reaches `/api/integrations/*/webhook` from outside DACH
- [ ] VPN/Tailscale admin path works independent of the geo rule

---

## Sequencing & rollback

Run **0 → 1 → 2 → 3**, verifying each phase's acceptance before starting the next. Every phase is
independently reversible:

| Phase | Rollback |
|-------|----------|
| 0 | Docs/tag only — revert the commit |
| 1 | Remove env flags / `deploy.resources`, `docker compose up -d --force-recreate app` |
| 2 | Remove `crowdsec-*@file` from the router label, recreate app — Traefik hot-reloads; plugin stays loaded |
| 3 | Path A: disable the CF rule. Path B: remove the `geo-*@file` token / merge routers back |

Emergency kill-switch for the whole app remains `APP_TRAEFIK_ACCESS=acc-deny` (runbook §7).

---

## See also

- [`cloudflare.md`](cloudflare.md) — Cloudflare edge settings (edge WAF, geo allowlist, origin lock)
- [`ops-runbook.md`](ops-runbook.md) — deploy, secret rotation, SMTP emergency, kill-switch
- [`UPSTREAM.md`](../UPSTREAM.md) — fork (cal.forte) model, upgrade checklist
- [`core/crowdsec/docs/profiles.md`](../../../core/crowdsec/docs/profiles.md) — CrowdSec profile architecture
- [`core/crowdsec/docs/geoblocking.md`](../../../core/crowdsec/docs/geoblocking.md) — why geo is global blocklist, not per-app allowlist
- [`core/crowdsec/docs/appsec.md`](../../../core/crowdsec/docs/appsec.md) — WAF mechanics, per-app false positives
