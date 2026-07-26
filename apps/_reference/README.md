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
`scripts/ci/check-baseline.py`, which reports drift as **FAIL** (dangerous) or
**WARN** (inconsistent).

| Lens | Question | Spec |
|------|----------|------|
| **Structure** | Is it laid out and named like every other app? | [env-structure.md](../../docs/standards/env-structure.md) · [compose-structure.md](../../docs/standards/compose-structure.md) · [naming-conventions.md](../../docs/standards/naming-conventions.md) |
| **Security** | Secrets isolated, privileges dropped, nothing needlessly exposed? | [security-baseline.md](../../docs/standards/security-baseline.md) |
| **Architecture** | Right networks, routing, dependencies, healthchecks? | [networking.md](../../docs/standards/networking.md) · [traefik-labels.md](../../docs/standards/traefik-labels.md) |
| **Resources** | Bounded memory/CPU/pids, sane healthcheck timing? | *(spec pending)* |

## Files

| File | Purpose | Status |
|------|---------|--------|
| [`.env.example`](.env.example) | Canonical env layout — sections, order, layer tags, pinning rules | ✅ |
| [`docker-compose.yml`](docker-compose.yml) | Production stack — Traefik, Docker Secrets, resource caps | ✅ |
| [`docker-compose.local.yml`](docker-compose.local.yml) | Local stack — localhost port, plain env, no Traefik | ✅ |
| [`.env.local.example`](.env.local.example) | Local env — deliberately minimal | ✅ |
| [`config/entrypoint.sh`](config/entrypoint.sh) | Secret-injection wrapper for images without `_FILE` support | ✅ |
| [`.gitignore`](.gitignore) | Keeps `.env`, `.secrets/`, `volumes/` out of git | ✅ |
| `UPSTREAM.md` | Per-app upstream reference + upgrade checklist | *pending* |

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

- `UPSTREAM.md` — the per-app upstream/upgrade doc every app carries
- Boot the stack once (above) to confirm it truly runs
- `scripts/ci/check-structure.py` is not wired into CI yet
- `docs/templates/` still holds an older skeleton — fold it into this directory
  so there is only one template

## Stand-in images (deliberate)

| Service | Image | Demonstrates |
|---------|-------|--------------|
| `db` | `postgres` | Native `_FILE` secrets (`POSTGRES_PASSWORD_FILE`) |
| `app` | `nginx` | Images **without** `_FILE` → `config/entrypoint.sh` wrapper |

Both secret patterns appear in one place, which is the point.
