# Security Baseline

## Required for Every Service

```yaml
security_opt:
  - no-new-privileges:true
```

No exceptions. Prevents privilege escalation inside the container.

## Recommended

### Read-only Root Filesystem

```yaml
read_only: true
tmpfs:
  - /tmp
  - /run
```

Use when the image supports it. Examples: Redis, Whoami, Socket Proxy.
Skip for images that write to the root filesystem (Ghost, Paperless).

### Capability Drop

```yaml
cap_drop:
  - ALL
cap_add:
  - NET_BIND_SERVICE    # Only if binding to port < 1024
```

Ideal for lightweight services (Whoami, dnsmasq).

### Non-root User

```yaml
user: "${USERMAP_UID}:${USERMAP_GID}"
```

Only set when the image supports it. Don't guess — check the image documentation.

**⚠ Never use `user:` with s6-overlay or supervisord images.** These init
systems must start as root to set up `/run`, fix permissions, and then drop
privileges internally. Images like Paperless-ngx and Linuxserver.io containers
provide `USERMAP_UID`/`USERMAP_GID` or `PUID`/`PGID` environment variables
instead.

### Resource Limits

```yaml
# Baseline — calibrate per service profile (see table below)
deploy:
  resources:
    limits:
      memory: 512M
      cpus: "0.50"
      pids: 100
    reservations:
      memory: 128M
```

Prevents a crashed or compromised container from starving the host kernel.
`deploy.resources` caps memory and CPU so a single container cannot exhaust
the host under load or during a memory leak. `pids` blocks fork-bomb
escalation inside the container.

Note: `pids_limit` is the legacy top-level key — Docker Compose v2 maps it
to `deploy.resources.limits.pids` internally and errors if both are set.
Always use `deploy.resources.limits.pids` when a `deploy:` block is present.

**Calibration by service profile:**

| Profile | Example services | `memory` limit | `cpus` | `pids` |
|---|---|---|---|---|
| Lightweight helper | Whoami, Socket Proxy, init containers | `128M` | `0.25` | `50` |
| Cache / queue | Redis, Valkey | `256M` | `0.25` | `50` |
| Standard web app | Ghost, Vaultwarden, Dockhand | `512M` | `0.50` | `100` |
| Database | PostgreSQL, MariaDB | `1G` | `1.00` | `200` |
| Heavy app | Nextcloud, Paperless-ngx | `2G` | `2.00` | `500` |
| One-shot / migration | init-perms, DB migration runners | omit — let it finish | — | — |

> **`deploy.resources` vs. `mem_limit`**: Always use `deploy:` — it is the
> Compose v3 standard and works with both standalone `docker compose` and
> Swarm mode. The legacy top-level `mem_limit` key is deprecated.

## Secrets

### Rule

Passwords, tokens, and API keys **never** in `environment:` — always via Docker Secrets.

### Pattern 1: Image supports `_FILE`

```yaml
environment:
  POSTGRES_PASSWORD_FILE: /run/secrets/DB_PWD
secrets:
  - DB_PWD

secrets:
  DB_PWD:
    file: ./.secrets/db_pwd.txt
```

Supported by: PostgreSQL, MySQL/MariaDB, Paperless-ngx.
Not supported by: OnlyOffice, Seafile, Vaultwarden, Dockhand (use Pattern 2).

### Pattern 2: Custom entrypoint

When the image doesn't support `_FILE` (Vaultwarden, Dockhand, Hawser):

```sh
#!/bin/sh
set -e
export DATABASE_URL="postgres://${DB_USER}:$(cat /run/secrets/DB_PWD)@db:5432/${DB_NAME}"
exec "$@"
```

```yaml
entrypoint: ["/bin/sh", "/config/entrypoint.sh"]
volumes:
  - ./config/entrypoint.sh:/config/entrypoint.sh:ro
```

### Pattern 3: No secret possible

When the value is embedded in a JSON string (e.g. Paperless SSO `PAPERLESS_SOCIALACCOUNT_PROVIDERS`):
Keep as env var in `.env` — it's gitignored, so acceptable.

## Docker Socket

### Never mount directly on the app container

```yaml
# WRONG
volumes:
  - /var/run/docker.sock:/var/run/docker.sock
```

### Always use a Socket Proxy

```yaml
# CORRECT
socket-proxy:
  image: tecnativa/docker-socket-proxy:v0.4.2
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock:ro
  environment:
    CONTAINERS: "1"    # Only what the app needs
    POST: "0"          # Write access only when required

app:
  environment:
    DOCKER_HOST: tcp://socket-proxy:2375
```

Exception: Hawser — needs direct socket access as its core function. Socket proxy is the target pattern but requires upstream TCP support (tracked in Hawser issue tracker). Until then, the direct mount is an accepted, documented deviation.

## Network Isolation

- Databases, Redis, internal services: **only** in `app-internal` network
- Web apps: `proxy-public` + `app-internal`
- Database ports **never** exposed on host

## Checklist

- [ ] `no-new-privileges:true` on every service
- [ ] `read_only: true` where possible
- [ ] Secrets via `secrets:` block, never in `environment:`
- [ ] Secret files generated without trailing newlines (`| tr -d '\n'`)
- [ ] Docker socket only through socket proxy
- [ ] Config mounts with `:ro`
- [ ] Database only in internal network
- [ ] Images pinned (never `:latest`)
- [ ] `./.secrets/` and `./volumes/` in `.gitignore`
- [ ] Resource limits set per service profile (`deploy.resources`) — optional, discuss per app
