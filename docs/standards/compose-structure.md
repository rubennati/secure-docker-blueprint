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
    image:                    # Image hardcoded, tag via ${VAR}
    container_name:           # Derived from ${COMPOSE_PROJECT_NAME}
    restart:                  # Restart policy
    depends_on:               # Service dependencies

    # --- Security ---
    security_opt:             # no-new-privileges (mandatory)
    read_only:                # Read-only root filesystem
    tmpfs:                    # Temp dirs when read_only: true
    cap_drop:                 # Drop capabilities
    cap_add:                  # Re-add only what's needed
    user:                     # Non-root user (if image supports it)

    # --- Resources ---
    memswap_limit:            # memory + swap ceiling — bounds swap explicitly
    deploy:                   # resources.limits (memory, cpus, pids) + reservations

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
| 3 | Resources | What it may consume — a containment control, so it sits with Security |
| 4 | Configuration | What the service receives (env vars, secrets) |
| 5 | Storage | Where data lives |
| 6 | Networking | Which networks the service joins |
| 7 | Traefik | How the service is exposed (routing, TLS, middleware) |
| 8 | Health | Verification — how to check the service works |

> The canonical, runnable embodiment of this structure is
> [`apps/_reference/`](../../apps/_reference/). Copy it when adding an app.

## Block Rules

**Identity** (required)

- `image:` — Image name hardcoded in compose, only the tag via `${APP_TAG}`. Image name + Docker Hub link as comment in `.env.example`.
- `build:` — only where the stack builds its own image, and then directly above `image:`, which names the resulting artifact. `business/vikunja` is the one instance. Most stacks pull a published image and have no `build:` block; having one is not a requirement, and what it implies is [`custom-application.md`](custom-application.md).
- `container_name:` — Derived from `${COMPOSE_PROJECT_NAME}` via `${CONTAINER_NAME_APP}`, `${CONTAINER_NAME_DB}`, etc.
- `restart: unless-stopped` — standard for all services.
- `depends_on:` with `condition: service_healthy` when the dependency has a healthcheck.

**Security** (required)

- `security_opt: no-new-privileges:true` — mandatory on every service, no exceptions.
- `read_only: true` + `tmpfs:` — use when the image supports it (Redis, Traefik, Whoami, Socket Proxy, nginx). Skip when the app writes to the root filesystem (Ghost, WordPress).
- `cap_drop: ALL` — for lightweight services. Re-add only specific capabilities needed.
- `user:` — only when the image explicitly supports non-root operation.

**Resources** (required)

A memory limit is a blast radius, not an allocation. It exists so a leak in one
container cannot take the host down with it — and it must sit far enough above
the working set that ordinary work never reaches it. A container killed mid-import
looks like an application fault, and that is a worse failure than the one the
limit was set to prevent.

Derive it, in this order:

1. **From the component's own configured budget**, where it has one. MariaDB with
   `--innodb-buffer-pool-size=1G` needs room for that plus connections, sort
   buffers and temporary tables — `2G`. Redis with `maxmemory 512mb` needs it
   plus allocator overhead — `768M`.
2. **From a measured peak**, where it does not. Measure under the workload that
   costs most, not at idle. Invoice Ninja idles near 500 MB and reaches 641 MB
   rendering a PDF; a limit derived from idle would kill the renderer.
3. **Never from upstream's stated minimum.** Those size a machine, not a
   container: "512 MB per PHP process" and "1 GB RAM, 2 GB recommended" describe
   the whole deployment. They belong in a README's requirements section.

Then leave roughly half again on top.

`pids` bounds a fork bomb and costs nothing to set. **CPU limits are not applied by
default** — they make a stack slow under load rather than safe,
and a busy container is not the failure mode this is guarding against.

### Swap has to be bounded on purpose

A memory limit alone does not bound what a container can take from the host.
`memory` caps resident memory; swap is a separate allowance, and Docker grants one
implicitly. With `memory` set and `memswap_limit` unset, the container may use **the
memory limit again in swap** — a 4G service becomes 4G RAM plus 4G swap. Verified
against the running daemon: unset renders `MemorySwap` at twice `Memory`.

That is the failure a memory limit does not catch. A container inside its cap, paging
steadily against a small host swap area, degrades the whole machine without ever being
killed — the container OOM-killer fires only once memory *and* the swap allowance are
exhausted. Several such containers need no bug to make a host unusable.

**Every service with a memory limit states its swap policy.** The mechanism is fixed;
the value is not:

| `memswap_limit` | Effect | Use when |
|---|---|---|
| equal to `memory` | no swap; the container reaches its cap and is OOM-killed cleanly | the default choice — failure stays inside the container |
| greater than `memory` | a bounded, deliberate amount of swap on top | a workload with a known transient peak that is cheaper to page than to kill |
| unset | implicit: as much swap again as `memory` | not acceptable — the amount is accidental rather than chosen |

`memswap_limit` sits beside `deploy:` in the Resources block. Unlike `pids_limit` it
does not conflict with a `deploy:` block.

```yaml
memswap_limit: 512m          # == memory: no swap
deploy:
  resources:
    limits:
      memory: 512m
```

A value above `memory` carries its justification the way a `cpus` value does — upstream
requirement, measured peak, or repository evidence. Where none exists yet, say so:

```yaml
# memswap_limit: estimated / requires validation — v0.10.0
memswap_limit: 6g
deploy:
  resources:
    limits:
      memory: 4g
```

**A swap policy is not a memory budget.** Lowering `memory` to reserve host memory is
the wrong move: the ceiling is a blast radius, and a workload that reaches it during
ordinary work was capped too low.

A `cpus` value stands in two cases: where a component demonstrably pins a core, and
where a derived starting value is carried until v0.10.0 measures it. The second case
is declared beside the value in the compose file, so a reader can tell a measurement
from a derivation:

```yaml
# cpus: derived starting value, not measured — v0.10.0
cpus: "1.00"
```

A value carrying neither justification is removed rather than kept.

| Role | Typical limit | Basis |
|---|---|---|
| Web server | `128M` | measured single-digit MB, generous ceiling |
| Cache | configured `maxmemory` + ~50% | its own budget |
| Database | configured buffer pool + ~100% | its own budget plus connections |
| Application | measured peak + ~50% | workers × measured RSS, or the renderer's peak |

Put `pids` inside `deploy.resources.limits` — a top-level `pids_limit` alongside
`deploy.resources` is rejected by Compose. Use `deploy:` rather than the top-level
`mem_limit`, which is deprecated and does not apply in Swarm mode.

`memory`, `pids` and `memswap_limit` are required on every service. `cpus` is the
exception, set only where a component demonstrably pins a core;
[`security-baseline.md`](security-baseline.md#resource-limits) states which host
failure each of them bounds.

### What is written here is not what is running

These values describe the repository. They say nothing about a running host until a
container is **recreated** — `docker compose up -d` after the file changed. Restarting
a container reuses its existing `HostConfig`, so a restart applies no new limit, and
neither does a Docker daemon restart. A limit in git and a limit in the kernel are two
different facts, and only the second one contains anything.

Confirming the second is a separate procedure, in
[`../resource-measurement.md`](../resource-measurement.md).

**Configuration** (required)

- `entrypoint:` — only when the image doesn't support `_FILE` env vars. The custom entrypoint reads secrets and exports them as env vars. See [Security Baseline](security-baseline.md) for patterns.
- `environment:` — explicit map format (key: value). Never use `env_file:`. Never put passwords or tokens here — use secrets.
- `secrets:` — list of secret names the service needs.

**Storage** (required when app has persistent data)

- Config file mounts use `:ro` — e.g. `./config/entrypoint.sh:/config/entrypoint.sh:ro`.
- Volume style (bind mounts vs named volumes) is decided per app. See individual app documentation.

**Networking** (required)

- Web apps: `proxy-public` + `app-internal`.
- Databases, Redis, caches: `app-internal` only.
- Never expose database ports on the host.
- `ports:` only for services that need direct host access (rare).

**Traefik** (required for web apps)

- Full label block. See [Traefik Labels](traefik-labels.md) for structure.
- Always include `traefik.docker.network=${TRAEFIK_NETWORK}` when the service is in multiple networks.
- Non-web services (databases, socket proxies, workers) have no labels.

**Health & Observability** (strongly recommended)

A healthcheck sets a status. **Nothing acts on it by itself** — Docker will not
restart or report an unhealthy container. Three things read it, and only the
second has an effect at runtime:

| Reader | Effect |
|---|---|
| `depends_on: condition: service_healthy` | start ordering |
| **Traefik** | drops an unhealthy container from the load balancer — the proxy then answers 404 |
| `docker compose ps`, a monitoring stack | visibility, if anyone is looking |

That second row is why a *wrong* healthcheck is worse than none: a check that
fails on a redirect takes the service out of rotation, and the symptom looks
like a routing fault.

So verify the command against the running image before committing it. Check what
the image actually contains — `docker run --rm --entrypoint sh <image> -c 'command -v curl wget'`
— and prefer an endpoint that proves the path end to end. Nextcloud's
`/status.php` returns `{"installed":true,…}`, which exercises nginx, FastCGI and
the application in one request; `nginx -t` would only have parsed a config file.

Some services legitimately have none, and the compose file says which:

```yaml
    # healthcheck: inherited from the image, which declares its own.
    # healthcheck: none — the image is FROM scratch and has no shell.
```

`check-structure.py` accepts either marker and warns on anything else, so the
exemption cannot be used to wave a service through without stating why.

**`healthcheck: {disable: true}` is not a way to declare you have none.** The key
suppresses a `HEALTHCHECK` baked into the image — it never defines one, so a
service using it is a service without a healthcheck and needs the same written
marker. Four services carried it with a reason in prose and none was reported,
because the dict is truthy and the rule tested `if not hc`. Use it only where the
image really does declare a check that has to be turned off, and say so:

```yaml
    # healthcheck: none — upstream removed the built-in check in 2025.10.2. The
    # image still declares one, so it is disabled explicitly.
    healthcheck:
      disable: true
```

## Service Names

Use short, generic names:

| Service | Name |
|---------|------|
| Application | `app` |
| Database | `db` |
| Cache/Queue | `redis` |
| Web server | `nginx` |
| Socket proxy | `socket-proxy` |

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

# --------------------------------------------------------
# SECRETS
# --------------------------------------------------------
secrets:
  DB_PWD:
    file: ./.secrets/db_pwd.txt
```

Order: `services` > `volumes` (if needed) > `networks` > `secrets`

### Two properties of file-based secrets that surprise people

**`uid`, `gid` and `mode` on a secret reference do nothing.** Compose accepts
them and ignores them outside Swarm. What appears inside the container is the
host file's ownership and mode. So when a process reads a secret as a non-root
user — anything the application does at request time, rather than an entrypoint
running as root — the access has to be granted on the host:

```bash
sudo chown "$USER":<container-gid> .secrets/foo.txt
chmod 640 .secrets/foo.txt
```

Grant it through the group, not by handing the file to the container's user, or
the operator can no longer edit the file they just created.

**Rotating a secret needs `--force-recreate`, not `restart`.** Each secret is
bind-mounted as a single file, resolved once when the container starts. Most
editors save by writing a temporary file and renaming it over the target, which
replaces the file — the mount stays attached to the one that was replaced, and
the container keeps serving the old value:

```bash
docker compose up -d --force-recreate <service>
```

Writing in place (`printf '%s' "$NEW" > .secrets/foo.txt`) keeps the same file
and avoids this. Neither case changes the container's health status, so a stack
can report healthy while authenticating with a secret that no longer exists on
disk.

## Section Comments

Use consistent separators:

```yaml
  # --------------------------------------------------------
  # SERVICE NAME (uppercase)
  # --------------------------------------------------------
```

Between services, and for top-level blocks (VOLUMES, NETWORKS, SECRETS).

---

## Common Patterns

### App + Database (standard)

Most apps follow this pattern:

- `db` service first (no external dependencies)
- `app` service depends on db with healthcheck
- `db` in `app-internal` only
- `app` in both `proxy-public` and `app-internal`
- Database passwords via Docker Secrets

### App Only (no database)

Services like Whoami, Portainer, or simple web apps:

- Remove `db` service
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
- Set `entrypoint: ["/bin/sh", "/config/entrypoint.sh", "<original-entrypoint>"]`
- The entrypoint ends with `exec "$@"` to run the original command

### Multi-Service Apps

Complex stacks like Paperless (App + DB + Redis + Gotenberg + Tika) or Seafile:

- Each service follows the same block order
- Services ordered by dependency (dependencies first)
- Optional components via `COMPOSE_FILE` overlay pattern (e.g. `sso.yml`)

---

## Local test stack

A stack may carry `docker-compose.local.yml` beside the production file, for
running it on one machine without a proxy, DNS or certificate.
`apps/_reference/docker-compose.local.yml` is the form.

| | |
|---|---|
| Ports | published on `127.0.0.1` only |
| Credentials | plain values from `.env.local`, covered by the root `.gitignore` |
| Network | one, named `<stack>-local`, not `internal` |
| Container names | `<stack>-local-<service>` |
| Volumes | `./volumes/local/<name>` |
| Hardening, healthchecks | as in the production file |
| Resource limits | out of scope — `apps/_reference/docker-compose.local.yml` carries none |
| Absent | Traefik labels, `proxy-public`, `secrets:`, `/run/secrets`, secret `*_FILE` variables |

**The production resource baseline — `memory`, `pids`, `memswap_limit` — does not
extend to the local file.** A local stack binds to `127.0.0.1`, runs alone rather
than beside unrelated stacks on a shared host, and exists to be tried, not
operated; the blast-radius problem those three controls solve does not arise the
same way. This is a scope boundary, not a gap to close — it does not need its own
resource policy, only the explicit statement that the production one stops here.

Its companion `.env.local.example` carries only the variables the local file
uses, with `__REPLACE_ME__` for anything secret and the generating command above
it.

The header is the app name and the commands, and nothing else:

```yaml
# BookStack — local
#
#   cp .env.local.example .env.local
#   mkdir -p volumes/local/config volumes/local/mysql
#   sudo chown -R 1000:1000 volumes/local/config
#   docker compose -f docker-compose.local.yml --env-file .env.local up -d
#   http://localhost:8080 — first login admin@admin.com / password
#   docker compose -f docker-compose.local.yml --env-file .env.local down
```

No statement of what the file is for, no comparison with the production file, no
justification for a setting. A comment belongs in the file only when removing it
stops someone running the stack.

A stack that shows nothing when run alone gets none: a reverse proxy, an agent
reporting to a central instance elsewhere, something that needs host networking,
or a client for another stack's data. `LIFECYCLE.md` lists which stacks have the
file.

For split-compose stacks the file is excluded from the production set by
`scripts/ci/check-structure.py`, which otherwise counts every `*.yml` in the
directory.

---

## Checklist

- [ ] Block order correct (Identity > Security > Configuration > Storage > Networking > Traefik > Health)
- [ ] `security_opt: no-new-privileges:true` on every service
- [ ] Images pinned to specific version (never `:latest`)
- [ ] Image name hardcoded in compose, only tag via `${APP_TAG}` / `${DB_TAG}`
- [ ] Container names derived from `${COMPOSE_PROJECT_NAME}`
- [ ] Explicit `environment:` blocks (no `env_file:`)
- [ ] Secrets via Docker Secrets in `.secrets/`, never in `environment:`
- [ ] Config mounts with `:ro`
- [ ] Database only in `app-internal` network
- [ ] `traefik.docker.network=${TRAEFIK_NETWORK}` label when service has multiple networks
- [ ] Healthcheck on every service where possible (app-specific, no forced standard)
- [ ] Service names: `app`, `db`, `redis`, `nginx`
- [ ] `docker-compose.local.yml`, where the stack shows something run alone
