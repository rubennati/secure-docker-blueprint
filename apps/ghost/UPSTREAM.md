# Upstream Reference

## Source

- **Image:** https://hub.docker.com/_/ghost
- **GitHub:** https://github.com/TryGhost/Ghost
- **Docs:** https://ghost.org/docs/
- **Config reference:** https://ghost.org/docs/config/
- **Based on version:** `6.27.0-alpine`
- **Last checked:** 2026-04-16

## What we use

- Official `ghost` image (Alpine variant), pinned tag
- Official `mysql:8.4` LTS as backend
- Ghost's native `__file` config pattern for secrets — no entrypoint wrapper needed

## What we changed and why

| Change | Reason |
|--------|--------|
| MySQL 8.4 (not 8.0) | 8.4 is the current LTS; 8.0 reached EOL April 2026 |
| `cap_drop: ALL` + minimal `cap_add` on MySQL | MySQL needs `CHOWN`/`SETUID`/`SETGID`/`DAC_OVERRIDE` for user switching; everything else is dropped |
| `mysqladmin ping` healthcheck | `healthcheck.sh` is MariaDB-specific and not shipped in the upstream MySQL image |
| `utf8mb4` character set | Correct Unicode storage for post content and member names; Ghost requires it |
| SMTP via external relay | The Alpine image has no local MTA — using an external SMTP service is the only option that works out of the box |
| TLS profile `tls-aplus` + `acc-public` + `sec-2` | Public blog, standard web-app security posture, A+ on SSL Labs |

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

## Related images to keep in sync

- `mysql:8.4` — safe to update within the 8.4 LTS line. Do NOT jump to MySQL 9 without reading the MySQL 8.4 → 9.x migration notes; Ghost officially supports MySQL 8 only.

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

# Test SMTP configuration from inside the container
docker compose exec app sh -c 'echo "mail test" | sendmail -t'

# Inspect Ghost's resolved config (after __file substitutions)
docker compose exec app node -e 'console.log(JSON.stringify(require("ghost/core/shared/config").get(), null, 2))'
```
