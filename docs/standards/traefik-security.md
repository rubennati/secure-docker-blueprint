# Traefik Security Architecture

Defines the middleware model of the reverse proxy: what the entrypoint does for every router, the four positions every router carries, the per-app blocks, TLS, and the integrations.

For Traefik label patterns, see [Traefik Labels](traefik-labels.md).
For general container security, see [Security Baseline](security-baseline.md).
What the model replaced, router by router, and how an installation moves: [`core/traefik/docs/middleware-model-migration.md`](../../core/traefik/docs/middleware-model-migration.md).

---

## Overview

Every router on the `websecure` entrypoint passes the same two steps and then its own four:

```text
entrypoint websecure
  threat-crowdsec        when CROWDSEC_BOUNCER_ENABLED — a banned address is refused before any work
  compress               always — the response is compressed, exact exclusions for binary types
router
  1  access-*            who may reach it, by connecting address        (operator)
  2  limit-*             how fast one address may ask                   (repository, from a measurement)
     [block before the profile: frame-self · csp-self-only · hsts-include-subdomains · header-*]
  3  headers-*           which browser-security headers the proxy sets  (repository, from a measurement)
  4  auth-*              who must be identified                         (operator)
     [block after the four: forwarded-proto-https · a path strip · a redirect]
service
```

The definitions live in `core/traefik/ops/templates/dynamic/`:

| File | What it contains |
|------|-----------------|
| `model.yml` | Every value of the four positions, the per-app blocks, and `compress` |
| `tls-profiles.yml` | The three TLS profiles and Traefik's reserved `default` option, built from `TLS_DEFAULT_OPTION` |
| `crowdsec.yml` | `threat-crowdsec` and `threat-crowdsec-appsec` — rendered only with `CROWDSEC_BOUNCER_ENABLED=true` |
| `authentik.yml` | `auth-authentik` — rendered only with `AUTHENTIK_FORWARD_AUTH_ENABLED=true` |
| `routers-system.yml` | The dashboard router, on the four positions |

All files are rendered from `.tmpl` templates via `render.sh`. Traefik watches `config/dynamic/` and hot-reloads changes; the entrypoint list in `config/traefik.yml` is static and changes on a recreate of the container.

The decisions behind the model (D1–D8, 2026-10-18) are in [`.ai/decisions.md`](../../.ai/decisions.md); the measurements they rest on are in [`docs/audits/traefik-architecture-review-2026-10-17.md`](../audits/traefik-architecture-review-2026-10-17.md).

---

## Access Policies (position 1)

Controls WHO can reach a router. Pick one per router; the operator's choice.

| Policy | Who gets through |
|--------|-----------------|
| `access-public` | Everyone (no restriction) |
| `access-lan` | LAN only (RFC1918 + IPv6 ULA) |
| `access-vpn` | VPN only (IPv4 + IPv6) |
| `access-lan-vpn` | LAN + VPN combined |
| `access-blocked` | Nobody (emergency kill switch) |

All policies support IPv4 + IPv6. The VPN ranges are operator-configurable via `core/traefik/.env`:

```env
TAILSCALE_CIDR_V4=100.64.0.0/10
TAILSCALE_CIDR_V6=fd7a:115c:a1e0::/48
```

Local network ranges (RFC1918 for IPv4, ULA `fc00::/7` for IPv6) are hardcoded in `model.yml.tmpl` and are not operator-configurable env variables. `access-lan` and `access-lan-vpn` admit `172.16.0.0/12`, which includes the Docker bridge gateway — an instance can reach itself through the proxy. No external client arrives as the gateway as long as Traefik is published only on the address families `proxy-public` carries, which `validate.sh` checks (see the IPv6 note below).

**Known limitation — the ULA range contains the Tailscale range.** `fd7a:115c:a1e0::/48`, Tailscale's IPv6 range, lies inside `fc00::/7`. On a dual-stack install `access-lan` therefore admits a tailnet client that connects over IPv6, although the policy is meant for the LAN alone; `access-lan-vpn` admits it by design. Over IPv4 it does not — `100.64.0.0/10` is not RFC1918. Open; not changed by the published-address check.

---

## Trusted Proxy Headers (`traefik.yml` — `forwardedHeaders`)

`forwardedHeaders.trustedIPs` decides whose `X-Forwarded-*` headers survive the
entrypoint. Traefik's reference: *"Set the IPs or CIDR from where Traefik trusts
the forwarded headers information (`X-Forwarded-*`)."* From any other sender the
`X-Forwarded-*` headers and `X-Real-Ip` are deleted before a middleware or the
application sees them, and `X-Real-Ip` is set from the connecting address.

The setting changes which headers the application receives. It does not change
what the access policies and rate limits evaluate:

- `ipAllowList` — *"If no strategy is set, the default behavior is to match
  `sourceRange` against the Remote address found in the request."*
- `rateLimit`, `sourceCriterion` — *"If none are set, the default is to use the
  request's remote address field (as an `ipStrategy`)."*

`model.yml.tmpl` sets no `ipStrategy` and no `sourceCriterion`, so every
`access-*` policy and every `limit-*` counter evaluates the address of the TCP
connection. Which address that is depends on the path:

| Path | Connecting address | `access-lan` / `access-vpn` / `access-lan-vpn` | `limit-*` | The application receives |
|---|---|---|---|---|
| Direct — VPN, LAN, a public client with no CDN in front | the client | evaluate the client | one bucket per client | `X-Forwarded-For` and `X-Real-Ip` carry the client; a header the client sent is deleted |
| Cloudflare's proxy | Cloudflare's edge address | evaluate the edge, which is in none of their ranges — every request is refused | one bucket per edge address, shared by every visitor behind it | `X-Forwarded-For` = `client, edge`; `X-Real-Ip` = the edge |

Which senders are trusted is `TRAEFIK_FORWARDED_PROXY` in `core/traefik/.env`:

| Mode | Entrypoints trust | CrowdSec bouncer compares | Rendered besides |
|---|---|---|---|
| `none` (default) | nobody — the list renders empty | the connecting address | — |
| `cloudflare` | the ranges of `ops/cloudflare-ips.txt`, compared with cloudflare.com weekly | the last `X-Forwarded-For` entry outside those ranges (`forwardedHeadersTrustedIPs`): the client Cloudflare appended; a direct client by its connection, because the entrypoint deleted its header | `config/host/cloudflare-ranges.nft`, the same ranges as nftables defines for a rule on the forward hook |

The bouncer plugin never checks who sent its header: it takes the configured
header from any request, walks it from the right past the trusted ranges and
falls back to the connection only when nothing is left. What makes the result
trustworthy is the entrypoint, which deletes `X-Forwarded-For` from every
sender outside `trustedIPs` — so the plugin's default header is the only one
that can be used, and `forwardedHeadersCustomName` (`CF-Connecting-IP`,
`True-Client-IP`) must never be set: Traefik deletes only its own
`X-Forwarded-*` set and `X-Real-Ip`, and any other header reaches the
middleware from any client. `validate.sh` refuses a rendered middleware that
names one. The same holds for an application: one that reads
`CF-Connecting-IP`, `True-Client-IP` or `Forwarded` is on its own in both
modes, since nothing deletes those from a direct client.

The closed access policies evaluate the connecting address in both modes —
their clients connect directly, and a proxied request to such a host is refused
over IPv4 and IPv6; an IPv4-only `proxy-public` accepts no IPv6 connection at all
(README, "IPv6 between Cloudflare and the origin"). The rate limits count per edge address at the origin behind
Cloudflare: a `sourceCriterion` that reads a header puts every direct client
into one shared bucket, so the per-client limit of a public route is a
Cloudflare rate-limiting rule by IP at the edge. What Cloudflare has to be set
to, the origin firewall on the forward hook, where the mode's trust ends
(Workers, other zones, WARP clients) and the per-application consequences
(`X-Forwarded-For` carries two hops, `X-Real-Ip` is the edge) are in
`core/traefik/README.md`, "Behind Cloudflare". `render.sh` refuses to render
over a configuration whose list trusts anyone while `.env` does not declare
the mode — absent or empty — so an installation from before the switch decides
rather than loses its addresses; `validate.sh` refuses a rendered list that
differs from the ranges file.

**Never set `forwardedHeaders.insecure=true`.** It keeps the forwarded headers
from every sender — the reference: *"We recommend to use this option only for
tests purposes, not in production."* A client then chooses what the application
reads as its address, and any middleware that evaluates the header through an
`ipStrategy` passes a forged one.

**IPv6 note:** Tailscale always gives a client an IPv6 address, and no
header carries it on this path: Traefik sees it only if `proxy-public`
carries IPv6. On an IPv4-only `proxy-public` Traefik is published on IPv4
only, so an IPv6 connection — a tailnet client's, Cloudflare's to an
`AAAA`-only origin, a direct client's — is refused rather than handed to
Traefik from the Docker gateway, which `access-lan` would admit. The
dual-stack overlay publishes IPv6 together with the IPv6 subnet, and
`validate.sh` checks that the Docker daemon forwards it by NAT (README,
"Published addresses"). See
[`core/traefik/docs/ipv6-dual-stack.md`](../../core/traefik/docs/ipv6-dual-stack.md)
for the full explanation, the dual-stack network setup, and the
migration path for existing IPv4-only installs. Allowlisting the gateway
address as a workaround is explicitly **not** the fix — see "Why
`172.19.0.1/32` in `ipAllowList` is a workaround, not a fix" in that
document.

---

## Rate Limits (position 2)

Each counter counts per client address and per router. `burst` is the size of
the bucket: that many requests pass at once. `average` is what refills it per
second. A request the bucket cannot cover is answered `429`: Traefik holds it
for at most half the interval between two refills — 4 ms at 125 per second —
and no longer.

| Limit | Average / burst | For |
|---|---|---|
| `limit-standard` | 125 per second, 500 | the default. Every first load measured in this repository fits, except Twenty's and Windmill's |
| `limit-strict` | 20 per second, 40 | administration surfaces and login-only routes — requests are few and each is worth slowing an attacker down. The wrong choice for anything a browser loads assets from |
| `limit-sync` | 1000 per second, 1000 | applications whose desktop or mobile clients synchronise files (Nextcloud, Seafile): a sync is bounded by the sustained rate, not by the bucket |
| `limit-extra-large` | 125 per second, 1000 | a whole first load in one bucket (Twenty 516 requests, Windmill 857, measured). CI accepts it only behind `access-lan`, `access-vpn`, `access-lan-vpn` or `access-blocked` (`burst-exposure`) |
| `limit-none` | no counter | a websocket or long-poll endpoint, a static-asset router, a server called by another server — each a documented choice, not a type rule |

The sustained rate — 125 per second — bounds abuse; the burst is a first-load
allowance. Behaviour over time (crawling, password guessing, probing) is
CrowdSec's layer, which already draws the static/dynamic line the counter
cannot. What a wider bucket costs is more requests from one address before the
first `429`; what it buys is an interface that loads. **Measure rather than
assume** — a single-page app, a gallery grid and a dashboard all look alike
from outside:

```bash
# Load the app in a private window with the network tab open, then read the
# request count for the first paint. Or, from the host, count what arrives:
docker compose -f core/traefik/docker-compose.yml logs --since 1m app \
  | grep -c "$(date +%Y-%m-%d)"
```

A `429` on first load presents as a blank page or a half-rendered interface,
which nobody attributes to the proxy. A sync client under `limit-standard`
empties the bucket within seconds and reports every `429` as a failed file.

Record the answer where the value lives: the stack's `.env.example` carries
`APP_TRAEFIK_LIMIT`, with the measurement beside it. A value with no stated
reason is a value the next person cannot safely change. This document keeps no
per-stack list — a second copy of a value drifts from the one the stack ships.

---

## Header Profiles (position 3)

Traefik's `headers` middleware **sets** a header; it never adds only what is
missing (measured 2026-10-18). A profile therefore says "the proxy sets
these", and an application that sends its own takes
`headers-application-owned` plus the single blocks for what it lacks. Every
profile starts with the HSTS base: HTTPS is the only operating mode, and a
router on `headers-none` still commits its host name to it. The position is
mandatory on every router.

| Profile | The proxy sets | For |
|---|---|---|
| `headers-standard` | `hsts-base`, `header-nosniff`, `header-frame-deny`, `header-referrer`, `header-permissions` | an application that sends none of these — the conservative default |
| `headers-application-owned` | `hsts-base` | an application measured to send its own; the compose file appends the `header-*` blocks it lacks (Keycloak: `header-permissions`; Matomo: `header-nosniff`, `header-permissions`; Vaultwarden: none) |
| `headers-none` | `hsts-base` | debugging a route |

| Block | Header |
|---|---|
| `hsts-base` | `Strict-Transport-Security: max-age=<HSTS_MAX_AGE>` — two years as shipped, from `core/traefik/.env` |
| `header-nosniff` | `X-Content-Type-Options: nosniff` |
| `header-frame-deny` | `X-Frame-Options: DENY` |
| `header-referrer` | `Referrer-Policy: strict-origin-when-cross-origin` |
| `header-permissions` | `Permissions-Policy` — camera, microphone, geolocation, payment, USB, magnetometer, gyroscope, accelerometer off |

### HSTS — the HTTPS policy

HTTPS is mandatory for every web service Traefik serves; the `web` entrypoint
only redirects. HSTS with a two-year `max-age` is on for every router.
`includeSubDomains` and `preload` are decided **per host name**, never
deployment-wide: the block `hsts-include-subdomains`, placed before the
profile in the router's list, sends both. `preload` commits a domain to the
browsers' preload list once submitted and is hard to reverse; `includeSubDomains`
on an apex host covers the whole zone. Neither is ever set by a default. An
application's own `Strict-Transport-Security` is overwritten by the profile's
value — what a migration preserves is the behaviour clients already receive
through the proxy, not the backend's direct header.

### Per-app blocks

A block corrects one thing for one application, with its reason in that
stack's `.env.example` or `README.md`. Its side of the four is what makes it
work:

| Block | Placed | What it does |
|---|---|---|
| `frame-self` | before the profile | `X-Frame-Options: SAMEORIGIN` — the application frames its own pages (listmonk's campaign preview, Nextcloud) |
| `csp-self-only` | before the profile | an enforcing `Content-Security-Policy` for an application tested against it (whoami) |
| `hsts-include-subdomains` | before the profile | the per-domain HSTS extension, see above |
| `header-*` | before the profile | one header an `application-owned` stack lacks |
| `forwarded-proto-https` | after the four | `X-Forwarded-Proto: https` to the backend — an application that derives its URLs from it (Paperless-ngx, Matomo, the office servers, Ghost's ActivityPub) |

Traefik applies the response changes of the first middleware in the list
last, so a response-header block placed **before** the profile overrides it,
and one placed after it loses (measured 2026-10-18; first seen on v3.6,
[`docs/bugfixes/keycloak-admin-console-iframe-2026-09-07.md`](../bugfixes/keycloak-admin-console-iframe-2026-09-07.md)).
CI reports a block on the wrong side (`block-order`).

### Framing — what `frame-self` is, and what it is not

Being framed is the application's own attack surface: a page any site may
frame is a page any site can overlay, and the user acts on what they think
they see. Keep the denying default unless embedding is a feature the operator
uses.

`frame-self` sends `SAMEORIGIN`, and same origin means the same scheme, host
and port. `dash.example.com` embedding `paperless.example.com` is a different
origin, so the frame is refused exactly as it would be under `DENY`. The block
covers an application framing *its own* pages. It does nothing for one stack
embedding another — the four dashboards this blueprint ships (`apps/dashy`,
`apps/heimdall`, `apps/homarr`, `apps/homepage`) frame nothing by default, and
a dashboard tile that opens the app in a new tab needs none of this. Where
embedding is wanted, the **target** names the parent origin with a
`frame-ancestors` CSP of its own, as the office servers do for the file host
that embeds the editor:

```yaml
- "traefik.http.middlewares.${COMPOSE_PROJECT_NAME}-csp.headers.contentSecurityPolicy=frame-ancestors 'self' https://dash.example.com;"
```

placed before the profile. An application that sets its own frame header per
page or per endpoint — Keycloak, Vaultwarden, Matomo, measured — is
`headers-application-owned`, so the proxy sets none and the application's
value reaches the browser.

### Which profile for an application

Answer against the running application, not from its category:

```bash
curl -sI https://app.example.com/ | grep -iE 'strict-transport|x-content-type|x-frame|referrer-policy|permissions-policy|content-security-policy'
```

Sends none of them → `headers-standard`. Sends some → `headers-application-owned`
plus one `header-*` block per header it lacks, and the measurement in the
stack's `README.md`. Sends a frame header that varies per page → never
`headers-standard`, whose `DENY` would overwrite it on every page.

---

## The Auth Position (position 4)

Who must be identified before the request reaches the application. The value
carries its provider:

| Value | Meaning |
|---|---|
| `auth-none@file` | the application has its own login, or none is wanted — the explicit "no gate" |
| `auth-authentik@file` | forward-auth through `core/authentik`: the outpost is asked for every request; no session, no pass; outpost unreachable, no pass. Exists only with `AUTHENTIK_FORWARD_AUTH_ENABLED=true` |
| `${COMPOSE_PROJECT_NAME}-auth@docker` | a basicAuth the stack defines itself from its own user list (`apps/paperless-gpt`, `monitoring/scrutiny`) |

A gate on one path of a host — `apps/paperless-ngx`'s `/admin` — is a second
router with `auth-authentik@file` in its auth position and `auth-none@file`
on the main one ([`core/authentik/README.md`](../../core/authentik/README.md#integrating-other-apps-via-forward-auth)).

---

## Threat Enforcement and Compression (the entrypoint)

Both are deployment decisions, made once in `core/traefik/.env` and placed by
`render.sh` on `entryPoints.websecure.http.middlewares`, in front of every
router — first on the request, last on the response (measured 2026-10-18).

| Entrypoint middleware | Switch | What it does |
|---|---|---|
| `threat-crowdsec` | `CROWDSEC_BOUNCER_ENABLED=true` | refuses a request from an address the CrowdSec LAPI has a decision for, before any other work; stream mode, fail-open |
| `threat-crowdsec-appsec` | `CROWDSEC_APPSEC_ENABLED=true` as well | the same, plus synchronous inspection of each request against the AppSec rule sets, fail-open — placed instead of `threat-crowdsec` |
| `compress` | always | compresses responses above 1024 bytes whose type is not excluded; the exclusions are exact types (`application/octet-stream`, `image/png` measured; jpeg, webp, avif, gif, zip, gzip, mp4, mpeg, woff2 by type). Streams are not buffered: `text/event-stream` stays compressible, a websocket upgrade is untouched |

CrowdSec and AppSec are optional parts of the blueprint and off as shipped;
each installation decides whether to enable them. Once enabled they hold for
every router on the entrypoint — a router cannot opt out, and an address that
must never be refused is a CrowdSec AllowList (`core/crowdsec`,
`CROWDSEC_ALLOWLIST_ADMIN`), never a label. AppSec in particular is one
decision for every application at once: an application with known WAF false
positives (`core/crowdsec/docs/appsec.md` lists them) keeps the whole
installation at `threat-crowdsec` until a path-scoped exclusion exists. The
entrypoint list is static configuration: after a render that switches the
bouncer off, the Traefik container has to be recreated at once — until then
the running list names a middleware the dynamic configuration no longer
defines, and every router on the entrypoint is disabled. Switching it on has
no such window. The bouncer's settings, AppSec's progression and what each
blocks: [`core/crowdsec/docs/profiles.md`](../../core/crowdsec/docs/profiles.md),
[`core/crowdsec/docs/appsec.md`](../../core/crowdsec/docs/appsec.md).

---

## Integrations (`crowdsec.yml`, `authentik.yml`)

External services that plug into Traefik as middleware. Each is independent and
optional, and each is rendered by its own switch in `core/traefik/.env` — no
template is edited to enable one, and `integrations.yml` renders empty.

| Integration | Type | Where it acts | Switch |
|-------------|------|-------------|--------|
| `threat-crowdsec`, `threat-crowdsec-appsec` | Traefik plugin | the `websecure` entrypoint, every router | `CROWDSEC_BOUNCER_ENABLED`, `CROWDSEC_APPSEC_ENABLED` |
| `auth-authentik` | Forward auth | the auth position of the routers whose `APP_TRAEFIK_AUTH` names it | `AUTHENTIK_FORWARD_AUTH_ENABLED` |

One switch renders both CrowdSec halves: the plugin into Traefik's **static**
configuration and the entrypoint list, which take effect on a recreate of the
container, and the two middleware definitions into `config/dynamic/crowdsec.yml`,
which is hot-reloaded; with the switch off, `render.sh` removes the middleware
file. The forward-auth gate is dynamic configuration only —
`config/dynamic/authentik.yml`, hot-reloaded, removed the same way; a router
whose auth position still names it is then disabled by Traefik, not left open.
`validate.sh` refuses a `config/` that disagrees with either switch, and
`render.sh` refuses to render over a configuration that carries an
integration `.env` does not declare.

AppSec is CrowdSec's request-inspection (WAF) component; what it blocks
depends on which rule sets are installed, so treat its coverage as the rule
sets' coverage rather than as general request filtering. It needs the AppSec
listener on port 7422. See [`core/crowdsec/docs/appsec.md`](../../core/crowdsec/docs/appsec.md)
before switching it on, and the [Traefik README](../../core/traefik/README.md)
for the step-by-step enable and disable procedure.

---

## TLS Profiles (`tls-profiles.yml`)

| Profile | Min TLS | Use case |
|---------|---------|----------|
| `tls-compatible` | 1.2 | older clients must connect |
| `tls-standard` | 1.2 | strict ciphers and curves, X25519 preferred — the deployment standard |
| `tls-strict` | 1.3 | current browsers and clients only |

A router with `tls=true` — every blueprint router — takes the file provider's
reserved `default` option, never the entrypoint's (measured 2026-10-18: an
entrypoint-level option reaches no such router, so the template sets none).
`render.sh` builds `default` from `TLS_DEFAULT_OPTION` in `core/traefik/.env`,
`tls-standard` as shipped. Changing it takes effect on a recreate of the
container, not on a reload.

A router names an option of its own only as a documented exception —
`tls.options=${APP_TRAEFIK_TLS_OPTION}@file`, with the reason above the variable
in the stack's `.env.example`: `tls-strict` for a password manager or a
privileged-access console, `tls-compatible` where a client that is not current
has to connect. Two routers of one stack serving the same host name with
different options are a conflict Traefik resolves by serving `default` to both
and logging it; CI refuses it (`tls-conflict`) and `overview.sh --host` repeats
the check across stacks with the live `.env` files. `core.strictTLSOptions`,
which would fail such a conflict closed instead, stays off until the check has
run on every host.

---

## Reaching a backend over TLS (`servers-transports.yml`)

The profiles above cover the connection a *client* makes to Traefik. A
**serversTransport** covers the other hop: the one Traefik makes to the
container behind it. Nothing needs it while a backend speaks plain HTTP on the
internal network, which is the normal case here.

One case needs it. A service whose clients speak gRPC needs HTTP/2 with TLS the
whole way, so the container terminates TLS itself with a certificate no public
authority issued. `backend-selfsigned` is the transport for that:

```yaml
traefik.http.services.<name>.loadbalancer.server.scheme=https
traefik.http.services.<name>.loadbalancer.serverstransport=backend-selfsigned@file
```

Traefik does not verify that certificate. The hop stays encrypted and stays on
this host's Docker network; what is given up is the assurance that the container
answering is the one the certificate was issued for. It is therefore for a
backend on this host, not for one reached across a network somebody else routes.

**A serversTransport comes from the file provider only.** The equivalent Docker
labels are ignored — a service naming `<name>@docker` fails with "servers
transport not found" and its router serves nothing. Measured against Traefik
v3.7 on 2026-09-23. `backup/kopia` is the stack that uses it.

---

## Incident Response

An application router's middlewares are labels that read the application's `.env`,
so each move below is an `.env` change in that stack, applied with
`docker compose up -d`. `config/dynamic/*.yml` is rendered output and is overwritten
by the next `render.sh`; the dashboard's values live in `core/traefik/.env` and reach
`config/dynamic/` through the render, which the file provider hot-reloads.

| Action | How |
|--------|-----|
| Block a service immediately | `APP_TRAEFIK_ACCESS=access-blocked` |
| Lock to VPN only | `APP_TRAEFIK_ACCESS=access-vpn` |
| Escalate rate limiting | `APP_TRAEFIK_LIMIT=limit-strict` — 20 requests per second and burst 40, answers `429` to a browser's asset load as well |
| Block an IP via CrowdSec | `docker exec crowdsec cscli decisions add --ip X.X.X.X --duration 24h --reason "incident"` — enforced on every router after the next poll (60 s) while `CROWDSEC_BOUNCER_ENABLED` is on; on none otherwise |
| Switch certificate resolver | `APP_TRAEFIK_CERT_RESOLVER` between `cloudflare-dns` (DNS-01), `httpResolver` (HTTP-01) and `tlsResolver` (TLS-ALPN-01), with the `certresolver` label uncommented; `TRAEFIK_DASHBOARD_CERT_RESOLVER` for the dashboard, then `render.sh` |
