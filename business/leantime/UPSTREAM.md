# Upstream Reference

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
- **Based on version:** `3.9.8`

## Project maturity

11 642 stars, pushed 2026-09-07, release 3.9.8 on 2026-07-08. Past 3.0 and on a
regular patch cadence.

## What we use

- `leantime/leantime:3.9.8`, one container. Inside it supervisord runs three
  programs: nginx on 8080, php-fpm on 127.0.0.1:9000, and
  `bin/leantime schedule:work` — the scheduler that sends notifications and the
  daily digest. It is not optional.
- `mysql:8.4.11`. Upstream's own compose example ships `mysql:8.4`, and the
  schema builder is written against it; the MariaDB the other stacks here run
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
| `APP_TRAEFIK_ACCESS=acc-tailscale` | A project management instance holds the customer names, rates and deadlines of everything the company runs |

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

What a host run still has to establish: the route through `core/traefik`, the
`sec-2` chain against the application's own pages, a mail path for the
notifications the scheduler sends, and a restore from the volumes below.

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
docker run --rm --entrypoint sh leantime/leantime:3.9.8 -c 'cat config/sample.env'
```
