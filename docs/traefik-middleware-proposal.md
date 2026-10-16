# Traefik middleware model — proposal

A proposal, revised 2026-10-15 after the maintainer's review of the first
draft. It answers decision D1 of
[`audits/core-v1-readiness-2026-10-15.md`](audits/core-v1-readiness-2026-10-15.md):
how the `sec-*` chains, the `acc-*` policies, the `tls-*` profiles and the
integrations are named and combined on a router. The model and the names are
accepted; three conditions in [Before release](#before-release) are open and
block the implementation. This document in the repository records the decisions
D1–D4 with their conditions, the open detail questions, the technical
prerequisites and the migration requirements — it is not the release of Phase
4, which is given separately once the conditions are met. Nothing here changes
a file; what is adopted lands in
`docs/standards/traefik-security.md`, `docs/standards/traefik-labels.md` and
the templates under `core/traefik/ops/templates/dynamic/` through the pull
requests of Phase 4.

## Requirements

Stated by the maintainer on 2026-10-15:

1. Names that explain themselves; no abbreviation where a word fits.
2. One naming logic for every function, derived from what the setting does.
3. Security functions that combine independently.
4. A default case that needs as few decisions as possible.
5. Every protection the current chains provide is kept, or exceeded —
   established against the real response headers of the affected
   applications, before and after, not assumed.
6. Existing deployments keep working through the migration, and no
   installation receives a different security profile without an explicit
   step. A router that answers is not evidence of an equivalent migration.

And from the audit: every value states a purpose in one sentence, and its
numbers follow from the purpose; an operator turns a function up or down
without editing a file the repository owns.

## The model

A router carries **six functions, in a fixed order, one variable each**. Every
value is a middleware in the file provider, named `<function>-<variant>`, and
every function has a variant that switches it off for the router, so a slot is
never empty and no value carries a separator.

| Order | Function | Variable | Variants | Default | Decided by |
|---|---|---|---|---|---|
| 1 | Threat remediation | `APP_TRAEFIK_THREAT` | `threat-none` · `threat-crowdsec` · `threat-crowdsec-appsec` | `threat-none` | the deployment (whether CrowdSec runs) |
| 2 | Access | `APP_TRAEFIK_ACCESS` | `access-public` · `access-lan` · `access-vpn` · `access-lan-vpn` · `access-blocked` | — | **the operator, per stack** |
| 3 | Limit | `APP_TRAEFIK_LIMIT` | `limit-none` · `limit-standard` · `limit-large` · `limit-extra-large` · `limit-sync` · `limit-strict` — today's counters under new names (D2) | `limit-standard` | the repository, from the application's measured behaviour |
| 4 | Authentication gate | `APP_TRAEFIK_AUTH` | `auth-none` · `auth-authentik` | `auth-none` | the operator, where an application has no login of its own |
| 5 | Response headers | `APP_TRAEFIK_HEADERS` | `headers-none` · `headers-hsts-only` · `headers-standard` — `headers-standard-frame-self` under review | `headers-standard` | the repository, from the application's measured response headers |
| 6 | Compression | — | `compress` | fixed | — |

Two further router settings keep their place outside the middleware list:

| Setting | Variable | Variants | Default |
|---|---|---|---|
| TLS profile | `APP_TRAEFIK_TLS_OPTION` | `tls-compatible` · `tls-standard` · `tls-strict` | `tls-standard` |
| Certificate resolver | `APP_TRAEFIK_CERT_RESOLVER` | unchanged | unchanged |

The label block of every stack becomes:

```yaml
- "traefik.http.routers.${COMPOSE_PROJECT_NAME}.tls.options=${APP_TRAEFIK_TLS_OPTION}@file"
- "traefik.http.routers.${COMPOSE_PROJECT_NAME}.middlewares=${APP_TRAEFIK_THREAT}@file,${APP_TRAEFIK_ACCESS}@file,${APP_TRAEFIK_LIMIT}@file,${APP_TRAEFIK_AUTH}@file,${APP_TRAEFIK_HEADERS}@file,compress@file"
```

Every variable is referenced without a Compose default. An `.env` that does not
set one produces an empty name, and Traefik disables the router and logs it —
loud, never a silently different profile ([Migration](#migration)).

The `.env.example` of a stack:

```ini
APP_TRAEFIK_ACCESS=access-vpn            # the one value an operator decides
APP_TRAEFIK_THREAT=threat-none           # threat-crowdsec once core/crowdsec runs
APP_TRAEFIK_LIMIT=limit-standard
APP_TRAEFIK_AUTH=auth-none
APP_TRAEFIK_HEADERS=headers-standard     # headers-hsts-only: the application sets its own
APP_TRAEFIK_TLS_OPTION=tls-standard
```

The operator decides one value, as today. The repository ships the other five
from what it measured about the application, each with its reason in the
stack's README, and an operator changes any one of them without touching the
others — which is what the single chain name prevented.

**The order is the request path.** A banned address is rejected before any
work is done (1); an address outside the policy is rejected before it is counted
(2); a client over its limit is rejected before the authentication gate is
asked, so a flood never reaches the portal (3, 4); headers are set on the way
back (5); the response is compressed last (6). Traefik applies response changes
in reverse list order, so a per-application header middleware that must win
over `headers-*` is placed **before** it — the rule the Keycloak fix measured
on 2026-09-07 — and a path rewrite is placed last.

**`none` means one thing everywhere:** the function does nothing on this
router. The access policy is the one function whose "nothing" is the open door,
so its open variant is `access-public` and its closed one `access-blocked`;
neither is called `none`.

## The functions

### 1. Threat remediation — `threat-*`

| Variant | What it does | Today |
|---|---|---|
| `threat-none` | nothing | empty `APP_TRAEFIK_THREAT` |
| `threat-crowdsec` | rejects an address CrowdSec has a decision for; stream mode, decisions cached, fails open when the engine is unreachable | `crowdsec-basic` |
| `threat-crowdsec-appsec` | the same, plus inspection of each request by the AppSec engine (Coraza); blocks the request, not the address; fails open | `crowdsec-appsec` |

Rendered with `CROWDSEC_BOUNCER_ENABLED=true` as today; `threat-none` is
always defined. A router naming a CrowdSec variant while the switch is off is
disabled by Traefik rather than left unprotected — unchanged, and stated. The
deferred profiles of `core/crowdsec/docs/profiles.md` keep their slot:
`threat-crowdsec-strict` (fail closed) when it is implemented. Geo-blocking is
not a variant: it is a decision in the engine and applies to every router that
carries any `threat-crowdsec-*`.

### 2. Access — `access-*`

| Variant | Who gets through, by connecting address | Today |
|---|---|---|
| `access-public` | anyone | `acc-public` |
| `access-lan` | RFC1918 and IPv6 ULA | `acc-local` |
| `access-vpn` | the VPN ranges from `core/traefik/.env` — `TAILSCALE_CIDR_V4`/`V6`, renamed `VPN_CIDR_V4`/`V6` with the old names accepted | `acc-tailscale` |
| `access-lan-vpn` | both | `acc-private` |
| `access-blocked` | no one — the kill switch | `acc-deny` |

`vpn` is accurate for what the policy checks: two address ranges the operator
configures, which are a VPN's ranges whether the VPN is Tailscale, Headscale
or another one that delivers its clients' addresses to the host. The
defaults stay Tailscale's `100.64.0.0/10` and `fd7a:115c:a1e0::/48`.

Unchanged in content, in both modes of D3: the closed policies evaluate the
connecting address, because the clients they admit connect directly
([Behind Cloudflare](#behind-cloudflare--d3)). What `access-lan` and
`access-lan-vpn` admit besides the LAN — the Docker bridge gateway, and with it
any container on a shared network and any process on the host — is stated in
the template and the standard (audit RP4, D12).

### 3. Limit — `limit-*`

**Decided 2026-10-15 (D2): the counters stay exactly as they are; the model
renames them.** The values are the interim ones of 2026-10-03, and no new
bound is introduced before its effect on the applications is measured. Phase
4 measures what each application needs — synchronisation, large file
transfers, APIs, long-lived connections — and only then is decided whether,
and on which routers, a bound on requests in flight is added. A counter and a
bound in flight protect against different things — how fast one address may
ask, against what one address may hold open — and neither replaces the other.

| Variant | Purpose | Today, unchanged |
|---|---|---|
| `limit-none` | nothing — a path-scoped router whose protocol a counter breaks, a websocket | `sec-0`, `sec-1*`, routers with no chain |
| `limit-standard` | an application a browser uses; a first load of up to a few hundred requests passes | `rl-soft` 125/s, burst 200 |
| `limit-large` | a code-split interface whose first load exceeds `limit-standard`'s bucket | `rl-spa` 125/500 |
| `limit-extra-large` | a first load beyond `limit-large`'s bucket; behind a closed access policy only, as today (CI rule `burst-exposure`) | `rl-spa-xl` 125/1000 |
| `limit-sync` | an application with file-sync clients, bounded by the sustained rate rather than the bucket | `rl-sync` 1000/1000 |
| `limit-strict` | an administration surface or a login-only route, where each request is worth slowing a sender down | `rl-hard` 20/40 |

The entrypoint timeouts (audit RP6) are separate from this list and land in
Phase 2. Every limit groups requests by client address and follows D3's switch
for which address that is. The name `limit-extra-large` is a candidate: the
variant exists because today's 1000 bucket is a distinct protection level with
its own CI rule, and the name is the one open naming question left.

### 4. Authentication gate — `auth-*`

| Variant | What it does | Today |
|---|---|---|
| `auth-none` | nothing | — |
| `auth-authentik` | forward-auth to the Authentik outpost; the request reaches the application only with a session | `sec-authentik`, commented out in a tracked template |

Rendered with `AUTHENTIK_FORWARD_AUTH_ENABLED=true` in `core/traefik/.env`,
the same shape as the CrowdSec switch (audit RP11, decision D4). An
application with its own login carries `auth-none`; the gate is for
applications that have none, and for an administration path of one that does
(a path-scoped router with `auth-authentik`, as `apps/paperless-ngx` suggests
for `/admin`). Single sign-on inside an application — OIDC against Keycloak or
Authentik — is application configuration and no proxy function.

Decided 2026-10-15 (D4), with three states kept apart:

| State | What it means | Today |
|---|---|---|
| Maintained reference implementation | the one integration `core/traefik` renders, tests and keeps current | Authentik — `auth-authentik` |
| Prepared integration | a variant the model has a slot for and nothing renders yet | none; `auth-authelia` is the shape one would take |
| Available application | a stack in the repository with its own documentation, usable on its own | Authelia, Keycloak |

A second forward-auth variant is added when a concrete need exists and it
can be tested in full and maintained for good; the model allows it without
requiring it now. Both portals get their missing entry in `.ai/decisions.md`
under this distinction.

### 5. Response headers — `headers-*`

| Variant | What the proxy adds to every response | For |
|---|---|---|
| `headers-none` | nothing | debugging; a router whose application is measured to own every header |
| `headers-hsts-only` | `Strict-Transport-Security` only | an application measured to set its own security headers — the candidates are Keycloak, Nextcloud, Vaultwarden, Matomo and the three office stacks. HSTS is the one header that belongs to the proxy's host name and that the application cannot know |
| `headers-standard` | HSTS · `X-Content-Type-Options: nosniff` · `X-Frame-Options: DENY` · `Referrer-Policy: strict-origin-when-cross-origin` · `Permissions-Policy` (camera, microphone, geolocation, payment, usb, magnetometer, gyroscope, accelerometer denied) | every application that sets none of these |
| `headers-standard-frame-self` | the same with `X-Frame-Options: SAMEORIGIN` and `Referrer-Policy: same-origin` | **under review** — see below |

**No header is dropped or moved on the strength of this table.** Each stack's
value is set in Phase 4 from a measurement of the application's own response
headers without the proxy, then confirmed through the proxy — the `curl -sI`
procedure `traefik-security.md` already prescribes — and the before/after pair
is recorded beside the value. A stack whose application is not measured keeps
`headers-standard`.

**Whether `headers-standard-frame-self` is needed.** Today one stack selects an
`-e` chain through its `.env` (`business/listmonk`, `sec-2e`, for its campaign
preview); the one literal `sec-3e` (`apps/vaultwarden`) serves an application
that sets its own frame header and belongs to `headers-hsts-only`; `sec-1e` and
`sec-3e-spa` are selected by nothing. If the Phase 4 measurement confirms that
listmonk is the only application that frames its own pages and sets no frame
header, it carries a per-application frame middleware before `headers-standard`
and the variant is not created. Three variants are then enough: `none`,
`hsts-only`, `standard`.

HSTS carries three deployment-wide values from `core/traefik/.env`, because
they are decisions about the domain and not about one application:

| Variable | Default | What it changes |
|---|---|---|
| `HSTS_MAX_AGE` | `63072000` | two years, as today |
| `HSTS_INCLUDE_SUBDOMAINS` | `false` | today's `sec-2` behaviour for every router. The 46 stacks on a `sec-3` tier send `includeSubDomains` today; after the switch they do so only once the operator sets it — the migration note names them. On `app.example.com` the directive covers `*.app.example.com`; a stack served at the registrable domain commits every subdomain to HTTPS for the max-age, which is why it is a deployment decision |
| `HSTS_PRELOAD` | `false` | the directive has no effect until the registrable domain is submitted to the browsers' preload list, which requires it on that domain with `includeSubDomains`; an operator who submits sets this to `true` — today `sec-3` sends it on application host names, where it does nothing |

The report-only Content Security Policy of today's `hdr-strict` names no
reporting endpoint, so a violation is visible in the developer console of
whoever opens the page and collected nowhere; it is not carried over — and the
Phase 4 measurement records, per affected stack, that no application relied on
it. A Content Security Policy is application-specific and is not a function of
this list: a stack that is tested against one appends its own middleware
before `headers-*` — the enforcing policy `csp-self-only` (today
`csp-enforce`, carried by `apps/whoami`) stays defined in the file provider for
that use, and a stack whose upstream names a policy defines it in its own
labels. The same place serves a dashboard target that must name the
dashboard's origin in `frame-ancestors`.

`headers-hsts-only` replaces the `strip-xfo` pattern: instead of adding a
header and removing it again in the right order, the proxy adds nothing the
application owns.

### 6. Compression — `compress`

Decided 2026-10-15: fixed, not a variable. Every chain except `sec-0`
compresses today, and no stack chooses it. It stays the last entry of the
label. A stack that must not compress — pre-compressed assets, or a response
that mixes a secret with attacker-controlled input, which compression can
leak — omits the entry in its own compose file and says why in its README; the
standard names the two cases.

### TLS — `tls-*`

| Variant | Minimum | Ciphers | Today | Stacks |
|---|---|---|---|---|
| `tls-compatible` | 1.2 | Traefik's defaults | `tls-basic` | 6 |
| `tls-standard` | 1.2 | ECDHE with AES-GCM or ChaCha20, X25519 preferred | `tls-aplus` | 97 |
| `tls-strict` | 1.3 | — | `tls-modern` | 7 |

Unchanged in content, renamed to the same three words the limit uses. The
entrypoint default `TLS_DEFAULT_OPTION` moves from `tls-basic` to
`tls-standard`; it applies only to a router that sets no option, and every
shipped router sets one.

## Behind Cloudflare — D3

Decided 2026-10-15: Cloudflare's proxy is a supported operating variant,
selected by one switch in `core/traefik/.env` — `TRAEFIK_FORWARDED_PROXY`,
`none` (default) or `cloudflare` — and without it nothing changes. The
conditions: one traceable way of establishing the client address; trusted
proxy addresses only from a defined, maintained source; no client-supplied
address header taken on trust; the same address evaluated by access policies,
limits, CrowdSec and the log; the origin protected so Cloudflare cannot be
bypassed; and proof with and without Cloudflare, over IPv4 and IPv6.

**What the Traefik v3.7 source establishes, and why the first draft's
`ipStrategy.depth: 1` is wrong.** At the entrypoint, `forwarded_header.go`
deletes every `X-Forwarded-*` header and `X-Real-Ip` from a sender outside
`trustedIPs`, keeps them from a trusted sender, sets `X-Real-Ip` from the
connection only when absent, and never appends the connecting address to
`X-Forwarded-For` — the proxy to the backend does that later, after every
middleware has run. A client that connects directly — every VPN and LAN client
— therefore reaches the middlewares with no `X-Forwarded-For` at all. In
`ip/strategy.go`, both `DepthStrategy` and `PoolStrategy` (`excludedIPs`)
return an empty string in that case; `ipallowlist` passes it to the allow-lister
and rejects with 403; `ratelimiter` builds its key as `name:source`, so every
direct client shares the key `name:`. A single middleware definition cannot
express "the forwarded address when the sender is Cloudflare, otherwise the
connection" — only the CrowdSec plugin does that, per request, through
`forwardedHeadersTrustedIPs`.

The design that follows, per function and mode:

| Function | `none` | `cloudflare` |
|---|---|---|
| Entrypoint `forwardedHeaders.trustedIPs` | empty — no sender's forwarded headers are trusted. Today the Cloudflare list is trusted unconditionally; whether a sender inside those ranges that is not the proxy (a Worker) could set forwarded headers against an origin that does not use Cloudflare is to be tested before this is stated | Cloudflare's published ranges, from one maintained file in the repository, compared by CI with `cloudflare.com/ips-v4` and `ips-v6` (audit RP16) |
| `access-lan`, `access-vpn`, `access-lan-vpn` | connecting address | connecting address, unchanged. Their clients connect directly; a request to such a host through Cloudflare arrives from an edge address and is refused — which is correct, because a closed host name is not proxied |
| `access-public` | no address evaluated | no address evaluated |
| `limit-*` | connecting address | `sourceCriterion.requestHeaderName: X-Real-Ip`, which is the connecting address for a direct client (Traefik deletes and re-sets it) and the real client for a proxied request **only if Cloudflare sets `X-Real-Ip` to the connecting client on every proxied request** — a Transform Rule that overwrites whatever the client sent. Without that rule a client can send its own `X-Real-Ip` through Cloudflare and the origin trusts it, which is the state of every Cloudflare installation today for an application that reads the header (`apps/vaultwarden`, `IP_HEADER=X-Real-IP`) |
| `threat-crowdsec`, `threat-crowdsec-appsec` | connecting address | `forwardedHeadersTrustedIPs` = the same list; the plugin takes the forwarded address from a trusted sender and the connection otherwise |
| Access log, CrowdSec detection | `ClientHost` = connection | `ClientHost` = the last `X-Forwarded-For` entry, which Cloudflare appends — correct today, unchanged |
| The application | `X-Real-Ip` and `X-Forwarded-For` = client | `X-Real-Ip` = client (with the rule); `X-Forwarded-For` = `client, edge` — a stack that counts proxy hops counts two |

**Origin protection** (documented with the switch): public host names are
proxied, closed host names are DNS-only or resolved by split DNS; the host
firewall admits 80 and 443 from Cloudflare's ranges and the VPN and LAN ranges
only, from the same maintained list; Authenticated Origin Pulls as the stronger
option, with what it needs at the entrypoint.

**Proof, Phase 3, on a host behind Cloudflare, IPv4 and IPv6 each:** `whoami`
through Cloudflare shows the client in `X-Real-Ip` and as the last
`X-Forwarded-For` entry; a direct VPN client reaches an `access-vpn` route and
the same route through Cloudflare answers 403; a manual CrowdSec decision on
the client's address answers 403 through `threat-crowdsec`; the `429` count in
the access log is per client, not per edge; a client-sent `X-Real-Ip` or
`X-Forwarded-For` through Cloudflare does not change what the origin sees; and
the `none` mode's empty trust list is exercised with a request that carries
forged forwarded headers from inside Cloudflare's ranges.

**To confirm before implementation:** that the Transform Rule is available on
the Cloudflare plan in use, and that the switch renders the five places —
entrypoint list, limit source, two CrowdSec middlewares, the documented
firewall list — from one file.

## Every current chain, mapped

What each chain actually sets today, and the values it maps to. The headers
column is the candidate; the per-stack value is set only from the measurement
above.

| Today | Headers today | Limit today | Maps to — headers | Maps to — limit | Stacks |
|---|---|---|---|---|---|
| `sec-0` | none; no compression | none | `headers-none` | `limit-none` | 0 |
| `sec-1` | HSTS, nosniff, DENY | none | `headers-standard` | `limit-none` | 1 (Authentik's second router, literal) |
| `sec-1e` | HSTS, nosniff, SAMEORIGIN | none | `headers-standard-frame-self` | `limit-none` | 0 |
| `sec-2` | HSTS, nosniff, DENY | 125/s, burst 200 | `headers-standard` | `limit-standard` | 49 |
| `sec-2e` | HSTS, nosniff, SAMEORIGIN | 125/200 | `headers-standard-frame-self`, or a per-app frame middleware | `limit-standard` | 1 (listmonk) |
| `sec-2-spa` | HSTS, nosniff, DENY | 125/500 | `headers-standard` | `limit-large` | 5 |
| `sec-2-spa-xl` | HSTS, nosniff, DENY | 125/1000, closed policy only | `headers-standard` | `limit-extra-large` | 2 (windmill, twenty) |
| `sec-2-sync` | HSTS, nosniff, DENY | 1000/1000 | `headers-standard` | `limit-sync` | 2 (seafile, seafile-pro) |
| `sec-3` | + includeSubDomains, preload, Referrer-Policy, CSP report-only, Vary, Permissions-Policy | 125/200 | `headers-standard`; includeSubDomains by the switch, preload and report-only dropped | `limit-standard` | 37 (36 + matomo, literal) |
| `sec-3e` | as `sec-3` with SAMEORIGIN and `same-origin` referrer | 125/200 | `headers-hsts-only` where the application sets its own frame header | `limit-standard` | 1 (vaultwarden, literal) |
| `sec-3-spa` | as `sec-3` | 125/500 | `headers-standard` | `limit-large` | 5 |
| `sec-3e-spa` | as `sec-3e` | 125/500 | `headers-standard-frame-self` | `limit-large` | 0 |
| `sec-3e-sync` | as `sec-3e` | 1000/1000 | `headers-hsts-only` if Nextcloud is measured to set its own | `limit-sync` | 1 (nextcloud) |
| `sec-4` | as `sec-3` | 20/40 | `headers-standard` | `limit-strict` | 3 (adminer, portainer, ntfy) |
| `sec-5` | as `sec-3` + enforcing CSP | 20/40 | `headers-standard` + `csp-self-only` appended | `limit-strict` | 1 (whoami) |

Every `-e` chain exists today for one of two reasons, and they separate: an
application that frames its own pages and sets no frame header; and an
application that sets its own frame header — the Keycloak, Vaultwarden, Matomo
and Nextcloud cases, each carrying or needing a `strip-xfo`. Which of the two
applies is the measurement.

The other current names:

| Today | Becomes |
|---|---|
| `acc-public` · `acc-local` · `acc-tailscale` · `acc-private` · `acc-deny` | `access-public` · `access-lan` · `access-vpn` · `access-lan-vpn` · `access-blocked` |
| `tls-basic` · `tls-aplus` · `tls-modern` | `tls-compatible` · `tls-standard` · `tls-strict` |
| `crowdsec-basic` · `crowdsec-appsec` | `threat-crowdsec` · `threat-crowdsec-appsec` |
| `sec-authentik` | `auth-authentik` |
| `csp-enforce` | `csp-self-only` (a per-stack addition, not a slot) |
| `${COMPOSE_PROJECT_NAME}-strip-xfo` | removed; the router carries `headers-hsts-only` once measured |
| `hdr-basic` · `hdr-basic-embed` · `hdr-strict` · `hdr-strict-embed` · `rl-soft` · `rl-spa` · `rl-spa-xl` · `rl-sync` · `rl-hard` · `permissions-policy` | folded into the variants above; no block is referenced by any stack today |

## Protection, before and after

What the mapping changes if every stack takes the candidate value. The
per-stack confirmation is the measurement; this table is the plan.

| Protection | Today | After |
|---|---|---|
| HSTS | every chain but `sec-0` | every `headers-*` but `none` |
| HSTS `includeSubDomains` | `sec-3` and above (46 stacks) | the deployment switch, default off — the 46 stacks send it again once the operator sets it; named in the migration note |
| HSTS `preload` | `sec-3` and above, without effect on an application host name | off until the operator submits the domain; then every host |
| `X-Content-Type-Options` | every chain but `sec-0` | `standard` (and `frame-self` if kept); `hsts-only` leaves the application's own, which the measurement has shown to be present |
| `X-Frame-Options` | every chain but `sec-0` | the same; an application measured to set its own is no longer overridden |
| `Referrer-Policy` | `sec-3` and above | every `standard` router — 59 stacks gain it |
| `Permissions-Policy` | `sec-3` and above | every `standard` router — 59 stacks gain it |
| CSP, report-only | `sec-3` and above, collected nowhere | not carried; an application's own policy passes through |
| CSP, enforced | `sec-5` | `csp-self-only`, appended by the stacks that are tested against it |
| Requests per address | `sec-2` and above, four bucket sizes | the same counters, same values, under the `limit-*` names (D2); a bound on requests in flight only after Phase 4's measurement, per router |
| Address check, threat decision, TLS profile, compression | as today | as today, renamed |

Two things the current chains send are dropped because they do nothing where
they are sent (`preload` on an application host name, a report-only policy
with no endpoint); one is moved to a deployment switch whose default is off
(`includeSubDomains`), by decision.

## Migration

The requirement: no installation receives a different security profile
without an explicit step, and a router that answers proves nothing.

**Release N — the model ships.** Three things at once:

1. The templates define the new names, and every old name as an alias composed
   of the new blocks: `sec-2` is a chain of `headers-standard`,
   `limit-standard` and `compress`; `acc-tailscale` is `access-vpn`;
   `tls-aplus` is `tls-standard`. A router that names an old value resolves to
   exactly the profile it had — the alias is the same middlewares under the old
   name, and the Phase 4 measurement includes one route per alias, before and
   after the render, with identical response headers and identical `429`
   behaviour as the pass criterion.
2. The label pattern of every compose file and every `.env.example` switch to
   the six variables, with no Compose default. A stack updated to release N
   with an `.env` that still carries `APP_TRAEFIK_SECURITY` produces empty
   middleware names; Traefik disables that router and logs which name is
   missing. Nothing serves under a profile the operator did not set.
3. `scripts/migrate-traefik-env.sh <stack>` rewrites an `.env` from the
   mapping tables above — one chain value becomes exactly its two new values
   (`sec-4` → `headers-standard` + `limit-strict`), one policy or profile name
   becomes its new name — prints every change, and refuses a value it does not
   know. `overview.sh` lists every stack whose `.env` still carries an old
   variable or an old name, before the operator recreates anything. The
   `CHANGELOG.md` migration carries the tables, the command, the list of stacks
   whose candidate header value differs from a plain rename (the
   `hsts-only` candidates) and the 46 stacks that stop sending
   `includeSubDomains` until the switch is set.

**v1.0.0 — the aliases go.** The old names are removed in the release that
promises stability, with the migration note repeated; after v1.0.0 no
middleware name changes. The migration script stays.

**What does not change for an operator who does nothing:** a running
deployment. The rendered configuration changes only when `render.sh` runs, and
the first render after release N produces a configuration in which every old
name still resolves to its former profile.

## Before release

Three conditions from the review of 2026-10-15, each a gate for Phase 4:

1. **D2 is decided**: the counters keep their values and are only renamed.
   What remains for Phase 4 is the measurement per application —
   synchronisation, large file transfers, APIs, long-lived connections — and,
   on its evidence, whether a bound on requests in flight is added to a router.
2. **Every header change is measured** against the real response headers of
   each affected application — without the proxy, through the proxy today,
   through the proxy after — and no header is removed from a stack without
   that pair on record. The first measurement decides whether
   `headers-standard-frame-self` is created at all.
3. **The migration is explicit per installation**: the alias check in
   Migration 1, the empty-name failure in Migration 2 and the script in
   Migration 3 are implemented and tested on a disposable host before release
   N is tagged.

## Decided on the names — 2026-10-15

| Question | Decision |
|---|---|
| Open and closed access variant | `access-public` / `access-blocked` |
| The VPN policy | `access-vpn` — accurate, see [Access](#2-access--access-) |
| The AppSec variant | `threat-crowdsec-appsec` |
| The HSTS-only header variant | `headers-hsts-only` |
| Compression | fixed in the label, no variable |
| `HSTS_INCLUDE_SUBDOMAINS` default | off |
| D2 — the limits | today's counters and values, renamed; a bound in flight only after measurement, per router |
| The name of today's 1000 bucket | `limit-extra-large` proposed, open |
| D3 — behind Cloudflare | a switch, `none` / `cloudflare`; the mechanism in [Behind Cloudflare](#behind-cloudflare--d3), verified against the Traefik source; implementation after the proof on a host |

| D4 — front doors | Authentik is the maintained reference; Authelia and Keycloak are available applications; a second variant only on a concrete need, fully tested and maintained |

What this proposal does not decide: every per-stack value, which Phase 4
derives from the measurements.
