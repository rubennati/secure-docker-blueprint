# Zammad

> **Status: 🚧 Draft**

Self-hosted helpdesk / ticketing / customer support. Multi-channel (email, web form, Twitter, Telegram, SMS), SLA tracking, time accounting, knowledge base.

## Architecture

Heavy stack — 7 services. Upstream default deployment.

| Service | Image | Purpose |
|---------|-------|---------|
| `nginx` (= `app`) | `ghcr.io/zammad/zammad:6` + `zammad-nginx` | Web gateway, static assets, reverse-proxy to rails + websocket |
| `railsserver` | same + `zammad-railsserver` | Rails app (API + core logic) |
| `websocket` | same + `zammad-websocket` | Agent live updates |
| `scheduler` | same + `zammad-scheduler` | Background jobs (email import, SLA checks) |
| `init` | same + `zammad-init` | One-shot DB migrations on every start |
| `db` | `postgres:16-alpine` | Primary data store |
| `redis` | `redis:7-alpine` | Background job queue |
| `memcached` | `memcached:alpine` | Rails cache |
| `elasticsearch` | `bitnami/elasticsearch:8` | Full-text ticket search |

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
# Watch for: "Puma starting" then "* Listening on http://0.0.0.0:3000"

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

- **Live-tested: no.**
- **First boot is slow** — Elasticsearch warmup + schema migrations ~3-5 min.
- **Elasticsearch vm.max_map_count** — required host-level sysctl. If not set, ES crashes on start.
- **`APP_TAG=6` tracks the 6.x line** — pin to a specific release (`6.2.0` etc.) for reproducibility.
- **YAML anchor `x-shared`** reuses env + security across zammad-* services — cannot use per-service secrets here, but all use the same DB_PWD.
- **`elasticsearch.healthcheck` uses `curl`** — if the bitnami image doesn't have curl, switch to a bash loop against `/dev/tcp/127.0.0.1/9200`.

## Email integration

Agents typically configure an inbound IMAP mailbox (Admin → Channels → Email) so `support@firma.at` tickets auto-create. SMTP outbound likewise. Requires either:
- Own mailserver (Mailcow/Mailu — planned) — direct IMAP/SMTP
- Hosted provider (mailbox.org, Brevo) — IMAP + SMTP credentials

## Integration with Listmonk

For "customer opens ticket → added to marketing list" workflows, route via n8n:
Zammad webhook (Admin → Triggers) → n8n → Listmonk API `POST /api/subscribers`.
