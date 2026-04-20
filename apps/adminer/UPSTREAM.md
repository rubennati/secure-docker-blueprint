# Upstream Reference

## Source

- **Image:** https://hub.docker.com/_/adminer
- **Project home:** https://www.adminer.org/
- **GitHub:** https://github.com/vrana/adminer
- **Based on version:** `4.x` (standalone variant)
- **Last checked:** 2026-04-17

## What we use

- Official `adminer` image, `4-standalone` tag (pure Adminer — no bundled web server stack)
- No database — Adminer connects to external DBs
- Blueprint-standard Traefik routing + Docker network model

## What we changed and why

| Change | Reason |
|--------|--------|
| No bundled MariaDB in the compose | Adminer's canonical use-case is managing existing app databases (wordpress-db, ghost-db, etc.). Bundling a MariaDB makes it a development-only fixture. Dropped, with the original inbox variant preserved in the `docs` branch notes. |
| Traefik labels instead of host port mapping | Consistent with the rest of the blueprint. Original inbox used `ports: "8014:8080"`. |
| `security_opt: no-new-privileges` | Blueprint baseline. |
| Access policy defaults to `acc-tailscale` | Admin-access tools must never be publicly reachable by default. |
| Security chain defaults to `sec-4` | Hard rate limiting against credential-stuffing on the DB-login form. |
| `4-standalone` tag instead of `latest` | Reproducible; other variants (`fastcgi`, `4-fastcgi`) are less useful behind Traefik. |

## Upgrade checklist

Adminer moves in minor versions (`4.8.x` → `4.9.x`). Major `5.x` not yet out as of 2026-04-17.

1. Check [GitHub releases](https://github.com/vrana/adminer/releases) for notes on deprecated drivers
2. Bump `APP_TAG` in `.env`
3. `docker compose pull && docker compose up -d`
4. Verify login still works against one known DB

No DB migrations, no data to back up — Adminer is stateless.

## Related images to keep in sync

None. Adminer is a standalone client.

## Useful commands

```bash
# Shell into the container
docker compose exec app sh

# Adminer version (check running instance)
docker compose exec app sh -c 'grep version /var/www/html/adminer/adminer*.php | head -1'

# Attach Adminer to a specific app's internal network (e.g. to reach wordpress-db)
docker network connect wordpress-internal adminer-app

# Detach
docker network disconnect wordpress-internal adminer-app

# List networks adminer is currently on
docker inspect adminer-app --format '{{json .NetworkSettings.Networks}}' | jq 'keys'
```
