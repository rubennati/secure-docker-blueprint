# Gatus

YAML-driven health checks, status page, and alerting. Go-based, single-container. The config-as-code counterpart to Uptime Kuma's click-UI.

## Architecture

| Service | Image | Purpose |
|---------|-------|---------|
| `app` | `twinproduction/gatus:v5` | Probe scheduler + web UI + alerter |

Config lives in `./config/config.yaml`. Result history in `./volumes/data/data.db` (SQLite default; Postgres supported).

## Setup

```bash
cp .env.example .env
mkdir -p config volumes/data
cp config.example.yaml config/config.yaml
# Edit config.yaml — add your endpoints + alerting channels

docker compose up -d
docker compose logs app --follow
# Watch for: "Listening on :8080"
```

Gatus auto-reloads on config changes — just `vim config/config.yaml` + save, no restart.

> **Note:** `config.example.yaml` lives next to `docker-compose.yml`, **not** inside `config/`. Gatus reads every `.yaml` file in the config directory — if `config.example.yaml` ends up in `config/` alongside `config.yaml`, Gatus panics on duplicate keys.

## Security Model

- **YAML config is the source of truth** — version-control your `config.yaml` (but NOT with embedded secrets — use `${ENV_VAR}` references).
- **Secret references** — `config.yaml` supports `${NAME}` that Gatus reads from its environment. Pass sensitive alert-webhook URLs via `.env` or a `.env.secrets` sourced into the compose environment.
- **Default access `acc-tailscale` + `sec-3`** — the UI and `/api/v1/endpoints/statuses` expose all target URLs, conditions, and alerting destinations. Switch to public only after redaction review.
- **`read_only: true` + tmpfs /tmp** — the container has no writable root FS.

## Integration patterns

- **Prometheus export**: add `metrics: true` to `config.yaml` — Gatus exposes `/metrics` with per-endpoint availability, response times, SSL expiry.
- **Forward to n8n**: use a `custom` alert with a webhook URL pointing at `https://n8n.example.com/webhook/<path>` for richer routing.

## Backup

| | |
|---|---|
| **Configuration** | `config.yaml` — the endpoints and alerting rules. This is the part worth keeping. |
| **State** | `./volumes/data` — SQLite result history |
| **Reproducible** | The result history. Losing it costs graphs, not function. |
| **Quiescing** | Not needed for the config; the database is live, so dump it rather than copying it |

Config-as-code is the point here: `config.yaml` belongs in version control or in the
backup, and a restore is essentially that file plus a container start.

```yaml
sqlite_databases:
    - name: gatus
      path: /srv/docker/monitoring/gatus/volumes/data/data.db
```

Confirm the filename on the running instance. With the optional PostgreSQL backend
enabled instead, use `postgresql_databases:` with the `container:` option.

**Restore order:** restore `config.yaml`, then the database if the history matters,
then start.

## Known Issues

- **`config.example.yaml` must NOT be inside `config/`** — Gatus merges all `.yaml` files in the config directory. Duplicate top-level keys cause a panic on startup: `only maps and slices/arrays can be merged`. The example file lives at `monitoring/gatus/config.example.yaml` (next to `docker-compose.yml`), not in `config/`.
- **SQLite is sufficient for ~100 endpoints**. For 500+ endpoints or long history retention, switch `storage.type` to `postgres` and add a db service (copy pattern from `apps/paperless-ngx/`).
- **No built-in authentication beyond basic-auth** — use Traefik `sec-*` + `acc-tailscale`, or add an Authentik forward-auth middleware for SSO.
- **Config hot-reload is best-effort** — a syntax error during reload leaves the old config running; check logs after every save.
