# Open WebUI

A chat interface for OpenAI-compatible model endpoints, with user accounts, chat
history, document upload and a built-in retrieval store. Standalone — the endpoint
it talks to (`BACKEND_URL`) can be LiteLLM, vLLM, Ollama's `/v1`, agentgateway or a
hosted provider; none is required. Upstream:
[Open WebUI](https://github.com/open-webui/open-webui).

## Architecture

```text
Internet → Traefik (TLS) → open-webui :8080 ──→ BACKEND_URL (outbound)
                              │
                       volumes/data (SQLite, uploads, vector store, model cache)
```

One container. SQLite, the vector store and uploads live in `volumes/data`; no
separate database service is needed for a single instance.

## Setup

```bash
cp .env.example .env            # host name, ADMIN_EMAIL, BACKEND_URL
ops/init.sh                     # secrets in .secrets/
mkdir -p volumes/data && sudo chown 1000:1000 volumes/data
docker compose up -d
```

The first start downloads the embedding model's full Hugging Face repository,
about 890 MB, into `volumes/data/cache` and takes a couple of minutes. Log in as `ADMIN_EMAIL` with the
password `ops/init.sh` printed. After the first start, set `HF_HUB_OFFLINE=1` in
`.env` and run `docker compose up -d`: the model is cached and no request leaves
for Hugging Face. Set `.secrets/openai_api_key.txt` to the backend's key if it
needs one (`none` otherwise).

## Credentials

| Who | Credential | Where it lives |
|---|---|---|
| Administrator | Email + password | Created once from `WEBUI_ADMIN_EMAIL` and the Docker Secret `WEBUI_ADMIN_PASSWORD` on an empty database. Changing the secret later does not change the account |
| Other users | Created by the administrator | Database. Self-signup is off (`ENABLE_SIGNUP=false`) |
| Session tokens | Signed with `WEBUI_SECRET_KEY` | Docker Secret. Changing it logs everyone out |
| Backend | API key | Docker Secret `OPENAI_API_KEY` |

Without the admin variables Open WebUI makes whoever registers first the
administrator; the stack sets them so nobody has to win that race on an exposed
host.

## Security notes

- **Hardening.** uid 1000 (the image defaults to root), `read_only`,
  `cap_drop: ALL`, `no-new-privileges`, only `/tmp` (tmpfs) and `volumes/data`
  writable, no published port.
- **Startup errors that are safe to ignore.** The log shows
  `Read-only file system: '/app/backend/open_webui/static/…'` for a dozen files
  (`favicon.png`, `logo.png`, `loader.js`, `site.webmanifest` and others). Open
  WebUI tries to copy branding files it already ships; the files exist and are
  served (`200`). The same error occurs for any non-root user, since the
  directory is root-owned in the image.
- **Egress.** Only Hugging Face (first start, see Setup) and `BACKEND_URL`. The
  update check and telemetry variables are switched off. Document upload and web
  search features make further outbound requests when used.
- **Secrets.** No `_FILE` variants exist; `config/entrypoint.sh` exports them from
  Docker Secrets, so they are absent from `docker inspect`.
- **Ollama.** `ENABLE_OLLAMA_API=false`: the stack talks to one OpenAI-compatible
  endpoint and does not assume Ollama.

## Status

Run behind Traefik with TLS on 2026-09-21 (v0.11.3): login, a document
uploaded and answered from, LiteLLM as a second backend, offline mode, a restart,
and the restore below. Full log in
[`UPSTREAM.md`](UPSTREAM.md#verification-performed-2026-09-21).

## Try it locally

```bash
cp .env.local.example .env.local
ops/init.sh
mkdir -p volumes/data
docker compose -f docker-compose.local.yml --env-file .env.local up -d
# http://localhost:8080 — log in as ADMIN_EMAIL with .secrets/webui_admin_password.txt
docker compose -f docker-compose.local.yml --env-file .env.local down
```

Ports bind to `127.0.0.1`; Traefik and the Docker Secrets mechanism are not used.

## Backup

Back up `volumes/data` (`webui.db`, `uploads/`, `vector_db/`) and
`.secrets/webui_secret_key.txt`. Stop the container first for a consistent SQLite
copy. Restore by placing both back and running `docker compose up -d`.

`cache/` can be left out of the backup; the embedding model in it is downloaded
again — but only while `HF_HUB_OFFLINE=0`. With `HF_HUB_OFFLINE=1` a restore
without `cache/` starts `healthy` and logs `Error loading SentenceTransformer`:
answers ignore attached documents and new uploads fail to process. Start once
with `HF_HUB_OFFLINE=0`, then set it back to `1` and run `docker compose up -d`
again — or keep `cache/embedding` in the backup.
