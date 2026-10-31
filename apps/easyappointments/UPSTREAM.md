# Upstream Reference

## Source

- **Project:** https://easyappointments.org/
- **GitHub:** https://github.com/alextselegidis/easyappointments
- **Docker Hub:** https://hub.docker.com/r/alextselegidis/easyappointments
- **License:** GPL-3.0
- **Decision facts checked:** not yet
- **Origin:** Greece · Alex Tselegidis · EU
- **Domain:** Publishing, forms and scheduling
- **Role:** Appointment booking in PHP, established since 2013
- **Based on version:** `1.6.1`
- **Last verified:** 2026-05-03 (1.5.x)

## What we use

- Official `alextselegidis/easyappointments`
- Official `mariadb:11.4`
- Docker Secrets for MariaDB user + root password
- Bind-mount `./volumes/storage` for the app's uploads directory

## What we changed vs. upstream examples

The upstream Docker compose example is minimal (app + db, linked via env). Blueprint conformance adds:

| Change | Reason |
|--------|--------|
| `MYSQL_PASSWORD_FILE` + `MYSQL_ROOT_PASSWORD_FILE` | MariaDB `_FILE` support — root password out of `.env` |
| `DB_PWD_INLINE` for the app | Easy!Appointments reads `DB_PASSWORD` inline (no `_FILE` support), same pattern as Monica / BookStack / Immich |
| Traefik labels instead of `ports: 80:80` | Blueprint routes via Traefik |
| `app-internal` network (`internal: true`) | DB not reachable from host |
| `cap_drop: ALL` + minimal `cap_add` on MariaDB | Baseline hardening |
| `no-new-privileges:true` on both services | Baseline hardening |
| Healthcheck-gated `depends_on` | Prevents EA from starting before MariaDB is ready |
| `TZ` env on both services | Blueprint convention |
| Default access `access-public`, `limit-standard` and `headers-standard` | Booking URLs must reach external visitors |

## Version notes

- Moved to `1.6.1` on 2026-10-31 (released 2026-10-19), not run at this tag;
  `Last verified` stays at 1.5.x. The release is largely security fixes: Guzzle
  and phpseclib raised to patched releases, CalDAV SSRF hardening, login
  throttling restored, a CAPTCHA bypass, REST API role and protected-settings
  checks, HTML escaping on the booking page. CORS and cookie `SameSite` settings
  move from the root `config.php` into `application/config/` — this stack mounts
  no config file, so nothing carries over. Whether `1.6.1` needs the database
  wizard is not stated; the release shows a message when the database needs
  updating, so open the UI after the pull.

## Upgrade checklist

Easy!Appointments has a slower, more predictable release cadence than Cal.com. Check [releases](https://github.com/alextselegidis/easyappointments/releases) every few months.

1. Back up:

   ```bash
   docker compose exec db sh -c \
     'mariadb-dump -u root -p"$(cat /run/secrets/DB_ROOT_PWD)" easyappointments' \
     > easyappointments-$(date +%Y%m%d).sql
   tar czf easyappointments-storage-$(date +%Y%m%d).tgz volumes/storage/
   ```

2. Bump `APP_TAG` in `.env`
3. `docker compose pull && docker compose up -d`
4. Visit the UI — EA runs schema migrations through a web wizard on first request after a major version bump
5. Verify: log in, open an existing appointment, create a test booking, check email notification

### Rollback

Restore DB dump and `volumes/storage/`, revert `APP_TAG`. Downgrade across major versions requires the SQL dump.

## Useful commands

```bash
# Shell into the app
docker compose exec app bash

# Manual DB backup
docker compose exec db sh -c \
  'mariadb-dump -u root -p"$(cat /run/secrets/DB_ROOT_PWD)" easyappointments' > dump.sql

# Restore DB
cat dump.sql | docker compose exec -T db sh -c \
  'mariadb -u root -p"$(cat /run/secrets/DB_ROOT_PWD)" easyappointments'
```

## Why this app is in the blueprint

The `apps/calcom/` + `apps/caldiy/` pair sits on a heavy Next.js stack with ongoing licence uncertainty (commercial vs MIT-community split in 2026). Easy!Appointments is the honest "boring-PHP alternative" — fewer features, but unambiguous GPL-3.0, one codebase, one project maintainer, a 13-year track record. For small businesses that just need "customers book a 30-minute slot", it's arguably the pragmatic pick.
