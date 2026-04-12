# App Template

Copyable starter for new apps in the blueprint.

## Usage

```bash
# 1. Copy template
cp -r docs/templates apps/my-new-app
cd apps/my-new-app

# 2. Create and adjust .env
cp .env.example .env
# Edit all values in .env

# 3. Create secrets
mkdir -p secrets
openssl rand -base64 32 > secrets/db_password.txt

# 4. Start
docker compose up -d
```

## Customization

- **No database:** Remove `database` service, `app-internal` network, and `secrets` block
- **No Traefik:** Remove `labels` block and `proxy-public` network
- **read_only:** Uncomment `read_only` and `tmpfs` if the image supports it
- **Healthcheck:** Adjust to the app (port, path, timing)

## Reference

See the standards documentation:
- [Compose Structure](../standards/compose-structure.md) — block order, rules, common patterns
- [Env Structure](../standards/env-structure.md) — section order, variable rules, checklist
- [Naming Conventions](../standards/naming-conventions.md) — containers, env vars, networks, volumes
- [Traefik Labels](../standards/traefik-labels.md) — routing, security levels, TLS profiles
- [Security Baseline](../standards/security-baseline.md) — hardening, secrets, socket proxy
- [Networking](../standards/networking.md) — isolation, network types
