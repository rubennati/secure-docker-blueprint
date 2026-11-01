# Traefik Reverse Proxy

Security-focused edge gateway for Docker-first servers.
Secure defaults, composable policies, fast incident response.

## Prerequisites

- `docker` + `docker compose`
- `envsubst` (package: `gettext-base` on Debian/Ubuntu)

## Setup

```bash
# 1. Create and edit your environment file
cp .env.example .env
```

Edit `.env` — at minimum change these:

| Variable | What to set |
|----------|-------------|
| `ACME_EMAIL` | Your real email for Let's Encrypt |
| `TRAEFIK_DASHBOARD_HOST` | FQDN for the Traefik dashboard (e.g. `traefik.yourdomain.com`) |
| `CF_DNS_API_TOKEN` | Cloudflare API token (Zone:Read + DNS:Edit) — only needed for DNS-01 |
| `ACME_WILDCARD_DOMAIN` | Uncomment and set if you want a wildcard certificate (optional) |
| `TAILSCALE_CIDR_V4` | Your Tailscale IPv4 CIDR (default: `100.64.0.0/10`) |
| `TAILSCALE_CIDR_V6` | Your Tailscale IPv6 CIDR (default: `fd7a:115c:a1e0::/48`) |
| `TRUSTED_RANGES` | The client networks `access-trusted` admits — your LAN's prefixes; empty admits nobody |
| `EDGE_NETWORKS` | The edge network of every stack you install (`<project>-edge`, each stack's `TRAEFIK_NETWORK`); `COMPOSE_FILE` applies the rendered file — [`docs/edge-networks.md`](docs/edge-networks.md) |

```bash
# 2. Validate environment variables
bash ops/scripts/validate.sh

# 3. Render templates (.tmpl -> config files)
bash ops/scripts/render.sh

# 4. Validate rendered output (checks for unresolved variables)
bash ops/scripts/validate.sh

# 5. Start
docker compose up -d

# 6. Verify
docker compose ps
bash ops/scripts/validate.sh --strict   # published addresses, against the running container
# Dashboard should be reachable at https://<TRAEFIK_DASHBOARD_HOST>
# (only from Tailscale/VPN by default)
```

## Structure

```text
.env.example                          # All configurable variables
docker-compose.yml                    # Docker Socket Proxy + Traefik
network-dual-stack.yml                # Optional overlay: IPv4+IPv6 on proxy-public
config/edge-networks.yml              # Rendered from EDGE_NETWORKS: the edge network of every installed stack (gitignored)
config/published-ports.yml            # Rendered from TRAEFIK_BIND_V4/_V6: the published ports, one block per family (gitignored)
config/host/ingress.nft               # Rendered host firewall for the derived exposure profile — installed by hand (gitignored)
docs/
  edge-networks.md                    # One network per stack (default) or the shared network — the choice, the migration
  host-firewall.md                    # The exposure profile, the rendered host firewall, the exposure test and its marker
  ipv6-dual-stack.md                  # IPv4-only vs. dual-stack — concepts, migration, troubleshooting
  middleware-model-migration.md       # The cut to the middleware model (v0.9.5): every router before and after, the migration, the rollback
ops/
  cloudflare-ips.txt                  # Senders whose forwarded headers the entrypoints trust (Cloudflare's ranges)
  host-files.manifest                 # Files installed outside the checkout (logrotate, watchdog) — docs/standards/host-files.md
  templates/
    traefik.yml.tmpl                  # Static Traefik config
    haproxy.cfg.template.tmpl         # Socket proxy ACL config
    dynamic/
      model.yml.tmpl                  # The middleware model: the four positions, the per-app blocks, compress
      crowdsec.yml.tmpl               # CrowdSec middlewares — rendered by CROWDSEC_BOUNCER_ENABLED
      authentik.yml.tmpl              # Authentik forward-auth — rendered by AUTHENTIK_FORWARD_AUTH_ENABLED
      integrations.yml.tmpl           # Empty; says which switch renders what
      tls-profiles.yml.tmpl           # TLS option profiles
      routers-system.yml.tmpl         # Dashboard router
      redirects.yml.tmpl              # Redirects (empty by default)
      acme-wildcard.yml.tmpl          # Wildcard cert router (optional)
      servers-transports.yml.tmpl     # How Traefik reaches a backend that serves its own TLS
  scripts/
    validate.sh                       # Check .env + rendered config
    render.sh                         # envsubst all .tmpl files -> config/
    reset-templates.sh                # Delete rendered files
config/                               # Generated output (gitignored)
  host/                               # Host files rendered with this checkout's path (scripts/host-files.sh render)
```

Traefik does not substitute `${VARS}` in YAML. All `.tmpl` files are rendered via `envsubst` into `config/`.

Two things in `.env` shape the entrypoints beyond the ports: the three
timeouts (`TRAEFIK_READ_TIMEOUT`, `TRAEFIK_WRITE_TIMEOUT`, `TRAEFIK_IDLE_TIMEOUT`,
shipped at Traefik's own defaults — the file says what each one ends), and the
trusted proxy ranges, which are not in `.env` at all but in
`ops/cloudflare-ips.txt`: one range per line, rendered into
`forwardedHeaders.trustedIPs` on both entrypoints. `validate.sh` refuses a line
that is not a range, CI checks that the file parses, and the `Cloudflare ranges`
workflow compares it with Cloudflare's published lists once a week. After editing
the file: `render.sh`, then `docker compose up -d --force-recreate traefik` — the
entrypoint list is static configuration.

## IPv4-only vs. Dual-Stack Networking

`proxy-public` (the network Traefik and every routed app share) is **IPv4-only by default**, and Traefik is then published on IPv4 only. A port on `[::]` while `proxy-public` cannot carry IPv6 hands every IPv6 connection to Traefik from the Docker gateway — an address inside `172.16.0.0/12`, which the retired LAN policies admitted and CrowdSec's default whitelist skips. IPv6 is therefore published only when `TRAEFIK_BIND_V6` names an address, and `render.sh` refuses that unless `network-dual-stack.yml` adds the IPv6 subnet. The bindings are one variable per family, rendered into `config/published-ports.yml`; an empty variable publishes nothing for its family, so dual-stack, IPv4 only and IPv6 only are three settings of the same two variables, not modes. On an IPv4-only install an IPv6 connection is refused: a Tailscale client, which prefers its IPv6 address, needs IPv4 or dual-stack, and behind Cloudflare the origin needs `A` records — see "Behind Cloudflare", "IPv6 between Cloudflare and the origin". The access policies and rate limits evaluate the connecting address on every path — behind Cloudflare that is the edge address; see [Trusted Proxy Headers](../../docs/standards/traefik-security.md#trusted-proxy-headers-traefikyml--forwardedheaders).

**Recommended for new deployments — dual-stack from day one:**

```bash
# .env: uncomment and set
#   PUBLIC_NETWORK_SUBNET_V4=172.30.0.0/16
#   PUBLIC_NETWORK_SUBNET_V6=<your own ULA prefix>/64
#   COMPOSE_FILE=docker-compose.yml:network-dual-stack.yml:config/published-ports.yml:config/edge-networks.yml
#   TRAEFIK_BIND_V6=[::]          (IPv6 only: also TRAEFIK_BIND_V4= empty)
# Docker daemon prerequisites first — see docs/ipv6-dual-stack.md

bash ops/scripts/render.sh
docker compose up -d

# Verify it actually applied — EnableIPv6 must be true. This command
# only CREATES a dual-stack network; if proxy-public already existed
# (e.g. you're re-running this against a live deployment instead of a
# fresh one), Compose reuses the existing network as-is and does NOT
# error — so always check this rather than assuming the command above
# succeeded silently:
docker network inspect "$(grep ^PUBLIC_NETWORK= .env | cut -d= -f2)" \
  --format 'EnableIPv6={{.EnableIPv6}}'
bash ops/scripts/validate.sh --strict
```

**This command only works for a fresh `proxy-public` that doesn't exist yet.** Migrating an existing IPv4-only install needs a parallel network + tested cutover, not an in-place edit — Docker cannot add IPv6 to a network that already exists without recreating it, and Compose will not warn you if you try. Full explanation (why the public network needs IPv6 but `app-internal` doesn't, why this isn't solved with `network_mode: host`), Docker daemon prerequisites with backup/rollback, the migration guide, and troubleshooting commands: **[`docs/ipv6-dual-stack.md`](docs/ipv6-dual-stack.md)**.

**Setting `COMPOSE_FILE` in `.env` (above) is not optional convenience — set it.** Once the dual-stack network exists, any later `docker compose` command run *without* the overlay (e.g. someone runs `docker compose up -d --force-recreate traefik` and forgets the `-f` flag) makes Compose see only the IPv4-only network definition from `docker-compose.yml`. Compose then tries to remove and recreate the network to match — which fails loudly if other containers are still attached to it (`network proxy-public has active endpoints`, and Traefik ends up stopped until you redo the command correctly), or can silently revert the network to IPv4-only if nothing else happens to be attached. `COMPOSE_FILE` in `.env` means every future command in this directory includes the overlay automatically, with no flag to forget.

### Exposure profile

`validate.sh` derives what the configuration intends to expose — `direct`,
`proxied` or `private` — from the two bindings and `TRAEFIK_FORWARDED_PROXY`,
lists the protection layers present and absent for it, and renders the host
firewall for it into `config/host/ingress.nft`. What the internet reaches is
measured by `scripts/exposure-test.sh` from another machine; `--strict` requires
its marker in `config/exposure-verified` for a public binding
([`docs/host-firewall.md`](docs/host-firewall.md)).

### Published addresses

| Variable | Holds | Default |
|---|---|---|
| `TRAEFIK_HTTP_PORT`, `TRAEFIK_HTTPS_PORT` | the host port, a number only | `80`, `443` |
| `TRAEFIK_BIND_V4` | the IPv4 host address of both ports; empty publishes no IPv4 | `0.0.0.0` (also when unset) |
| `TRAEFIK_BIND_V6` | the IPv6 host address, bracketed; empty publishes no IPv6. Needs `network-dual-stack.yml` | none — empty |

`render.sh` writes the two into `config/published-ports.yml`, one block per family, and `COMPOSE_FILE` applies it — `docker-compose.yml` publishes no port itself. `render.sh` refuses a `COMPOSE_FILE` without that file, an IPv6 binding without the overlay, and the overlay with `TRAEFIK_BIND_V6` unset; `validate.sh` refuses a rendered file that names other bindings than `.env`.

| Shape | `TRAEFIK_BIND_V4` | `TRAEFIK_BIND_V6` | Overlay |
|---|---|---|---|
| IPv4 only (shipped) | `0.0.0.0` | empty | no |
| dual-stack | `0.0.0.0` | `[::]` | `network-dual-stack.yml` |
| IPv6 only — no public IPv4 ingress | empty | `[::]` | `network-dual-stack.yml` |

IPv6 only concerns ingress. The public network still carries IPv4 behind Traefik, and what a host without IPv4 egress needs for its outbound connections is the prerequisite list in the ingress audit (§3.4); that shape is not verified on a host yet.

`validate.sh` refuses `address:port` in a port variable and prints the lines that keep the binding — `TRAEFIK_HTTPS_PORT=0.0.0.0:443` becomes `TRAEFIK_HTTPS_PORT=443` and `TRAEFIK_BIND_V4=0.0.0.0`. It then compares the published address families with the network, the Docker daemon and the running container:

| Result | Meaning | What to do |
|---|---|---|
| `ERROR` | IPv6 published while `proxy-public` has none; the overlay while the daemon keeps `docker-proxy` (`userland-proxy` not `false`), has `ip6tables` off or cannot be read; the overlay while the existing network is IPv4-only | correct `.env`, the daemon or the network — [`docs/ipv6-dual-stack.md`](docs/ipv6-dual-stack.md) |
| `PENDING` | the running container is published differently from the configuration, or `docker-proxy` relays one of its IPv6 ports | `docker compose up -d` recreates Traefik |
| `NOT VERIFIED` | a check could not run — no Docker CLI, Docker refused an inspect — or the running container was created from other compose files than the ones checked | run where Docker answers, with the deployment's compose files |

With no `ERROR` but something pending or not verified, `validate.sh` prints `VALID, SECURITY NOT CONFIRMED` and exits 0, so it does not block the update that resolves it. After `docker compose up -d`, confirm the deployment:

```bash
bash ops/scripts/validate.sh --strict      # fails on anything open; reads COMPOSE_FILE from .env
bash ops/scripts/validate.sh --strict -f docker-compose.yml -f network-dual-stack.yml -f config/published-ports.yml -f config/edge-networks.yml   # files passed by hand
```

A Docker daemon on another host or in a VM cannot be read from here. Confirm `userland-proxy: false` and `ip6tables: true` there, then set `DOCKER_DAEMON_CHECK=manual` in `.env`.

**Which network the ports arrive on.** Docker maps a container's published ports to its address on one network — the one that provides its default gateway. Without a priority Docker takes the first in Compose order, which is `crowdsec-security`, not `proxy-public` (measured 2026-10-31). `docker-compose.yml` therefore gives `proxy-public` `gw_priority: 100`: the ports are DNAT'd to Traefik's address there, where the address family is checked, and a connection from the host itself or from another container reaches Traefik as that network's gateway. `validate.sh` refuses a model in which `proxy-public` does not carry the highest priority, reports a running container created before the pin as `PENDING` until `docker compose up -d` recreates it, and reports `NOT VERIFIED` on a daemon that knows no gateway priority. Needs Docker Engine 28.0 and Compose 2.33.1; `validate.sh` refuses an older Compose by name. From Engine 29.4.1 a single-stack network with a higher priority would take its own family; with the priority on the dual-stack `proxy-public`, both families stay there.

Under dual-stack, `https://[::1]` and IPv6 link-local addresses (`fe80::/10`) do not reach Traefik: with `userland-proxy: false` Docker forwards neither to a container. Check from the host over `127.0.0.1`, from elsewhere over a routed address.

Not exercised on a host: a global IPv6 address reached from the Internet, and Cloudflare connecting to an `AAAA` origin.

## The Middleware Model

Every router carries four middlewares, in this order, each named by a variable
in the stack's `.env`; threat enforcement and compression act on the entrypoint
in front of every router. The definitions are `dynamic/model.yml`
(`ops/templates/dynamic/model.yml.tmpl`); the standard is
[`docs/standards/traefik-security.md`](../../docs/standards/traefik-security.md),
the label pattern [`docs/standards/traefik-labels.md`](../../docs/standards/traefik-labels.md).

**An installation from before v0.9.5 has to migrate** — the model replaced
every middleware name before it, and a router that still carries one answers
nothing (a breaking change; [`CHANGELOG.md`](../../CHANGELOG.md) 0.9.5).
`scripts/migrate-traefik-env.sh` moves the `.env` files;
[`docs/middleware-model-migration.md`](docs/middleware-model-migration.md)
§4 is the order, the checks and the rollback, §3 every router's before and
after.

```yaml
middlewares=${APP_TRAEFIK_ACCESS}@file,${APP_TRAEFIK_LIMIT}@file,${APP_TRAEFIK_HEADERS}@file,${APP_TRAEFIK_AUTH}
```

| Position | Variable | Values | Decided by |
|---|---|---|---|
| 1 access | `APP_TRAEFIK_ACCESS` | `access-public` · `access-trusted` · `access-vpn` · `access-trusted-vpn` · `access-blocked` | the operator |
| 2 limit | `APP_TRAEFIK_LIMIT` | `limit-standard` (125/s, burst 500) · `limit-strict` (20/s, 40) · `limit-sync` (1000/s, 1000) · `limit-extra-large` (125/s, 1000 — closed access only) · `limit-none` | the repository, from a measurement |
| 3 headers | `APP_TRAEFIK_HEADERS` | `headers-standard` · `headers-application-owned` · `headers-none` — every profile starts with the HSTS base | the repository, from a measurement |
| 4 auth | `APP_TRAEFIK_AUTH` | `auth-none@file` · `auth-authentik@file` · `${COMPOSE_PROJECT_NAME}-auth@docker` | the operator |

### Access

| Middleware | Who gets through |
|-----------|-----------------|
| `access-public` | Everyone (no restriction) |
| `access-trusted` | the networks `TRUSTED_RANGES` declares in `.env` — nothing for being private; empty admits nobody |
| `access-vpn` | VPN only — `TAILSCALE_CIDR_V4` + `TAILSCALE_CIDR_V6` from `.env` |
| `access-trusted-vpn` | the declared networks + VPN |
| `access-blocked` | Nobody (emergency kill switch) |

> **Note:** `TRUSTED_RANGES` is quoted and space-separated (`.env` is read by the shell). `validate.sh` refuses a range that is not a network, overlaps the VPN range or overlaps a Docker network of this host; no closed policy admits a container, so a route a container has to reach is `access-public`. `access-lan` and `access-lan-vpn` are retired: `scripts/migrate-traefik-env.sh --all` adds the line to `.env` and renames every stack's value ([`docs/standards/traefik-security.md`](../../docs/standards/traefik-security.md), "Access Policies").

### Headers

| Profile | The proxy sets | For |
|---|---|---|
| `headers-standard` | HSTS base, `nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy` | an application that sends none of these |
| `headers-application-owned` | HSTS base only | an application measured to send its own; the compose file appends the `header-*` blocks it lacks |
| `headers-none` | HSTS base only | debugging a route |

The HSTS base is `max-age=${HSTS_MAX_AGE}` (two years as shipped) on every
router. `includeSubDomains` and `preload` are a decision per host name — the
block `hsts-include-subdomains`, placed before the profile — never a default.

### Per-app blocks

A block corrects one thing for one application and stands on the side of the
four that makes it work: a response header **before** `${APP_TRAEFIK_HEADERS}@file`,
where it overrides the profile (Traefik applies the first middleware's response
changes last), a request header **after** `${APP_TRAEFIK_AUTH}`.

| Block | Side | Used by |
|---|---|---|
| `frame-self` — `X-Frame-Options: SAMEORIGIN`, the application frames its own pages | before | listmonk, Nextcloud |
| `csp-self-only` — an enforcing CSP for an application tested against it | before | whoami |
| `hsts-include-subdomains` — the per-domain HSTS extension | before | no stack by default |
| `header-nosniff`, `header-permissions`, `header-frame-deny`, `header-referrer` — one header an `application-owned` stack lacks | before | Keycloak, Matomo, the office servers |
| `forwarded-proto-https` — `X-Forwarded-Proto: https` to the backend | after | Paperless-ngx, Matomo, the office servers, Ghost's ActivityPub |

### Examples: which values for which app?

| App | Values | Why |
|-----|--------|-----|
| whoami | `access-vpn`, `limit-strict`, `headers-standard` + `csp-self-only` | static page, no external resources — an enforcing CSP holds |
| Traefik dashboard | `access-vpn`, `limit-strict`, `headers-standard`, `auth-none` | administration surface, VPN-only, strict counter (`dynamic/routers-system.yml`) |
| Vaultwarden | `access-vpn`, `limit-standard`, `headers-application-owned` | sends its own `nosniff`, frame header per route, referrer policy, Permissions-Policy and CSP (measured 2026-10-18) |
| Keycloak | `access-vpn`, `limit-standard`, `headers-application-owned` + `header-permissions` | sends everything but the Permissions-Policy; its frame headers vary per page |
| Nextcloud | `access-trusted-vpn`, `limit-sync`, `headers-standard` + `frame-self` | sync clients need the sustained rate; it frames its own pages |
| WordPress, Ghost | `access-public`, `limit-standard`, `headers-standard` | a CMS with inline scripts, the standard set |
| listmonk | `access-public`, `limit-standard`, `headers-standard` + `frame-self` | frames its campaign preview; a different subdomain stays refused |
| Paperless-ngx | `access-vpn`, `limit-standard`, `headers-standard`, then `forwarded-proto-https` | builds absolute URLs from the forwarded protocol; its `/admin` path can take `auth-authentik@file` on a second router |
| Twenty, Windmill | `access-vpn` / `access-blocked`, `limit-extra-large`, `headers-standard` | a first load of 516 and 857 requests (measured); CI accepts the bucket of 1000 behind a closed policy only |

### Threat enforcement and compression

Neither is a router position. `render.sh` places `compress@file` on the
`websecure` entrypoint, in front of every router, with exact
`excludedContentTypes` for binary types; streams are not buffered. CrowdSec is
optional and off as shipped: an installation that enables it
(`CROWDSEC_BOUNCER_ENABLED`; `CROWDSEC_APPSEC_ENABLED` for the inspecting
variant) gets `threat-crowdsec@file` on the same entrypoint — for every router,
with no per-router opt-out, and AppSec for every application at once. The
CrowdSec section below has the switches and what each covers.

## TLS Profiles

| Profile | Min Version | Notes |
|---------|------------|-------|
| `tls-compatible` | TLS 1.2 | older clients must connect |
| `tls-standard` | TLS 1.2 | strict cipher suite, curve preferences — the deployment standard |
| `tls-strict` | TLS 1.3 | TLS 1.3 only |

`TLS_DEFAULT_OPTION` in `.env` names the profile the file provider's reserved
`default` option is built from; every router with `tls=true` takes it, so the
standard label pattern names no option. A stack overrides with
`tls.options=${APP_TRAEFIK_TLS_OPTION}@file` only as a documented exception; the
dashboard names `TRAEFIK_DASHBOARD_TLS_OPTION`. A change of the default takes
effect on a recreate of the container.

## ACME Resolvers

| Resolver | Challenge | Needs reachable | Wildcards | Use case |
|----------|-----------|-----------------|-----------|----------|
| `cloudflare-dns` | DNS-01 | nothing inbound | yes | Wildcard certs, and any host with no public port at all |
| `httpResolver` | HTTP-01 | TCP 80 | no | Standard certs, no Cloudflare account needed |
| `tlsResolver` | TLS-ALPN-01 | TCP 443 | no | One public port for everything — no port 80 forward, no DNS credentials |

All three are defined in the rendered configuration. A resolver that no router
names issues nothing, so defining one costs nothing; the choice is made per
router, through `APP_TRAEFIK_CERT_RESOLVER` (or `TRAEFIK_DASHBOARD_CERT_RESOLVER`).

## Certificate strategy — wildcard vs. per-domain

Two working modes, one of them in two shapes. Pick one for the instance: a
wildcard certificate (Path A), or one certificate per hostname — issued over
DNS-01 or HTTP-01 (Path B), or over TLS-ALPN-01 on port 443 alone (Path C).

### Path A — Wildcard (`*.example.com`)

One certificate covers every subdomain. Requires DNS at Cloudflare — the one DNS-01 provider wired into this stack. Another provider needs its own resolver, credentials and a tested issuance before it counts as supported; HTTP-01 and TLS-ALPN-01 work with any DNS provider.

**Setup:**

1. In `core/traefik/.env` set:

   ```env
   ACME_WILDCARD_DOMAIN=example.com
   CF_DNS_API_TOKEN=<real-token-with-Zone:Read-+-DNS:Edit>
   ```

2. Run `bash ops/scripts/render.sh` (generates `acme-wildcard.yml`)
3. `docker compose up -d`

**Apps:** leave the `tls.certresolver` label commented out in every `docker-compose.yml`. Traefik serves the wildcard for any subdomain via SNI.

**Dashboard:** leave `TRAEFIK_DASHBOARD_CERT_RESOLVER` empty. It follows the same rule as the apps — `render.sh` omits the router's `certResolver` and Traefik serves the wildcard. A resolver set here requests a second certificate and publishes the dashboard hostname in Certificate Transparency logs; `validate.sh` warns when both are set.

`*.example.com` matches exactly one label: `traefik.example.com` is covered, `traefik.admin.example.com` is not. `validate.sh` checks the actual relationship between `TRAEFIK_DASHBOARD_HOST` and `ACME_WILDCARD_DOMAIN`, and refuses a configuration where neither a covering wildcard nor a resolver exists.

### Path B — Per-domain (one cert per subdomain)

Each app requests its own cert. Works with any resolver, no wildcard setup.

**Setup:**

1. In `core/traefik/.env` leave `ACME_WILDCARD_DOMAIN` **unset** (or commented out)
2. Choose resolver per app via `APP_TRAEFIK_CERT_RESOLVER` in that app's `.env`:
   - `cloudflare-dns` for DNS-01 (no port 80 exposure needed)
   - `httpResolver` for HTTP-01 (port 80 must be public)
3. **Uncomment the `tls.certresolver` label** in each app's `docker-compose.yml`:

   ```yaml
   - "traefik.http.routers.${COMPOSE_PROJECT_NAME}.tls.certresolver=${APP_TRAEFIK_CERT_RESOLVER}"
   ```

4. Set `TRAEFIK_DASHBOARD_CERT_RESOLVER` — without a wildcard the dashboard needs its own certificate.

### Path C — Per-domain over port 443 only (TLS-ALPN-01)

The same per-domain shape as Path B, with the challenge answered on 443 instead
of 80. Let's Encrypt opens a TLS connection, asks for the ALPN protocol
`acme-tls/1`, and Traefik serves the challenge certificate on the connection it
is already listening on. Nothing else is forwarded, and no DNS credentials exist
anywhere in the deployment.

This is the path for a firewall that forwards one port:

```text
Internet ──TCP 443──▶ firewall ──TCP 443──▶ this host ──▶ Traefik
                                                            ├── TLS-ALPN-01 → certificate
                                                            └── router → application
```

**Setup:**

1. In `core/traefik/.env` leave `ACME_WILDCARD_DOMAIN` **unset**
2. Per app: `APP_TRAEFIK_CERT_RESOLVER=tlsResolver` in that app's `.env`, and
   uncomment the `tls.certresolver` label in its `docker-compose.yml`
3. `TRAEFIK_DASHBOARD_CERT_RESOLVER=tlsResolver` if the dashboard is published

**Three conditions, and all three are outside this repository:**

- **TCP 443 reachable from the internet.** UDP 443 is HTTP/3 and plays no part in
  the challenge — a firewall that forwards only TCP is enough.
- **Nothing may terminate TLS in front of Traefik.** A CDN or load balancer in
  front answers the handshake itself and does not forward the ALPN protocol;
  issuance then fails with `cannot negotiate ALPN protocol "acme-tls/1"`. This
  rules the path out behind **Cloudflare's proxy (orange cloud)** — which
  `apps/caldiy/docs/cloudflare.md` recommends for that stack. Use DNS-01 there,
  or set the record to DNS-only. HTTP-01 is unaffected by proxy status; this is
  the one resolver that is not.
- **No wildcards.** Let's Encrypt issues those over DNS-01 alone. A deployment
  that wants `*.example.com` needs `cloudflare-dns` no matter which ports are open.

**On a host already running wildcard mode, this resolver will not visibly do
anything for a hostname the wildcard already covers.** Traefik matches an
incoming SNI against every certificate already in its store, independent of
which resolver is named on the router; if the wildcard already covers the
hostname, that match wins and no request ever reaches `tlsResolver`'s ACME
provider. Verified on a live host on 2026-09-15: the resolver loaded without
error and the router carried it correctly, and `acme.json` still held nothing
under `tlsResolver` after the restart, because `*.example.com` already covered
the test hostname. To actually see this resolver issue something, point it at
a hostname the wildcard does not cover.

**Port 80 becomes optional on this path.** Publishing it is still the default,
because the `web` entrypoint redirects HTTP to HTTPS and a visitor who types a
bare hostname lands on `http://`. Dropping the forward at the firewall keeps that
redirect working for anyone already inside; removing the `:80/tcp` port line
from `docker-compose.yml` (and from `network-dual-stack.yml` where it is used) removes it entirely, and those visitors get a connection
refused instead of a redirect.

### Migrating an existing wildcard deployment

Before this rule existed, the dashboard always carried a resolver, so a wildcard
deployment also holds a separate certificate for its dashboard hostname. Emptying
`TRAEFIK_DASHBOARD_CERT_RESOLVER` and re-rendering stops **new** requests for it.
It does not remove the one already stored:

- Traefik loads every certificate in `acme.json` into its certificate store at
  startup, whether or not a router references it, and keeps renewing it based on
  expiry alone. The stored dashboard certificate therefore stays live and keeps
  being served for that hostname.
- Traefik documents no command, API or procedure for retiring a single stored
  certificate, so there is no supported way to remove it selectively.
- Certificate Transparency logs are append-only. A hostname already published
  stays published, whatever happens to the certificate.

The change is therefore forward-looking. A new installation issues no separate
dashboard certificate; an existing one stops requesting further ones. Neither the
stored certificate nor the transparency entry it already produced can be undone by
configuration — changing the dashboard hostname does not retire either, it only
means the new name is served by the wildcard.

### Hybrid

Both modes coexist. A router can request its own cert (uncommented `certresolver` label) even while a wildcard exists for the parent domain.

### Verify after setup

```bash
# Which certificate is actually served for a hostname? This is the check that
# catches a missing resolver: CN=TRAEFIK DEFAULT CERT means nothing matched.
openssl s_client -connect <hostname>:443 -servername <hostname> 2>/dev/null | \
  openssl x509 -noout -subject -issuer -dates
# Wildcard mode, dashboard included: subject=CN=example.com, SAN *.example.com
# Per-domain mode:                   subject=CN=<hostname>

# Which certificates does Traefik hold? Domain metadata only.
docker compose exec traefik cat /etc/traefik/acme/acme.json | \
  jq '.[] | .Certificates[]?.domain // "no certs yet"'

# Dashboard reachable over HTTPS?
curl -I https://<TRAEFIK_DASHBOARD_HOST>

# What do the logs say about ACME / cert issuance?
docker exec traefik-core cat /var/log/traefik/traefik.log | grep -iE "acme|cert|challenge" | tail -20
```

If `acme.json` is empty or the dashboard returns 404 before TLS: check
`docker exec traefik-core cat /var/log/traefik/traefik.log | grep -i error` —
most issues surface as file-provider errors or auth failures against
Cloudflare. Traefik writes to files, not stdout, so `docker compose logs` shows
nothing (see [Logging & Logrotate](#logging--logrotate)).

## CrowdSec Bouncer Plugin (optional)

Blocks malicious IPs and inspects HTTP requests before they reach your apps.
CrowdSec detects threats (brute force, CVE probes, crawling), the bouncer enforces the bans at Traefik level.

### What it provides

| Feature | What it does |
|---------|-------------|
| **IP blocking** | Bans IPs flagged by CrowdSec scenarios (probing, brute force, sensitive files) |
| **Community blocklist** | Shared threat intelligence from the CrowdSec network |
| **AppSec / WAF** | Inspects request bodies for SQL injection, XSS, path traversal |
| **Stream mode** | Polls CrowdSec every 60s, caches decisions locally (no per-request latency) |

### How to enable

One switch in `.env`. The templates are not edited — `render.sh` reads
`CROWDSEC_BOUNCER_ENABLED` and emits the plugin block into `config/traefik.yml`
and the middleware file `config/dynamic/crowdsec.yml`, or neither.

```bash
# -----------------------------------------------
# Step 1: CrowdSec Engine must be running
# -----------------------------------------------
cd /path/to/secure-docker-blueprint/core/crowdsec
docker compose ps   # should show "healthy"

# -----------------------------------------------
# Step 2: Generate a bouncer API key
# -----------------------------------------------
docker exec crowdsec cscli bouncers add traefik-bouncer
# Save the output key — it cannot be retrieved later!

# -----------------------------------------------
# Step 3: Set the switch in Traefik's .env
# -----------------------------------------------
cd /path/to/secure-docker-blueprint/core/traefik
nano .env
#   CROWDSEC_BOUNCER_ENABLED=true
#   CROWDSEC_BOUNCER_PLUGIN_VERSION=v1.7.1      # a release the running Traefik loads
#   CROWDSEC_BOUNCER_KEY=<key-from-step-2>

# -----------------------------------------------
# Step 4: Render, validate, restart
# -----------------------------------------------
./ops/scripts/render.sh
./ops/scripts/validate.sh
docker compose up -d --force-recreate traefik
# The plugin block is static configuration, read at startup — a restart is
# required. validate.sh refuses the switch without a key, a plugin version
# that is not a release tag, and a config/ that does not match the switch.

# -----------------------------------------------
# Step 5: Confirm it is in front of every router
# -----------------------------------------------
# The recreate placed threat-crowdsec@file on the websecure entrypoint, in
# front of every router — the dashboard included. No router is attached by
# hand; an address that must never be refused is a CrowdSec AllowList
# (core/crowdsec, CROWDSEC_ALLOWLIST_ADMIN), never a label. Run the
# whoami-first validation in core/crowdsec/docs/profiles.md: a banned test
# address must be answered 403 on whoami, your own path must still load.
```

What the rendered result looks like, and what each half does:

| Half | File | Rendered when | Takes effect |
|---|---|---|---|
| Plugin declaration (`experimental.plugins.bouncer`) | `config/traefik.yml` | switch on | Traefik restart — static configuration |
| `threat-crowdsec`, `threat-crowdsec-appsec` middlewares | `config/dynamic/crowdsec.yml` | switch on; the file is removed when off | hot reload |
| The entrypoint list (`entryPoints.websecure.http.middlewares`) | `config/traefik.yml` | `threat-crowdsec@file` with the switch on, `threat-crowdsec-appsec@file` when `CROWDSEC_APPSEC_ENABLED` is on as well, `compress@file` always | Traefik recreate — static configuration |

### How to disable

```bash
# The bouncer is on for every router or for none: there is no per-router
# detach. To exempt one address, use a CrowdSec AllowList instead.
# In .env:  CROWDSEC_BOUNCER_ENABLED=false
./ops/scripts/render.sh          # announces the removal and drops config/dynamic/crowdsec.yml
./ops/scripts/validate.sh
docker compose up -d --force-recreate traefik   # AT ONCE — see below
```

**Recreate immediately after the render.** The entrypoint list is static
configuration: until the recreate, the running Traefik keeps naming
`threat-crowdsec@file`, which the render just removed from the dynamic
configuration, and every router on `websecure` is disabled in between.
Switching the bouncer on has no such window. `render.sh` says so when it
removes the integration.

### Migrating an installation that enabled the integration before the switch

Before the switch, the README had the operator uncomment blocks in two tracked
templates and render. Both templates are in git, so the next `git pull` or
checkout put the comments back — and the next `render.sh` then wrote a
`config/` without the plugin and without the middlewares while the running
container still had both. `render.sh` now refuses exactly that state:

```text
ERROR: config/ carries the CrowdSec integration ... but CROWDSEC_BOUNCER_ENABLED is not set in .env.
```

To carry the installation over:

```bash
# 1. Read what config/ currently has — this is what Traefik is running with
grep -nE 'version:' config/traefik.yml                     # the plugin version
grep -nE 'crowdsecLapiKey' config/dynamic/*.yml            # the key in use

# 2. Put both into .env, alongside the switch
#   CROWDSEC_BOUNCER_ENABLED=true
#   CROWDSEC_BOUNCER_PLUGIN_VERSION=<the version from step 1>
#   CROWDSEC_BOUNCER_KEY=<the key from step 1>

# 3. Render into a copy first and diff — the middlewares move from
#    integrations.yml into crowdsec.yml; the plugin block stays where it was
cp -r config /tmp/traefik-config-before
./ops/scripts/render.sh
diff -r /tmp/traefik-config-before config

# 4. If traefik.yml changed only in comments, no restart is needed: the file
#    provider hot-reloads the dynamic directory. If the plugin version changed,
#    restart. validate.sh confirms config/ and .env agree.
./ops/scripts/validate.sh
```

If the templates themselves were edited on that host, `git status` shows them
modified; `git checkout -- ops/templates` restores them. The state now lives in
`.env`, which is not tracked.

### What the two middlewares set

| Setting | `threat-crowdsec` | `threat-crowdsec-appsec` |
|---------|---------|-------------|
| `crowdsecMode` | `stream` | `stream` |
| `crowdsecAppsecEnabled` | `false` | `true` |
| `crowdsecAppsecFailureBlock`, `crowdsecAppsecUnreachableBlock` | `false` | `false` (fail-open) |

`threat-crowdsec` blocks addresses with a decision and inspects nothing; it is
what the bouncer switch places on the entrypoint. `threat-crowdsec-appsec` adds
request inspection and takes its place only when `CROWDSEC_APPSEC_ENABLED=true`
— for every router at once — after the progression in
[`core/crowdsec/docs/appsec.md`](../crowdsec/docs/appsec.md#enabling-appsec-safely).

**The two fail-closed flags are not a default.** If AppSec is unreachable at the
moment Traefik evaluates a request and `crowdsecAppsecUnreachableBlock` is `true`,
every request returns 403 — the Traefik dashboard and every service behind the
proxy included. Both flags belong at the end of the progression documented there,
after AppSec has run long enough for its false-positive rate to be known.

### Geo-blocking

Country-level decisions are made in the CrowdSec engine and enforced by every bouncer
that polls it; nothing is configured in Traefik for them. The procedure, where the GeoIP
enrichment comes from, and the lockout risks:
[`core/crowdsec/docs/geoblocking.md`](../crowdsec/docs/geoblocking.md).

### Verify

```bash
# Check if plugin is loaded (Traefik logs to a file, not stdout)
docker exec traefik-core cat /var/log/traefik/traefik.log | grep -i crowdsec

# Check bouncer connection from CrowdSec side
docker exec crowdsec cscli bouncers list

# Test: ban the address you are testing from, then request the app from it.
# A forged X-Forwarded-For proves nothing: the entrypoint deletes the header
# from any sender outside forwardedHeaders.trustedIPs, and the bouncer compares
# the connecting address. Read your address out of the access log first, and
# keep a second way in — a router without the middleware, or the console.
docker exec crowdsec cscli decisions add --ip <your-address> --duration 3m --reason "test"
sleep 65        # stream mode polls every 60 s
curl -sI https://your-app.example.com/ | head -1
# Expected: HTTP/2 403. Not from the host itself — a request through the
# Docker bridge arrives as the gateway address (core/crowdsec/README.md,
# "Verify reverse-proxy remediation").

# Clean up test ban
docker exec crowdsec cscli decisions delete --ip <your-address>
```

### Troubleshooting

| Problem | Check |
|---------|-------|
| Plugin not loading | `docker exec traefik-core cat /var/log/traefik/traefik.log` — look for plugin errors (Traefik logs to a file, not stdout). Is `CROWDSEC_BOUNCER_ENABLED=true` in `.env`, was `render.sh` run since, and was Traefik recreated afterwards? `grep -n experimental config/traefik.yml` shows whether the block was rendered |
| 403 for legitimate IPs | `docker exec crowdsec cscli decisions list` — check if the IP is banned. Remove with `cscli decisions delete --ip X.X.X.X` |
| WAF blocking valid requests | Set `crowdsecAppsecEnabled: false` temporarily. Check CrowdSec logs for false positives |
| Bouncer not connecting | `docker exec crowdsec cscli bouncers list` — check last heartbeat. Verify both containers are on the `crowdsec-security` network |
| High latency | Verify `crowdsecMode: stream` (not `live`). Stream mode has no per-request overhead |

## Authentik forward-auth (optional)

A login in front of an application that has none of its own: Traefik asks the
Authentik outpost for every request and lets it through only with a session.
The middleware is `auth-authentik`; it exists only while the switch is on, and
a router carries it in its auth position — `APP_TRAEFIK_AUTH=auth-authentik@file`
in the stack's `.env`.

```bash
# core/traefik/.env
AUTHENTIK_FORWARD_AUTH_ENABLED=true
AUTHENTIK_FORWARD_AUTH_ADDRESS=http://authentik-server:9000/outpost.goauthentik.io/auth/traefik

bash ops/scripts/validate.sh && bash ops/scripts/render.sh && bash ops/scripts/validate.sh
```

| | |
|---|---|
| What the switch renders | `config/dynamic/authentik.yml` — dynamic configuration, hot-reloaded, no restart |
| What it does not touch | access policies, limits, headers, the CrowdSec integration — none depends on it |
| Which routers use it | none until a stack's `APP_TRAEFIK_AUTH` names `auth-authentik@file`; which application and how: [`core/authentik/README.md`](../authentik/README.md#integrating-other-apps-via-forward-auth) |
| Outpost unreachable | the request is refused — forward-auth fails closed |
| Switching off | move every `APP_TRAEFIK_AUTH` away from `auth-authentik@file` first; a router naming a middleware that no longer exists is disabled by Traefik. Then `false`, render |
| A `config/` that carries the middleware while `.env` says nothing | `render.sh` refuses, with the two ways out, instead of removing it silently |

## Behind Cloudflare

`TRAEFIK_FORWARDED_PROXY` in `.env` says who may set the client address.
`none`, the default, trusts no sender: every client's `X-Forwarded-*` and
`X-Real-Ip` are deleted at the entrypoint and the connecting address is the
client. `cloudflare` is for a host whose public records Cloudflare proxies
(orange cloud). What changes, hop by hop:

| | `none` | `cloudflare` |
|---|---|---|
| Entrypoints | trust nobody | trust Cloudflare's published ranges — `ops/cloudflare-ips.txt`, compared with cloudflare.com weekly |
| Access log, CrowdSec detection | `ClientHost` = connecting address | `ClientHost` = the whole `X-Forwarded-For` value Cloudflare sent: `client`, or `forged, client` when the client sent a header first, because Cloudflare appends the real one behind it. CrowdSec's Traefik parser takes the last element; anything else that reads the log sees the list |
| CrowdSec bouncer | compares the connecting address — no header reaches it | compares the last `X-Forwarded-For` entry outside the ranges, the client Cloudflare appended. A direct client is compared by its connection, because the entrypoint deleted its header. The plugin keeps its default header: `CF-Connecting-IP` is not used, because the plugin reads whatever header it is given from any sender, and Traefik deletes only `X-Forwarded-*` and `X-Real-Ip` |
| `access-trusted`, `access-vpn`, `access-trusted-vpn` | connecting address | connecting address, unchanged — their clients connect directly; a request to such a host through Cloudflare arrives from an edge address and is refused. Over IPv6 as well; an IPv4-only `proxy-public` accepts no IPv6 connection — "IPv6 between Cloudflare and the origin" below |
| Rate limits (`limit-*`) | per client | **per edge address** at the origin; per client at the edge, through a Cloudflare rate-limiting rule by IP on the public host names (one rule on the Free plan, two on Pro) |
| The application | `X-Forwarded-For` and `X-Real-Ip` = client | from Cloudflare: `X-Forwarded-For` = `client, edge` (two hops), `X-Real-Ip` = edge, `CF-Connecting-IP` = client. From a direct client: `X-Forwarded-For` and `X-Real-Ip` = that client, `CF-Connecting-IP` = whatever it sent |

Traefik's `ipAllowList` and `rateLimit` have no way to read a forwarded address
from Cloudflare and the connecting address from everyone else in one
definition. A strategy that reads the header leaves a direct client with no
address: `ipAllowList` then refuses it, `rateLimit` puts every direct client
into one shared bucket. That is why the closed policies stay on the connecting
address and the per-client limit of a public route moves to the edge. Whether
a shared bucket for direct clients — LAN and VPN only, behind the origin
firewall — would serve better than per-edge buckets for the whole Internet is
a measurement, not settled here (D2 in the core audit).

**What Cloudflare has to be set to**

- Public host names proxied; VPN-only and LAN-only host names DNS-only, or
  resolved by split DNS.
- **Pseudo IPv4: Off.** Its *Overwrite headers* setting replaces
  `CF-Connecting-IP` and `X-Forwarded-For` with a pseudo-IPv4 address for IPv6
  clients; *Add header* adds `Cf-Pseudo-IPv4` and leaves both alone. Off is
  the setting this mode is written for.
- A rate-limiting rule by IP for the public host names, with the budget a
  first load needs (`docs/standards/traefik-security.md`, "Choosing the
  level").
- Origin records: `A` only, or `proxy-public` dual-stack — next paragraph.
- Certificates: DNS-01 or HTTP-01. TLS-ALPN-01 cannot work behind the proxy
  (above, Path C).

**IPv6 between Cloudflare and the origin.** Cloudflare connects to the origin
over IPv6 when only an `AAAA` record exists, and possibly when both exist —
Cloudflare documents a preference for IPv4 there, not a guarantee. On an
IPv4-only `proxy-public` Traefik is published on IPv4 only ("IPv4-only vs.
Dual-Stack Networking" above), and such a connection is refused. So in
`cloudflare` mode one of two must hold: `proxy-public` is dual-stack (the
overlay above), or the origin has `A` records only. Neither shape is verified
with Cloudflare yet.

**Protect the origin.** Without this a client that connects to the host
directly bypasses everything Cloudflare does — the edge rule, Cloudflare's own
protections — and sends `CF-Connecting-IP` to any application that reads it.
The rendered file carries the ranges as nftables defines:

```bash
bash ops/scripts/render.sh                            # writes config/host/cloudflare-ranges.nft
scripts/host-files.sh install-commands core/traefik   # prints the install line for it
```

The rule that uses them goes on the **forward** hook. Traefik's ports are
published by Docker, and a published port is DNAT'd and forwarded, never
delivered to the host: a rule on `input` filters nothing of it and leaves the
origin open while looking closed — measured on a host, in
[`core/crowdsec/docs/firewall-bouncer.md`](../crowdsec/docs/firewall-bouncer.md),
"Why Docker traffic needs FORWARD, not INPUT". One table of its own, loaded
with `nft -f` and never through a ruleset flush (the same document, "Recovery":
Docker and the VPN own live state). Public interface named `eth0` — substitute
the real one; the define file is only visible inside the run that includes it:

```text
# /etc/nftables.d/origin-cloudflare.nft — load: sudo nft -f /etc/nftables.d/origin-cloudflare.nft
include "/etc/nftables.d/cloudflare-ranges.nft"

destroy table inet origin
table inet origin {
  chain public-forward {
    type filter hook forward priority filter - 20; policy accept;
    # Cloudflare's proxy, both families — the container ports after DNAT,
    # whatever TRAEFIK_HTTP_PORT and TRAEFIK_HTTPS_PORT publish
    iifname "eth0" ct original ip  saddr $cloudflare_v4 tcp dport { 80, 443 } accept
    iifname "eth0" ct original ip6 saddr $cloudflare_v6 tcp dport { 80, 443 } accept
    # everything else on the public interface to those ports — including
    # UDP 443, which Cloudflare does not use towards an origin
    iifname "eth0" tcp dport { 80, 443 } drop
    iifname "eth0" udp dport 443 drop
  }
}
```

VPN and LAN clients arrive on other interfaces and are not touched. A LAN that
shares the public interface needs its ranges admitted in the same chain,
before the drop. For boot, an `include` of this file from `/etc/nftables.conf`
is enough — the flush there runs before Docker starts; on a running host never
`systemctl restart nftables`, reload this file. After a change to
`ops/cloudflare-ips.txt`: render, reinstall the define file, `nft -f` this one.
`destroy` needs nftables 1.0.8 or later, as the CrowdSec chains do. The table
parses and loads (checked with `nft -c` and `nft -f` in a container during the
second review); it has not been run on a host.

The table filters the DNAT path, and only that. A connection that
`docker-proxy` relays never takes it: the relay terminates the connection on the
host's **input** path, where the table does nothing, and hands it to Traefik
from the bridge gateway ([`docs/ipv6-dual-stack.md`](docs/ipv6-dual-stack.md),
"The failure mode this prevents"). Traefik's ports are published so that no
external connection takes that path: IPv4 only on an IPv4-only `proxy-public`,
and IPv6 only with the dual-stack overlay, which `validate.sh` accepts only with
`userland-proxy: false` and `ip6tables: true` — both families are then DNAT'd,
and the table covers both ("Published addresses" above).

**What the mode cannot promise.** The trusted ranges are Cloudflare's network,
not this zone. Anything that leaves Cloudflare's edge arrives from them and
passes the firewall above: a Worker, which towards an origin outside its own
zone may set `CF-Connecting-IP` and `x-real-ip` as it likes (Cloudflare's
header reference says so), and another tenant's zone pointed at this origin
address, which carries none of this zone's edge rules — the per-client limit at
the edge is advisory against it. What binds trust to this zone is
Authenticated Origin Pulls (Cloudflare presenting a client certificate, a TLS
option with `clientAuth` on the public routers) or a Tunnel; neither is shipped
here. A sender whose own address lies inside the ranges is compared by the
bouncer as the edge, because the plugin skips every trusted entry, and can
place an entry before it. Cloudflare's own egress space `172.64.0.0/13` is in
the published list; whether a WARP client arrives from inside it Cloudflare
does not document — it states that Zero Trust client egress addresses are not
in the published ranges, and says nothing either way about consumer WARP. A
WARP client outside the ranges is compared as its shared egress address, and a
decision against it hits every client behind that address; both are
host-firewall matters, where the bouncer's allowlist holds
(`core/crowdsec/README.md`, step 5). None of this is a guarantee the mode
gives; it is where the mode ends.

**Per application**

- A stack that reads `X-Real-Ip` for the client — `apps/vaultwarden`'s
  `IP_HEADER` — reads the edge behind Cloudflare; set it to `CF-Connecting-IP`
  there. That header is honest from Cloudflare and unsanitised from a direct
  client, so Vaultwarden's own lockouts count against whatever a LAN or VPN
  client sends; the origin firewall keeps everyone else out.
- A stack that trusts one proxy hop in `X-Forwarded-For` (n8n, HeyForm) needs
  two.
- A stack with a trusted-proxy subnet keeps it: the proxy it sees is still
  Traefik.

**Switching an existing installation.** Before this switch, every rendered
configuration trusted Cloudflare's ranges whether Cloudflare was in front or
not. `render.sh` refuses to render over such a `config/` until `.env` says
`cloudflare` or `none` — an empty value counts as not set — because rendering
`none` over an installation behind Cloudflare would make every layer see edge
addresses, and CrowdSec would ban them. The refusal is keyed on the shape of
the rendered list, comment lines included — every release up to v0.9.4 rendered
`# Cloudflare IPv4` right after the key, and a first version of the guard read
that as "trusts nobody" — so it holds after the ranges file changes and against
a release's file; the test carries that shape, a real host has not. Decide, render,
then `docker compose up -d --force-recreate traefik`: the entrypoint list is
static configuration. `validate.sh` afterwards refuses a rendered list that
differs from the file — the weekly workflow changes the file, the host has to
render again.

**Not verified on a host** — kept open, never marked passed here:

1. The address at every hop through Cloudflare, IPv4 and IPv6: `whoami` behind
   `access-public`, the access log's `ClientHost` (last element), the bouncer's
   compared address (a manual decision answered `403`), Vaultwarden's lockout
   address.
2. A closed route refusing a proxied request over IPv4 and over IPv6, with
   `proxy-public` dual-stack and with it IPv4-only.
3. Forged `CF-Connecting-IP` and `X-Forwarded-For` from a direct client in both
   modes, with the origin firewall in place and absent.
4. A Worker subrequest and a second zone pointing at the origin — what arrives,
   what the bouncer compares, whether `Host` can be made to match a router.
5. The forward-hook table above on a running Docker host: Traefik unreachable
   from a non-Cloudflare address, reachable from the VPN, the CrowdSec tables
   intact after the reload.
6. `scripts/host-files.sh check` and `overview.sh --host` on a `none`-mode
   host.
7. The parser version on the host carries the last-element split
   (`traefik-logs` from the hub).
8. A direct IPv6 client from the Internet, on a host with a global IPv6
   address and the table installed — refused on an IPv4-only `proxy-public`,
   evaluated as its own address after the dual-stack overlay. Both were measured
   without the table, with a client in a network namespace on a test host.
9. The address a WARP client arrives from, inside or outside the published
   ranges, and what the bouncer compares for it.
10. The migration guard on a real pre-switch host: `render.sh` with the switch
    absent over the installed `config/traefik.yml` from a v0.9.x release.

The plan is `docs/host-verification-phase-2.md`'s shape, with a Phase 3
section to follow.

## Incident Quickmoves

An application router takes its middlewares from labels, and the labels read the
application's `.env`. A move is therefore an `.env` change in that stack's
directory, applied with `docker compose up -d` — a changed label recreates the
container, and Traefik picks the router up within seconds. `config/dynamic/*.yml`
is rendered output: an edit made there lasts until the next `render.sh`.

| Move | In the application's `.env` | What happens |
|---|---|---|
| Lock a service to the VPN | `APP_TRAEFIK_ACCESS=access-vpn` | every other source is answered `403`. Which address is evaluated: [Trusted Proxy Headers](../../docs/standards/traefik-security.md#trusted-proxy-headers-traefikyml--forwardedheaders) |
| Take a service off the proxy | `APP_TRAEFIK_ACCESS=access-blocked` | nobody reaches it; the container keeps running |
| Slow a scanner down | `APP_TRAEFIK_LIMIT=limit-strict` | 20 requests per second, burst 40, per client address — a browser loading the interface's assets is answered `429` as well |
| Block one address | `docker exec crowdsec cscli decisions add --ip <address> --duration 24h --reason "incident"` | every router refuses it after the next poll (60 s) while `CROWDSEC_BOUNCER_ENABLED` is on; with the switch off, no router does |
| Change the certificate resolver | `APP_TRAEFIK_CERT_RESOLVER`, with the `certresolver` label uncommented; for the dashboard `TRAEFIK_DASHBOARD_CERT_RESOLVER` in `core/traefik/.env`, then `render.sh` | the next issuance uses the new resolver; a certificate already stored stays |

## Logging & Logrotate

Traefik writes two log files into `volumes/logs/` (bind-mounted from the host):

| File | What it contains |
|------|-----------------|
| `traefik.log` | Startup, config reload, TLS, errors |
| `access.log` | HTTP requests answered with `200-599`, one JSON object per line |

### What the access log contains, and what it costs

`traefik.yml` filters on `statusCodes: 200-599`. That is wider than the error-only
filter it is easy to assume, and it is deliberate — CrowdSec parses this file, and
a scenario about successful activity cannot fire on a log that holds only errors.

What it means in practice:

| | |
|---|---|
| **Included** | every request answered `2xx`, `3xx`, `4xx` and `5xx`. The range is inclusive at both ends, so `300-399` is inside it — a backend's `302` login redirect or a `304` reaches the log like any other response |
| **Excluded** | `1xx` |
| **The global redirect is still missing** | the HTTP-to-HTTPS redirect on the `web` entrypoint writes no access log line at all, so no scenario can match on it. That is not the status filter — widening or narrowing the range does not bring it back |
| **Volume** | one line per successful request rather than per failed one. On a busy host that is orders of magnitude more, which is why logrotate below is not optional |
| **Query strings appear** | the request URI is logged whole. Anything an application accepts as a query parameter — a share token, a search term, an id — lands in this file and in every backup that includes it |
| **Not logged** | request bodies, cookies and `Authorization` headers. Traefik does not record them by default and nothing here turns that on |

Narrowing to `400-599` is a supported choice if the volume or the query strings
matter more than detection breadth. CrowdSec's shipped scenarios are built around
4xx and 5xx patterns — probing, sensitive file access, path traversal, CVE scans —
and keep working either way. What a narrower filter removes is the ability to write
a scenario about authenticated activity, or about a backend's redirect behaviour,
later.

**`docker compose logs traefik` shows nothing — this is expected.** Both files above are configured via `log.filePath` / `accessLog.filePath` in `traefik.yml`, so Traefik writes to files, not stdout. Read the logs directly instead:

```bash
docker exec traefik-core cat /var/log/traefik/traefik.log
docker exec traefik-core cat /var/log/traefik/access.log
# or from the host:
cat volumes/logs/traefik.log
```

`access.log` is buffered (`TRAEFIK_ACCESSLOG_BUFFER`, default 100 entries) — recent requests may not appear until the buffer flushes. `traefik.log` is not affected by this buffer and is the one to check first for startup/ACME/TLS issues.

Docker does **not** rotate bind-mount files. Without logrotate, `access.log` grows unboundedly on busy servers.

### Activate logrotate (one-time, on the host)

The stanza is a host file listed in `ops/host-files.manifest`. Render it with
this checkout's path, then run the printed commands:

```bash
# from the repository root
scripts/host-files.sh render core/traefik
scripts/host-files.sh install-commands core/traefik   # prints the sudo install lines; run them
sudo logrotate -d /etc/logrotate.d/traefik             # dry run: every log must be listed
```

After every blueprint update, `./scripts/overview.sh --host` compares the
installed stanza with the one the checkout now ships and reports `differs` when
they have drifted apart — the earlier shapes of this file (below) are what that
catches. `scripts/host-files.sh diff core/traefik /etc/logrotate.d/traefik`
shows the difference; the rule is [`docs/standards/host-files.md`](../../docs/standards/host-files.md).

The config rotates daily, keeps 7 days and compresses with gzip. Both logs are
copied out and truncated in place (`copytruncate`); no signal is sent to the
container:

| Choice | Why |
|---|---|
| No `docker kill --signal=USR1` | Docker treats any `docker kill`, whatever the signal, as a stop by hand and cancels the restart policy until the next start. After a rotation that sent `USR1`, an OOM kill left Traefik down with every route. Measured on 2026-09-22 (Docker 29.8.1) |
| No rename for `traefik.log` | Traefik 3 announces "Closing and re-opening log files for rotation" on `USR1` and reopens the access log only; the main log descriptor stays on the renamed file. Measured on v3.7.13 on 2026-09-14 |
| `copytruncate` is safe | Traefik opens both files `O_APPEND` and continues at the new end. Lines written between the copy and the truncate are lost |

Earlier shapes of this file each had a failure: until 2026-09-14 one
rename-and-signal stanza for both logs left `traefik.log` empty after the first
rotation (`TROUBLESHOOTING.md` §8.3); until 2026-09-22 the signal for the access
log switched off the restart policy (§8.4). Both sections have the repair.

> **Note:** logrotate runs on the host, not inside the container. This is the correct approach for bind-mounted Docker log files — it is standard practice for any containerized app that writes logs to a host volume.

## Reset

Delete all rendered config files (templates stay untouched):

```bash
bash ops/scripts/reset-templates.sh
```

## Watchdog (optional)

Not installed by default. `ops/scripts/traefik-watchdog.sh` restarts this
container after it has been reported unhealthy for several consecutive
checks in a row, and only once per confirmed episode — see
[`core/host-watchdog/README.md`](../host-watchdog/README.md) for the shared
model, the reasoning, and why this is judged acceptable for Traefik
specifically (it holds no state) and not a general pattern.

Its four files — script, env, service, timer — are host files listed in
`ops/host-files.manifest`: `scripts/host-files.sh render core/traefik`, then
the lines `scripts/host-files.sh install-commands core/traefik` prints, then
edit `/etc/traefik-watchdog.env` and `sudo systemctl enable --now
traefik-watchdog.timer`. They are optional in the manifest, so a host without
the watchdog reports them as `not installed` and nothing else.

## Backup

| | |
|---|---|
| **Database** | None. |
| **State** | `./volumes/letsencrypt` — `acme.json`, holding the ACME account key and every issued certificate |
| **Reproducible** | `./config` — rendered by `ops/scripts/render.sh` from the tracked templates in `ops/templates/` and `.env` · `./volumes/logs` · `./volumes/plugins-storage` — plugins are re-downloaded on start |
| **Quiescing** | Not needed. `acme.json` is rewritten atomically on issuance and renewal. |

No database hook. This stack is `source_directories` only. The static and
dynamic configuration under `config/` is neither backed up nor in git — it is
generated output (`.gitignore`), rendered again from the templates and `.env`.
`.env` is what the render needs and is not in git either: it holds
`CF_DNS_API_TOKEN` and, with the bouncer switched on, `CROWDSEC_BOUNCER_KEY`,
so it has to be in place before a restore
([`docs/standards/restore.md`](../../docs/standards/restore.md), step 3).

**`acme.json` contains private keys.** It is the one file in this repository that
combines "small enough to overlook" with "grants the ability to impersonate every
host it covers". Two consequences for the backup plan:

- The archive containing it deserves the same protection as a secret store. It is
  not merely configuration.
- Its file mode is `600` and Traefik refuses to start if that is widened. A
  restore that flattens permissions produces a proxy that will not come up, which
  during an incident reads as a much larger failure than it is.

Certificates can be reissued, so this is recoverable. But reissuing during an
outage means DNS or HTTP validation has to work while the proxy is down.

**Restore order:** early. Nothing else in the deployment is reachable until the
proxy is up.
