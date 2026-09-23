# Upstream Reference

## Source

- **Image:** https://hub.docker.com/r/brotandgames/ciao
- **GitHub:** https://github.com/brotandgames/ciao
- **Docs:** https://brotandgames.com/ciao/
- **License:** MIT
- **Decision facts checked:** 2026-09-23
- **Use restrictions:** none — https://github.com/brotandgames/ciao/blob/master/LICENSE · checked 2026-09-23
- **Origin:** Brot & Games · no country stated · no country
- **Domain:** Monitoring
- **Role:** HTTP checks on a cron schedule with a dashboard, webhook notifications and TLS expiry warnings
- **Based on version:** `1.10.1`

## Origin, stated precisely

The project publishes no imprint and the GitHub account states its location as
"Earth". **Origin** above records that rather than a guess.

## Project maturity

1 981 stars, 20 commits in the twelve months to 2026-07-16, newest release
1.10.1 on that date. One person wrote 263 of the commits and the next
contributor 7, so the project is effectively single-maintainer. The image is
published on Docker Hub only; there is no copy on another registry.

## What we use

- `brotandgames/ciao:1.10.1` — Ruby 4.0 and Rails 8.1, one container.
- SQLite in `/app/db/sqlite`, which is the image's own volume path. Upstream
  ships no database service and the application needs none.

## What we changed and why

| Change | Reason |
|--------|--------|
| `config/entrypoint.sh` exports `SECRET_KEY_BASE` from a Docker Secret | No `_FILE` variant exists. Left unset, `start.sh` generates a key on every start and voids every session the previous start handed out |
| The same wrapper exports the basic-auth, Prometheus and SMTP passwords | Same reason; each is optional and guarded, so an empty file leaves the feature off |
| `command: ["./start.sh"]` restated | Overriding `entrypoint` clears the image's `CMD`; without it the container has nothing to run |
| `tmpfs` with `mode=1777` on `/app/tmp`, `/app/log` and `/home/rails` | Under `read_only` Rails still writes its pid and caches. A tmpfs without the mode belongs to root, and the server died on `Permission denied @ dir_s_mkdir - /app/tmp/cache` as uid 1000. Measured 2026-09-23 |
| Healthcheck through Ruby | The image carries neither curl nor wget, and ciao has no unauthenticated health route. The check accepts the 401 that basic auth returns and fails from 500 upwards |
| `BASIC_AUTH_USERNAME` set in `.env.example` | With an empty user name ciao asks for no credentials at all — upstream's default. Its README says to put authentication in front before exposing it |
| `PROMETHEUS_ENABLED=false` | Upstream's default, restated because `/metrics` is served outside the application's basic auth and carries its own pair |
| `RAILS_LOG_TO_STDOUT=true` | One place to read the log, and nothing written into the read-only filesystem |
| No `user:` line | The image already runs as uid 1000 (`rails`); `./volumes/db` has to belong to that uid |
| `APP_TRAEFIK_ACCESS=acc-tailscale` | The dashboard lists every URL being watched and its history |

## Verified on the image (2026-09-23)

Not a host verification: this ran the stack's own `docker-compose.local.yml`,
without Traefik and without TLS.

- Started with `read_only`, `cap_drop: ALL`, `no-new-privileges` as uid 1000 and
  reported healthy; `Listening on http://0.0.0.0:3000`.
- Without the four tmpfs mounts the start failed — recorded above.
- `/` answered 401 without credentials and 200 with them.
- `/metrics` answered 404 with `PROMETHEUS_ENABLED=false`.
- A check created over the API appeared in the list, and survived a restart.
- Two checks ran on their cron expressions and recorded status 200 with a
  timestamp. The scheduler runs inside the web process (rufus-scheduler), and
  `config/initializers/create_background_jobs.rb` recreates the jobs of every
  active check at start, so no second container schedules anything.
- The data directory held `production.sqlite3` with its `-shm` and `-wal` files.

What a host run still has to establish: the route behind Traefik with TLS, a
refused client outside the access policy, a check actually firing on its cron
and a webhook arriving, and the restore in the README.

## Upgrade checklist

1. Read the release notes — https://github.com/brotandgames/ciao/releases
2. Raise `APP_TAG` in `.env` and in `.env.local.example`
3. `docker compose pull && docker compose up -d`
4. `docker compose logs ciao-app` — migrations run first, then `Listening on`
5. Sign in, confirm the existing checks are still listed and still run
6. Record the result in `Last verified` once it ran behind Traefik

## Diff against upstream

Upstream publishes no compose file in the repository; its deployment examples are
in the README and in `helm-chart/`.

```bash
# What the image sets by default — user, command, volume, port
docker image inspect brotandgames/ciao:1.10.1 --format '{{json .Config}}'

# The environment variables this version reads
docker run --rm --entrypoint sh brotandgames/ciao:1.10.1 -c \
  'grep -rhoE "ENV[.\[][\"'\'']?[A-Z_]+" /app/app /app/config /app/config.ru | sort -u'
```
