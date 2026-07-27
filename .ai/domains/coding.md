# Domain — Compose and Env

The canonical structure is `apps/_reference/` — runnable, not a paper skeleton. Copy
it to start; diff against it to find drift.

**Specs:** [`compose-structure.md`](../../docs/standards/compose-structure.md) ·
[`env-structure.md`](../../docs/standards/env-structure.md) ·
[`naming-conventions.md`](../../docs/standards/naming-conventions.md) ·
[`security-baseline.md`](../../docs/standards/security-baseline.md)

## Conventions that are decided, not open

- Image name hardcoded in compose, **tag from `.env`** (`image: wordpress:${APP_TAG}`).
  Image name plus registry link as a comment in `.env`.
- Container names derive from `${COMPOSE_PROJECT_NAME}`.
- Service names are uniform: `app`, `db`, `redis`, `nginx`.
- Traefik variables keep the `APP_TRAEFIK_*` prefix; the network is `${TRAEFIK_NETWORK}`.
- The certresolver label stays commented out — a per-domain certificate leaks the
  subdomain to Certificate Transparency logs when a wildcard already covers it.
- Traefik labels are grouped with `# Router`, `# TLS`, `# Middlewares`, `# Service`.
- Secrets live in `.secrets/` — a dotfolder, gitignored.
- `TZ`, not `TIMEZONE`.
- Explicit `environment:` maps, never `env_file:` — every value stays visible.
- Comments in English. `.gitignore` per app, not one at the root.
- Healthchecks are app-specific: use what the image actually ships.

Deviating from any of these needs a reason and approval.

## Block order in every service

Identity → Security → Resources → Configuration → Storage → Networking → Traefik →
Health. Identical everywhere, so any file can be read at a glance.

## Secret patterns

1. Image supports `_FILE` → use it. Always preferred.
2. Image does not → entrypoint wrapper reads `/run/secrets/` and execs the original
   command.
3. Secret embedded in a config file → env var in the gitignored `.env`, documented
   as a deviation.

Passwords that end up inside a URL are generated as **hex**, not base64 — base64
contains `/`, `+` and `=`, which break connection-string parsers. Always strip the
trailing newline: `| tr -d '\n'`.

## Before writing YAML

Verify against the image rather than assuming: entrypoint and command, available
tools for the healthcheck, expected environment variables, whether an init system
(s6-overlay, supervisord) forbids `user:`, and which ports it actually listens on.
