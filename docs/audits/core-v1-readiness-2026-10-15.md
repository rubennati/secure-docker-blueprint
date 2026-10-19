# Core audit — reverse proxy, threat detection, update path and working memory

State of the local `dev` checkout at `04f846a`, examined 2026-10-15. `origin/dev`
is seven commits ahead, all dependency updates under `site/` and `development/`;
none touches a file examined here. The templates, the standards, the checkers
and git history are the evidence. Where a claim depends on how Traefik or
CrowdSec behaves, the upstream reference documentation or source was read and
is quoted — it outranks every statement in this repository (L1 in
`.ai/rules.md`).

This file is the findings register for the core layer before v1.0.0, the
counterpart of [`../v1-readiness-audit.md`](../v1-readiness-audit.md), which
covered repository truth, stacks, site and CI. A finding carries its evidence,
its class and its status. The programme in [I](#i-programme) orders the work;
the decisions only the maintainer can take are in [J](#j-decisions-required),
each with a recommendation. Nothing here changes a file.

**Out of scope:** per-stack verification (S1 of the stabilization audit), the
operator site, resource measurement (v0.10.0), host hardening outside Docker,
and the chain redesign itself — this audit scopes it and proposes a model; the
design lands in `docs/standards/traefik-security.md` through its own pull
request.

Classes as in the stabilization audit: **FIX BEFORE V1** (objective, closable by
editing) · **DECISION REQUIRED** · **NEEDS HOST EVIDENCE** · **CLEANUP** ·
**POST-V1 / ON HOLD**. No finding below is a V1 BLOCKER on its own; the first
three findings of [C.1](#c1-which-address-the-proxy-decides-on) together are one
for any installation behind a CDN proxy.

## A. Executive state

The proxy's mechanics hold: the render is atomic, the switch for the CrowdSec
integration lives in `.env`, the memory ceiling is measured, the log rotation
no longer cancels the restart policy, and CI renders the configuration in both
switch states. What this audit found sits in four places.

1. **The repository states the wrong address semantics.** Traefik's
   `ipAllowList` and `rateLimit` evaluate the connecting address unless an
   `ipStrategy` is set, and the templates set none; the CrowdSec bouncer
   middleware compares the connecting address unless `forwardedHeadersTrustedIPs`
   is set, and it is not. Behind a CDN proxy, access policies and rate limits
   therefore key on the CDN's edge addresses, and CrowdSec's decisions — which
   are keyed on the real client, because the access log carries the forwarded
   address — never match what either bouncer compares. The static template, the
   owning standard and the September evaluation all state the opposite.
   Without a CDN the addresses are correct, with the two gateway cases the
   repository already documents. [C.1](#c1-which-address-the-proxy-decides-on)
2. **State outside git has no owner on the host.** Eleven kinds of file are
   installed by hand — the logrotate stanza, two watchdogs, Borgmatic, the
   Docker daemon configuration, three `sysctl` files, a crontab line and the
   CrowdSec host-firewall bouncer — and no procedure re-checks any of them after
   a blueprint update. The logrotate stanza that cancelled the restart policy
   is the measured consequence: fixed in v0.9.2, with a migration step, and
   nothing tells an installation that still runs the old shape.
   [C.3](#c3-the-render-system-and-state-outside-it), [E](#e-findings--the-update-path)
3. **The chain names encode three independent properties and state no
   purpose.** Two of fifteen chains carry 81 % of the stacks, five are used by
   none, and the "strict" tier adds headers whose effect depends on decisions
   the proxy cannot take. The rate limits are interim values by decision of
   2026-10-03. [C.4](#c4-the-security-chains)
4. **The working memory lost a section and carries stale state.** A merge on
   2026-09-23 dropped three sections of `.ai/tasks.md` with 31 open items;
   `.ai/state.md` still points at them and carries five statements git has
   overtaken. `.ai/` also breaks the repository's own public-content rule in
   six places. [G](#g-findings--working-memory-and-governance)

Everything else is documentation drift with a named owner, or needs a host.

## B. What was examined

`core/traefik` in full (templates, scripts, compose, README, UPSTREAM, docs),
`core/crowdsec` in full, the standards `traefik-security.md`,
`traefik-labels.md`, `networking.md`, `logrotate.md`,
`deployment-lifecycle.md`, `env-structure.md`, `compose-structure.md`, the two
checkers, every `.env.example` and production compose file (122 and 134),
`.ai/` in full, `ROADMAP.md`, `CHANGELOG.md` v0.8.0–v0.9.4,
`docs/maintenance-log.md`, the September audits and the bugfix records they
cite, and 500 commits of history (2026-05-11 to 2026-10-04). Upstream sources
read: Traefik's reference pages for IPAllowList, RateLimit, EntryPoints, the
file provider, TLS options and access logs; Traefik v3.7 source files
`pkg/middlewares/accesslog/logger.go` and
`pkg/middlewares/forwardedheaders/forwarded_header.go`; the CrowdSec hub parser
`crowdsecurity/traefik-logs`; the README of
`maxlerebourg/crowdsec-bouncer-traefik-plugin`.

## C. Findings — reverse proxy

### C.1 Which address the proxy decides on

Traefik's documentation, verbatim:

- IPAllowList — *"If no strategy is set, the default behavior is to match
  `sourceRange` against the Remote address found in the request."*
- RateLimit, `sourceCriterion` — *"If none are set, the default is to use the
  request's remote address field (as an `ipStrategy`)."*
- EntryPoints, `forwardedHeaders.trustedIPs` — *"Set the IPs or CIDR from where
  Traefik trusts the forwarded headers information (`X-Forwarded-*`)."* The
  setting decides which senders' headers survive; it does not change what a
  middleware evaluates.

Traefik v3.7 source: `forwarded_header.go` deletes every `X-Forwarded-*` header
and `X-Real-Ip` when the connecting address is outside `trustedIPs`
(`if !x.insecure && !x.isTrustedIP(r.RemoteAddr) { DeleteXForwardedHeaders }`),
and sets `X-Real-Ip` from the connecting address only when absent.
`accesslog/logger.go` writes the connecting address to `ClientAddr` and
`ClientHost`, then overwrites `ClientHost` with the whole `X-Forwarded-For`
value when the header is present. The CrowdSec hub parser takes `source_ip`
from the last comma-separated entry of `ClientHost`.

The templates: `access.yml.tmpl:29-69` sets no `ipStrategy`;
`security-blocks.yml.tmpl:61-94` sets no `sourceCriterion`;
`crowdsec.yml.tmpl:45-92` sets neither `forwardedHeadersTrustedIPs` nor
`clientTrustedIPs`; `traefik.yml.tmpl:40-76` trusts forwarded headers from
Cloudflare's published ranges, hard-coded, and never sets `insecure`.

What follows for each hop, per installation shape:

| Hop | Direct client (no CDN) | Client behind Cloudflare's proxy |
|---|---|---|
| Entrypoint | headers from the client deleted; `X-Real-Ip` = client | headers from the edge kept; `X-Forwarded-For` = client; `X-Real-Ip` = edge (absent from Cloudflare, so set from the connection) |
| `acc-local` / `acc-tailscale` / `acc-private` | connecting address = client — correct | connecting address = edge, outside every range — every request refused |
| `rl-*` | per client — correct | per edge address — every visitor behind one edge shares a bucket; one sender is spread over many |
| `crowdsec-basic` / `crowdsec-appsec` | compares the client | compares the edge; decisions are keyed on the client (next row) |
| CrowdSec detection (access log → parser) | `ClientHost` = client | `ClientHost` = client — decisions name the real client |
| Host-firewall bouncer (`iifname <public>`, `ct original saddr`) | drops the client | matches the edge address; a decision on a client never matches, a decision on an edge range drops every visitor through it |
| Application (`X-Forwarded-For`, `X-Real-Ip`) | `client` / `client` | `client, edge` / `edge` |

| ID | Finding | Evidence | Class | Status |
|---|---|---|---|---|
| RP1 | `ipAllowList` and `rateLimit` evaluate the connecting address; the static template (`traefik.yml.tmpl:29-32`), the owning standard (`traefik-security.md:50-57`) and the September evaluation (`reverse-proxy-limits-2026-09-23.md:187-192`, "already answered") state that trusting Cloudflare's headers gives `ipAllowList` the real client. `.ai/state.md:390-395` carries the correct reading, marked not measured | the three files; Traefik reference as quoted above | FIX BEFORE V1 — corrected at the owners; the mechanism is D3 | Closed 2026-10-15 at the three owners; the mechanism is D3 — delivered in Phase 3 as `TRAEFIK_FORWARDED_PROXY` (`none` trusts nobody, `cloudflare` the maintained ranges); the standard states what each middleware evaluates in both modes |
| RP2 | Behind a CDN proxy the two CrowdSec remediation points compare an address the decisions do not name. The plugin's own README: `forwardedHeadersTrustedIPs` (default `[]`) is the *"List of IPs of trusted Proxies that are in front of traefik (ex: Cloudflare)"*. No document says what `crowdsec-basic` compares behind Cloudflare, and `apps/caldiy/docs/cloudflare.md:31-34` assumes the real client | `crowdsec.yml.tmpl:45-92`; `core/crowdsec/README.md:87-115`; `docs/firewall-bouncer.md:218-257` | FIX BEFORE V1 for CDN installations (D3) · NEEDS HOST EVIDENCE once configured | Closed in configuration — Phase 3: `cloudflare` renders `forwardedHeadersTrustedIPs` and `forwardedHeadersCustomName: CF-Connecting-IP` into both middlewares, so the bouncer compares the client Cloudflare names; the host-firewall bouncer stays on the connection by design (origin firewall from the same ranges). Host proof open (README, "Behind Cloudflare") |
| RP3 | A direct client cannot forge the address any layer sees: untrusted `X-Forwarded-*` headers are deleted at the entrypoint. The verification step in `core/traefik/README.md:567-570` sends `-H "X-Forwarded-For: 1.2.3.4"` from an untrusted source and therefore tests nothing; `core/crowdsec/README.md:589-603` has the sound method | `forwarded_header.go` as quoted | CLEANUP (README) | Closed 2026-10-15 |
| RP4 | The bridge gateway stands in for two kinds of client: IPv6 clients on an IPv4-only `proxy-public`, and requests from the host itself. `acc-local` and `acc-private` admit the gateway (issue #129, open), the CrowdSec default whitelist covers it, and every masked client shares one bucket. Dual-stack is opt-in while `docs/host-session-findings.md:33-49` calls it "effectively mandatory for Tailscale". `acc-tailscale` admits the whole CGNAT `/10` and ULA `/48` by connecting address — any tailnet, which is by design because only the host's `tailscaled` delivers such addresses, and nowhere stated | `ipv6-dual-stack.md:100-146`; `host-session-findings.md:608-616`; `access.yml.tmpl:10-14,36-62`; `core/crowdsec/README.md:219` | DECISION REQUIRED (D12) | Open |
| RP5 | The address an application sees depends on a trusted-proxy value no example can get right for every host: the value is the subnet of `proxy-public` (two with dual-stack), and the examples guess three different ones — `172.19.0.0/16` (Nextcloud), `172.30.0.0/16` (Invoice Ninja), `172.16.0.0/12` (Shlink, Gotify, Headscale, mailserver-jeboehm); seven stacks trust any address (`*`, `0.0.0.0/0`); Paperless ships none and lists the variable as missing; Vaultwarden reads `X-Real-IP`, which behind a CDN is the edge; n8n and HeyForm trust one hop, which behind a CDN is one too few. Nextcloud's own comment states the consequence of a wrong value: brute-force protection counts every user against one address | `apps/nextcloud/.env.example:55-60`; `business/invoiceninja/.env.example:52-57`; `apps/paperless-ngx/CONFIG.md:80,112`; `apps/vaultwarden/docker-compose.yml:120`; the table in [E](#e-findings--the-update-path) is not repeated here | FIX BEFORE V1 — one rule in `env-structure.md` (the check command, no guessed subnet) and the twenty stacks aligned | Open |

### C.2 Availability

| ID | Finding | Evidence | Class | Status |
|---|---|---|---|---|
| RP6 | No `transport.respondingTimeouts` are set. Traefik 3.7 defaults: `readTimeout` 60 s, `writeTimeout` 0 — *"If zero, no timeout exists"* — `idleTimeout` 180 s. Held connections are the load that ended the proxy on 2026-09-22 (`reverse-proxy-limits-2026-09-23.md:23-27`); the write side is unbounded | `traefik.yml.tmpl` (no `transport:` key); Traefik EntryPoints reference | FIX BEFORE V1 — set all three, env-overridable, with the measurement beside them | Open |
| RP7 | The log rotation that cancelled the restart policy is fixed since v0.9.2 (`63858a1`, both logs `copytruncate`, no signal) and `CHANGELOG.md:192-199` carries the migration. Nothing in the repository tells an installation that it still runs an earlier shape: the stanza carries no version marker, and `validate.sh`, `overview.sh` and CI never read `/etc/logrotate.d/` | `core/traefik/config/logrotate/traefik`; `TROUBLESHOOTING.md` §8.3–8.4 (symptom-driven only) | FIX BEFORE V1 — RP10 | Open |
| RP8 | The Traefik watchdog is optional and host-installed; its service hardening "has not been run on a live host" (`traefik-watchdog.service.example:16-18`); the script lives under `core/traefik/ops/scripts/` while the shared model is `core/host-watchdog/README.md:107-119`; the service example cites `backup/borgmatic.service.example`, which is at `backup/borgmatic/borgmatic.service.example` | the four `traefik-watchdog.*` files | NEEDS HOST EVIDENCE · CLEANUP | Open |
| RP9 | Settled inputs, no finding: the memory ceiling is measured (`TRAEFIK_MEMORY`, 2026-09-23); the render is atomic (`render.sh:91-97`, rename into place); `providersThrottleDuration: 30s` bounds reload churn | — | — | — |

### C.3 The render system and state outside it

`render.sh` is the only path for the CrowdSec switch, the wildcard router and the
dashboard's resolver (`render.sh:35-44,100-144`), and `validate.sh` refuses a
`config/` that disagrees with `.env` (`validate.sh:188-206`). Two things are not
under it.

| ID | Finding | Evidence | Class | Status |
|---|---|---|---|---|
| RP10 | **Host-side files have no owner after installation.** Under `core/traefik` alone: the logrotate stanza (`/etc/logrotate.d/traefik`, deployment path substituted by hand), the watchdog's env, script, service and timer (four targets), the optional hourly `logrotate.timer` override, and `/etc/docker/daemon.json` for dual-stack. Three install instructions for the stanza disagree: `README.md:649-651` substitutes the placeholder path; `config/logrotate/traefik:7` and `docs/standards/logrotate.md:23` copy the file as is — a stanza naming `/path/to/secure-docker-blueprint/...` matches no file, and `missingok` keeps logrotate silent about it. `deployment-lifecycle.md` §7 names none of these files; `overview.sh` reads git state and env files only | `render.sh`; `validate.sh`; `overview.sh:97-111`; `host-session-findings.md:97-99` ("Nothing in the setup path prompts for it, and nothing detects that it was skipped") | FIX BEFORE V1 — D5 decides the mechanism | Open |
| RP11 | **Authentik forward-auth is enabled by editing a tracked template** (`integrations.yml.tmpl:15-19`), the pattern the CrowdSec switch replaced because a checkout restored the comments and the next render silently dropped the integration (`.ai/decisions.md:1043-1069`). The same file says "Nothing in this repository is enabled by editing a template" (`:12-13`). Two further portals exist with no decision entry — `core/keycloak` (2026-09-07) and `core/authelia` (2026-09-26) — against "at most one maintained reference implementation" (`decisions.md:1107-1111`); `state.md:149` names Authentik alone | `integrations.yml.tmpl`; `CHANGELOG.md:23,358` | FIX BEFORE V1 (switch) · DECISION REQUIRED (D4) | Open |
| RP12 | **Operator instructions edit rendered output.** `core/traefik/README.md:447-452` and `:586-597` ("Incident Quickmoves") and `traefik-security.md:381-391` ("Incident Response") change `config/dynamic/*.yml` — gitignored output the next render overwrites (`render.sh:148`). Application routers take their middlewares from labels, not from `config/dynamic` | the three sections | FIX BEFORE V1 — the instructions name the `.env` variable and the render | Closed 2026-10-15 |
| RP13 | `validate.sh` requires 29 variables and omits `CROWDSEC_SECURITY_NETWORK`, which `docker-compose.yml:170` uses with no default — an `.env` written before the variable existed renders an empty network name; `TRAEFIK_MEMORY` and the container names are not validated; the post-render presence check covers six of ten rendered files (not `servers-transports.yml`, `redirects.yml`, `crowdsec.yml`, `acme-wildcard.yml`) and not `config/haproxy.cfg.template`, which `docker-compose.yml:34` mounts | `validate.sh:58-88,171-182` | CLEANUP | Open |
| RP14 | `.env.example` has no `COMPOSE_FILE=` line to uncomment, although `README.md:88-91` and `ipv6-dual-stack.md:377-380` say to uncomment it (`.env.example:51` mentions it in prose) | the three files | CLEANUP | Open |
| RP15 | The DNS-01 provider is hard-coded (`provider: cloudflare`, `traefik.yml.tmpl:133`; the token at `docker-compose.yml:113`) while `README.md:242` promises "any provider the Traefik DNS-01 challenge supports". A second provider needs a template edit — the pattern RP11 names | the two files | DECISION REQUIRED (D7) | Closed 2026-10-16 — D7 decided: the README and `deployment-lifecycle.md` state Cloudflare as the one wired DNS-01 provider; a second provider stays post-v1 work |
| RP16 | Cloudflare's trusted ranges are a hand-kept list with no date of last verification (`traefik.yml.tmpl:38-39`), no env override and no CI check (`docs/security-verification.md:168`) | `traefik.yml.tmpl:40-65` | CLEANUP — a dated check in the Version Chain, or a CI comparison with `cloudflare.com/ips-v4` and `ips-v6` | Open |
| RP17 | `render.sh:93` creates the temporary file inside the watched `config/dynamic/` directory, named `<file>.yml.XXXXXX`. Traefik's file-provider reference does not state which files a watched directory loads; the host render of 2026-09-14 showed no reload fault | `render.sh:91-97`; `docs/maintenance-log.md:65` | NEEDS HOST EVIDENCE (low) — or render into a sibling directory | Open |

### C.4 The security chains

**Use.** 105 of 122 `.env.example` files select a chain through
`APP_TRAEFIK_SECURITY`: `sec-2` 49, `sec-3` 36, `sec-2-spa` 5, `sec-3-spa` 5,
`sec-4` 3, `sec-2-sync` 2, `sec-2-spa-xl` 2, `sec-2e` 1, `sec-3e-sync` 1,
`sec-5` 1. Five of the fifteen chains are selected by no file (`sec-0`,
`sec-1`, `sec-1e`, `sec-3e`, `sec-3e-spa`); three stacks write a chain into the
label instead of the variable (`core/authentik/docker-compose.yml:241` `sec-1`,
`apps/vaultwarden/docker-compose.yml:168` `sec-3e`,
`business/matomo/docker-compose.yml:157` `sec-3`); five carry
`APP_TRAEFIK_ACCESS` and no `APP_TRAEFIK_SECURITY` (collabora, euro-office,
onlyoffice, vaultwarden, matomo). Access policies: `acc-tailscale` 66,
`acc-public` 28, `acc-private` 14, `acc-local` 1, `acc-deny` 1. No block is
referenced by any stack directly, so a block change reaches stacks only through
chains: `rl-soft` → 88 stacks, `hdr-basic` → 59, `hdr-strict` → 46,
`permissions-policy` → 48, `rl-spa` → 10, `rl-hard` → 4, `rl-sync` → 3.

**The name.** A chain name encodes three independent properties — the header
set (`basic`/`strict`), the framing (`e`), the rate-limit bucket (none, `soft`,
`spa`, `spa-xl`, `sync`, `hard`) — plus CSP enforcement. Fifteen of the
twenty-four combinations exist. The chain file's own table names a use case per
chain (`security-chains.yml.tmpl:16-32`); the standard's "Choosing the level"
derives the choice from four measured properties of the application
(`traefik-security.md:146-257`). The name says neither.

**What the tiers add.** `hdr-basic`: HSTS two years, `nosniff`, `X-Frame-Options`.
`hdr-strict` adds `includeSubDomains`, `preload`, a referrer policy, a CSP in
report-only mode and `Vary` (`security-blocks.yml.tmpl:36-46`):

- `preload` takes effect only through submission of the registrable domain to
  the browsers' preload list, which requires the directive with
  `includeSubDomains` on that domain. A header on `app.example.com` cannot make
  that commitment; an operator who submits `example.com` because the header
  invites it commits every subdomain, including those that serve no HTTPS.
- The report-only CSP names no reporting endpoint, so a violation appears in
  the developer console of whoever opens the page and is collected nowhere.
- Every `hdr-*` value and the `permissions-policy` block replace the
  application's own header — measured 2026-09-07 (`state.md:316-321`;
  `docs/bugfixes/keycloak-admin-console-iframe-2026-09-07.md`): Keycloak's and
  Nextcloud's `no-referrer` become the weaker proxy value, and a per-app removal
  placed after the chain changes nothing.

| ID | Finding | Evidence | Class | Status |
|---|---|---|---|---|
| RP18 | The chain model: three properties in one name, two chains on 81 % of the stacks, five unused, a strict tier whose additions depend on decisions the proxy cannot take, and header blocks that replace what an application sets. `state.md:322-328` proposes a family without a header block (`sec-own`) plus single-purpose blocks an application appends | above | DECISION REQUIRED (D1) | Open |
| RP19 | The rate limits are interim by decision (`decisions.md:43-85`, 2026-10-03): the purpose is availability, not password guessing (`reverse-proxy-limits-2026-09-23.md:80-91`); the values are measured against first loads only; sync rates are read from client source and not counted on a host; buckets are in-memory per instance and empty on restart; a limit on a code-split interface or a sync protocol answers `429` to legitimate use, which is how Seafile and Nextcloud failed in operation. First-load counts for the same interface differ between documents with no method stated — CISO Assistant 77 (`state.md:337`) against 225 (`reverse-proxy-limits-2026-09-23.md:171`), DefectDojo 42 against 120, ERPNext 67 against 126. `sec-4`'s `rl-hard` (20/40) on `core/portainer` is uncounted (issue #37) | the two files; `traefik-security.md:238-246` | DECISION REQUIRED (D2) · NEEDS HOST EVIDENCE | Open |
| RP20 | `strip-xfo` sits **after** the chain in `apps/vaultwarden/docker-compose.yml:168` and `business/matomo/docker-compose.yml:157`, the order measured ineffective on 2026-09-07 and left open in the bugfix record ("not part of this fix"); `core/keycloak/docker-compose.yml:175` has the working order. All three reference the middleware without the `@docker` suffix that `traefik-labels.md:5` requires | the three compose files; the bugfix record §Also affected | FIX BEFORE V1 — one line each | Open |
| RP21 | The `-xl` chains' coupling to a closed access policy is enforced in CI on `.env.example` only (`check-structure.py:647-655`); neither `validate.sh` nor Traefik checks an operator's `.env` | the checker | CLEANUP — stated in the standard; or checked by `overview.sh` | Open |
| RP22 | `sec-authentik` carries the chains' prefix and is a forward-auth gate with no slot in the label pattern (`state.md:371-374`); `sec-authentik` is defined only in the commented block (RP11) | `integrations.yml.tmpl:50-64` | folds into D1 and D4 | Open |

### C.5 TLS and certificates

| ID | Finding | Evidence | Class | Status |
|---|---|---|---|---|
| RP23 | The entrypoint's default TLS option is referenced by bare name (`options: ${TLS_DEFAULT_OPTION}` → `tls-basic`, `traefik.yml.tmpl:92`). Traefik's TLS reference requires the provider namespace for cross-provider references from routers (`myoptions@file`); whether the entrypoint default resolves for Docker-provider routers that set no option is unverified. Every shipped router sets `APP_TRAEFIK_TLS_OPTION=...@file` (121 of 121 labelled services), so only routers without one are affected | `traefik-labels.md:44`; Traefik TLS options reference | NEEDS HOST EVIDENCE — `openssl s_client -tls1_1` against a router with no option, and the startup log for "unknown TLS options" | Open |
| RP24 | The wildcard bootstrap router (`acme-wildcard.yml.tmpl:3-13`) carries no access policy and no chain; it serves `noop@internal`. Not documented | the template | CLEANUP — document, or attach `acc-deny` | Open |
| RP25 | The README describes three certificate paths and a hybrid (`README.md:236-359`); `.env.example:88-105` describes "Two working modes" and lists the TLS-ALPN resolver at `:128-132`. The shipped file preselects none, and `validate.sh` exits 1 until a choice is made — by design (`:88-90`) | the two files | CLEANUP | Closed 2026-10-15 |
| RP26 | Settled, no finding: the dashboard follows the certificate strategy (`decisions.md:1158-1189`); `sniStrict: true` on all three profiles; stored dashboard certificates cannot be retired (`README.md:335-355`) | — | — | — |

### C.6 Documentation drift

| ID | Finding | Evidence | Class | Status |
|---|---|---|---|---|
| RP27 | `integrations.yml` is named as the home of the CrowdSec middlewares in `core/traefik/README.md:64,118`, `traefik-security.md:12-19` and `:309-321` ("All three are commented out by default", contradicted at `:329-332` in the same section), `traefik-labels.md:9,16`, `core/crowdsec/docs/profiles.md:9-11,58`, `appsec.md:152-153,186-193,390-391`, and the migration pre-flight `core/crowdsec/README.md:404-411`, which greps a file the render no longer writes. The middlewares live in `crowdsec.yml.tmpl` under the switch since v0.8.3 | `integrations.yml.tmpl:9-13` | FIX BEFORE V1 | Closed 2026-10-15 |
| RP28 | `traefik-security.md` carries per-stack assignments that have drifted — Dockhand `sec-4` (`:276`) against `sec-3-spa` in `core/dockhand/.env.example` and its own line 243; Invoice Ninja `sec-2` (`:286`) against `sec-3` — and a "Changes vs. Previous System" table (`:259-268`), history in a reference document. The owner of a stack's value is its `.env.example` | the standard; `documentation-workflow.md` §What does not belong | CLEANUP — remove the table or generate it | Closed 2026-10-15 — both tables removed |
| RP29 | `core/traefik/README.md`: the chain table omits `sec-3e-spa` (`:147-162`); `hdr-strict` is described without `includeSubDomains` and `Vary` (`:203-204`); the `permissions-policy` list omits two directives (`:211`; also `traefik-security.md:113`); `README.md:242` promises any DNS provider (RP15). `core/README.md:26` says "5 security levels". `traefik-labels.md:92` lists two of five access values; `:59,93` omit the `-sync` and `-xl` chains | the files | CLEANUP | Closed 2026-10-15; the DNS-provider sentence followed on 2026-10-16 with D7 |
| RP30 | `core/traefik/UPSTREAM.md`: socket proxy `v0.4.2` at `:18` against `v0.5.0` at `:19,101` and `.env.example:21`; `:122` says the commented Authentik block sets `trustForwardHeader`, `integrations.yml.tmpl:43` says it does not and the block does not contain it; heading "Minor bump (`v3.6` → `v3.x`)" at `:108` with 3.7 pinned; "Tail access log (if enabled in .env)" at `:205` — there is no switch. `traefik.yml.tmpl:37` and `docs/bugfixes/traefik-ipv6-dualstack-2026-06-19.md:63` cite a heading "Cloudflare vs Tailscale" that `ipv6-dual-stack.md` does not have | the files | CLEANUP | Closed 2026-10-15 |
| RP31 | `docs/standards/logrotate.md`: step numbers repeat (`:42,55,80,88,94`); the example stanza (`:103-112`) is a glob the shipped file does not use (acknowledged at `:115`) | the standard | CLEANUP | Closed 2026-10-15; the three install instructions agree — substitute the path |

## D. Findings — threat detection

The model holds as documented: one engine, two independent remediation points,
the reverse-proxy one switched in `.env`, the host-firewall one scoped to the
public ingress interface and set-only (`core/crowdsec/README.md:7-42`;
`docs/firewall-bouncer.md:151-231`). Detection, the plugin bouncer and AppSec
have each been measured once on a host; the host-firewall bouncer's acceptance
steps 6–9 remain open for want of a second machine (`state.md:166-179`). The
WAF question is answered: CrowdSec's AppSec engine is Coraza, the Core Rule Set
is available as hub collections and is not installed by default — the reason
is stated at `appsec.md:105-114` (`ROADMAP.md:158-169`). What follows is what
the documents get wrong or leave open.

| ID | Finding | Evidence | Class | Status |
|---|---|---|---|---|
| TD1 | Behind a CDN proxy neither remediation point acts on the decisions — RP2 | — | — | — |
| TD2 | **The VPN exemption has two procedures, one of which cannot work.** The default whitelist covers RFC1918 and loopback, not `100.64.0.0/10` or `fd7a:115c:a1e0::/48` (`README.md:219`); the tailnet administrator was banned (`docs/bugfixes/crowdsec-firewall-bouncer-2026-08-28.md:17-32,46-56`). The exemption that also covers community decisions is a LAPI AllowList (`docs/firewall-bouncer.md:86-114`), done on the test host (`:858`) and absent from the runbook, which puts the range into a parser whitelist (`runbook.md:224-234`) that `firewall-bouncer.md:93-101` says cannot exempt community decisions. The shipped middleware sets no `clientTrustedIPs` | the files | FIX BEFORE V1 (one procedure, in the runbook and the setup) · DECISION REQUIRED (D8, the default) | Open |
| TD3 | **The runbook describes the managed-mode bouncer the blueprint does not run:** `chain ip crowdsec crowdsec-chain` (`runbook.md:41,91,160,395`) against the set-only objects `cs-public-forward` and `crowdsec-blacklists` (`firewall-bouncer.md:196-231`); rules "persist after a stop" (`:386-388,462`) against removal on stop (`firewall-bouncer.md:261-273`); edits to the package-managed `.yaml` (`:681`) against `.yaml.local` only (`firewall-bouncer.md:424-425`); the retired "Phase" model (`state.md:161`) at `runbook.md:3,456-462` and `acquis.yaml:18-20`. An operator follows the runbook in an incident | the files | FIX BEFORE V1 | Closed 2026-10-15 |
| TD4 | `core/crowdsec/UPSTREAM.md:19-23` lists the plugin and the firewall bouncer as TODO; `:15` says both were verified on a live host | the file | CLEANUP | Closed 2026-10-15 |
| TD5 | `docker-compose.yml:56-57` says the `sshd` collection ships enabled; `.env.example:28-29` does not include it | the two files | CLEANUP | Closed 2026-10-15 — the collection comes with the image (`crowdsecurity/linux`, `build/docker/Dockerfile` at v1.7.8), stated at the compose file |
| TD6 | Two geoblocking mechanisms: `core/traefik/README.md:544-556` installs `geoloc-enrich` and writes a custom scenario; `docs/geoblocking.md:14-16` says `geoip-enrich` already ships with the Traefik collection and describes manual decisions. No measurement of either | the files | CLEANUP · NEEDS HOST EVIDENCE | Documentation closed 2026-10-15: one owner (`geoblocking.md`), the enrichment traced to the image's `crowdsecurity/linux` collection, `geoloc-enrich` removed; the host measurement is open |
| TD7 | `core/traefik/README.md:524` recommends `crowdsecAppsecEnabled: true`; `profiles.md:99` and `appsec.md:45-53` keep it deferred. `profiles.md:239` says `crowdsec-basic` was carried by ntfy's public router in the v0.8.0 host session; `docs/host-session-v0.8.0.md` records no bouncer and `monitoring/ntfy` ships `APP_TRAEFIK_THREAT=` empty | the files | CLEANUP | Closed 2026-10-15 |
| TD8 | Masked traffic is described incompatibly: `ipv6-dual-stack.md:564-576` (a ban "bans the shared gateway identity") against `README.md:219` (the gateway is inside the default whitelist, so the engine derives no such decision) | the files | CLEANUP | Closed 2026-10-15 |
| TD9 | 43 of the 105 stacks with a chain have no `APP_TRAEFIK_THREAT` slot (48 of 129 routers), so the bouncer cannot be attached from `.env` on them; the roll-out was planned "as each is reviewed" (`host-session-plan.md:148`). Every existing value is empty | `traefik-labels.md:46,67-72`; the compose files | FIX BEFORE V1 — the slot on every router is mechanical and changes no behaviour | Open |
| TD10 | Figures kept by hand have drifted: five Traefik scenarios named (`README.md:312-318`) against 55 measured (`reverse-proxy-limits-2026-09-23.md:194-196`); "106 stacks … 101 from `.env`" (`state.md:367`) against 108 and 105 | the files | CLEANUP — generate or drop | Closed 2026-10-15 — the README names the command and the collections; `state.md` recounted (108, 105, fifteen, 49/36, 47 without a slot) |
| TD11 | The access-log buffer is 100 lines by default (`core/traefik/.env.example:169`); the measurement that denied requests write no line used a buffer of 0 (`host-session-findings.md:69-70`); on a quiet host lines reach the engine late (`core/crowdsec/README.md:208`) | the files | CLEANUP — state it at the acquisition section | Closed 2026-10-15 |
| TD12 | Open from before, unchanged: host-firewall acceptance steps 6–9 (second machine); which JSON field the parser reads is now answered (`ClientHost`, last entry) and belongs in `acquis.yaml`'s comment | `state.md:166-179` | NEEDS HOST EVIDENCE | Open |

## E. Findings — the update path

The documented model (`deployment-lifecycle.md`): a git clone checked out at a
tag; update by `git fetch --tags` and `git checkout <tag>`, then the
`CHANGELOG.md` entries between the tags, then recreate the stacks the release
touched; `.env`, `.secrets/` and `volumes/` survive; blueprint and image are two
lifecycles; a copied directory "works and loses" release identity
(`:151-157`). `overview.sh` states the release or that it cannot be identified.

| ID | Finding | Evidence | Class | Status |
|---|---|---|---|---|
| UP1 | **The procedure does not name the render.** `deployment-lifecycle.md` never mentions `render.sh`; the re-render after a checkout is documented only inside the stack (`core/traefik/UPSTREAM.md:142-150`; `README.md:479-512`). A release that changes a template — v0.9.4 did — changes nothing on a host until `render.sh` runs, which `CHANGELOG.md:41` states per release and the lifecycle does not | the files | FIX BEFORE V1 | Open |
| UP2 | **No procedure re-checks host-side files after an update.** The complete list, with the stack that owns each: Traefik logrotate stanza; Traefik watchdog (4 files); Docker daemon watchdog (4 files, "neither script has been run on a live host", `CHANGELOG.md:231`); Borgmatic (config, two units, the binary, the passphrase file, the SSH key); `/etc/docker/daemon.json` (dual-stack flags; also the only place a log-size limit appears, as an example); `sysctl` files for Zammad, Seafile and Seafile Pro; a root crontab line for WordPress; the CrowdSec host-firewall bouncer (package, `.yaml.local`, a systemd drop-in with two `ExecStart`/`ExecStop` scripts and a companion service — described, not shipped as files). `deployment-lifecycle.md:27-30` calls host settings "not yet standardised"; `maintenance.md`'s chains name no host file | `core/crowdsec/docs/firewall-bouncer.md:277-284,405-408,465-476,562-563`; `backup/borgmatic/README.md:45-107`; `business/zammad/README.md:55-57`; `apps/seafile/README.md:488-492`; `apps/wordpress/README.md:216-219` | FIX BEFORE V1 — D5 | Open |
| UP3 | **A second update model contradicts the first.** `TROUBLESHOOTING.md` §5.1 (`:450-469`) and the checklist at `:760-762` describe `git push origin dev` locally and `git pull` on the server — a host tracking `dev`, which `deployment-lifecycle.md:40-42` rules out | the two files | FIX BEFORE V1 | Closed 2026-10-15 |
| UP4 | **Nothing lists what a release touches per stack.** The lifecycle sends the operator to `CHANGELOG.md` prose; `git diff --stat <old>..<new> -- '*/*/'` grouped by stack directory answers it in one command and is written nowhere. No document maps a middleware name to the stacks that reference it (the map in [C.4](#c4-the-security-chains) is the first) | `deployment-lifecycle.md:95-110` | FIX BEFORE V1 — one command in §7, and the map generated by a script beside `lifecycle-report.py` | Open |
| UP5 | **The security-update lane is manual at every step** and `SECURITY.md:52-54` promises a fix within 7 days for Critical. Detection: the Version Chain is triggered by reading advisories (`maintenance.md:147-166`), the two sweeps are dated 2026-07-26 and 2026-09-13 with no cadence; Dependabot covers Actions and `site/` npm only (`.github/dependabot.yml`); `renovate.json` is committed with regex managers, the App is not installed and no pin carries a marker (`docs/renovate-proposal.md:3-19,225-231`); the Trivy gate judges CRITICAL findings on pull requests into `main` only. Repository to release: branch, PR into `dev`, PR into `main`, tag. Release to host: checkout, then an `.env` edit, because pins are never in git. **The shortest path needs no release:** an operator edits the pin and recreates the stack; for Traefik within the 3.7 line, `docker compose pull && docker compose up -d` suffices because `TRAEFIK_IMAGE=traefik:v3.7` floats on the minor (`core/traefik/.env.example:20`; `UPSTREAM.md:54`) | the files | DECISION REQUIRED (D6) · FIX BEFORE V1 (the lane written down) | Open |
| UP6 | **Taking one stack from `dev` is not documented.** `git checkout <ref> -- <stack>/` appears nowhere; the lifecycle says an edited tree makes the release unidentifiable (`:146-149`), which is true of a partial checkout as well | `deployment-lifecycle.md` | CLEANUP — state it as unsupported, or state the procedure and its cost | Open |
| UP7 | **A deployment that is a copied directory cannot run the procedure.** The lifecycle says so (`:148-149`) and gives no way back to a checkout. The way exists: `git init` in place, `git remote add`, `git fetch --tags`, `git reset --soft <tag>` or `git checkout <tag>` with the three ignored paths untouched, then `git status --porcelain` lists what was edited in place — and `host-session-findings.md:903-907` warns against cloning over an existing checkout because Compose adopts the old containers by project name, which a conversion in place avoids | the files | FIX BEFORE V1 — one subsection in the lifecycle | Open |
| UP8 | Open by the documents' own words and unchanged: whether a deployment must stay a git checkout (`:155-156`), multi-host, host hardening; the deploy-script idea (`ROADMAP.md:218-219`); `host-session-plan.md:143-145,215,276` (hand edits discarded by a render; update versus upgrade; dnsmasq zones overwritten) | — | POST-V1 / ON HOLD, except the first, which D5 touches | Open |

## F. Findings — stack shape

Measured over 122 `.env.example` and 134 production compose files (303
services). What the checkers enforce holds everywhere: section order over
recognised sections, `COMPOSE_PROJECT_NAME` first, pinned tags for `_TAG` and
`_IMAGE` variables, no plaintext secrets, no real domains in `_HOST` values,
healthcheck presence or a waiver, resource and swap keys, datastore exposure,
shared-network identity, `@file` on TLS options, `-xl` exposure, and the
baseline flags (0 FAIL in both checkers; 13 WARN: eight missing healthchecks in
`business/plane`, four `identity-source`, one `section-order`). What nothing
enforces:

| ID | Finding | Evidence | Class | Status |
|---|---|---|---|---|
| SH1 | Two `.env.example` dialects: 52 files use the reference's long-dash section headers with layer tags (`apps/_reference/.env.example:26`), 70 the standard's short form (`env-structure.md:11-32`); 66 carry the standard's copy line, 51 the reference's, 4 neither (`core/portainer-agent`, `business/kimai`, `business/opensign`, `business/zammad`). The standard says `COMPOSE_PROJECT_NAME` has no section header (`:36`); the reference and `check-structure.py:63` carry `# --- Project ---` | the files | CLEANUP — one dialect, decided at the standard, applied by script | Decision written into the standard 2026-10-15 — the reference's long form with the layer tag, `Project` header included; the 70 files in the short form convert in Phase 6 |
| SH2 | Eleven files set `TZ` under no Timezone header; seven set none; `apps/seafile/.env.example:104` uses `TIMEZONE=UTC` against the checklist (`env-structure.md:188-201`). Seventeen stacks have a compose `secrets:` block and no `# --- Secrets ---` section | the files | CLEANUP | Open |
| SH3 | `core/shellhub` pins through `SHELLHUB_VERSION`, which `pinned_tag()` (`check-structure.py:559-575`) and the Renovate regex do not read — the one pin the tag rule does not cover; `monitoring/scrutiny` pins a digest variable | the files | CLEANUP — the checker reads `_VERSION`, or the stack renames | Open |
| SH4 | **No service carries a `logging:` policy** (0 of 303) and no standard names a daemon-level `log-opts`; the only occurrence is an example in `ipv6-dual-stack.md:264-266`. With Docker's default `json-file` driver and no `max-size`, container logs grow without bound. `docs/standards/logrotate.md:16` says json-file logs "do not need logrotate", which is true of the driver and only with a size option set somewhere | the files | FIX BEFORE V1 — one line in "Prepare the host" (UP2's daemon.json) or `logging:` in the compose standard | Open |
| SH5 | Six one-shot services use `restart: "no"` or `on-failure` (`core/authentik:14`, `apps/defectdojo:278`, `business/erpnext:370`, `business/openproject:54`, `business/plane:241`, `business/zammad:168`) while `compose-structure.md:78` says `unless-stopped` for all services — correct behaviour, unstated exception | the files | CLEANUP (standard) | Open |
| SH6 | Ten files use `x-` extension fields under eleven unrelated names; the standard is silent. Two files deviate from the top-level key order (`business/openproject`, `business/vikunja`); the same two name the networks `proxy`/`internal` instead of `proxy-public`/`app-internal`. Ten stacks use a third network, `app-egress`, that `compose-structure.md:214-219` does not describe | the files | CLEANUP (standard first, then the files) | Open |
| SH7 | The `APP_TRAEFIK_*` label shape is unchecked beyond `@file` on TLS options: 61 routers carry the canonical three-slot pattern, 48 lack the THREAT slot (TD9), 14 are secondary routers with the access slot only, 3 write a chain literally (RP20) | `traefik-labels.md:43-73` | CLEANUP — one rule in `check-structure.py` once D1 fixes the pattern | Open |
| SH8 | Five stacks parameterise a container limit in `.env` (`TRAEFIK_MEMORY`, ollama, qdrant, vllm, urbackup) while the standard places values in the compose file; `no-resources` checks key presence only, so a `${VAR}` passes | `compose-structure.md:88-190`; `check-structure.py:713-717` | CLEANUP (state the exception) | Open |
| SH9 | The trusted-proxy table behind RP5 — twenty stacks, five value shapes: a guessed `/16` (Nextcloud, Invoice Ninja), `172.16.0.0/12` (Shlink, Gotify, Headscale, mailserver-jeboehm), any address (Monica, OpnForm, Lychee, Zammad, ERPNext, Kimai, ShellHub), a hop count (n8n, HeyForm), a header name (Vaultwarden), an API call (Stalwart), a config key (Keycloak, ntfy, Vikunja, Warpgate documented only); Paperless none | the stacks' compose and env files | with RP5 | Open |

## G. Findings — working memory and governance

| ID | Finding | Evidence | Class | Status |
|---|---|---|---|---|
| WM1 | **Three sections of `.ai/tasks.md` were dropped by a merge.** Both parents of `9b7a171` (2026-09-23, "Merge branch 'dev' into feature/plausible") carry *Blocked on a host*, *Open decisions for the maintainer* and *Doable without a host* with 44 open boxes in total; the merge result carries one section with 13; no commit ever removed the text (`git log -S'Blocked on a host' -- .ai/tasks.md` returns only the commit that added it); the result reached `dev` through PR #186, and `697f2d2` restored two entries. `state.md:178,247,253,402-403` still point at the sections. Of the items, checked against git on 2026-10-15 (corrects the list this row first carried): done — the UrBackup restore section (2026-08-18), the three `Based on version` fields (2026-09-13), the CrowdSec 1.8 hold (by decision, 2026-09-13), Invoice Ninja's entrypoint wrapper (2026-07-29); open and tracked only in `state.md` or a stack file — Priority-1 verification (the same item as §2), Cal.diY `v6.2.0-6`, the Seafile routers (issue #39), borgmatic → Healthchecks, UrBackup, nine majors, legacy stamps, host-firewall acceptance, host-reserve rehearsal, OOM/PSI monitoring, photo-gallery and it-tools first-load counts, dnsmasq/homepage verification, append-only exercise, bouncer-key reproducibility; tracked nowhere — non-root for monitoring stacks running as root, booting `apps/_reference`, OpenProject worker mail after isolation, Vaultwarden to Docker Secrets, `-f` on 18 `curl` healthchecks | `git show 9b7a171^1:.ai/tasks.md`, `9b7a171^2`, `9b7a171` | FIX BEFORE V1 — restore from `9b7a171^1`, reconcile against git | Closed 2026-10-15 — restored from `9b7a171^1`, six items closed with a reason, the rest open with an owner. Of the items listed here as done per git, the UrBackup restore section, the `Based on version` fields, the CrowdSec 1.8 hold and the Invoice Ninja wrapper are; Priority-1 verification, Cal.diY `v6.2.0-6` and the Seafile routers are open, and no item named required checks was in the lost sections |
| WM2 | **`state.md` carries five statements git has overtaken** (corrected 2026-10-15 from six: `.trivy-baseline.json` does list the three unscannable images under `unscanned`, so `state.md:87-90` holds)**:** Suricata and Coraza "are being added" with a ROADMAP section "Being added" (`:203-205`) — decided not, 2026-09-24, no such section; Dify/Langfuse "pending review" (`:122`) — merged 2026-09-19 (#117); "an env-gated render is in `tasks.md`" (`:133`) — landed 2026-09-14; "the disposable host carried v0.7.0 and v0.8.0" (`:257`) — v0.8.1 ran on 2026-09-13 and the candidate sessions on 09-21/23; the review figures (`:367-374`: 106, 101, twelve chains, 48/35) against 108, 105, fifteen, 49/36. "Nine major versions pinned but never started … `LIFECYCLE.md` marks each `pin-drifted`" (`:421`; `ROADMAP.md:103-104`) against zero `pin-drifted` rows in `LIFECYCLE.md` (17 on 2026-09-20) | the files | FIX BEFORE V1 — `state.md` is the session entry point | Closed 2026-10-15, except the Trivy point: `.trivy-baseline.json` carries the three images under `unscanned`, so `state.md` was right there |
| WM3 | The four *Open decisions* in `state.md:281-308`: **1** (commit format) — practice converged on the standard's `scope:` form (154 of 179 September subjects, all of October; the only `type(scope)` subjects since 2026-09-19 are Dependabot's), so the premise is gone; **2** (backup isolation) — still contradictory, `docs/architecture.md:511` ("own isolated backup repository … not a shared monorepo") against `backup/README.md:178-182` ("an option, not a rule"), and `decisions.md:1039-1041` sides with the latter; **3** (host-installed agent) — `docs/architecture.md:17` still promises no host assumption beyond Debian and Docker, no exception recorded; **4** (commit procedure) — `commit-rules.md:8,343,358,398-400` already require asking, nothing proposes otherwise; **5** (Renovate) — `renovate.json` committed 2026-09-17, unmentioned at `:310-314`; the header measurement at `:316-328` is open (D1). The cited line numbers at `:289-290` are stale (`architecture.md:511`, `backup/README.md:178`) | the files | DECISION REQUIRED (D9) | Closed 2026-10-15 — D9 decided as recommended: 1 and 4 struck, 2 changed at `docs/architecture.md`, 3 recorded there as a named exception; 5 (Renovate) stays as D6 |
| WM4 | `progress.md`'s release table ends at v0.8.0 (nine tags since); `risks.md:8` counts 59 stacks, `:15-16` says Trivy blocks nothing and three checks are not required — both overtaken (`state.md:55-57`; `quality-gates.md:74-75`); `quality-gates.md:133-134` says missing limits are "reported, not enforced" against `:64` and `ROADMAP.md:29-32` | the files | CLEANUP | Closed 2026-10-15 |
| WM5 | `decisions.md:3` says newest first; a 2026-09-20 entry at `:933` follows 2026-08 entries, and `:1043-1241` interleave 2026-09, 2026-08 and 2026-04. Two 2026-09 entries carry no day (`:764`, `:1071`). `:62` and `CHANGELOG.md:27` say `rl-spa-xl` kept its bucket; `a9a9a90` also moved its average 100 → 125, recorded nowhere. `:256-259` describes obot's proxy as "tried first"; the outcome is in `CHANGELOG.md:60` only. `:1100` and `state.md:236` say `live-restore` is in "the reference daemon configuration"; no tracked file carries `live-restore` — the only `daemon.json` text in the tree is the dual-stack example | the files | CLEANUP | Closed 2026-10-15 — sorted newest first, the fourteen September entries dated by their recording commit, the three details recorded |
| WM6 | Decisions with no entry: `core/keycloak` (2026-09-07) and `core/authelia` (2026-09-26) — RP11/D4. Entries whose outcome is partly in the tree: 2026-09-20 "image findings as facts" (`:294-325`) reads as decided, while the per-image facts file, the `Exposure` field and the `acc-public` checker do not exist and `tasks.md:22-38` lists them open | the files | CLEANUP — the entry states what is built and what is not | Closed 2026-10-15 — the 2026-09-20 entry states what is built, and the D4 entry is the decision record for Keycloak and Authelia |
| WM7 | **`.ai/` breaks the public-content rule it states** (`state.md:424-426`; `rules.md:105-106`): a real domain (`progress.md:35`; `domains/release.md:15`); a password-manager reference (`decisions.md:403`); personal attribution (`decisions.md:273,337-338`); session context (`state.md:53,278`; `tasks.md:100-102,131`, which names a local working area a clone does not contain); wording that judges earlier work rather than states the fact (`decisions.md:700,817,959-960,1013`; `progress.md:90`; `risks.md:16`). `commit-rules.md:88` carries a model's co-author trailer inside the format template | the files | FIX BEFORE V1 — D10 decides whether history is also rewritten | Closed 2026-10-15 in the files (D10: history stays) — domain, vault path, attribution, session context and judging wording rewritten; the trailer in `commit-rules.md` is a placeholder |
| WM8 | `v1-readiness-audit.md` §G "Remaining work" states "75 of 89 scaffolded" (`:370`) in a section meant to be current; `LIFECYCLE.md` has 89 of 121. `CHANGELOG.md:252,213` date v0.9.0 and v0.9.1 one day before their tags | the files | CLEANUP | Closed 2026-10-15 |
| WM9 | The coherence of the chain: decisions → standards → templates → stacks holds for the twelve most recent decisions (each reflected in the tree, two with the unrecorded details above). The failures are in the other direction — tree changes without an entry (WM6) and memory not updated after a change (WM2) — and in one merge (WM1). The Session Chain (`maintenance.md:116-126`) names `state.md` as the last step and no step for `tasks.md` or `progress.md` | `maintenance.md` | CLEANUP — the chain names all three, and a merge touching `.ai/` is reviewed for lost sections | Open |

## H. Existing installations

What an installation deployed before v0.9.4 establishes before anything in the
programme touches it. Paths assume the checkout at `/path/to/secure-docker-blueprint`.

1. **Which release runs.** `./scripts/overview.sh`, or `git describe --tags`.
   A copied directory answers "not a git checkout"; UP7 is the way back to one.
2. **The v0.9.2 migration** (`CHANGELOG.md:192-199`): install the current
   logrotate stanza with the path substituted, then restart the proxy once so
   the restart policy is armed again. Check first what is installed:

   ```bash
   grep -nE 'docker kill|/path/to/' /etc/logrotate.d/traefik
   ```

   A hit on either line is the earlier shape — the signal that cancels the
   restart policy, or a path that matches no file.
3. **The v0.9.4 migration** (`CHANGELOG.md:41`): in `core/traefik`,
   `bash ops/scripts/render.sh && bash ops/scripts/validate.sh`. Until then the
   proxy runs the rate limits it was rendered with — `rl-soft` 100/50, which is
   what answered `429` to the sync clients.
4. **Where the `429` went** (`TROUBLESHOOTING.md` §4.9): the router and the
   address, from the access log. A sync client or a code-split interface that
   still fails after the render is a candidate for D2, not for a wider bucket.
5. **The trusted-proxy value of every stack that has one** (SH9) against the
   real subnet:

   ```bash
   docker network inspect proxy-public --format '{{range .IPAM.Config}}{{.Subnet}} {{end}}'
   ```

   For Nextcloud additionally `occ config:system:get trusted_proxies` and
   `grep -c 'Bruteforce attempt' nextcloud.log`: a count that grows under
   ordinary use means every user is being throttled as one client.
6. **Host files against the shipped versions** (UP2): the watchdog units if
   installed, `daemon.json` if dual-stack is on, the firewall bouncer's drop-in
   if the host-firewall remediation is on. Until D5 lands, `diff` by hand.
7. **Behind Cloudflare** (RP1–RP2): access policies other than `acc-public` are
   refusing every request, rate limits count per edge, and CrowdSec's decisions
   are not enforced by either bouncer. Nothing to do on the host until D3
   lands; what to expect is now known.

## I. Programme

Phases are ordered so that each one is verifiable on its own and the decisions
that gate the later ones can be taken while the earlier ones land. One pull
request per phase into `dev`, smaller where a phase touches many stacks.

**Phase 0 — existing installations.** Section [H](#h-existing-installations).
No repository change. *Verified by:* the grep in H.2 returns nothing; `validate.sh`
passes after the render; the `429` count is zero for ordinary use.

**Phase 1 — truth at the owners.** Documentation and memory only. RP1 at the
three owners (`traefik-security.md`, the template comment, a note in the
September evaluation); RP3, RP12, RP25, RP27–RP31; TD3–TD8, TD10–TD11; UP3;
WM1 (restore and reconcile), WM2–WM8; SH1's decision written into
`env-structure.md`. *Verified by:* CI's docs jobs; `python3 scripts/ci/check-prose.py --hints`;
`check-links.py`; the three logrotate instructions agree; every pointer in
`state.md` resolves; `git diff 9b7a171^1 -- .ai/tasks.md` shows only items
closed with a reason.

**Phase 2 — proxy operations.** Small, env-gated code changes with a test each
in `scripts/ci/`: RP6 (timeouts, three variables with defaults); RP10/UP2 under
D5 (`render.sh` writes the host files with the real paths into `config/host/`,
`overview.sh --host` diffs them against the installed copies; installing stays
a `sudo` step the README shows); RP11 (Authentik under a switch, same shape as
CrowdSec's); RP13–RP14; RP16; RP20 (two one-line order fixes, `@docker`
suffixes); TD9 (the THREAT slot on every router); SH3–SH4. *Verified by:*
`check-crowdsec-config.py --templates` extended to the new switch; a render with
every switch on and off; on a host: `validate.sh`, `logrotate -d`, `curl -sI`
unchanged on every route, the startup log clean.

**Phase 3 — the client address behind a CDN (D3).** One switch,
`TRAEFIK_FORWARDED_PROXY=none|cloudflare`. The mechanism as designed in `docs/traefik-middleware-proposal.md` (branch `feature/traefik-middleware-proposal`, not merged) — the limits on `requestHeaderName: X-Real-Ip` with a Cloudflare Transform Rule — was dropped during implementation: Cloudflare's Transform Rules cannot modify `x-real-ip`, and a header-reading strategy leaves a direct client without an address. As shipped (2026-10-17): closed access policies and rate limits keep the connecting address, the per-client limit of a public route is a Cloudflare rate-limiting rule at the edge, the CrowdSec middlewares get `forwardedHeadersTrustedIPs` with the plugin's default `X-Forwarded-For` (an independent review, `docs/reviews/phase-3-cloudflare-mode-review-2026-10-17.md`, found the first cut's `CF-Connecting-IP` readable from any sender). *Verified by:* `whoami` from a client behind the proxy
showing the client in `X-Forwarded-For`; an `acc-tailscale` route refusing and
admitting the right addresses; a manual decision on the client's address
answered `403` through `crowdsec-basic`; the last element of the access log's `ClientHost`
equal to the address the bouncer compared. Until measured, the README states
the limitation in one sentence.

**Phase 4 — the chain review (D1, D2).** The standard is rewritten first —
purpose per block in one sentence, the numbers with their measurement — then
the templates, with the existing chain names kept as aliases of the new
compositions for one release so every deployed `.env` keeps its router
(`decisions.md:77-79`). Then the per-stack defaults, re-derived from the four
measured properties and recorded in each `.env.example` with the reason; one
pull request for Traefik, one per group of stacks that move. RP5/SH9 ride
along per stack. *Verified by:* `curl -sI` per route before and after, diffed;
the `429` count on a first load and on a sync run; CI's `burst-exposure` and
the new label-shape rule (SH7).

**Phase 5 — the update path.** `deployment-lifecycle.md` gains the render step
(UP1), the host-file check (UP2), the "what this release touches" command and
the generated middleware map (UP4), the conversion of a copied directory (UP7),
the security-update lane with its shortest path (UP5), and the statement on
partial checkouts (UP6); `TROUBLESHOOTING.md` §5.1 is aligned (UP3). D6
executed either way. *Verified by:* a disposable host taken from v0.9.2 to the
current tag by the written procedure alone.

**Phase 6 — stack shape.** SH1–SH2 and SH5–SH8 by script where mechanical; one
standard change each first. *Verified by:* both checkers at 0 WARN except the
accepted exceptions; `git diff --stat` shows only the intended lines.

What needs a host and no edit closes: RP8, RP17, RP19's measurements, RP23,
TD6, TD12, and Phase 3's measurement.

## J. Decisions required

All twelve were decided on 2026-10-15 and 2026-10-16 and are recorded in
`.ai/decisions.md` at their dates; the recommendations below stay as written.

| ID | Question | Recommendation |
|---|---|---|
| D1 | **The chain model.** (a) Two axes in the label — `APP_TRAEFIK_HEADERS` (`hdr-standard`, `hdr-standard-embed`, `hdr-none` for applications that set their own, `hdr-strict` opt-in) and `APP_TRAEFIK_LIMIT` (`rl-none`, `rl-browser`, `rl-sync`, `rl-admin`), `compress` always, existing `sec-*` names kept as aliases for one release; (b) purpose-named chains (`app-web`, `app-spa`, `app-sync`, `app-own-headers`, `app-admin`, …) in the one existing variable; (c) keep `sec-N`, remove the five unused, state a purpose per chain | **(a).** Each axis is one measured property of the application — does it set its own headers, what does its first load or its sync client issue, is it an admin surface — so the default per stack follows from the measurement and an operator changes one axis without losing the other. (b) recombines the same properties into names and reaches Nextcloud's case (sync, own headers, embed) only with a fourth name. (c) keeps the ladder nobody climbs |
| D2 | **The default rate limit.** Keep a per-address frequency limit in the default (interim values until measured), or make the default headers and compression with the entrypoint timeouts (RP6) and an `inFlightReq` block per router as the availability control, and attach a frequency limit only where a stack states why (admin surfaces, unauthenticated APIs) | **The second**, after Phase 3 and one measurement. The purpose on record is availability; a frequency limit per connecting address answers `429` to the first load of a code-split interface and to every sync client, and spreads one sender over many buckets behind a CDN. The timeouts bound held connections without counting, and the in-flight limit bounded memory per client in the September measurement (400 held requests: 41 MiB with a limit of 100, 95 MiB without). Open risk: long-lived requests — websockets, streams, job logs — hold a slot for their lifetime; untested, which is the measurement |
| D3 | **A CDN mode as a render switch** (Phase 3), Cloudflare only, default off | **Yes** — decided 2026-10-15: `TRAEFIK_FORWARDED_PROXY=none\|cloudflare`. Designed in `docs/traefik-middleware-proposal.md` (branch `feature/traefik-middleware-proposal`, not merged) with the limits on `requestHeaderName: X-Real-Ip` plus a Cloudflare Transform Rule; dropped in Phase 3 (2026-10-17) because Transform Rules cannot modify `x-real-ip`. Shipped: closed policies and rate limits on the connecting address, the per-client limit at the edge, the CrowdSec middlewares with `forwardedHeadersTrustedIPs` and the default `X-Forwarded-For` header — `.ai/decisions.md`, D3 addendum. |
| D4 | **Front doors.** Authentik stays the reference implementation with forward-auth under a switch; Authelia and Keycloak are documented alternatives with no forward-auth template, each recorded in `decisions.md` | **Yes.** Three portals with one switchable integration keep the "one reference implementation" rule; the alternatives keep their stacks |
| D5 | **Host-side state.** (a) `render.sh` renders the host files with real paths into `config/host/`, `overview.sh --host` reports drift against the installed copies, installation stays a shown `sudo` step; (b) an install script that writes to `/etc`; (c) documentation only, with a checklist in the lifecycle | **(a).** Drift becomes visible on every `overview.sh` run without the blueprint writing outside its directory; the shown command stays the operator's act. (b) crosses the line the blueprint keeps; (c) is the state that produced RP7 |
| D6 | **Detection of upstream security releases.** Install Renovate with marker comments added by script to every pin, or keep manual sweeps and write a cadence into the Version Chain. The stabilization audit's D5 recommended deleting `renovate.json` when nothing required lead time; `SECURITY.md:52-54` requires seven days for Critical | **Renovate**, markers added mechanically, majors behind dashboard approval as `renovate.json:50-55` already configures. A seven-day promise with manual detection is a promise about attention |
| D7 | **DNS-01 providers for v1.0.** State Cloudflare as the one wired provider, or make the provider and its credential variable env-selectable | **State it.** No second provider is needed by any deployment on record; the sentence in the README costs nothing and the variable is post-v1 work with a test per provider |
| D8 | **VPN ranges exempt from CrowdSec decisions by default.** Ship the LAPI AllowList step in the setup with its reason, or leave the exemption to the operator | **Ship the step, operator decides.** The banned administrator of 2026-08-28 is the case; the counter-case — a compromised tailnet device — is one the operator can weigh only if the step is in front of them |
| D9 | **The four open decisions in `state.md`.** Strike 1 and 4 (settled by practice and by the standing rule); change 2 at the owner (`architecture.md` adopts the trade-off `backup/README.md` states); record 3 as a named exception in `architecture.md` with the reason from `backup/README.md` | **As stated** |
| D10 | **The public-content violations in `.ai/`.** Rewrite the files, or also rewrite history | **Files only.** The vault path is a reference, not a secret; rewriting a public repository's history is out of proportion and breaks every fork |
| D11 | **`tasks.md`.** Restore the three sections from `9b7a171^1` and close what git shows done, or re-create the open items from the list in WM1 | **Restore.** The parent's text carries the reasons the list in WM1 condenses |
| D12 | **Dual-stack and the bridge trust set.** Keep dual-stack opt-in and close issue #129 by stating in `access.yml.tmpl` and the standard what `acc-local` and `acc-private` admit — the bridge gateway, and therefore any container on a shared network and any process on the host — or make dual-stack the default | **Keep opt-in, state it.** The default touches `daemon.json` and restarts every container on the host; the statement is what the issue asked for |

A decision taken here is recorded in `.ai/decisions.md` at its date and applied
at the owning file in the phase that names it; the status column above changes
in the pull request that closes the finding.
