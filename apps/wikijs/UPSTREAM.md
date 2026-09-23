# Upstream Reference

## Source

- **Image:** https://github.com/requarks/wiki/pkgs/container/wiki
- **GitHub:** https://github.com/requarks/wiki
- **Docs:** https://docs.requarks.io/
- **License:** AGPL-3.0
- **Decision facts checked:** 2026-09-23
- **Use restrictions:** none — https://github.com/requarks/wiki/blob/main/LICENSE · checked 2026-09-23
- **Origin:** Canada · Requarks · non-EU
- **Domain:** Files, wiki and collaboration
- **Role:** Wiki with Markdown and visual editors, per-page permissions and about twenty authentication modules
- **Based on version:** `2.5.315`

## Which version line, and why it matters

2.5 receives security fixes — 2.5.315 is from 2026-09-21 — while development
runs on 3.0, which is in beta and whose release notes say it is not for
production. Upstream's documentation lists the 2.x upgrade path as coming soon,
so a migration is ahead rather than optional.

Two consequences this stack takes now:

- **PostgreSQL**, although 2.5 also accepts MySQL, MariaDB, MSSQL and SQLite.
  3.0 supports PostgreSQL only, and upstream's own documentation says the other
  engines will not be supported in the next major version.
- **`DB_PASS_FILE` stays the only secret from a file.** In the 3.0 beta the
  variable is present but marked in the source as never taking effect, so a
  migration has to re-check how the password reaches the application.

## What we use

- `ghcr.io/requarks/wiki:2.5.315` — upstream's own registry rather than the
  Docker Hub copy of the same image.
- `postgres:18.6-alpine` for the database.
- Two containers. Pages, users and settings live in the database; the data
  volume holds caches, upload staging and the optional Git content mirror.

## What we changed and why

| Change | Reason |
|--------|--------|
| `PGDATA: /var/lib/postgresql/data` on the database | PostgreSQL 18 keeps its cluster under `/var/lib/postgresql/<major>` and refuses to start when a volume sits on the old path. Measured here: without it the container restart-loops with "there appears to be PostgreSQL data in /var/lib/postgresql/data (unused mount/volume)". Same pattern as `apps/defectdojo` |
| `DB_PASS_FILE` instead of `DB_PASS` | Wiki.js reads the file itself and trims it, so no wrapper is needed and no password reaches `docker inspect` |
| `SSL_ACTIVE: "false"` | Traefik terminates TLS. Left on, Wiki.js would try to obtain its own certificate |
| `read_only: true`, `cap_drop: ALL`, `tmpfs: /tmp` | Verified against 2.5.315; only `/tmp` and the data volume are written |
| No `user:` line | The image already runs as uid 1000 (`node`); `./volumes/data` has to belong to that uid |
| Healthcheck on `/healthz` | The endpoint answers without a session, and `curl` is in the image. The image ships no healthcheck of its own |
| `APP_TRAEFIK_ACCESS=acc-tailscale` | The first request opens a setup wizard with no password in front of it, and whoever completes it becomes the administrator |
| Database on `app-internal` (`internal: true`) | The baseline's network rule: a datastore has no route out and none in from other stacks |

## Verified on the image (2026-09-23)

Not a host verification: this ran the stack's own `docker-compose.local.yml`,
without Traefik and without TLS.

- Both containers healthy with `read_only`, `cap_drop: ALL`,
  `no-new-privileges`, the application as uid 1000.
- `DB_PASS_FILE` took effect — the application connected to PostgreSQL 18.6 and
  ran its migrations.
- The setup wizard completed over its own endpoint and created the
  administrator; the home page then answered 200.
- A login through the GraphQL API returned a session token.
- Idle memory right after setup: application 241 MiB, database 103 MiB.
- The setup bundle carries `telemetry: true`, so the checkbox in the wizard is
  ticked unless the operator unticks it.

What a host run still has to establish: the route behind Traefik with TLS, a
refused client outside the access policy, the first-load request count against
the rate limit, a restart, and the restore in the README.

## Upgrade checklist

1. Read the release notes — https://github.com/requarks/wiki/releases
2. Raise `APP_TAG` in `.env` and in `.env.local.example`
3. `docker compose pull && docker compose up -d`
4. `docker compose logs wikijs-app` — migrations first, then `HTTP Server: [ RUNNING ]`
5. Sign in, open a page, edit it, and check *Administration → System Info*
6. Record the result in `Last verified` once it ran behind Traefik

**Before 3.0:** it is a different application with its own database schema and
its own configuration model. Treat it as a migration with a restore path, not as
a tag bump, and re-check `DB_PASS_FILE` first.

## Diff against upstream

```bash
# Upstream's compose example
curl -s https://raw.githubusercontent.com/requarks/wiki/main/dev/examples/docker-compose.yml

# The configuration template the image ships, with its env placeholders
docker run --rm ghcr.io/requarks/wiki:2.5.315 cat /wiki/config.yml
```
