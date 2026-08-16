# Security Baseline

## Required for Every Service

```yaml
security_opt:
  - no-new-privileges:true
```

Prevents privilege escalation inside the container. Required on every service.
Exceptions must be documented in `scripts/ci/check-baseline.py` with a full
justification (reason, alternatives considered, risk acceptance) — see
[`docs/standards/ci.md`](ci.md).

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

Every service carries a `memory` and a `pids` limit. An unbounded leak runs until
the kernel OOM-killer fires, and the process it selects is not necessarily the one
that allocated. A fork bomb exhausts the global pid space, after which the host
starts no further process, including a login shell.

A CPU limit bounds neither. Under contention the scheduler distributes cycles, so a
container spinning on the CPU makes the others slow rather than unavailable. `cpus`
is therefore not part of this baseline; `compose-structure.md` states when one is
set.

The values, their derivation and the role table are in
[`compose-structure.md`](compose-structure.md#block-rules), which owns every rule in
this repository that carries a number.

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

Supported by: PostgreSQL, MySQL/MariaDB, Paperless-ngx, Vaultwarden.
Not supported by: OnlyOffice, Seafile, Dockhand (use Pattern 2).

Vaultwarden supports `_FILE` but is not on Pattern 1 today: its password sits
inside `DATABASE_URL`, so the secret has to carry the whole connection string
(`DATABASE_URL_FILE`) or an entrypoint has to assemble it. Support for `_FILE` is
therefore not the same question as whether a stack is already on Pattern 1 — check
the stack's `UPSTREAM.md` for what actually blocks it.

### Pattern 2: Custom entrypoint

When the image doesn't support `_FILE` (Dockhand, Hawser, Vikunja), or when it
does but the value is a connection string the secret would have to carry whole
(Vaultwarden):

```sh
#!/bin/sh
set -e
# POSIX quirk: `export VAR=$(cmd)` masks cmd's exit status — export is a special
# builtin whose own exit code (always 0) is what set -e sees. A failing cat is
# silently ignored and VAR is set to empty. Use intermediate variables instead:
_pwd="$(cat /run/secrets/db_pwd)"   # set -e fires here if cat fails
export DATABASE_PASSWORD="$_pwd"
unset _pwd
exec "$@"
```

**Wrong — set -e does NOT catch a failing cat here:**

```sh
export DATABASE_PASSWORD="$(cat /run/secrets/db_pwd)"  # silent failure!
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
- [ ] `memory` and `pids` limit on every service (`deploy.resources.limits`) — values per [`compose-structure.md`](compose-structure.md#block-rules)
