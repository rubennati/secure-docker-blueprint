# Upstream Reference

## Source

- **Image:** https://github.com/shlinkio/shlink/pkgs/container/shlink
- **GitHub:** https://github.com/shlinkio/shlink
- **Docs:** https://shlink.io/documentation/
- **License:** MIT
- **Decision facts checked:** 2026-09-23
- **Use restrictions:** none — https://github.com/shlinkio/shlink/blob/main/LICENSE · checked 2026-09-23
- **Origin:** Spain · Alejandro Celaya · EU
- **Domain:** Publishing, forms and scheduling
- **Role:** URL shortener on your own domain with visit statistics and a REST API; no user accounts, API keys instead
- **Based on version:** `5.1.7`

## What we use

- `ghcr.io/shlinkio/shlink:5.1.7` — the server, RoadRunner with PHP workers.
- `ghcr.io/shlinkio/shlink-web-client:4.8.1` — the browser interface, static
  files behind nginx. Optional; the API works without it.
- `postgres:18.6-alpine`. Shlink's own default is SQLite, which upstream states
  is not supported for production.

## What we changed and why

| Change | Reason |
|--------|--------|
| Three routers instead of one published port | The short links, the REST API and the browser interface have different audiences. Traefik matches the longer rule first, so `/rest` keeps its own access policy even when the redirects are opened |
| `APP_TRAEFIK_ACCESS=acc-private` on the redirects | Every stack here ships restricted. A short link is meant to be followed, so this is the one value an operator decides deliberately — the README says what opening it accepts |
| `AUTO_RESOLVE_TITLES: "false"` | Upstream's default is `true`, which makes the server fetch every long URL that is shortened to read its `<title>` — an outbound request to an address the caller chose |
| `SKIP_INITIAL_GEOLITE_DOWNLOAD: "true"` | Without a MaxMind licence key the download cannot succeed; skipping it keeps the start clean. Set a key and remove this to geolocate visits |
| `ANONYMIZE_REMOTE_ADDR: "true"`, `TRUSTED_PROXIES` | Upstream's default restated, and the proxy named so a visit records the visitor rather than Traefik |
| `INITIAL_API_KEY_FILE`, `DB_PASSWORD_FILE` | Every Shlink variable has a `_FILE` counterpart, resolved by the image's entrypoint through its own CLI before the server starts |
| No `SHLINK_SERVER_URL` / `SHLINK_SERVER_API_KEY` on the client | Those bake the server and an API key into the configuration the client serves; upstream warns the key can then be read by anyone who loads the page. The server is added in the browser instead |
| `PGDATA: /var/lib/postgresql/data` on the database | PostgreSQL 18 keeps its cluster under `/var/lib/postgresql/<major>` and refuses to start when a volume sits on the old path. Same pattern as `apps/defectdojo` |
| `read_only: true`, `cap_drop: ALL`, `tmpfs: /tmp` on all three | Verified; the server writes only its data volume, and every nginx path in the client image points below `/tmp` |
| No `user:` lines | The images already run as uid 1001 (server) and uid 101 (client). `./volumes/data` has to belong to 1001 |
| Client healthcheck with `curl` | The image carries `curl` and `wget` but no `bash`, so the `/dev/tcp` pattern used elsewhere in this repository does not apply here |

## Verified on the images (2026-09-23)

Not a host verification: this ran the stack's own `docker-compose.local.yml`,
without Traefik and without TLS.

- All three containers healthy with `read_only`, `cap_drop: ALL` and
  `no-new-privileges`; the server as uid 1001, the client as uid 101.
- Without `chown 1001:1001` on `./volumes/data` the server restart-loops with
  `mkdir: can't create directory 'data/cache': Permission denied` — which is why
  the README and `.env.example` both name that step.
- `INITIAL_API_KEY_FILE` and `DB_PASSWORD_FILE` took effect: the key from the
  file created a short URL, and the server reached PostgreSQL 18.6.
- `/rest/health` returned `{"status":"pass","version":"5.1.7"}`; `/rest/v3/short-urls`
  without a key returned 401.
- A short URL created over the API redirected with 302 to its long URL, and the
  visit was recorded — one visit, with no location, since no GeoLite database is
  downloaded.
- `bin/cli api-key:generate --name ci --author-only` created a key limited to
  the links it authors.
- Idle memory right after the first start: server 455 MiB, database 78 MiB,
  client 7 MiB. The server's ceiling was raised to 1 GiB because of it.

What a host run still has to establish: the three routers behind Traefik with
TLS, a refused client on the API router while a redirect still works, the
first-load request count for the web client, a restart, and the restore in the
README.

## Upgrade checklist

1. Read the release notes — https://github.com/shlinkio/shlink/releases and
   https://github.com/shlinkio/shlink-web-client/releases
2. Raise `APP_TAG`, `CLIENT_TAG` in `.env` and in `.env.local.example`
3. `docker compose pull && docker compose up -d`
4. `docker compose logs shlink-app` — the installer runs migrations, then
   `RoadRunner server started`
5. Follow an existing short link, create one over the API, and open the client
6. Record the result in `Last verified` once it ran behind Traefik

## Diff against upstream

```bash
# Upstream's compose example
curl -s https://raw.githubusercontent.com/shlinkio/shlink/main/docker-compose.yml

# The environment variables this version reads, with their defaults
docker run --rm --entrypoint sh ghcr.io/shlinkio/shlink:5.1.7 -c \
  'grep -rhoE "^ *case [A-Z_]+" $(grep -rl "enum EnvVars" module | head -1)'
```
