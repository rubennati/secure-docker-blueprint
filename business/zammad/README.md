# Zammad

Self-hosted helpdesk / ticketing / customer support. Multi-channel (email, web form, Twitter, Telegram, SMS), SLA tracking, time accounting, knowledge base.

Project, source, licence and origin: [`UPSTREAM.md`](UPSTREAM.md).

## Architecture

Heavy stack — 9 services. Upstream default deployment.

| Service | Image | Purpose |
|---------|-------|---------|
| `zammad-nginx` (= `app`) | `ghcr.io/zammad/zammad:${APP_TAG}` + `zammad-nginx` | Web gateway, static assets, reverse-proxy to rails + websocket |
| `railsserver` | same + `zammad-railsserver` | Rails app (API + core logic) |
| `websocket` | same + `zammad-websocket` | Agent live updates |
| `scheduler` | same + `zammad-scheduler` | Background jobs (email import, SLA checks) |
| `init` | same + `zammad-init` | One-shot DB migrations on every start |
| `db` | `postgres:18.6-alpine` | Primary data store |
| `redis` | `redis:8.10.3-alpine` | Background job queue |
| `memcached` | `memcached:1.6.45` | Rails cache |
| `elasticsearch` | `docker.elastic.co/elasticsearch/elasticsearch:9.5.6` | Full-text ticket search |

## Resource requirements

This is **not a lightweight stack**. Minimum for a live system:

- 4 GB RAM free (Elasticsearch alone grabs 512 MB heap)
- 2 CPU cores
- 10 GB disk for ES index + Postgres

On a small VPS, consider `ELASTICSEARCH_ENABLED=false` — tickets will still work, only full-text search is degraded.

## Try it locally

Runs on `http://localhost:8080` without Traefik, DNS or a certificate.

```bash
cp .env.local.example .env.local # fill the empty secrets
docker compose -f docker-compose.local.yml --env-file .env.local up -d
# http://localhost:8080
docker compose -f docker-compose.local.yml --env-file .env.local down
```

`.env.local` holds plain values, not Docker Secrets — local only.

## Setup

```bash
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, TZ

mkdir -p .secrets volumes/postgres volumes/redis volumes/elasticsearch volumes/zammad-storage
# Redis runs as the image's own user and cannot fix ownership itself
sudo chown 999:1000 volumes/redis
openssl rand -base64 32 | tr -d '\n' > .secrets/db_pwd.txt
sed -i "s|^DB_PWD_INLINE=.*|DB_PWD_INLINE=$(cat .secrets/db_pwd.txt)|" .env

# Elasticsearch needs vm.max_map_count
sudo sysctl -w vm.max_map_count=262144
# Persist:
echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.d/99-zammad.conf

docker compose up -d
# First boot runs migrations — takes 3-5 minutes
docker compose logs railsserver --follow
# Watch for: "* Listening on http://[::]:3000"

# https://<APP_TRAEFIK_HOST>
# Over the VPN: the first visit prompts the setup wizard — create the admin
# account and organization. The route ships closed (APP_TRAEFIK_ACCESS=access-vpn);
# open it afterwards for the customer web form
```

## Security Model

- **First-visit wizard creates the owner account** — until it has run (`/api/v1/getting_started` answers `setup_done: false` without authentication, measured on the lab host at 7.2.2), whoever opens the UI first becomes the owner. The route therefore ships at `access-vpn`: run the wizard over the VPN, then open it.
- **`DB_PWD_INLINE` duplicates the DB password** — Zammad reads `POSTGRESQL_PASS` from env only.
- **Elasticsearch has no auth here** — it's on `app-internal` only, not reachable from outside. If you move it off-host, add xpack.security.
- **`no-new-privileges:true`** on all services.
- **Default access `access-vpn` until the wizard has run, then `access-public`, with `limit-standard` and `headers-standard`** — customers submit tickets via public web form `/customer_ticket_new`; agents log in at `/#login`. For agent-only VPN access, see the two-router split pattern (see `business/listmonk/README.md` for the pattern).

## What it sends outward

Three vendor services are contacted as the application is used, not on a timer:
`images.zammad.com` for avatar and organisation lookups — which sends the
address or domain being looked up — and `geo.zammad.com` for location and
calendar data.

No persistent installation identifier and no version string is sent. Turn them
off in **Settings → System → Services**.

## Backup

| | |
|---|---|
| **Database** | PostgreSQL · container `zammad-db` · database `zammad_production` · user `zammad` |
| **Password** | `.secrets/db_pwd.txt` |
| **State** | `./volumes/postgres` (database) · `./volumes/zammad-storage` (ticket attachments) |
| **Reproducible** | `./volumes/elasticsearch` (search index — rebuildable) · `./volumes/redis` (cache) |
| **Quiescing** | Not needed. The dump is consistent on its own. |

```yaml
postgresql_databases:
    - name: zammad_production
      username: zammad
      # The server's own client, inside its container (FA-03)
      pg_dump_command: docker exec zammad-db pg_dump
      pg_restore_command: docker exec -i zammad-db pg_restore
      psql_command: docker exec -i zammad-db psql
```

**Excluding the Elasticsearch volume is deliberate, and it has a cost.** The index
is derived data and rebuilds from the database, so backing it up wastes
considerable space. But it does not rebuild by itself — after a restore, run the
searchindex rebuild and expect it to take a while on a large ticket history.
Until it finishes, Zammad is up and its search returns nothing, which looks like
data loss and is not.

**Restore order:** database first, then `init` (it runs migrations), then the
remaining services once it has exited cleanly.

## Known Issues

- **First boot is slow** — Elasticsearch warmup + schema migrations ~3-5 min.
- **Elasticsearch vm.max_map_count** — required host-level sysctl. If not set, ES crashes on start.
- **Pin the highest build of a release, not the first** — Zammad tags as `X.Y.Z-NNNN`, and a release keeps receiving builds after it ships. `7.1.2-0001` and `7.1.2-0013` are both `7.1.2` and carry different images. Do not use a floating tag like `7` or `7.1`.
- **7.1.2 closes 18 advisories published 2026-08-04**, one critical (account takeover through unverified e-mail matching during SSO auto-link) and four high, including remote code execution through the AI Agent template sanitizer. Anything at `7.1.1` or below is affected.
- **bitnami/elasticsearch is no longer free** — switched to `docker.elastic.co/elasticsearch/elasticsearch`. xpack security is disabled via env (`xpack.security.enabled=false`) since ES is on `app-internal` only.
- **nginx needs DB credentials to pass the readiness check** — nginx runs `bundle exec rails r 'Translation.any? || raise'` in a loop until init has seeded the DB. This requires all `POSTGRESQL_*` env vars. The `zammad-nginx` service therefore merges `*zammad-env` (same as railsserver/scheduler) even though nginx itself doesn't query the DB at runtime.
- **Setup wizard email step: select SMTP, not Local MTA** — no sendmail/postfix is present in the container. Choosing "Local MTA" fails with `exitstatus 1`. Select "SMTP - configure your own outgoing SMTP settings" or click Skip and configure later under Admin → Channels → Email.
- **WebSocket console errors from browser extensions** — errors to `wss://sync.heylogin.app` (or similar third-party domains) during the setup wizard are from browser extensions (e.g. HeyLogin), not from Zammad. Ignore them.
- **geo.zammad.com outbound calls fail silently** — init and scheduler attempt to fetch holiday calendar data from `https://geo.zammad.com/calendar`. This fails with `RuntimeError: 0` on networks with restricted outbound access. Non-fatal — Zammad continues normally.
- **YAML anchor `x-shared`** reuses env + security across zammad-* services — cannot use per-service secrets here, but all use the same DB_PWD.

## Email integration

Agents typically configure an inbound IMAP mailbox (Admin → Channels → Email) so `support@example.com` tickets auto-create. SMTP outbound likewise. Requires either:

- Own mailserver (Mailcow/Mailu — planned) — direct IMAP/SMTP
- Hosted provider (mailbox.org, Brevo) — IMAP + SMTP credentials

## Integration with Listmonk

For "customer opens ticket → added to marketing list" workflows, route via n8n:
Zammad webhook (Admin → Triggers) → n8n → Listmonk API `POST /api/subscribers`.

## Open findings

<!-- findings:start — generated by scripts/ci/lifecycle-report.py from upstream-status.json; edit the text around it -->

**Findings in the upstream images** at the pin `7.2.2-0045` — the newest upstream release. Scanned 2026-11-09; counted are findings with a published fix, as CRITICAL · HIGH. They come with the images as upstream publishes them.

| Image | Base system | Libraries | Programs |
|---|---|---|---|
| `docker.elastic.co/elasticsearch/elasticsearch:9.5.6` | — | 0 · 5 | — |
| `ghcr.io/zammad/zammad:7.2.2-0045` | 0 · 2 | 0 · 1 | — |
| `memcached:1.6.45` | 0 · 2 | — | — |
| `postgres:18.6-alpine` | — | — | 1 · 25 |
| `redis:8.10.3-alpine` | — | — | — |

<!-- findings:end -->

The PostgreSQL image, `postgres`, carries one CRITICAL finding, CVE-2025-68121, in the Go runtime of `gosu`, the helper that drops root privileges at start. Every current image of this line ships the same gosu build, and its maintainer has not rebuilt it with a fixed Go.

**Risk:** the flaw is in TLS session resumption, and gosu opens no network connection, so it is not reached. The finding clears when upstream ships a rebuilt gosu.
