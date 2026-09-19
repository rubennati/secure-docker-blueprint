# LiteLLM

An OpenAI-compatible gateway in front of model providers: one API, virtual keys
with per-key model allowlists and budgets, and a spend log in PostgreSQL.
Standalone — any OpenAI-compatible backend (Ollama, vLLM, a hosted provider) can
be listed in `config/config.yaml`; none is required. Upstream:
[LiteLLM](https://github.com/BerriAI/litellm).

## Architecture

```text
Internet → Traefik (TLS) → litellm :4000 ──→ model backend (outbound)
                              │
                 app-internal (internal: true)
                              │
                         db (PostgreSQL)
```

## Setup

```bash
cp .env.example .env            # set the host name
ops/init.sh                     # three secrets in .secrets/
docker compose up -d
```

The first start applies the database migrations and takes about a minute.
Edit `config/config.yaml` before or after: the shipped model entry points at
`http://ollama:11434/v1`, which resolves only when an Ollama container shares a
network with this stack.

## Three kinds of credential

| Who | Credential | Where it lives |
|---|---|---|
| Operator (admin API, UI) | Master key | Docker Secret `LITELLM_MASTER_KEY` |
| API client | Virtual key from `POST /key/generate` | PostgreSQL (hashed); limited to the models and budget set at creation |
| Gateway calling a provider | Provider API key | Not in the config. Add the model through the admin API: LiteLLM stores the credential encrypted with the salt key (`LITELLM_SALT_KEY`) |

```bash
curl -H "Authorization: Bearer $(cat .secrets/litellm_master_key.txt)" \
     -H 'content-type: application/json' \
     https://litellm.example.com/key/generate \
     -d '{"models":["local-chat"],"max_budget":5,"key_alias":"team-a"}'
```

## Security notes

- **Secrets.** LiteLLM has no `_FILE` variants. `config/entrypoint.sh` builds
  `DATABASE_URL`, `LITELLM_MASTER_KEY` and `LITELLM_SALT_KEY` from Docker Secrets
  and starts the image's own entrypoint; they are not in the container's
  configured environment.
- **Salt key is permanent.** Do not change it once models with credentials are
  stored; they become unreadable.
- **Unauthenticated routes.** `/health/liveliness`, `/health/readiness`, `/routes`
  and `/openapi.json` answer without a key (`/routes` and the OpenAPI document list
  the API surface, no data). Everything else, including `/v1/models`, `/metrics`
  and `/health`, returned `401`. `/ui` redirects to the admin login (not exercised beyond the redirect).
- **Hardening.** Non-root image (uid 65534), `read_only`, `cap_drop: ALL`,
  `no-new-privileges`, only `/tmp` writable (tmpfs), no published ports.
- **Network.** The database has no route out. The proxy is on `proxy-public` to
  reach Traefik and its backends; every container on that network can reach port
  4000, where a key is still required.
- **Telemetry.** `litellm_settings.telemetry: false` is set.

## Status

`scaffolded` — see [UPSTREAM.md](UPSTREAM.md#verification-performed-2026-09-19).

## Local deployment validation

```bash
cp .env.local.example .env.local
ops/init.sh
docker compose -f docker-compose.local.yml --env-file .env.local up -d
curl -H "Authorization: Bearer $(cat .secrets/litellm_master_key.txt)" http://localhost:4000/v1/models
docker compose -f docker-compose.local.yml --env-file .env.local down
```

Ports bind to `127.0.0.1`; Traefik and the Docker Secrets mechanism are not used.

## Backup

Back up the database and the three secret files.

```bash
docker exec litellm-db pg_dump -U litellm litellm > litellm.sql
```

Restore into an empty database with `psql`, place `litellm_salt_key.txt` and
`litellm_master_key.txt` back unchanged, then `docker compose up -d`. Without the
original salt key, stored provider credentials cannot be decrypted. `config/config.yaml`
is tracked in git.
