# Upstream Reference

## Source

- **Image:** https://hub.docker.com/_/ghost
- **GitHub:** https://github.com/TryGhost/Ghost
- **Docs:** https://ghost.org/docs/
- **Config reference:** https://ghost.org/docs/config/
- **License:** MIT
- **Origin:** Ireland · Ghost Foundation · EU
- **Based on version:** `6.27.0-alpine`
- **Last verified:** 2026-05-02 (v6.27.0-alpine)

### ActivityPub service

- **Image:** https://github.com/orgs/TryGhost/packages/container/package/activitypub
- **GitHub:** https://github.com/TryGhost/ActivityPub
- **Based on version:** `1.2.2`

### ActivityPub migrations

- **Image:** https://github.com/orgs/TryGhost/packages/container/package/activitypub-migrations
- **Based on version:** `1.2.2`

## What we use

- Official `ghost` image (Alpine variant), pinned tag
- Official `mysql:8.4` LTS as backend
- Custom entrypoints for Docker Secret injection — Ghost, ActivityPub, and the migrations runner do not support `_FILE` env vars
- Optional: `ghcr.io/tryghost/activitypub` + `ghcr.io/tryghost/activitypub-migrations` via overlay compose

## Architecture

```
Internet → Traefik (TLS, port 443) → Ghost :2368
                                    → ActivityPub :8080  (overlay, high-priority router)
```

The official ghost-docker setup uses Caddy as an internal webserver. This blueprint uses Traefik directly for all routing — the same paths Caddy handles in the official setup are covered by a high-priority Traefik router in the ActivityPub overlay.

## What we changed and why

| Change | Reason |
|--------|--------|
| Traefik instead of Caddy | Blueprint standard — all apps use Traefik. ActivityPub path routing is handled by a separate high-priority Traefik router instead of Caddy snippets. |
| `X-Forwarded-Proto: https` middleware on ActivityPub router | ActivityPub reconstructs request URLs from this header. Caddy (official) forwards it automatically. Traefik requires an explicit `customrequestheaders` middleware to guarantee the header reaches the container. |
| Custom entrypoint for Ghost secrets | Ghost does not support Docker's `_FILE` env var pattern. The `__file` suffix in Ghost's nconf notation creates a nested object (`{file: '...'}`) not a string, causing mysql2 to crash with `ERR_INVALID_ARG_TYPE` at authentication. Custom entrypoint reads secret files and exports plain env vars. |
| Custom entrypoints for ActivityPub + migrations | Same reason — neither image supports `_FILE`. Wrapper scripts read the Docker Secret and export the plain password before handing off. |
| Docker Secrets throughout | Official compose uses plain `DATABASE_PASSWORD` in environment. Blueprint standard: passwords never in env vars. |
| MySQL 8.4 (not 8.0) | 8.4 is the current LTS; 8.0 reached EOL April 2026. |
| `cap_drop: ALL` + minimal `cap_add` on MySQL | MySQL needs `CHOWN`/`SETUID`/`SETGID`/`DAC_OVERRIDE` for user switching; everything else is dropped. |
| `mysqladmin ping -p"$(cat secret)" -h 127.0.0.1` healthcheck | `healthcheck.sh` is MariaDB-specific and not in the MySQL image. `-h 127.0.0.1` forces TCP (localhost uses a Unix socket, ready before TCP). Password read from secret file because `MYSQL_ROOT_PASSWORD_FILE` is not resolved outside the init phase. |
| `utf8mb4` character set | Correct Unicode storage for post content and member names; Ghost requires it. |
| SMTP via external relay | The Alpine image has no local MTA — an external SMTP service is required. |
| TLS profile `tls-aplus` + `acc-public` + `sec-2` | Public blog, standard web-app security posture, A+ on SSL Labs. |
| ActivityPub as optional overlay | Adds 2 services + one-shot migration runner. Separated into `activitypub.yml` so the base stack works independently. |
| ActivityPub shares Ghost content volume | Official pattern — images written by ActivityPub land in `./volumes/content/images/activitypub/` and are served by Ghost at `/content/images/activitypub`. No separate volume or Traefik route needed for image delivery. |
| `MYSQL_MULTIPLE_DATABASES: activitypub` + `mysql-init/` | Official pattern — the activitypub database is created by an init script on first MySQL startup instead of a separate compose service. |
| `ALLOW_PRIVATE_ADDRESS=true` on ActivityPub | Required for Docker internal network communication between services. |
| `USE_MQ=false` on ActivityPub | Disables Google PubSub dependency — not available in self-hosted deployments. |
| `app-internal: internal: true` | Blueprint network isolation — databases and backend services never have direct internet access. The official uses a single `ghost_network` without the `internal` flag. |

## Upgrade checklist

Ghost has major-version migrations that can rewrite the database schema. Plan them.

1. Read the Ghost release notes for breaking changes and required migration steps: https://github.com/TryGhost/Ghost/releases
2. **Backup** the database and content volume:
   ```bash
   docker compose exec db mysqldump -u root -p"$(cat .secrets/db_root_pwd.txt)" ghost > ghost-$(date +%Y%m%d).sql
   tar czf ghost-content-$(date +%Y%m%d).tgz ./volumes/content/
   ```
3. Bump `APP_TAG` in `.env` (one major version at a time — e.g. 5 → 6, not 4 → 6)
4. `docker compose pull && docker compose up -d`
5. Watch migration output: `docker compose logs app --tail 200 --follow`
6. Verify: admin UI loads, posts are intact, members list is intact, newsletter send works

### Rollback

Ghost's DB migrations are one-way. Rollback = restore the SQL dump AND revert `APP_TAG`.

### Upgrading ActivityPub

1. Check https://github.com/TryGhost/ActivityPub/releases for breaking changes
2. Bump `ACTIVITYPUB_TAG` in `.env`
3. `docker compose pull && docker compose up -d`
4. The `activitypub-migrate` service runs automatically and applies any new migrations

## Related images to keep in sync

- `mysql:8.4` — safe to update within the 8.4 LTS line. Do NOT jump to MySQL 9 without reading the MySQL 8.4 → 9.x migration notes; Ghost officially supports MySQL 8 only.
- `ghcr.io/tryghost/activitypub` — keep in sync with `ghcr.io/tryghost/activitypub-migrations` (both track the same release)

## Useful commands

```bash
# Shell into Ghost
docker compose exec app sh

# Tail Ghost logs
docker compose logs app --follow

# Manual DB backup
docker compose exec db mysqldump -u root -p"$(cat .secrets/db_root_pwd.txt)" ghost > dump.sql

# Restore DB from dump (into fresh instance)
cat dump.sql | docker compose exec -T db mysql -u root -p"$(cat .secrets/db_root_pwd.txt)" ghost

# Check ActivityPub database tables
docker compose exec db sh -c 'mysql -u root -p"$(cat /run/secrets/DB_ROOT_PWD)" activitypub -e "SHOW TABLES;"'

# Re-run ActivityPub migrations manually (e.g. after adding ActivityPub to existing install)
docker compose run --rm activitypub-migrate
```
