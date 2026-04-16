# App Template

Copyable starter for new apps in the blueprint. Follows all current standards.

## Usage

```bash
# 1. Copy template
cp -r docs/templates apps/my-new-app
cd apps/my-new-app

# 2. Create and adjust .env
cp .env.example .env
# Edit at minimum: COMPOSE_PROJECT_NAME, APP_TRAEFIK_HOST, APP_TAG, DB_TAG, APP_INTERNAL_PORT

# 3. Create secrets (use hex for URL-embedded passwords)
mkdir -p .secrets
openssl rand -hex 32 | tr -d '\n' > .secrets/db_pwd.txt
openssl rand -hex 32 | tr -d '\n' > .secrets/db_root_pwd.txt

# 4. Replace 'your-image' in docker-compose.yml with the actual image name

# 5. Start
docker compose up -d
```

## Customization

- **No database:** Remove `db` service, `app-internal` network, and `secrets` block
- **No Traefik:** Remove `labels` block and `proxy-public` network
- **read_only:** Uncomment `read_only: true` + `tmpfs` if the image supports it
- **Docker Secrets for app:** Uncomment `secrets:` block if image supports `_FILE` env vars
- **Healthcheck:** Adjust to the app (port, path, timing, available tools like `curl`/`wget`)
- **Entrypoint wrapper:** If image doesn't support `_FILE` env vars, add a `config/entrypoint.sh` that reads secrets at runtime (see `apps/vaultwarden` for an example)

## Required Follow-up

After copying, create these files to meet the per-app documentation standard:

- `README.md` — setup steps, verify section, known issues (template: `apps/wordpress/README.md`)
- `UPSTREAM.md` — source, version, upgrade checklist (template: `apps/vaultwarden/UPSTREAM.md`)
- `.gitignore` — `.secrets/`, `volumes/`, `.env`

## Reference

Standards documentation:

- [Compose Structure](../standards/compose-structure.md) — block order, rules, common patterns
- [Env Structure](../standards/env-structure.md) — section order, variable rules
- [Naming Conventions](../standards/naming-conventions.md) — containers, env vars, networks
- [Traefik Labels](../standards/traefik-labels.md) — routing, security levels, TLS profiles
- [Traefik Security](../standards/traefik-security.md) — access policies, sec chains, TLS
- [Security Baseline](../standards/security-baseline.md) — hardening, secrets, socket proxy
- [Networking](../standards/networking.md) — isolation, network types
- [New App Checklist](../standards/new-app-checklist.md) — full step-by-step
