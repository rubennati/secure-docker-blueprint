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
