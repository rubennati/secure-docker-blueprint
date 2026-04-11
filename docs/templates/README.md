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
- [Naming Conventions](../standards/naming-conventions.md)
- [Traefik Labels](../standards/traefik-labels.md)
- [Security Baseline](../standards/security-baseline.md)
- [Networking](../standards/networking.md)
