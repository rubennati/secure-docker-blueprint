# Upstream Reference

## Source

- **Monica project:** https://www.monicahq.com/
- **GitHub:** https://github.com/monicahq/monica
- **Docker Hub:** https://hub.docker.com/_/monica (official image)
- **License:** AGPL-3.0
- **Origin:** Canada · Monica HQ · non-EU
- **Based on version:** `5-apache`
- **Last checked:** 2026-04-17

## What we use

- Official `monica:5-apache` (Laravel + Apache + PHP)
- Official `mariadb:11.4`
- Docker Secret for MariaDB user password + inline duplicate for Monica
- Bind-mount `./volumes/mysql`, `./volumes/data`

## What we changed and why

| Change | Reason |
|--------|--------|
| **Hardcoded `APP_KEY` removed** — inbox had a plaintext Laravel key | Shared key = backdoor across copies. Now `__REPLACE_ME__` + `artisan key:generate` documented |
| **Hardcoded DB password `secret` replaced** | Now Docker Secret + `DB_PWD_INLINE` |
| **`image: monica` → `monica:${APP_TAG}`** | Pinned tag (blueprint convention) |
| **Traefik labels instead of `ports: 8005:80`** | Blueprint routes via Traefik |
| **`MYSQL_RANDOM_ROOT_PASSWORD=true` kept** | Inbox had it; good practice — no root password on disk |
| **`APP_URL` added** | Inbox didn't set it; Laravel needs it for absolute URLs |
| **`APP_TRUSTED_PROXIES: "*"`** added | Required behind Traefik for correct `https://` URL generation |
| **`app-internal` network (`internal: true`)** | Isolate DB from host |
| **`security_opt: no-new-privileges`** + MariaDB `cap_drop: ALL` | Baseline hardening |
| **Container names standardized** — `monica-app/db` instead of bare `app/db` | Project-scoped naming avoids collision with other stacks |
| **Named volumes `data`, `mysql` → bind mounts** | Blueprint uses `./volumes/` for predictable backup paths; global `name: data`/`name: mysql` was a collision hazard |
| **Access `acc-tailscale` + security `sec-3` defaults** | Monica stores highly personal data (health notes, relationship details, journal) — VPN-only default; switch to `acc-public + sec-2` only if you deliberately want public access with password auth |

## Upgrade checklist

1. Check [Monica releases](https://github.com/monicahq/monica/releases) — Monica has had migration-heavy major bumps (3.x → 4.x → 5.x)
2. Back up:
   ```bash
   docker compose exec db sh -c \
     'mariadb-dump -u ${DB_USER} -p"$(cat /run/secrets/DB_PWD)" monica' \
     > monica-db-$(date +%Y%m%d).sql
   tar czf monica-data-$(date +%Y%m%d).tgz volumes/data/
   ```
3. Bump `APP_TAG` in `.env`
4. `docker compose pull && docker compose up -d`
5. Watch Laravel migration output:
   ```bash
   docker compose logs app --follow
   ```
6. Verify: log in, open a contact, add an activity, trigger an export

### Rollback

Restore DB dump and `volumes/data/`, revert `APP_TAG`. Note that major-version downgrades are not supported by Laravel.

## Useful commands

```bash
# Shell into the app
docker compose exec app bash

# Artisan commands
docker compose exec app php artisan <command>

# Run migrations manually
docker compose exec app php artisan migrate --force

# Generate a new APP_KEY (invalidates sessions)
docker compose exec app php artisan key:generate --show

# Manual DB backup
docker compose exec db sh -c \
  'mariadb-dump -u ${DB_USER} -p"$(cat /run/secrets/DB_PWD)" monica' > dump.sql

# Restore DB (requires the same password)
cat dump.sql | docker compose exec -T db sh -c \
  'mariadb -u ${DB_USER} -p"$(cat /run/secrets/DB_PWD)" monica'
```

## Not imported from inbox

The inbox compose file was minimal (33 lines) and did not configure email, Redis, queues, or OAuth. For production, consider adding:

- `MAIL_*` env vars for outgoing email (reminders, invitations)
- Redis service for session/cache driver if running multiple replicas
- `queue` worker (`php artisan queue:work`) for background jobs

See [Monica's Laravel .env reference](https://github.com/monicahq/monica/blob/main/.env.example).
