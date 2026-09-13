# Networking

## Architecture

```text
Internet
   │
   ▼
┌──────────────┐  crowdsec-security (external)  ┌──────────────┐
│   Traefik    │◄──────────────────────────────►│   CrowdSec   │
│  (core/)     │                                │   (core/)    │
└──────────────┘                                └──────────────┘
   │
   │ proxy-public (external)
   ▼
┌──────────┐  app-internal   ┌──────────┐  ┌──────────┐
│   App    │◄───────────────►│    DB    │  │  Redis   │
│  (web)   │  (isolated)     │          │  │          │
└──────────┘                 └──────────┘  └──────────┘
```

## Network Types

### proxy-public

```yaml
networks:
  proxy-public:
    external: true
```

- Created by `core/traefik`
- Referenced by every app that needs Traefik routing
- Only the web-facing service of an app belongs here

**IP family — IPv4-only by default, dual-stack opt-in.** `proxy-public` is
created IPv4-only unless the `core/traefik/network-dual-stack.yml` overlay
is applied. Dual-stack matters specifically for Tailscale ingress:
Tailscale always hands a client an IPv6 address, and that address only
reaches Traefik intact if `proxy-public` itself can carry IPv6 — there is
no header-based fallback the way there is for Cloudflare
(`forwardedHeaders.trustedIPs`). Recommended for new deployments. Full
rationale, Docker daemon prerequisites, and the migration path for
existing IPv4-only installs:
[`core/traefik/docs/ipv6-dual-stack.md`](../../core/traefik/docs/ipv6-dual-stack.md).
`app-internal` networks are unaffected — see below.

### app-internal

```yaml
networks:
  app-internal:
    name: ${COMPOSE_PROJECT_NAME}-internal
    internal: true
```

- One isolated network per app
- `internal: true` = no internet access
- For: DB, Redis, Gotenberg, Tika, Socket Proxy
- Stays IPv4-only regardless of `proxy-public`'s IP family — nothing outside the Docker host ever connects to these directly, so there is no client source IP to preserve

### Core-to-core service network

```yaml
networks:
  crowdsec-security:
    name: ${CROWDSEC_SECURITY_NETWORK}
    driver: bridge
```

Carries one conversation between two core services, with closed membership. It is
not a second `proxy-public`: the members are named in this repository, and an
application stack never joins one.

`crowdsec-security` is the only instance. `core/traefik` declares it; `core/crowdsec`
joins it with `external: true`. Traefik and the CrowdSec engine are the intended
members, and the engine joins no other network — its LAPI (8080), AppSec (7422) and
Prometheus (6060) ports are reachable from the reverse proxy and from no application
container.

- Not `internal: true`. The engine uses this bridge for the outbound access that hub
  updates, the Central API and blocklists need. Making it internal would require a
  separate egress network and would bound nothing further, because membership is
  what bounds reachability here.
- IPv4-only, for the same reason as `app-internal` — nothing outside the Docker host
  connects, so there is no client source IP to preserve.
- Host port publication is a separate mechanism and is unaffected: the engine still
  publishes its LAPI on `127.0.0.1` for the host-installed firewall bouncer.

Add another one when two core services need a private channel and the alternative is
placing one of them on `proxy-public`.

## Which Service in Which Network?

| Service Type | proxy-public | app-internal | crowdsec-security |
|-------------|:---:|:---:|:---:|
| Web app (Traefik routing) | ✅ | ✅ | ❌ |
| Database | ❌ | ✅ | ❌ |
| Redis / Memcached | ❌ | ✅ | ❌ |
| Socket Proxy | ❌ | ✅ | ❌ |
| Worker / Background Jobs | ❌ | ✅ | ❌ |
| Gotenberg / Tika | ❌ | ✅ | ❌ |
| Traefik | ✅ | ❌ | ✅ |
| CrowdSec engine | ❌ | ❌ | ✅ |

## Special Cases

### network_mode: host

```yaml
network_mode: "host"
```

Only for services that must bind directly to the host network stack.
Only example: `core/dnsmasq` (UDP/TCP 53).

No Traefik routing possible, no Docker networking.

Traefik itself is intentionally **not** in this list, including for
IPv6/dual-stack networking — host networking would break the Docker
provider's network-scoped service discovery and bypass every
container-level network isolation control in this blueprint. See "Why
not `network_mode: host`" in
[`core/traefik/docs/ipv6-dual-stack.md`](../../core/traefik/docs/ipv6-dual-stack.md).

### A host firewall and Docker share the forward path

Docker does not route container traffic through the host's input path. Traffic
leaving a container is forwarded, and traffic reaching a published port is
address-translated and then forwarded. A host firewall that adds its own forward
chain with a drop policy therefore cuts container egress, whether or not that was
the intent, and it does so without an error anywhere in Docker.

What breaks first is rarely the application. It is whatever needs to reach the
internet on its own account — a detection engine fetching a community blocklist, a
certificate client answering a challenge, an update check. The container starts,
reports healthy, and fails at the point it needs the network.

The pattern to hold to:

```text
host hardening on the input path
        +
an explicit allowance on the forward path for Docker's own traffic
        =
the host is closed, containers still reach what they are configured to reach
```

Two things decide whether a given ruleset does that. Check both on the host:

- **Which filter is actually in play.** Docker installs its rules through the
  iptables interface. On a system where that interface is backed by nftables,
  Docker's rules and a hand-written nftables ruleset end up in the same engine but
  not in the same place, and a `flush` on one side can remove the other. Establish
  which of the two is managing Docker's rules before adding anything.
- **Where a drop policy sits.** A drop policy on the forward path applies to
  container traffic. A hardening ruleset that is meant to protect the host's own
  services belongs on the input path, where it does not touch forwarding.

Verify by result, not by reading the ruleset: start a throwaway container on a
normal bridge network and have it reach a known external address. If that fails
while the host itself has connectivity, the forward path is the cause.

The one place this repository writes a forward rule is CrowdSec's host
remediation, and it is deliberately narrow — a single drop matched to one ingress
interface and one address set, described in
[`../../core/crowdsec/docs/firewall-bouncer.md`](../../core/crowdsec/docs/firewall-bouncer.md).
Nothing else here adds a forward rule, and nothing here manages a host firewall on
the operator's behalf.

### Exposing Ports

```yaml
ports:
  - "${APP_PORT}:8080"
```

**Avoid.** Only when the service cannot be routed through Traefik:

- dnsmasq (DNS, not HTTP)
- Hawser standard mode (Docker API, not web)

Database ports **never** exposed on host.

### Multiple Web Services

For apps with multiple public endpoints (e.g. Seafile + Thumbnail Server):
Both in `proxy-public`, each with its own Traefik router.
