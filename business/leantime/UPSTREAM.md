# Upstream Reference

- **Last verified:** 2026-11-08 (3.13.2) — lab host (VM), IPv4 LAN, run in a parallel batch: the installer served through the route before and after `down`/`up`, the refused client answered `403`; the installer was not driven (docs/labs/stack-refresh/2026-11-08-results.md)

## Source

- **Image:** https://hub.docker.com/r/leantime/leantime
- **GitHub:** https://github.com/leantime/leantime
- **Docs:** https://docs.leantime.io
- **License:** AGPL-3.0
- **Use restrictions:** none — https://github.com/leantime/leantime/blob/master/LICENSE · checked 2026-09-23
- **Edition gating:** the platform itself is open source and free; advanced functionality is sold as marketplace plugins, for the self-hosted version as well as the hosted one, and a plugin licence is perpetual with one year of updates — https://leantime.io/pricing/ · checked 2026-09-23
- **Commercial model:** paid add-on — https://leantime.io/pricing/ · checked 2026-09-23
- **Decision facts checked:** 2026-09-23
- **Origin:** US · Leantime, Inc. · non-EU
- **Domain:** Business operations
- **Role:** Project management for teams that do not have a project manager —
  projects, milestones, tasks, time tracking, retrospectives and goals

## Project maturity

11 642 stars, pushed 2026-09-07, release 3.9.8 on 2026-07-08. Past 3.0 and on a
regular patch cadence.

## What we use

- `leantime/leantime:3.13.2`, one container. Inside it supervisord runs three
  programs: nginx on 8080, php-fpm on 127.0.0.1:9000, and
  `bin/leantime schedule:work` — the scheduler that sends notifications and the
  daily digest. It is not optional.
- `mysql:9.7.4`, the current LTS line. Leantime requires MySQL 8.0 or newer;
  upstream's own compose example ships `mysql:8.4.13`; the MariaDB the other stacks here run
  is not a tested substitute.

**Single sign-on is in the AGPL core**, not behind the marketplace: OIDC
(`LEAN_OIDC_*`) and LDAP (`LEAN_LDAP_*`) are configuration, and
`app/Domain/Oidc/` ships in the image. Neither is exercised here.

## What we changed and why

| Change | Reason |
|--------|--------|
| The schema is created by `ops/install.sh`, not by the web installer | `/install` creates the first account — the owner — from an unauthenticated form. Making that the command line's job means the window never exists on a routed host name |
| `LEAN_ALLOW_TELEMETRY=false` | Upstream's default is `true`. Measured below |
| `LEAN_NEWS_ENABLED=false` | Pulls an RSS feed from leantime.io on its own. The variable is upstream's own answer for air-gapped installations |
| `LEAN_LOG_CHANNELS=stderr` | The default writes `storage/logs/error.log` inside the volume. Upstream documents `stderr` for containers |
| `LEAN_SESSION_SECURE=true` | Otherwise it is auto-detected, and TLS ends at Traefik |
| `LEAN_SESSION_PASSWORD_FILE` | Upstream's sample configuration ships a fixed session salt. Ours is a Docker Secret |
| `read_only: true`, `cap_drop: ALL`, `no-new-privileges` | Upstream's compose example adds CHOWN, SETGID and SETUID and mounts nothing read-only. None of it is needed: the image already runs as www-data and four bind mounts plus four tmpfs cover every path it writes |
| tmpfs on `/var/www/html/bootstrap/cache` | Laravel's package manifest. Without it the framework refuses to boot at all — measured, in both the web process and `bin/leantime` |
| No `ports:` | Upstream publishes 8080 to the host. Traefik reaches the container over the proxy network instead |
| `APP_TRAEFIK_ACCESS=access-vpn` | A project management instance holds the customer names, rates and deadlines of everything the company runs |

## Verified on the image (2026-09-23)

Not a host verification: this ran the stack's own files with a throwaway
network and no Traefik router.

- `ops/init.sh` → `docker compose up -d leantime-db` → the install command →
  `docker compose up -d`: 37 tables, one user with role 50 (owner), and the
  application healthy as www-data under `read_only`, `cap_drop: ALL` and
  `no-new-privileges`. No "read-only file system" in the logs, before or after
  a restart.
- **`db:install` does not exist as a command.** The source declares it as an
  alias of `db:migrate`, but Laravel registers the command under its name only
  and answers `db:install` with "Command not defined". `ops/install.sh` calls
  `db:migrate`.
- **`/start.sh` ignores its arguments** — it always execs supervisord — so a
  one-off CLI container has to resolve the `LEAN_*_FILE` variables itself. The
  same trap as `apps/calrs` and `backup/kopia`, in a different shape.
- **The installer stays reachable after installation.** `Install\Controllers\
  Index::init()` returns a redirect when the instance is installed, but
  `Controller::__construct` calls `app()->call([$this, 'init'])` and discards
  the return value, so the form is served anyway. Measured: `GET /install`
  answers 200 on an installed instance.
- **It cannot be used to take over an installed instance.** A POST to that form
  aborts in `SchemaBuilder::createCalendarTable()` because the table exists, and
  creates nothing — the user table was unchanged afterwards. On an *empty*
  database the same POST does create the owner and hand out an invite link,
  which is exactly why the schema is created from the command line first.
- **Telemetry.** `LEAN_ALLOW_TELEMETRY` is the name the configuration loader
  derives for `DefaultConfig::$allowTelemetry` (`'LEAN_'.Str::of($prop)
  ->snake()->upper()`), confirmed by running that expression on the image.
  Reading the effective configuration: unset → `true`, `=false` → `false`.
  Upstream posts to `https://telemetry.leantime.io` once a day from the
  scheduler when it is on.
- Session cookie on the login page: `secure; httponly; samesite=lax`.
- `/api/jsonrpc` answers 401 without credentials.
- Idle memory: application 131 MiB, database 478 MiB anonymous plus 214 MiB
  reclaimable page cache.

What a host run still has to establish: the route through `core/traefik`,
`limit-standard` against the application's own pages, a mail path for the
notifications the scheduler sends, and a restore from the volumes below.

## Version notes

- Moved to `3.13.2` on 2026-11-05, not run on a host at this tag. Database
  migrations in 3.12 (db version 3.5.30, merges duplicate plugin rows) and 3.13 (db
  version 3.5.33: a `metadata` column on projects for per-project modules, a separate
  key and base role for roles, the new permissions granted to existing roles). The
  image does not apply them by itself: run checklist step 4, or confirm the database
  update screen as an admin. 3.13 runs on Laravel 12 and the image moves to PHP 8.4
  with the `intl` extension; paths, ports and the `www-data` uid are unchanged.
  Plugins live in `./volumes/plugins`, which hides the plugins bundled in the image:
  installed ones must be updated by hand after the core — McpServer to 2.0 (core now
  ships laravel/mcp 1.x), and CustomFields, Notes, PgmPro, StrategyPro and Whiteboards
  to their 3.13 releases. 3.10.1 runs PHP in UTC; timestamps written before in a
  non-UTC timezone may display shifted. 3.10.2 signs everyone out once and invalidates
  earlier password-reset links, requires `LEAN_APP_URL` behind a proxy that rewrites
  the Host header (set here), trusts only private-network proxies by default (Docker
  networks qualify) and adds an origin check on state-changing requests
  (`LEAN_CSRF_ORIGIN_CHECK`) and rate limits (`LEAN_RATELIMIT_PASSWORD_RESET`,
  `LEAN_RATELIMIT_TWOFA`). 3.10.3 runs plugin scheduled jobs from cron, so expect a
  catch-up on the first scheduler run, and adds `GET /health`. 3.13.2 reports
  marketplace install results with the PHP, OpenSSL and OS versions to the
  marketplace. Security fixes: 3.10.2 (password-reset tokens, session rotation, rate
  limits, OIDC token validation, API role escalation, project-scoped authorization,
  file module, outbound webhook and calendar requests, CSRF), 3.10.3 (email links from
  a trusted app URL instead of the Host header, escaped theme CSS). No CVE or GHSA IDs
  are listed in the notes.
- Moved `mysql` from `8.4.11` to `9.7.4` (the newest LTS line) on 2026-11-05,
  not run on a host at this tag. Leantime requires "MySQL 8.0+ or MariaDB 10.6+"
  with no upper bound (https://github.com/Leantime/leantime); upstream's
  docker-leantime compose still ships `mysql:8.4`. MySQL upgrades in place from
  one LTS line to the next: the 9.7 server upgrades the data dictionary and
  system tables in `./volumes/mysql` at its first start. 9.x no longer has
  `mysql_native_password`; the accounts the 8.4 image created use
  `caching_sha2_password`, which `SELECT user, plugin FROM mysql.user;` confirms
  before the move. Take the `mysqldump` before the tag changes: going back to
  8.4 is only a restore of that dump.

## Upgrade checklist

1. Read the release notes — https://github.com/leantime/leantime/releases
2. Raise `APP_TAG` in `.env` and in `.env.local.example`
3. `docker compose pull && docker compose up -d`
4. Run the migrations: `ops/install.sh` — on a populated database `db:migrate`
   applies what is pending and creates nothing
5. `docker compose logs leantime-app` — no stack traces; check the scheduler
   process is up
6. Record the result in `Last verified` once it ran behind `core/traefik`

## Diff against upstream

```bash
# Upstream's own compose example — published port, no read_only, extra caps
curl -s https://raw.githubusercontent.com/leantime/leantime/master/.docker/docker-compose.yml

# Every setting the application knows, with upstream's defaults and comments
docker run --rm --entrypoint sh leantime/leantime:3.13.2 -c 'cat config/sample.env'
```
