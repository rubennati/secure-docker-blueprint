# Gatus

YAML-driven health checks, status page, and alerting. Go-based, single-container. The config-as-code counterpart to Uptime Kuma's click-UI.

Project, source, licence and origin: [`UPSTREAM.md`](UPSTREAM.md).

## Architecture

| Service | Image | Purpose |
|---------|-------|---------|
| `gatus-app` | `twinproduction/gatus:v5.38.0` | Probe scheduler + web UI + alerter |

Config lives in `./config/config.yaml`. Result history in `./volumes/data/data.db` (SQLite default; Postgres supported).

## Try it locally

Runs on `http://localhost:8080` without Traefik, DNS or a certificate.

```bash
cp .env.local.example .env.local
mkdir -p config
cp config.example.yaml config/config.yaml
docker compose -f docker-compose.local.yml --env-file .env.local up -d
# http://localhost:8080
docker compose -f docker-compose.local.yml --env-file .env.local down
```

## Setup

```bash
cp .env.example .env
mkdir -p config volumes/data
cp config.example.yaml config/config.yaml
chmod 600 config/config.yaml
# Edit config.yaml — add your endpoints + alerting channels

docker compose up -d
docker compose logs gatus-app --follow
# Watch for: "Listening on :8080"
```

Gatus auto-reloads on config changes — just `vim config/config.yaml` + save, no restart.

> **Note:** `config.example.yaml` lives next to `docker-compose.yml`, **not** inside `config/`. Gatus reads every `.yaml` file in the config directory — if `config.example.yaml` ends up in `config/` alongside `config.yaml`, Gatus panics on duplicate keys.

## Security Model

- **`config.yaml` is the source of truth and the secret file.** Alert tokens, webhook URLs and SMTP passwords are written into it as values. The file is owner-only (`chmod 600`), gitignored (`config/config.yaml`), and mounted read-only; Gatus runs as root in its container and reads it. Keep it in the encrypted backup, not in a public repository.
- **No secret in the environment.** Gatus expands `${NAME}` in `config.yaml` from its own environment, and this stack passes nothing but `TZ`, the config path and the log level into it. A `${NAME}` reference therefore expands to an empty string, and a value in `.env` never reaches the container. Passing secrets through `environment:` would work, but would show them in `docker inspect`; Gatus has no `_FILE` variant ([`UPSTREAM.md`](UPSTREAM.md)).
- **Default access `access-vpn`, with `limit-standard` and `headers-standard`** — the UI and `/api/v1/endpoints/statuses` expose all target URLs, conditions, and alerting destinations. Switch to public only after redaction review.
- **`read_only: true` + tmpfs /tmp** — the container has no writable root FS.

## Notifications

Gatus sends an alert through a provider in the `alerting:` block of `config.yaml`;
an endpoint names the provider under `alerts:`. `config.example.yaml` has an ntfy
example.

**ntfy on the same host.** `monitoring/ntfy` publishes on its operator router,
which is `access-vpn`. Gatus calling the public name from its container arrives
from a Docker address, not from the VPN, and is refused with `403`. Join Gatus to
ntfy's edge network with the opt-in `ntfy.yml` and publish to the container by name:

```bash
# .env
NTFY_NETWORK=ntfy-edge
COMPOSE_FILE=docker-compose.yml:ntfy.yml
```

```yaml
# config/config.yaml
alerting:
  ntfy:
    url: "http://ntfy-app:80"
    topic: "gatus"
    token: "tk_…"          # an ntfy user with write access to the topic
```

Create the user and token on the ntfy side (`monitoring/ntfy/README.md`, Setup):
one user for Gatus, write access to its topic only. Gatus gains a path to ntfy and
to Traefik on that network, and nothing else; setting `TRAEFIK_NETWORK=proxy-public`
on both stacks would work too, but puts both on the network every member of which
reaches every other.

**ntfy on another host.** `url: "https://ntfy.example.com"` with the same token. The
request has to arrive over the VPN — the host running Gatus on the tailnet, and the
name resolving to the ntfy host's tailnet address — or the operator router refuses
it.

**Check:** after a change to `config.yaml`, `docker compose logs gatus-app` shows the
reload without an error; an endpoint pointed at an address that fails delivers its
alert after `failure-threshold` checks.

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
enabled instead, use `postgresql_databases:` with `pg_dump_command`, `pg_restore_command`
and `psql_command` through `docker exec <container>`, as `backup/borgmatic/README.md`
describes.

**Restore order:** restore `config.yaml`, then the database if the history matters,
then start.

## Known Issues

- **`config.example.yaml` must NOT be inside `config/`** — Gatus merges all `.yaml` files in the config directory. Duplicate top-level keys cause a panic on startup: `only maps and slices/arrays can be merged`. The example file lives at `monitoring/gatus/config.example.yaml` (next to `docker-compose.yml`), not in `config/`.
- **SQLite is sufficient for ~100 endpoints**. For 500+ endpoints or long history retention, switch `storage.type` to `postgres` and add a db service (copy pattern from `apps/paperless-ngx/`).
- **No built-in authentication beyond basic-auth** — keep `access-vpn`, or put `auth-authentik@file` in `APP_TRAEFIK_AUTH` for SSO.
- **Config hot-reload is best-effort** — a syntax error during reload leaves the old config running; check logs after every save.

## Open findings

<!-- findings:start — generated by scripts/ci/lifecycle-report.py from upstream-status.json; edit the text around it -->

**Findings in the upstream images** at the pin `v5.38.0` — the newest upstream release. Scanned 2026-11-26; counted are findings with a published fix, as CRITICAL · HIGH. They come with the images as upstream publishes them.

| Image | Base system | Libraries | Programs |
|---|---|---|---|
| `twinproduction/gatus:v5.38.0` | — | — | 0 · 5 |

<!-- findings:end -->
