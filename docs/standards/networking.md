# Networking

## Architektur

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
└──────────┘                 └──────────┘  └──��───────┘
```

## Netzwerk-Typen

### proxy-public

```yaml
networks:
  proxy-public:
    external: true
```

- Erstellt von `core/traefik`
- Wird von jeder App referenziert die Traefik-Routing braucht
- Nur der Web-Service einer App hängt hier drin

### app-internal

```yaml
networks:
  app-internal:
    name: ${COMPOSE_PROJECT_NAME}-internal
    internal: true
```

- Pro App ein eigenes internes Netz
- `internal: true` = kein Internet-Zugang
- Für: DB, Redis, Gotenberg, Tika, Socket Proxy

## Welcher Service in welches Netz?

| Service-Typ | proxy-public | app-internal |
|-------------|:---:|:---:|
| Web-App (Traefik-Routing) | ✅ | ✅ |
| Datenbank | ❌ | ✅ |
| Redis / Memcached | ❌ | ✅ |
| Socket Proxy | ❌ | ✅ |
| Worker / Background Jobs | ❌ | ✅ |
| Gotenberg / Tika | ❌ | ✅ |

## Sonderfälle

### network_mode: host

```yaml
network_mode: "host"
```

Nur für Services die direkt am Host-Netzwerk lauschen müssen.
Einziges Beispiel: `core/dnsmasq` (UDP/TCP 53).

Kein Traefik-Routing möglich, kein Docker-Netzwerk.

### Ports exposen

```yaml
ports:
  - "${APP_PORT}:8080"
```

**Vermeiden.** Nur wenn der Service nicht über Traefik geroutet werden kann:
- dnsmasq (DNS, kein HTTP)
- Hawser Standard-Mode (Docker API, kein Web)

Datenbank-Ports **nie** auf Host exposen.

### Mehrere Web-Services

Bei Apps mit mehreren öffentlichen Endpunkten (z.B. Seafile + Thumbnail Server):
Beide in `proxy-public`, jeder mit eigenem Traefik-Router.
