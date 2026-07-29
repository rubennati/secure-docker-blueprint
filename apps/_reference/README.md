# Reference App

> **Status: 🔧 Reference** — not a deployable service. This is the canonical
> structure every app in this repo follows.

The single source of truth for **file structure, section order, naming, and
patterns**. It runs (nginx + postgres as neutral stand-ins) so the structure can
actually be tested, not just read.

Two ways to use it:

1. **Starting a new app** — copy it, then replace the stand-in images and delete
   what the app does not need:

   ```bash
   cp -r apps/_reference apps/my-app
   ```

2. **Checking an existing app** — diff your app's files against these and close
   the gaps. When a pattern here changes, existing apps get realigned to it.

The prose specs stay in [`docs/standards/`](../../docs/standards/) — this
directory is their working embodiment. Where they disagree, the standard wins
and this app gets fixed.

## Four lenses

Every file here is meant to hold up under all four. The same lenses drive
`scripts/ci/check-structure.py`, which reports drift as **FAIL** (dangerous) or
**WARN** (inconsistent) and runs in CI.

| Lens | Question | Spec |
|------|----------|------|
| **Structure** | Is it laid out and named like every other app? | [env-structure.md](../../docs/standards/env-structure.md) · [compose-structure.md](../../docs/standards/compose-structure.md) · [naming-conventions.md](../../docs/standards/naming-conventions.md) |
| **Security** | Secrets isolated, privileges dropped, nothing needlessly exposed? | [security-baseline.md](../../docs/standards/security-baseline.md) |
| **Architecture** | Right networks, routing, dependencies, healthchecks? | [networking.md](../../docs/standards/networking.md) · [traefik-labels.md](../../docs/standards/traefik-labels.md) |
| **Resources** | Bounded memory/CPU/pids, sane healthcheck timing? | [compose-structure.md](../../docs/standards/compose-structure.md) — `Resources` block |

## Files

| File | Purpose | Status |
|------|---------|--------|
| [`.env.example`](.env.example) | Canonical env layout — sections, order, layer tags, pinning rules | ✅ |
| [`docker-compose.yml`](docker-compose.yml) | Production stack — Traefik, Docker Secrets, resource caps | ✅ |
| [`docker-compose.local.yml`](docker-compose.local.yml) | Local stack — localhost port, plain env, no Traefik | ✅ |
| [`.env.local.example`](.env.local.example) | Local env — deliberately minimal | ✅ |
| [`config/entrypoint.sh`](config/entrypoint.sh) | Secret-injection wrapper for images without `_FILE` support | ✅ |
| [`.gitignore`](.gitignore) | Keeps `.env`, `.secrets/`, `volumes/` out of git | ✅ |
| [`UPSTREAM.md`](UPSTREAM.md) | Per-app upstream reference + upgrade checklist | ✅ |

## Backup

Every app README carries this section. It exists so the backup configuration can
be *assembled* from the apps rather than reverse-engineered from their compose
files at the moment someone needs a restore.

Keep it to what an operator writing `/etc/borgmatic/config.yaml` needs, and keep
the heading exactly `## Backup` — `scripts/ci/lifecycle-report.py` reads it to
fill the `Backup docs` column in `LIFECYCLE.md`.

| | |
|---|---|
| **Database** | PostgreSQL · container `${COMPOSE_PROJECT_NAME}-db` · database `myapp` · user `myapp` |
| **Password** | `.secrets/db_pwd.txt` |
| **State** | `./volumes/postgres` (database) — bind mount |
| **Reproducible** | `./volumes/*/cache` — safe to exclude |
| **Quiescing** | Not needed. The dump is consistent on its own; the app can keep running. |

Drop this straight into the borgmatic configuration — the path is the same
`.secrets/` file this stack already mounts, so there is one copy of the password
on the host:

```yaml
postgresql_databases:
    - name: myapp
      container: myapp-db
      username: myapp
      password: "{credential file /srv/docker/apps/myapp/.secrets/db_pwd.txt}"
```

**Restore order:** database first, then the app. Starting the app against an
empty or half-restored database can leave it writing migrations over the restore.

Where an app needs more than this — a maintenance mode, an index to rebuild, a
search engine to reseed — say so here rather than in a comment nobody reads
during an incident. Full architecture: [`backup/README.md`](../../backup/README.md).

## Try it locally

```bash
cp .env.local.example .env.local     # fill in the openssl one-liners
docker compose -f docker-compose.local.yml --env-file .env.local up -d
curl http://localhost:8080/          # nginx welcome page = the structure works
docker compose -f docker-compose.local.yml --env-file .env.local down
```

> Both compose files pass `docker compose config` and the security baseline, but
> the stack has **not been booted yet** — the run above is the outstanding proof.

## Open

- Boot the stack once (above) to confirm it truly runs — the one outstanding proof

## Stand-in images (deliberate)

| Service | Image | Demonstrates |
|---------|-------|--------------|
| `db` | `postgres` | Native `_FILE` secrets (`POSTGRES_PASSWORD_FILE`) |
| `app` | `nginx` | Images **without** `_FILE` → `config/entrypoint.sh` wrapper |

Both secret patterns appear in one place, which is the point.
