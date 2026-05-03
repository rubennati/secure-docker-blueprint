# Upstream Reference

## Source

- **n8n project:** https://n8n.io/
- **GitHub:** https://github.com/n8n-io/n8n
- **Docker docs:** https://docs.n8n.io/hosting/installation/docker/
- **License:** [Sustainable Use License](https://docs.n8n.io/sustainable-use-license/) (source-available; free for internal + commercial use up to limits)
- **Based on version:** `2.19.2`
- **Last verified:** 2026-05-02 (v2.19.2)

## What we use

- Upstream `docker.n8n.io/n8nio/n8n`
- Built-in SQLite database (in `./volumes/data/`)
- Docker Secret for `N8N_ENCRYPTION_KEY`
- Bind-mount `./volumes/data` (n8n state) and `./volumes/files` (workflow scratch space)

## What we changed and why

| Change | Reason |
|--------|--------|
| **`${SUBDOMAIN}.${DOMAIN_NAME}` → single `APP_TRAEFIK_HOST`** | Blueprint uses one variable for the full hostname |
| **Inline Traefik header middlewares removed** — inbox defined HSTS/XSS/nosniff/etc. inline | Replaced with shared `sec-3@file` chain (same headers, centralized) |
| **Traefik router entrypoints pared down** — inbox used `web,websecure` + `SSLRedirect: true` | Now just `websecure`; blueprint handles HTTP→HTTPS redirect at the entrypoint level |
| **`certresolver=dnsResolver` replaced with `APP_TRAEFIK_CERT_RESOLVER`** | Blueprint variable |
| **Port `8015:5678` exposure removed** | Blueprint routes via Traefik |
| **`N8N_ENCRYPTION_KEY_FILE` added** (Docker Secret) | n8n supports `_FILE` suffixes on every secret env var — the encryption key is the single most important secret |
| **Basic auth enabled by default** | Community Edition has no user management unless opted in; basic auth is the minimum viable gate |
| **`security_opt: no-new-privileges:true`** | Baseline hardening |
| **`traefik` external network → `proxy-public`** | Blueprint standard network name |
| **Unused `traefik_data` volume removed** | Stray leftover from a full Traefik+n8n bundle |
| **Access `acc-tailscale` + security `sec-3` defaults** | n8n hosts API tokens for many third-party services — VPN-only is safer than public |

## Upgrade checklist

1. Check [n8n releases](https://github.com/n8n-io/n8n/releases) — minor bumps can contain breaking changes to nodes and workflows
2. Back up:
   ```bash
   tar czf n8n-data-$(date +%Y%m%d).tgz volumes/data/
   ```
3. Bump `APP_TAG` in `.env` (pin to a specific release)
4. `docker compose pull && docker compose up -d`
5. Watch logs:
   ```bash
   docker compose logs app --follow
   ```
6. Verify: log in, open a workflow, trigger a manual execution, confirm credentials still decrypt (encryption key unchanged)

### Rollback

Restore `volumes/data/`, revert `APP_TAG`. SQLite schema migrations are forward-only; a downgrade after a major bump may need manual SQL intervention.

## Useful commands

```bash
# Shell into n8n
docker compose exec app sh

# CLI commands
docker compose exec app n8n --help
docker compose exec app n8n list:workflow
docker compose exec app n8n export:workflow --all --output=/files/backup.json
docker compose exec app n8n import:workflow --input=/files/backup.json

# User management (CE multi-user)
docker compose exec app n8n user-management:reset
```

## Upgrading to Postgres

For larger deployments, swap SQLite for Postgres:

```yaml
# Add to compose:
db:
  image: postgres:16
  environment:
    POSTGRES_DB: n8n
    POSTGRES_USER: n8n
    POSTGRES_PASSWORD_FILE: /run/secrets/DB_PWD
  secrets: [DB_PWD]
  volumes: ["./volumes/postgres:/var/lib/postgresql/data"]
  networks: [app-internal]

# On app, add env:
DB_TYPE: postgresdb
DB_POSTGRESDB_HOST: db
DB_POSTGRESDB_DATABASE: n8n
DB_POSTGRESDB_USER: n8n
DB_POSTGRESDB_PASSWORD_FILE: /run/secrets/DB_PWD
```

n8n supports `_FILE` on every secret env var, so no `DB_PWD_INLINE` duplication is needed.
