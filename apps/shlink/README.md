# Shlink

A URL shortener you run yourself: short links on your own domain, visit
statistics, tags, QR codes, and a REST API that everything else drives. There
are no user accounts — the API takes keys.
Upstream: [shlinkio/shlink](https://github.com/shlinkio/shlink).

## Architecture

```text
Whoever follows a link ──────→ Traefik (TLS) ─┬─→ app :8080   (redirects)
Operator, scripts, the client ─→ /rest ────────┘        │
                                                        │
Operator's browser ──────────→ Traefik (TLS) ──→ client :8080 (static files)
                                                        │
                                              PostgreSQL (links, visits, keys)
```

Three routers on two host names, and that split is the point:

| Router | Serves | Ships as |
|---|---|---|
| `<project>` | the short links themselves | `acc-private` — **the one to open**, see below |
| `<project>-api` | `/rest`, which creates, edits and deletes links and reads visits | `acc-tailscale` |
| `<project>-client` | the browser interface on its own host name | `acc-tailscale` |

Traefik matches the longer rule first, so `/rest` lands on the API router even
when the redirect router is opened to everyone.

## Try it locally

Runs on `http://localhost:8080` (links and API) and `http://localhost:8081`
(the web client), without Traefik, DNS or a certificate.

```bash
cp .env.local.example .env.local
mkdir -p .secrets volumes/data volumes/postgres
openssl rand -hex 32 | tr -d '\n' > .secrets/db_pwd.txt
openssl rand -hex 32 | tr -d '\n' > .secrets/initial_api_key.txt
sudo chown -R 1001:1001 volumes/data
docker compose -f docker-compose.local.yml --env-file .env.local up -d
# http://localhost:8081 — add http://localhost:8080 as the server, with that key
docker compose -f docker-compose.local.yml --env-file .env.local down
```

## Setup

```bash
cp .env.example .env                      # the short domain, the client host
mkdir -p .secrets volumes/data volumes/postgres
openssl rand -hex 32 | tr -d '\n' > .secrets/db_pwd.txt
openssl rand -hex 32 | tr -d '\n' > .secrets/initial_api_key.txt
sudo chown -R 1001:1001 volumes/data      # the server image runs as uid 1001
docker compose up -d
docker compose logs shlink-app --follow   # watch for: RoadRunner server started
```

`INITIAL_API_KEY` is read on the first start only. It has no roles, which in
Shlink means it may do everything — treat it as the administrator credential,
and create narrower keys for anything that only creates links:

```bash
# --author-only: the key may manage the links it created, and nothing else
docker compose exec shlink-app bin/cli api-key:generate --name ci --author-only
```

`bin/cli api-key:list` shows what exists, with its roles.

Creating a link, and following it:

```bash
curl -X POST https://s.example.com/rest/v3/short-urls \
  -H "X-Api-Key: $SHLINK_API_KEY" -H "Content-Type: application/json" \
  -d '{"longUrl":"https://example.com/a-very-long-address","customSlug":"abc"}'

curl -I https://s.example.com/abc      # 302, Location: the long URL
```

## Deciding what is public

A short link nobody outside can follow is a link that does not work, so this is
a decision rather than a default. The stack ships `acc-private` on the redirect
router, and opening it means accepting three things:

- **A redirect is unauthenticated by design.** Anyone holding the URL follows
  it; there is no account in front of it and there cannot be.
- **The link list is not secret either way.** Slugs are short, so a slug is
  guessable — Shlink can generate longer ones, and `ROBOTS_ALLOW_ALL_SHORT_URLS`
  stays off so crawlers are not invited.
- **`/rest` and the client stay where they are.** They are separate routers with
  their own policies, and opening the redirects does not move them.

`AUTO_RESOLVE_TITLES` is off in this stack. With it on, the server fetches every
long URL that is shortened, to read its `<title>` — which turns "create a short
link" into "this host makes a request to an address the caller chose".

## Visits and privacy

`ANONYMIZE_REMOTE_ADDR` is on, upstream's default: the visitor's address is
truncated before it is stored. Geolocation needs a free MaxMind licence key;
without one `SKIP_INITIAL_GEOLITE_DOWNLOAD` keeps the download from being
attempted and visits are simply not located. `TRUSTED_PROXIES` names Traefik, so
a visit records the visitor rather than the proxy.

## The web client

It is static files in the browser. Adding a server there stores its URL and the
API key in that browser's local storage, so it is only as private as the device.
This stack deliberately does **not** set `SHLINK_SERVER_URL` and
`SHLINK_SERVER_API_KEY`: those bake the key into the configuration the container
serves, and upstream warns it can then be read by anyone who loads the page.

## Known limits

- **The rate limit is not measured.** The chain ships `sec-2` for all three
  routers. A redirect is one request; the client is a small bundle. Neither has
  been measured behind Traefik.
- **The initial key cannot be rotated in place.** Generate a new key with the
  CLI and disable the old one (`bin/cli api-key:disable`).
- **Nothing here has run behind Traefik yet.** The stack is `scaffolded`: the
  hardening, the API, a redirect and the visit record were verified on the
  images, the routes were not.

## Backup

| | |
|---|---|
| **Database** | PostgreSQL · container `shlink-db` · database `shlink` · user `shlink` — short URLs, visits, tags, API keys |
| **Password** | `.secrets/db_pwd.txt` |
| **State** | Nothing outside the database. `./volumes/data` holds cache, locks and logs |
| **Reproducible** | `./volumes/data` in full, and the GeoLite database if one was downloaded |
| **Quiescing** | Not needed: dump the database rather than copying its files |

```yaml
# /etc/borgmatic/config.yaml
postgresql_databases:
  - name: shlink
    container: shlink-db
    username: shlink
    password: "${SHLINK_DB_PASSWORD}"
```

Restore: the database alone brings back every link, visit and key. Keep
`.secrets/initial_api_key.txt` with it — the key's hash is in the database, and
the plain value exists nowhere else.
