# Compose Structure

Rules and rationale for `docker-compose.yml` files.

For naming patterns, see [Naming Conventions](naming-conventions.md).
For Traefik label structure, see [Traefik Labels](traefik-labels.md).

---

## Block Order per Service

Every service follows this exact block order:

```yaml
services:
  service-name:
    # --- Identity ---
    image:                    # What runs (always via ${VAR})
    container_name:           # Unique name (via ${VAR})
    restart:                  # Restart policy
    depends_on:               # Service dependencies

    # --- Security ---
    security_opt:             # no-new-privileges (mandatory)
    read_only:                # Read-only root filesystem
    tmpfs:                    # Temp dirs when read_only: true
    cap_drop:                 # Drop capabilities
    cap_add:                  # Re-add only what's needed
    user:                     # Non-root user (if image supports it)

    # --- Configuration ---
    entrypoint:               # Custom entrypoint (only for secret injection)
    environment:              # Non-sensitive configuration
    secrets:                  # Sensitive values (passwords, tokens)

    # --- Storage ---
    volumes:                  # Persistent data + config mounts

    # --- Networking ---
    networks:                 # Network membership
    ports:                    # Host ports (only when necessary)

    # --- Traefik ---
    labels:                   # Traefik labels for routing

    # --- Health & Observability ---
    healthcheck:              # Container healthcheck
    logging:                  # Log driver/options (optional)
```

## Why This Order

| Position | Block | Rationale |
|----------|-------|-----------|
| 1 | Identity | Immediately see what the service is and how it starts |
| 2 | Security | Security is not an afterthought — it comes before config |
| 3 | Configuration | What the service receives (env vars, secrets) |
| 4 | Storage | Where data lives |
| 5 | Networking | Which networks the service joins |
| 6 | Traefik | How the service is exposed (routing, TLS, middleware) |
| 7 | Health | Verification — how to check the service works |

## Block Rules

**Identity** (required)
- `image:` — always via `${VAR}`, never hardcoded. Pin to a specific version, never `:latest`.
- `container_name:` — always via `${CONTAINER_NAME_*}` variable.
- `restart: unless-stopped` — standard for all services.
- `depends_on:` with `condition: service_healthy` when the dependency has a healthcheck.

**Security** (required)
- `security_opt: no-new-privileges:true` — mandatory on every service, no exceptions.
- `read_only: true` + `tmpfs:` — use when the image supports it (Redis, Traefik, Whoami, Socket Proxy). Skip when the app writes to the root filesystem (Ghost, WordPress).
- `cap_drop: ALL` — for lightweight services. Re-add only specific capabilities needed.
- `user:` — only when the image explicitly supports non-root operation.

**Configuration** (required)
- `entrypoint:` — only when the image doesn't support `_FILE` env vars. The custom entrypoint reads secrets and exports them as env vars. See [Security Baseline](security-baseline.md) for patterns.
- `environment:` — map format (key: value), not list format (- KEY=value). Never put passwords or tokens here — use secrets.
- `secrets:` — list of secret names the service needs.

**Storage** (required when app has persistent data)
- Always bind mounts (`./volumes/path:/container/path`), never named Docker volumes.
- Config file mounts use `:ro` — e.g. `./config/entrypoint.sh:/config/entrypoint.sh:ro`.
- Standard paths: `./volumes/data/`, `./volumes/mysql/`, `./volumes/postgres/`, `./volumes/redis/`.

**Networking** (required)
- Web apps: `proxy-public` + `app-internal`.
- Databases, Redis, caches: `app-internal` only.
- Never expose database ports on the host.
- `ports:` only for services that need direct host access (rare).

**Traefik** (required for web apps)
- Full label block. See [Traefik Labels](traefik-labels.md) for structure.
- Always include `traefik.docker.network=proxy-public` when the service is in multiple networks.
- Non-web services (databases, socket proxies, workers) have no labels.

**Health & Observability** (strongly recommended)
- Healthcheck on every service where possible.
- Database healthchecks use the image's built-in check (e.g. `healthcheck.sh --connect` for MariaDB/MySQL).
- App healthchecks probe a known endpoint (e.g. `/alive`, `/api/health`).

## Top-Level Blocks

After `services:`, the file contains:

```yaml
# --------------------------------------------------------
# NETWORKS
# --------------------------------------------------------
networks:
  proxy-public:
    external: true

  app-internal:
    name: ${COMPOSE_PROJECT_NAME}-internal
    internal: true

# --------------------------------------------------------
# SECRETS
# --------------------------------------------------------
secrets:
  DB_PWD:
    file: ./secrets/db_pwd.txt
```

Order: `services` > `networks` > `secrets`

## Section Comments

Use consistent separators:

```yaml
  # --------------------------------------------------------
  # SERVICE NAME (uppercase)
  # --------------------------------------------------------
```

Between services, and for top-level blocks (NETWORKS, SECRETS).

## Environment Format

Use **map format**, not list format:

```yaml
# Correct
environment:
  TZ: ${TIMEZONE}
  DB_HOST: database

# Wrong
environment:
  - TZ=${TIMEZONE}
  - DB_HOST=database
```

Exception: Traefik labels always use list format (Compose requirement for labels with dots).

---

## Common Patterns

### App + Database (standard)

Most apps follow this pattern:
- Database service first (no external dependencies)
- App service depends on database with healthcheck
- Database in `app-internal` only
- App in both `proxy-public` and `app-internal`
- Database passwords via Docker Secrets

### App Only (no database)

Services like Whoami, Portainer, or simple web apps:
- Remove `database` service
- Remove `app-internal` network (or keep if the app has other internal services)
- Remove `secrets` block (unless the app has its own secrets)

### App + Socket Proxy

Services like Portainer, Dockhand, Hawser:
- Socket Proxy service with `/var/run/docker.sock:/var/run/docker.sock:ro`
- Socket Proxy in dedicated internal network
- App connects via `DOCKER_HOST: tcp://socket-proxy:2375`
- Never mount docker.sock directly on the app container

### Custom Entrypoint (secret injection)

When the image doesn't support `_FILE` env vars:
- `config/entrypoint.sh` reads secrets from `/run/secrets/` and exports as env vars
- Mount as `./config/entrypoint.sh:/config/entrypoint.sh:ro`
- Set `entrypoint: ["/bin/sh", "/config/entrypoint.sh"]`
- The entrypoint ends with `exec "$@"` to run the original command

### Multi-Service Apps

Complex stacks like Paperless (App + DB + Redis + Gotenberg + Tika) or Seafile:
- Each service follows the same block order
- Services ordered by dependency (dependencies first)
- Optional components via `COMPOSE_FILE` overlay pattern (e.g. `sso.yml`)

---

## Checklist

- [ ] Block order correct (Identity > Security > Configuration > Storage > Networking > Traefik > Health)
- [ ] `security_opt: no-new-privileges:true` on every service
- [ ] Images pinned to specific version (never `:latest`)
- [ ] Image tags via `${VAR}` in compose, actual version in `.env.example`
- [ ] Container names via `${CONTAINER_NAME_*}` variables
- [ ] Environment in map format (not list format)
- [ ] Secrets via Docker Secrets, never in `environment:`
- [ ] Bind mounts only, no named volumes
- [ ] Config mounts with `:ro`
- [ ] Database only in `app-internal` network
- [ ] `traefik.docker.network=proxy-public` label when service has multiple networks
- [ ] Healthcheck on every service where possible
