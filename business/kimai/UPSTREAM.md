# Upstream Reference

## Source

- **Project:** https://www.kimai.org
- **GitHub:** https://github.com/kimai/kimai
- **Docker Hub:** https://hub.docker.com/r/kimai/kimai2
- **License:** AGPL-3.0
- **Edition gating:** audit trail logs, which record changes to timesheets, customers, projects and activities, are a paid store plugin rather than part of the AGPL core; paid plugins are annual subscriptions with a perpetual fallback licence, so the last downloaded version keeps working while updates need an active subscription — https://www.kimai.org/store/audit-trail-bundle.html · checked 2026-09-21
- **Commercial model:** paid add-on — https://www.kimai.org/store/audit-trail-bundle.html · checked 2026-09-21
- **Decision facts checked:** 2026-09-21
- **Origin:** Germany · Kevin Papst · EU
- **Domain:** Business operations
- **Role:** Time tracking with reports and invoicing hooks
- **Based on version:** `2.71.0` (see Version / tag notes — the `apache-` prefix is gone)
- **Last verified:** 2026-11-03 (2.66.0) — step 8 lab host behind Traefik 3.7.17 on its edge network: login, customer, project, activity and a timesheet through the API, a `ROLE_USER` refused the admin's data, and the README's borgmatic entry restored into a throwaway instance (docs/labs/ingress/2026-11-01-results.md). Earlier: 2026-05-03 (Last checked)

## What we use

- Official `kimai/kimai2` image (`apache` variant — includes built-in Apache server)
- MariaDB as backing database
- Docker Secrets for database password
- Traefik labels for HTTPS routing

## What we changed vs. upstream examples

| Change from upstream | Reason |
|---|---|
| **Traefik labels instead of `-p` port mapping** | Blueprint routing standard |
| **Docker Secrets for `DATABASE_URL` password** | Security baseline — no credentials in env |
| **`security_opt: no-new-privileges:true`** | Baseline hardening |
| **Healthcheck on `/api/ping`** | Proper readiness gate |

## Version / tag notes

- **Upstream dropped the `apache-` tag prefix.** The pin was `apache-2.61.0`, which no
  longer resolves — Docker Hub answers 404, so `docker compose pull` fails on it. The
  newest prefixed tag is `apache-2.57.0` (2026-05-21); everything after that is published
  as a bare semver tag. `2.66.0` and `apache` carry the same digest, so the bare tag is
  the Apache variant this stack expects. Corrected on 2026-09-13.
- Moved to `2.71.0` on 2026-11-05, not run on a host at this tag. 2.71.0 deactivates
  the long-deprecated API passwords (breaking, #6267): API clients must use API tokens,
  the `X-AUTH-USER` / `X-AUTH-TOKEN` password pair no longer authenticates. It also
  converts user roles from `Types::ARRAY` to JSON, a migration the entrypoint applies at
  start. 2.68.0 disables password reset when `TRUSTED_HOSTS` is unset (this stack sets
  it); 2.70.0 matches a bare host name in `TRUSTED_HOSTS` anchored, against the host and
  its subdomains, where Symfony matched it as an unanchored regex before (#6246); 2.68.0
  makes the invoice payment date in the API a date instead of a date-time. Security
  fixes: 2.68.0 (team ACL and teamlead permission checks, timesheet batch-update and
  PATCH authorization, 2FA on remember-me accounts, wizard skips, password-reset flags,
  entrypoint debug tracing removed), 2.70.0 (internal preferences via the API,
  password-change wizard skip, sessions ended on password reset, 2FA activation by
  another user, `TRUSTED_HOSTS` parsing), 2.70.1 (images rebuilt on fixed PHP versions
  after the October 2026 PHP security release). No GHSA or CVE IDs are listed in the
  notes.

## Upgrade checklist

1. Check [Kimai releases](https://github.com/kimai/kimai/releases) — the image tag is a bare
   `X.Y.Z` and carries the Apache variant; the older `apache-X.Y.Z` form stopped at `apache-2.57.0`
2. Back up:

   ```bash
   docker compose exec db mysqldump -u ${DB_USER} -p kimai > kimai-$(date +%Y%m%d).sql
   ```

3. Bump `APP_TAG` in `.env`
4. `docker compose pull && docker compose up -d`
5. Watch logs for DB migrations:

   ```bash
   docker compose logs app --follow
   ```

6. Verify: log in, create a timesheet entry, generate a report

## Useful commands

```bash
# Reload environment (after .env changes)
docker compose exec app bin/console kimai:reload --env=prod

# Run migrations manually (if automatic migration fails)
docker compose exec app bin/console doctrine:migrations:migrate --env=prod

# Create an admin user
docker compose exec app bin/console kimai:user:create admin admin@example.com ROLE_SUPER_ADMIN
```
