# Dockhand

Docker management UI with Git-based stack management. Deploy and update Compose stacks by pushing to Git — Dockhand watches the repo and applies changes.

Works best for homelab / small-team setups where stacks are version-controlled in a Git repository instead of configured through a web UI.

## Architecture

Three services:

| Service | Image | Purpose |
|---------|-------|---------|
| `app` | `fnsys/dockhand` | Dockhand web UI + Git poller + Compose orchestrator |
| `db` | `postgres:16-alpine` | Persistent state (stacks, users, Git repos config) |
| `socket-proxy` | `tecnativa/docker-socket-proxy` | Filtered Docker API access — Dockhand never talks to the Docker socket directly |

Dockhand reaches the Docker daemon via `DOCKER_HOST=tcp://socket-proxy:2375`. The proxy enforces which API endpoints are allowed — see `.env.example` / `docker-compose.yml` for the permission set.

## Setup

```bash
# 1. Create .env
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, TZ, APP_PUID/APP_PGID

# 2. Generate secrets
mkdir -p .secrets
openssl rand -base64 32 | tr -d '\n' > .secrets/db_pwd.txt
openssl rand -base64 32 | tr -d '\n' > .secrets/encryption_key.txt

# 3. Start
docker compose up -d

# 4. Open the web UI
# https://<APP_TRAEFIK_HOST> (only reachable from the configured access policy)
```

Default access policy is `acc-tailscale` + `sec-3-spa` (VPN-only, hardened, SPA-friendly rate limit). Adjust in `.env` if a different setup is needed.

## Adding the local environment

After first login, Dockhand asks you to add an environment. For the Docker daemon on the host where Dockhand itself runs, enter:

| Field | Value |
|---|---|
| Name | any label — e.g. `Production` |
| Connection type | `Direct connection` |
| Host | `socket-proxy` |
| Port | `2375` |
| Protocol | `HTTP` |
| Public IP | leave empty |

Dockhand reaches the Docker API through the filtered socket proxy on the internal `dockhand-internal` network. Plain HTTP is safe here because the proxy is never reachable from the host or the internet — only from containers on that network.

Click "Test connection" → should turn green → "Add". The environment appears in the sidebar with full stack management (containers, volumes, networks, Git-based deploys).

## Verify

```bash
docker compose ps                    # All three services should be healthy
docker compose logs app --tail 50    # Check for startup errors
docker compose logs socket-proxy     # Socket proxy access log
```

Log in to the web UI, add the environment as described above, then add a stack pointing at a Git repo — verify that Dockhand pulls and applies the compose file.

## Security Model

Socket proxy is the key hardening layer. Dockhand is granted only the API calls it needs. The environment variables in the `socket-proxy` service control this — the current set allows container management (start/stop/restart), network and volume operations, plus `POST`/`EXEC`/`DELETE` as needed for stack deployment.

If Dockhand doesn't need a capability (e.g. no image management from the UI), set the corresponding variable to `"0"` and restart.

## Backup

| | |
|---|---|
| **Database** | PostgreSQL · container `dockhand-db` · database `dockhand` · user `dockhand` |
| **Password** | `.secrets/db_pwd.txt` |
| **State** | `./volumes/postgres` (database) · `./volumes/data` |
| **Reproducible** | nothing |
| **Quiescing** | Not needed. The dump is consistent on its own. |

```yaml
postgresql_databases:
    - name: dockhand
      container: dockhand-db
      username: dockhand
      password: "{credential file /srv/docker/core/dockhand/.secrets/db_pwd.txt}"
```

**`.secrets/encryption_key.txt` decrypts what is stored in the database.** A
database restored without the matching key holds rows that cannot be read back.
Back the key up separately from the database and keep a copy off the host — the
two together are what makes the restore work, and keeping them in one place
defeats the point of encrypting at rest.

**Restore order:** database first, then the app.

## Known Issues

None currently documented.

## Details

- [UPSTREAM.md](UPSTREAM.md) — source, upgrade checklist, useful commands
