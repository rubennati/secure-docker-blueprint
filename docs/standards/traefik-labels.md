# Traefik Labels

How a stack's compose file attaches its routers to the reverse proxy: the
label block, the four middleware positions every router carries, the
variables in `.env` that fill them, and the cases that need more than the
pattern. What the middlewares do — the policies, the counters, the header
profiles, TLS — is [`traefik-security.md`](traefik-security.md).

## Provider Suffixes

Every Traefik resource reference (middleware, TLS option, router, service) names the provider that defines it.

| Suffix | Provider | Used for |
|--------|----------|----------|
| `@file` | File provider | Resources defined in `core/traefik/config/dynamic/*.yml` — `model.yml` (every position's values and the per-app blocks), `tls-profiles.yml`, `crowdsec.yml` and `authentik.yml` when their switch is on |
| `@docker` | Docker provider | Resources defined inline via `traefik.*` labels in a service's `docker-compose.yml` — a stack's own basicAuth, a CSP it owns, a path strip |

### Common references in this blueprint

- `access-*@file`, `limit-*@file`, `headers-*@file`, `auth-none@file` — the four positions, from `model.yml`
- `frame-self@file`, `csp-self-only@file`, `hsts-include-subdomains@file`, `header-*@file`, `forwarded-proto-https@file` — the per-app blocks, from `model.yml`
- `auth-authentik@file` — from `authentik.yml`, rendered only with `AUTHENTIK_FORWARD_AUTH_ENABLED=true` in `core/traefik/.env`
- `${COMPOSE_PROJECT_NAME}-auth@docker` — a basicAuth the stack defines itself (`apps/paperless-gpt`, `monitoring/scrutiny`)

`threat-crowdsec@file` and `compress@file` are never named on a router: `render.sh` places them on the `websecure` entrypoint, in front of every router.

### Common failure mode

Omitting the suffix (or mixing them up) produces:

```text
middleware "limit-standard" does not exist
middleware "my-app-auth@file" does not exist
```

Traefik disables a router that names a middleware it cannot find and answers 404 for it. An **empty** variable has the same effect — `${APP_TRAEFIK_LIMIT}@file` with `APP_TRAEFIK_LIMIT` unset is the middleware `@file`, which does not exist. `./scripts/overview.sh` lists such routers under *empty positions*. See [`troubleshooting.md`](troubleshooting.md) for diagnostic steps.

## Standard Pattern

Every service with web access gets this label block:

```yaml
labels:
  # Router
  - "traefik.enable=true"
  - "traefik.docker.network=${TRAEFIK_NETWORK}"
  - "traefik.http.routers.${COMPOSE_PROJECT_NAME}.rule=Host(`${APP_TRAEFIK_HOST}`)"
  - "traefik.http.routers.${COMPOSE_PROJECT_NAME}.entrypoints=websecure"
  # TLS — the file provider's default option; no tls.options label (see TLS below)
  - "traefik.http.routers.${COMPOSE_PROJECT_NAME}.tls=true"
  #- "traefik.http.routers.${COMPOSE_PROJECT_NAME}.tls.certresolver=${APP_TRAEFIK_CERT_RESOLVER}"
  # Middlewares — the four positions, in this order
  - "traefik.http.routers.${COMPOSE_PROJECT_NAME}.middlewares=${APP_TRAEFIK_ACCESS}@file,${APP_TRAEFIK_LIMIT}@file,${APP_TRAEFIK_HEADERS}@file,${APP_TRAEFIK_AUTH}"
  # Service
  - "traefik.http.services.${COMPOSE_PROJECT_NAME}.loadbalancer.server.port=80"
```

### The four positions on one router

The middleware list answers four independent questions, in this order:

| Position | Variable | Question | Values |
|---|---|---|---|
| 1 | `APP_TRAEFIK_ACCESS` | Who may reach this router, by connecting address? | `access-public` · `access-trusted` · `access-vpn` · `access-trusted-vpn` · `access-blocked` |
| 2 | `APP_TRAEFIK_LIMIT` | How fast may one address ask? | `limit-standard` · `limit-strict` · `limit-sync` · `limit-extra-large` · `limit-none` |
| 3 | `APP_TRAEFIK_HEADERS` | Which browser-security headers does the proxy set? | `headers-standard` · `headers-application-owned` · `headers-none` — every profile starts with the HSTS base |
| 4 | `APP_TRAEFIK_AUTH` | Who must be identified before the request reaches the app? | `auth-none@file` · `auth-authentik@file` · `${COMPOSE_PROJECT_NAME}-auth@docker` |

Every router carries all four, explicitly; a deliberate "off" is written as
`limit-none`, `headers-none` or `auth-none@file`, so that an empty variable —
a missing configuration — stays distinguishable from a choice. The access and
auth positions are the operator's; the limit and headers positions are the
repository's, from a measurement, and the stack's `.env.example` says why.

**Order matters.** Access is decided before anything is counted, the counter
before the gate asks who the caller is; the headers profile is applied on the
response, where its position decides what a per-app block may override.

**The auth value carries its provider.** `auth-none@file` and
`auth-authentik@file` come from the file provider; a stack's own basicAuth
needs the stack's user list and lives in its compose labels, so its value is
`${COMPOSE_PROJECT_NAME}-auth@docker`. The label therefore ends in
`${APP_TRAEFIK_AUTH}` without a suffix of its own.

**The line above the auth variable states the posture.** `# auth posture:
app-login`, `public`, `basic`, `forward-auth` or `none`, with the reason after a
dash; CI checks that it is there and fits the value, and that `none` sits behind
a closed access policy ([`traefik-security.md`](traefik-security.md), "The posture
beside the value").

**Threat enforcement and compression are not positions.** `compress` sits on
the `websecure` entrypoint in front of every router. CrowdSec is optional and
off as shipped: an installation that enables it (`CROWDSEC_BOUNCER_ENABLED`,
its inspecting variant by `CROWDSEC_APPSEC_ENABLED`) puts `threat-crowdsec` on
the same entrypoint, and then in front of every router — a stack cannot opt
out; an exemption from a CrowdSec decision is an AllowList in `core/crowdsec`,
never a label.

- Router and service name = `${COMPOSE_PROJECT_NAME}` (unique per app)
- Network via `${TRAEFIK_NETWORK}` variable (always set explicitly for multi-network setups)
- Port hardcoded per app (not a variable — it's a fixed property of the image)
- `certresolver` commented out by default — the wildcard path serves every subdomain without it, and a per-host certificate would publish that hostname in Certificate Transparency logs (see [Enabling certresolver](#enabling-certresolver))

## .env Values

| Variable | Possible Values |
|----------|----------------|
| `APP_TRAEFIK_HOST` | `app.example.com` |
| `APP_TRAEFIK_CERT_RESOLVER` | `cloudflare-dns`, `httpResolver`, `tlsResolver` |
| `APP_TRAEFIK_ACCESS` | `access-public`, `access-trusted`, `access-vpn`, `access-trusted-vpn`, `access-blocked` |
| `APP_TRAEFIK_LIMIT` | `limit-standard`, `limit-strict`, `limit-sync`, `limit-extra-large`, `limit-none` |
| `APP_TRAEFIK_HEADERS` | `headers-standard`, `headers-application-owned`, `headers-none` |
| `APP_TRAEFIK_AUTH` | `auth-none@file`, `auth-authentik@file`, `${COMPOSE_PROJECT_NAME}-auth@docker` |
| `APP_TRAEFIK_TLS_OPTION` | only on a stack with a documented exception: `tls-compatible`, `tls-standard`, `tls-strict` |
| `TRAEFIK_NETWORK` | `proxy-public` |

A secondary router whose answer differs from the stack's gets a variable of
its own, named for the router: `APP_TRAEFIK_API_ACCESS` and
`CLIENT_TRAEFIK_ACCESS` (`apps/shlink`), `AGW_UI_TRAEFIK_ACCESS`
(`apps/agentgateway`), `APP_TRAEFIK_UI_ACCESS` (`monitoring/ntfy`),
`STATIC_TRAEFIK_LIMIT` (`core/authentik`), `SIDE_TRAEFIK_LIMIT` (`apps/seafile`,
`apps/seafile-pro`), `ADMIN_TRAEFIK_AUTH` (`apps/paperless-ngx`). Where the
answer is the same, the router reads the stack's variable.

## Access Policies

| Policy | Who gets through |
|--------|-----------------|
| `access-public` | Everyone (no restriction) |
| `access-trusted` | the ranges `TRUSTED_RANGES` declares in `core/traefik/.env`; empty admits nobody |
| `access-vpn` | VPN only (`TAILSCALE_CIDR_V4` + `TAILSCALE_CIDR_V6` from `core/traefik/.env`) |
| `access-trusted-vpn` | the declared ranges + VPN |
| `access-blocked` | Nobody (emergency kill switch) |

Which address a policy evaluates: [`traefik-security.md`](traefik-security.md#trusted-proxy-headers-traefikyml--forwardedheaders).

## Rate Limits

| Limit | Average / burst | For |
|---|---|---|
| `limit-standard` | 125 per second, 500 | the default — every first load measured so far but two fits |
| `limit-strict` | 20 per second, 40 | administration surfaces, login-only routes |
| `limit-sync` | 1000 per second, 1000 | applications with file-sync clients |
| `limit-extra-large` | 125 per second, 1000 | a whole first load in one bucket; CI accepts it only behind `access-trusted`, `access-vpn`, `access-trusted-vpn` or `access-blocked` (`burst-exposure`) |
| `limit-none` | no counter | a websocket or long-poll endpoint, a server called by another server |

## Header Profiles

| Profile | The proxy sets |
|---|---|
| `headers-standard` | HSTS base, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy` |
| `headers-application-owned` | HSTS base only — the application sends its own, measured; the compose file appends the `header-*` blocks it lacks |
| `headers-none` | HSTS base only — debugging a route; never "nothing" |

Every profile starts with `hsts-base` (`max-age` from `HSTS_MAX_AGE` in
`core/traefik/.env`, two years). `includeSubDomains` and `preload` are a
decision per host name, the block `hsts-include-subdomains`, never a default.

## TLS

A router with `tls=true` takes the file provider's `default` option, which
`render.sh` builds from `TLS_DEFAULT_OPTION` in `core/traefik/.env`
(`tls-standard` as shipped). The standard pattern therefore has **no
`tls.options` label**. A stack names one only as a documented exception, with
the reason above `APP_TRAEFIK_TLS_OPTION` in its `.env.example`:

```yaml
- "traefik.http.routers.${COMPOSE_PROJECT_NAME}.tls.options=${APP_TRAEFIK_TLS_OPTION}@file"
```

| Profile | Min. Version | Compatibility |
|---------|-------------|---------------|
| `tls-compatible` | TLS 1.2 | older clients must connect |
| `tls-standard` | TLS 1.2 | strict ciphers and curves — the deployment standard |
| `tls-strict` | TLS 1.3 | current browsers and clients only |

Two routers of one stack that serve the same host name must name the same
option, or none: Traefik resolves the conflict by serving `default` to both
and logs it; CI refuses it (`tls-conflict`).

## Special Cases

### A per-app block

A block from `model.yml` corrects one thing the profile would get wrong for
this application. Where it stands decides what it does:

| Block | Where | Why there |
|---|---|---|
| `frame-self` (the application frames its own pages), `csp-self-only` (an enforcing CSP the application was tested against), `hsts-include-subdomains` (the per-domain HSTS extension), `header-nosniff`, `header-permissions`, `header-frame-deny`, `header-referrer` (a single header an `application-owned` stack lacks) | **before** `${APP_TRAEFIK_HEADERS}@file` | Traefik applies the response changes of the first middleware last, so a block before the profile wins over it (measured 2026-10-18) |
| `forwarded-proto-https` (the application builds its URLs from `X-Forwarded-Proto`), a path strip, a redirect | **after** `${APP_TRAEFIK_AUTH}` | a request header or a rewrite the gate never needs to see |

```yaml
# listmonk: frames its campaign preview
- "traefik.http.routers.${COMPOSE_PROJECT_NAME}.middlewares=${APP_TRAEFIK_ACCESS}@file,${APP_TRAEFIK_LIMIT}@file,frame-self@file,${APP_TRAEFIK_HEADERS}@file,${APP_TRAEFIK_AUTH}"
# Keycloak: sends its own headers, lacks the Permissions-Policy
- "traefik.http.routers.${COMPOSE_PROJECT_NAME}.middlewares=${APP_TRAEFIK_ACCESS}@file,${APP_TRAEFIK_LIMIT}@file,header-permissions@file,${APP_TRAEFIK_HEADERS}@file,${APP_TRAEFIK_AUTH}"
# Paperless-ngx: derives absolute URLs from the forwarded protocol
- "traefik.http.routers.${COMPOSE_PROJECT_NAME}.middlewares=${APP_TRAEFIK_ACCESS}@file,${APP_TRAEFIK_LIMIT}@file,${APP_TRAEFIK_HEADERS}@file,${APP_TRAEFIK_AUTH},forwarded-proto-https@file"
```

CI reports a block on the wrong side (`block-order`). A header the stack
owns — the office servers' `frame-ancestors` CSP, which names the file host
the operator embeds the editor in — stays a Docker middleware of the stack,
placed before the profile like a block:

```yaml
- "traefik.http.routers.${COMPOSE_PROJECT_NAME}.middlewares=${APP_TRAEFIK_ACCESS}@file,${APP_TRAEFIK_LIMIT}@file,header-nosniff@file,${COMPOSE_PROJECT_NAME}-csp@docker,${APP_TRAEFIK_HEADERS}@file,${APP_TRAEFIK_AUTH},forwarded-proto-https@file"
- "traefik.http.middlewares.${COMPOSE_PROJECT_NAME}-csp.headers.contentSecurityPolicy=frame-ancestors 'self' ${COLLABORA_ALLOWED_ORIGINS}"
```

### A stack's own gate

A basicAuth defined in the compose file is the auth position's value, provider-qualified, so the label stays the standard one:

```ini
# .env
APP_TRAEFIK_AUTH=${COMPOSE_PROJECT_NAME}-auth@docker
```

```yaml
- "traefik.http.middlewares.${COMPOSE_PROJECT_NAME}-auth.basicauth.users=${APP_BASIC_AUTH_USERS}"
- "traefik.http.middlewares.${COMPOSE_PROJECT_NAME}-auth.basicauth.realm=Scrutiny"
```

### Multiple routers (e.g. Seafile + Thumbnail)

```yaml
# Main router — catch-all
- "traefik.http.routers.${COMPOSE_PROJECT_NAME}.rule=Host(`${APP_TRAEFIK_HOST}`)"
- "traefik.http.routers.${COMPOSE_PROJECT_NAME}.priority=1"
- "traefik.http.routers.${COMPOSE_PROJECT_NAME}.middlewares=${APP_TRAEFIK_ACCESS}@file,${APP_TRAEFIK_LIMIT}@file,${APP_TRAEFIK_HEADERS}@file,${APP_TRAEFIK_AUTH}"
# Path-scoped router — the four positions again, with its own counter
- "traefik.http.routers.${COMPOSE_PROJECT_NAME}-thumbnail.rule=Host(`${APP_TRAEFIK_HOST}`) && PathPrefix(`/thumbnail`)"
- "traefik.http.routers.${COMPOSE_PROJECT_NAME}-thumbnail.priority=100"
- "traefik.http.routers.${COMPOSE_PROJECT_NAME}-thumbnail.middlewares=${APP_TRAEFIK_ACCESS}@file,${SIDE_TRAEFIK_LIMIT}@file,${APP_TRAEFIK_HEADERS}@file,${APP_TRAEFIK_AUTH}"
```

A middleware attaches to a router, not to a host. A second router is a second
entry point with its own policy, and a path-scoped router runs at a higher
priority than the catch-all it sits in front of, so it decides the request.
**Every router carries the four positions** (CI: `router-positions`). An
operator who sets `access-vpn` means the host, not one path of it, so the
access variable is the stack's on every router; a router whose counter or gate
differs reads a variable of its own:

| Endpoint | The position that differs |
|---|---|
| WebSocket or long-poll — `/socket.io`, a notification stream | `limit-none`: a counter would meter reconnects on a long-lived connection, and none has been measured against one |
| Asset or thumbnail service | its own counter, decided from a measurement — one page view issues many parallel requests |
| An admin path behind the identity provider | `auth-authentik@file` on that router, `auth-none@file` on the rest (`apps/paperless-ngx`) |

Where a router needs a rewrite of its own, it stands after the four, because
access and the gate are decided before the path changes:

```yaml
- "traefik.http.routers.${COMPOSE_PROJECT_NAME}-seadoc.middlewares=${APP_TRAEFIK_ACCESS}@file,${SIDE_TRAEFIK_LIMIT}@file,${APP_TRAEFIK_HEADERS}@file,${APP_TRAEFIK_AUTH},seadoc-strip@docker"
```

### No Traefik

Services without a web UI (dnsmasq, hawser) don't need labels.

### Enabling certresolver

Whether the line stays commented follows from the certificate strategy chosen in
`core/traefik/.env`, not from whether the app is public:

| Strategy (`core/traefik/README.md` → Certificate strategy) | This line |
|---|---|
| Wildcard — `ACME_WILDCARD_DOMAIN` set | stays commented. Traefik serves the wildcard for every subdomain under it |
| Per-domain — DNS-01 or HTTP-01, `ACME_WILDCARD_DOMAIN` unset | **required** on every router that needs a certificate |

```yaml
- "traefik.http.routers.${COMPOSE_PROJECT_NAME}.tls.certresolver=${APP_TRAEFIK_CERT_RESOLVER}"
```

Leaving it commented on the per-domain path does not fail: the router comes up,
HTTPS answers, and Traefik presents its self-signed default certificate
(`CN=TRAEFIK DEFAULT CERT`) without writing anything to its log at `INFO`. The
only symptom is a browser warning. After enabling a router on that path, check
which certificate is actually served — the command is in
[`troubleshooting.md`](troubleshooting.md#certificate-problems), the symptom entry
in [`TROUBLESHOOTING.md`](../../TROUBLESHOOTING.md) §4.5.

A per-host certificate publishes that hostname in public Certificate Transparency
logs (searchable on crt.sh). A wildcard publishes only `*.example.com`; the base
domain is public either way.
