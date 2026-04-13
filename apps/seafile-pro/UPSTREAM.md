# Upstream Reference

## Source

- **Repo:** https://manual.seafile.com/13.0/docker/pro/deploy_seafile_pro_with_docker/
- **Config source:** Official Seafile Pro Docker Compose files (inbox/seafile-pro_original)
- **Based on version:** Seafile Pro 13.0
- **Last checked:** 2026-04-13

## What we use from upstream

| File | Used as | Notes |
|------|---------|-------|
| `seafile-server.yml` | Adapted | Caddy → Traefik, Secrets, Blueprint naming |
| `seadoc.yml` | Adapted | Caddy labels removed, Secrets added |
| `notification-server.yml` | Adapted | Caddy labels removed, Secrets added |
| `md-server.yml` | Adapted | Caddy labels removed, Secrets added, S3 commented |
| `thumbnail-server.yml` | Adapted | Caddy labels removed, Secrets added, S3 commented |
| `seasearch.yml` | Adapted | Blueprint naming, S3 commented |
| `clamav.yml` | Adapted | Fixed tag, Blueprint naming |
| `elasticsearch.yml` | Kept as reference | Not in COMPOSE_FILE, use SeaSearch instead |
| `seafile-ai.yml` | Kept as reference | Not in COMPOSE_FILE, enable later |

## What we changed and why

| Change | Reason |
|--------|--------|
| Caddy → Traefik labels | Blueprint uses Traefik, not Caddy |
| `seafile-net` → `app-internal` + `proxy-public` | Blueprint network schema |
| Passwords → Docker Secrets + entrypoint wrapper | Blueprint standard; Seafile has no `_FILE` support |
| Redis password via hex (not base64) | Avoids +/= chars that break PHP/Python URL encoding |
| Container names → variables | Blueprint standard |
| Image names hardcoded, tags as variables | Blueprint standard |
| `security_opt: no-new-privileges` | Blueprint security baseline |
| S3 config commented out | Default is disk storage |
| `restart: always` → `unless-stopped` | Blueprint standard |
| `redis: condition: service_healthy` | CE learning — prevents race conditions |
| `start_period: 180s` for seafile | CE learning — first start takes long |
| Memcached removed | Pro uses Redis only |
| Elasticsearch not in default COMPOSE_FILE | SeaSearch recommended instead |
| SeaDoc SEAHUB_SERVICE_URL → `http://app` | Service renamed from `seafile` to `app` |

## Elasticsearch alternative

If you need Elasticsearch instead of SeaSearch (e.g. for partial document updates):

1. Replace `seasearch.yml` with `elasticsearch.yml` in `COMPOSE_FILE`
2. The `elasticsearch.yml` from Stage 0 is still in the directory
3. See: https://manual.seafile.com/13.0/docker/pro/deploy_seafile_pro_with_docker/

## First-time setup

After the very first `docker compose up -d`:

```bash
# Wait until app is healthy
docker compose ps

# Restart app to inject OnlyOffice + Metadata settings into seahub_settings.py
docker compose restart app

# Verify settings were injected
docker exec seafile-pro-app grep "Blueprint" /shared/seafile/conf/seahub_settings.py
```

**Why:** On first boot, Seafile creates `seahub_settings.py`. Our entrypoint wrapper
tries to append custom settings but the file doesn't exist yet during the first run.
The restart triggers the injection. This is only needed once.

## Upgrade checklist

When bumping the Seafile Pro version:

1. Check [Seafile changelog](https://manual.seafile.com/changelog/server-changelog/)
2. Check [upgrade notes](https://manual.seafile.com/13.0/upgrade/upgrade_docker/)
3. Bump `APP_TAG` and related service tags in `.env`
4. `docker compose pull` → `docker compose up -d`
5. Check `docker compose logs -f app` for migration output
6. Verify login and file access

## Upstream diff commands

```bash
# Compare upstream .env with ours
diff inbox/seafile-pro_original/.env apps/seafile-pro/.env.example

# Compare a specific service yml
diff inbox/seafile-pro_original/seafile-server.yml apps/seafile-pro/seafile-server.yml
```
