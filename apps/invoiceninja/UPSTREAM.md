# Upstream Reference

## Source

- **Repo:** https://github.com/invoiceninja/dockerfiles
- **Branch:** `debian`
- **Based on version:** 5.13.16
- **Last checked:** 2026-04-13

## What we use from upstream

| File | Used as | Notes |
|------|---------|-------|
| `nginx/laravel.conf` | 1:1 copy | Server block for Laravel/PHP-FPM |
| `nginx/invoiceninja.conf` | 1:1 copy | Global nginx settings (gzip, buffers) |
| `.env` | Reference for env vars | Restructured to Blueprint conventions |
| `docker-compose.yml` | Reference for service topology | Adapted: Traefik, secrets, naming |

## What we changed and why

| Change | Reason |
|--------|--------|
| No Dockerfile / build | Use pre-built Docker Hub image instead of local build |
| No `php/`, `scripts/`, `supervisor/` | Baked into the Docker Hub image already |
| Docker Secrets for DB/user passwords | Blueprint standard, Laravel needs entrypoint wrapper |
| `env_file` replaced with explicit `environment:` | Blueprint standard — control what enters the container |
| Service names: `app`, `db`, `nginx`, `redis` | Blueprint naming convention |
| Traefik labels on nginx | Blueprint routing via Traefik, no exposed ports |
| Named volumes (upstream) kept | Upstream pattern, volume strategy still open |

## Upgrade checklist

When bumping the image tag (`APP_TAG`):

1. Check upstream [releases](https://github.com/invoiceninja/invoiceninja/releases) for breaking changes
2. Check upstream [dockerfiles repo](https://github.com/invoiceninja/dockerfiles/tree/debian) for changes to:
   - `nginx/` configs (compare with ours)
   - `.env` (new required variables?)
   - `docker-compose.yml` (new services, volume paths?)
   - `scripts/init.sh` (migration logic changes?)
   - `Dockerfile` (new PHP extensions, system deps?)
3. Bump `APP_TAG` in `.env`
4. `docker compose pull` → `docker compose up -d`
5. Check `docker compose logs -f app` for migration output
6. Verify login + `/api/v1/health_check`

## Upstream update commands

```bash
# Refresh upstream reference
cd /path/to/docker-ops-blueprint/tmp/invoiceninja-dockerfiles
git pull

# Diff nginx configs against ours
diff /path/to/docker-ops-blueprint/tmp/invoiceninja-dockerfiles/debian/nginx/ /path/to/docker-ops-blueprint/apps/invoiceninja/nginx/

# Diff env vars
diff <(grep -v '^#\|^$' /path/to/docker-ops-blueprint/tmp/invoiceninja-dockerfiles/debian/.env | sort) \
     <(grep -v '^#\|^$' /path/to/docker-ops-blueprint/apps/invoiceninja/.env.example | sort)
```
