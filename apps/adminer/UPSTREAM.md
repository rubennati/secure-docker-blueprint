# Upstream Reference

## Source

- **Image:** https://hub.docker.com/_/adminer
- **Project home:** https://www.adminer.org/
- **GitHub:** https://github.com/vrana/adminer
- **License:** Apache-2.0
- **Decision facts checked:** not yet
- **Origin:** Czech Republic · Jakub Vrána · EU
- **Domain:** Developer tools
- **Role:** Web interface onto a database another stack already runs
- **Based on version:** `6.3.0` (standalone variant)
- **Last verified:** 2026-05-02 (v4.8.1-standalone)

## What we use

- Official `adminer` image, `6.3.0-standalone` tag (pure Adminer — no bundled web server stack)
- No database — Adminer connects to external DBs
- Blueprint-standard Traefik routing + Docker network model

## What we changed and why

| Change | Reason |
|--------|--------|
| No bundled MariaDB in the compose | Adminer's canonical use-case is managing existing app databases (wordpress-db, ghost-db, etc.). Bundling a MariaDB makes it a development-only fixture. Dropped; the README describes how to add one back for local work. |
| Traefik labels instead of host port mapping | Consistent with the rest of the blueprint. Original inbox used `ports: "8014:8080"`. |
| `security_opt: no-new-privileges` | Blueprint baseline. |
| Access defaults to `access-vpn` | Admin-access tools must never be publicly reachable by default. |
| Rate limit defaults to `limit-strict` | 20 per second, burst 40, against credential-stuffing on the DB-login form; headers `headers-standard`. |
| Exact `<version>-standalone` tag instead of `latest` | Reproducible; other variants (`fastcgi`, `4-fastcgi`) are less useful behind Traefik. |

## Upgrade checklist

Adminer moves in minor versions within a major line (`6.1.x` → `6.2.x`); Adminer releases no fixes on an older major line once the next one is out.

1. Check [GitHub releases](https://github.com/vrana/adminer/releases) for notes on deprecated drivers
2. Bump `APP_TAG` in `.env`
3. `docker compose pull && docker compose up -d`
4. Verify login still works against one known DB

No DB migrations, no data to back up — Adminer is stateless.

## Version / tag notes

- Moved to `6.3.0-standalone` on 2026-11-05 (released 2026-11-03), from
  `5.5.1-standalone` across 6.0.0–6.2.0, not run on a host at this tag. The 5.x line
  ends at `5.5.1`: no newer 5.x image exists, and the current pin carries a CRITICAL
  image finding. The hold of 2026-09-13 ends: 6.0.2 shipped the four fixes of
  2026-09-07 (GHSA-rwxg-xph9-82cj server-name check, a regression from 5.5.1;
  GHSA-7c5h-q78c-fpxx connection-id XSS; GHSA-77qq-q8fv-x45v ClickHouse and
  GHSA-q8h3-4cx4-prgm Elasticsearch response reflection), and every later 6.x
  release carries them. 6.1.1 adds GHSA-r9r5-j5q8-8c59 (SQLite `ATTACH`/`VACUUM INTO`
  behind a BOM); 6.3.0 restores the CSRF check on a login posted along with a request,
  a regression from 6.0.1. Image packaging is unchanged between the two lines
  (`php:8.4-alpine`, user `adminer`, `php -S [::]:8080`, same entrypoint,
  `ADMINER_DESIGN`, `ADMINER_DEFAULT_SERVER` and `ADMINER_PLUGINS`), and the
  `pepa-linha` design still ships, so the compose and its hardening stay as they are.
  Behaviour changes to know: 6.0.0 refuses servers that accept any password (for
  example PostgreSQL with `trust` authentication), removes the plugins `edit-calendar`,
  `tinymce`, `json-column`, `pretty-json-column`, `translation`, `email-table`,
  `dump-php` and `master-slave`, and needs an ES6 browser; 6.0.1 sends the session
  cookie `SameSite=lax` and checks the CSRF token on login, and renames the
  Elasticsearch database `elastic` to `data`; 6.1.0 shows Oracle schemas as databases
  instead of tablespaces; 6.2.0 drops the InterBase extension for PDO_Firebird; 6.3.0
  drops found-rows timeouts for MySQL < 5.7.8 and MariaDB < 10.1.2. Login throttling
  counts the proxy's address behind Traefik, as before; 6.0.0 suggests the
  `login-reverse-proxy` plugin for that case, not enabled here. No data or migration:
  Adminer is stateless. Sources:
  https://github.com/vrana/adminer/blob/master/CHANGELOG.md ,
  https://github.com/TimWolla/docker-adminer/tree/master/6

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
