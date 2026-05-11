# Zammad

**Status: 🚧 Draft**

Self-hosted helpdesk / ticketing / customer support. Multi-channel (email, web form, Twitter, Telegram, SMS), SLA tracking, time accounting, knowledge base.

## Architecture

Heavy stack — 9 services. Upstream default deployment.

| Service | Image | Purpose |
|---------|-------|---------|
| `nginx` (= `app`) | `ghcr.io/zammad/zammad:7.0.1` + `zammad-nginx` | Web gateway, static assets, reverse-proxy to rails + websocket |
| `railsserver` | same + `zammad-railsserver` | Rails app (API + core logic) |
| `websocket` | same + `zammad-websocket` | Agent live updates |
| `scheduler` | same + `zammad-scheduler` | Background jobs (email import, SLA checks) |
| `init` | same + `zammad-init` | One-shot DB migrations on every start |
| `db` | `postgres:16-alpine` | Primary data store |
| `redis` | `redis:7.4-alpine` | Background job queue |
| `memcached` | `memcached:1.6.41` | Rails cache |
| `elasticsearch` | `docker.elastic.co/elasticsearch/elasticsearch:8.17.4` | Full-text ticket search |

## Resource requirements

This is **not a lightweight stack**. Minimum for a live system:

- 4 GB RAM free (Elasticsearch alone grabs 512 MB heap)
- 2 CPU cores
- 10 GB disk for ES index + Postgres

On a small VPS, consider `ELASTICSEARCH_ENABLED=false` — tickets will still work, only full-text search is degraded.

## Setup

```bash
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, TZ

mkdir -p .secrets volumes/postgres volumes/redis volumes/elasticsearch volumes/zammad-storage
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
# First visit prompts setup wizard — create admin account + organization
```

## Security Model

- **First-visit wizard creates the owner account** — open the UI yourself immediately after start.
- **`DB_PWD_INLINE` duplicates the DB password** — Zammad reads `POSTGRESQL_PASS` from env only.
- **Elasticsearch has no auth here** — it's on `app-internal` only, not reachable from outside. If you move it off-host, add xpack.security.
- **`no-new-privileges:true`** on all services.
- **Default access `acc-public` + `sec-3`** — customers submit tickets via public web form `/customer_ticket_new`; agents log in at `/#login`. For agent-only VPN access, see the two-router split pattern (see `business/listmonk/README.md` for the pattern).

## Known Issues

- **First boot is slow** — Elasticsearch warmup + schema migrations ~3-5 min.
- **Elasticsearch vm.max_map_count** — required host-level sysctl. If not set, ES crashes on start.
- **`APP_TAG=7.0.1` is pinned** — update to a newer specific release tag for upgrades; do not use a floating tag like `7`.
- **bitnami/elasticsearch is no longer free** — switched to `docker.elastic.co/elasticsearch/elasticsearch`. xpack security is disabled via env (`xpack.security.enabled=false`) since ES is on `app-internal` only.
- **nginx needs DB credentials to pass the readiness check** — nginx runs `bundle exec rails r 'Translation.any? || raise'` in a loop until init has seeded the DB. This requires all `POSTGRESQL_*` env vars. The nginx service therefore merges `*zammad-env` (same as railsserver/scheduler) even though nginx itself doesn't query the DB at runtime.
- **geo.zammad.com outbound calls fail silently** — init and scheduler attempt to fetch holiday calendar data from `https://geo.zammad.com/calendar`. This fails with `RuntimeError: 0` on networks with restricted outbound access. Non-fatal — Zammad continues normally.
- **YAML anchor `x-shared`** reuses env + security across zammad-* services — cannot use per-service secrets here, but all use the same DB_PWD.

## Email integration

Agents typically configure an inbound IMAP mailbox (Admin → Channels → Email) so `support@firma.at` tickets auto-create. SMTP outbound likewise. Requires either:
- Own mailserver (Mailcow/Mailu — planned) — direct IMAP/SMTP
- Hosted provider (mailbox.org, Brevo) — IMAP + SMTP credentials

## Integration with Listmonk

For "customer opens ticket → added to marketing list" workflows, route via n8n:
Zammad webhook (Admin → Triggers) → n8n → Listmonk API `POST /api/subscribers`.
