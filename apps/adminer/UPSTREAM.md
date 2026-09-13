# Upstream Reference

## Source

- **Image:** https://hub.docker.com/_/adminer
- **Project home:** https://www.adminer.org/
- **GitHub:** https://github.com/vrana/adminer
- **License:** Apache-2.0
- **Origin:** Czech Republic · Jakub Vrána · EU
- **Based on version:** `5.5.1` (standalone variant)
- **Last verified:** 2026-05-02 (v4.8.1-standalone)

## What we use

- Official `adminer` image, `4.8.1-standalone` tag (pure Adminer — no bundled web server stack)
- No database — Adminer connects to external DBs
- Blueprint-standard Traefik routing + Docker network model

## What we changed and why

| Change | Reason |
|--------|--------|
| No bundled MariaDB in the compose | Adminer's canonical use-case is managing existing app databases (wordpress-db, ghost-db, etc.). Bundling a MariaDB makes it a development-only fixture. Dropped; the README describes how to add one back for local work. |
| Traefik labels instead of host port mapping | Consistent with the rest of the blueprint. Original inbox used `ports: "8014:8080"`. |
| `security_opt: no-new-privileges` | Blueprint baseline. |
| Access policy defaults to `acc-tailscale` | Admin-access tools must never be publicly reachable by default. |
| Security chain defaults to `sec-4` | Hard rate limiting against credential-stuffing on the DB-login form. |
| `4-standalone` tag instead of `latest` | Reproducible; other variants (`fastcgi`, `4-fastcgi`) are less useful behind Traefik. |

## Upgrade checklist

Adminer moves in minor versions (`4.8.x` → `4.9.x`). Major `5.x` not yet out as of 2026-04-17.

1. Check [GitHub releases](https://github.com/vrana/adminer/releases) for notes on deprecated drivers
2. Bump `APP_TAG` in `.env`
3. `docker compose pull && docker compose up -d`
4. Verify login still works against one known DB

No DB migrations, no data to back up — Adminer is stateless.

## Version / tag notes

- **Pinned to `5.5.1-standalone`, not to 6.x.** Four advisories published 2026-09-07 are
  fixed only in Adminer 6.0.2 — conditional RCE via a CONNECTION_ID XSS combined with
  `INTO DUMPFILE`, pre-authentication SSRF in the Elasticsearch plugin, the ClickHouse
  driver reflecting an arbitrary HTTP response body on the login page, and a
  privileged-port SSRF. **No 6.0.2 image exists**; Docker Hub's newest 6.x tag is
  `6.0.1-standalone`, which predates those fixes. One of the four is described as a
  regression introduced in 5.5.1, so 6.0.x is the affected line rather than the fixed one.
  `5.5.1` closes the advisory that applies to the 5.5.x line (GHSA-fr74-9mf9-gf44,
  X-Forwarded-Prefix backslash bypass). Re-check for a 6.0.2 image before moving to 6.x.
  Decided 2026-09-13.

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
