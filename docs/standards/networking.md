# Networking

## Architecture

```
Internet
   │
   ▼
┌──────────────┐
│   Traefik    │  proxy-public (external)
│  (core/)     │──────────────────────────────┐
└──────────────┘                              │
   │                                          │
   ▼                                          ▼
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

## Which Service in Which Network?

| Service Type | proxy-public | app-internal |
|-------------|:---:|:---:|
| Web app (Traefik routing) | ✅ | ✅ |
| Database | ❌ | ✅ |
| Redis / Memcached | ❌ | ✅ |
| Socket Proxy | ❌ | ✅ |
| Worker / Background Jobs | ❌ | ✅ |
| Gotenberg / Tika | ❌ | ✅ |

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
