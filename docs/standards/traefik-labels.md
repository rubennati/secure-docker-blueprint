# Traefik Labels

## Standard Pattern

Every service with web access gets this label block:

```yaml
labels:
  # Router
  - "traefik.enable=true"
  - "traefik.docker.network=${TRAEFIK_NETWORK}"
  - "traefik.http.routers.${COMPOSE_PROJECT_NAME}.rule=Host(`${APP_TRAEFIK_HOST}`)"
  - "traefik.http.routers.${COMPOSE_PROJECT_NAME}.entrypoints=websecure"
  # TLS
  - "traefik.http.routers.${COMPOSE_PROJECT_NAME}.tls=true"
  #- "traefik.http.routers.${COMPOSE_PROJECT_NAME}.tls.certresolver=${APP_TRAEFIK_CERT_RESOLVER}"
  - "traefik.http.routers.${COMPOSE_PROJECT_NAME}.tls.options=${APP_TRAEFIK_TLS_OPTION}@file"
  # Middlewares
  - "traefik.http.routers.${COMPOSE_PROJECT_NAME}.middlewares=${APP_TRAEFIK_ACCESS}@file,${APP_TRAEFIK_SECURITY}@file"
  # Service
  - "traefik.http.services.${COMPOSE_PROJECT_NAME}.loadbalancer.server.port=80"
```

- Router and service name = `${COMPOSE_PROJECT_NAME}` (unique per app)
- Network via `${TRAEFIK_NETWORK}` variable (always set explicitly for multi-network setups)
- Port hardcoded per app (not a variable — it's a fixed property of the image)
- `certresolver` commented out by default (avoid leaking subdomains to Certificate Transparency Logs / crt.sh)

## .env Values

| Variable | Possible Values |
|----------|----------------|
| `APP_TRAEFIK_HOST` | `app.example.com` |
| `APP_TRAEFIK_CERT_RESOLVER` | `cloudflare-dns`, `httpResolver` |
| `APP_TRAEFIK_TLS_OPTION` | `tls-basic`, `tls-aplus`, `tls-modern` |
| `APP_TRAEFIK_ACCESS` | `acc-public`, `acc-tailscale` |
| `APP_TRAEFIK_SECURITY` | `sec-0` through `sec-4` |
| `TRAEFIK_NETWORK` | `proxy-public` |

## Security Levels

| Level | Use Case | Headers |
|-------|----------|---------|
| `sec-0` | TLS only, no headers | No HSTS, no CSP |
| `sec-1` | Basic headers | HSTS, X-Content-Type |
| `sec-2` | Standard (recommended) | + X-Frame-Options, Referrer-Policy |
| `sec-3` | Elevated | + Permissions-Policy, CSP |
| `sec-4` | Maximum | + Rate-Limiting, strict CSP |

## Access Policies

| Policy | Access |
|--------|--------|
| `acc-public` | Open (internet) |
| `acc-tailscale` | Tailscale IP ranges only |

## TLS Profiles

| Profile | Min. Version | Compatibility |
|---------|-------------|---------------|
| `tls-basic` | TLS 1.2 | All modern browsers |
| `tls-aplus` | TLS 1.2 | Stricter cipher selection |
| `tls-modern` | TLS 1.3 | Current browsers/clients only |

## Special Cases

### Additional middlewares (e.g. custom headers)

```yaml
- "traefik.http.routers.${COMPOSE_PROJECT_NAME}.middlewares=${COMPOSE_PROJECT_NAME}-headers@docker,${APP_TRAEFIK_ACCESS}@file,${APP_TRAEFIK_SECURITY}@file"
- "traefik.http.middlewares.${COMPOSE_PROJECT_NAME}-headers.headers.customrequestheaders.X-Forwarded-Proto=https"
```

Note: Custom middlewares defined in Docker labels use `@docker` suffix. File-provider middlewares use `@file` suffix.

### Multiple routers (e.g. Seafile + Thumbnail)

```yaml
# Main router
- "traefik.http.routers.${COMPOSE_PROJECT_NAME}.rule=Host(`${APP_TRAEFIK_HOST}`)"
# Additional router with PathPrefix
- "traefik.http.routers.${COMPOSE_PROJECT_NAME}-thumbnail.rule=Host(`${APP_TRAEFIK_HOST}`) && PathPrefix(`/thumbnail`)"
```

### No Traefik

Services without a web UI (dnsmasq, hawser) don't need labels.

### Enabling certresolver

Uncomment the certresolver line when you need public TLS certificates:

```yaml
- "traefik.http.routers.${COMPOSE_PROJECT_NAME}.tls.certresolver=${APP_TRAEFIK_CERT_RESOLVER}"
```

Be aware: This registers the domain in public Certificate Transparency Logs (visible on crt.sh).
