# Traefik Labels

## Standard-Pattern

Jeder Service mit Web-Zugang bekommt diesen Label-Block:

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.${COMPOSE_PROJECT_NAME}.rule=Host(`${APP_TRAEFIK_HOST}`)"
  - "traefik.http.routers.${COMPOSE_PROJECT_NAME}.entrypoints=websecure"
  - "traefik.http.routers.${COMPOSE_PROJECT_NAME}.tls=true"
  - "traefik.http.routers.${COMPOSE_PROJECT_NAME}.tls.certresolver=${APP_TRAEFIK_CERT_RESOLVER}"
  - "traefik.http.routers.${COMPOSE_PROJECT_NAME}.tls.options=${APP_TRAEFIK_TLS_OPTION}"
  - "traefik.http.routers.${COMPOSE_PROJECT_NAME}.middlewares=${APP_TRAEFIK_ACCESS}@file,${APP_TRAEFIK_SECURITY}@file"
  - "traefik.http.services.${COMPOSE_PROJECT_NAME}.loadbalancer.server.port=${APP_INTERNAL_PORT}"
  - "traefik.docker.network=proxy-public"
```

- Router-Name = `${COMPOSE_PROJECT_NAME}` (eindeutig pro App)
- `traefik.docker.network` immer explizit setzen (Multi-Network)

## .env Werte

| Variable | Mögliche Werte |
|----------|----------------|
| `APP_TRAEFIK_HOST` | `app.example.com` |
| `APP_TRAEFIK_CERT_RESOLVER` | `cloudflare-dns`, `httpResolver` |
| `APP_TRAEFIK_TLS_OPTION` | `tls-basic`, `tls-aplus`, `tls-modern` |
| `APP_TRAEFIK_ACCESS` | `acc-public`, `acc-tailscale` |
| `APP_TRAEFIK_SECURITY` | `sec-0` bis `sec-4` |
| `APP_INTERNAL_PORT` | `80`, `8080`, `3000`, ... |

## Security-Stufen

| Level | Einsatz | Headers |
|-------|---------|---------|
| `sec-0` | Nur TLS, keine Header | Kein HSTS, kein CSP |
| `sec-1` | Basis-Headers | HSTS, X-Content-Type |
| `sec-2` | Standard (empfohlen) | + X-Frame-Options, Referrer-Policy |
| `sec-3` | Erhöht | + Permissions-Policy, CSP |
| `sec-4` | Maximum | + Rate-Limiting, strenge CSP |

## Access Policies

| Policy | Zugriff |
|--------|---------|
| `acc-public` | Offen (Internet) |
| `acc-tailscale` | Nur Tailscale IP-Ranges |

## TLS-Profile

| Profil | Min. Version | Kompatibilität |
|--------|-------------|----------------|
| `tls-basic` | TLS 1.2 | Alle modernen Browser |
| `tls-aplus` | TLS 1.2 | Strengere Cipher-Auswahl |
| `tls-modern` | TLS 1.3 | Nur aktuelle Browser/Clients |

## Sonderfälle

### Zusätzliche Middlewares (z.B. Custom Headers)

```yaml
- "traefik.http.routers.${COMPOSE_PROJECT_NAME}.middlewares=${COMPOSE_PROJECT_NAME}-headers,${APP_TRAEFIK_ACCESS}@file,${APP_TRAEFIK_SECURITY}@file"
- "traefik.http.middlewares.${COMPOSE_PROJECT_NAME}-headers.headers.customrequestheaders.X-Forwarded-Proto=https"
```

### Mehrere Router (z.B. Seafile + Thumbnail)

```yaml
# Haupt-Router
- "traefik.http.routers.${COMPOSE_PROJECT_NAME}.rule=Host(`${APP_TRAEFIK_HOST}`)"
# Zusätzlicher Router mit PathPrefix
- "traefik.http.routers.${COMPOSE_PROJECT_NAME}-thumbnail.rule=Host(`${APP_TRAEFIK_HOST}`) && PathPrefix(`/thumbnail`)"
```

### Kein Traefik

Services ohne Web-UI (dnsmasq, hawser) brauchen keine Labels.
