# Upstream Reference

## Source

- **Image:** https://github.com/open-webui/open-webui/pkgs/container/open-webui
- **GitHub:** https://github.com/open-webui/open-webui
- **Docs:** https://docs.openwebui.com/
- **License:** Open WebUI License (BSD-3-Clause with an added branding-preservation clause; not OSI-approved)
- **Use restrictions:** the Open WebUI name and branding may not be removed or altered, except for deployments whose end users do not exceed fifty individuals in any rolling thirty-day period, or with prior written permission or an executed enterprise licence — https://github.com/open-webui/open-webui/blob/main/LICENSE · checked 2026-09-21
- **Commercial model:** commercial licence — https://github.com/open-webui/open-webui/blob/main/LICENSE · checked 2026-09-21
- **Decision facts checked:** 2026-09-21
- **Origin:** Open WebUI · no country stated in its published terms · no country
- **Domain:** AI and local AI
- **Role:** Chat interface for any OpenAI-compatible endpoint, with accounts, history and document upload
- **Based on version:** `v0.11.3`
- **Last verified:** 2026-09-21 (v0.11.3) — behind Traefik with TLS: sign-in and an answer from an attached document in a browser, LiteLLM as a second backend, offline mode, a restart, and a restore

## What we use

- `ghcr.io/open-webui/open-webui:v0.11.3` — the standard image with a versioned
  tag. The `-cuda` and `-ollama` variants are not used: the bundled Ollama is
  what this stack avoids assuming.
- SQLite and the built-in vector store in `/app/backend/data`; no PostgreSQL,
  Redis or external vector database. Upstream supports those for multi-instance
  setups.

## What we changed and why

| Change | Reason |
|--------|--------|
| `user: 1000:1000`, `HOME=/tmp` | The image runs as root; it works as an unprivileged uid when `volumes/data` belongs to it |
| `read_only: true` with `tmpfs: /tmp` | Verified: login, chat, restart. Startup logs harmless `Read-only file system` errors for branding files that already exist in the image |
| `config/entrypoint.sh` exports the three secrets | No `_FILE` variants for `WEBUI_SECRET_KEY`, `WEBUI_ADMIN_PASSWORD` or `OPENAI_API_KEY` |
| `WEBUI_ADMIN_EMAIL` / `WEBUI_ADMIN_PASSWORD` | Upstream makes the first registrant the administrator; this creates the account before the port is reachable |
| `ENABLE_SIGNUP=false` | Verified: `POST /api/v1/auths/signup` returns `403` |
| `ENABLE_OLLAMA_API=false`, `OPENAI_API_BASE_URL` | One configurable OpenAI-compatible backend |
| `ENABLE_VERSION_UPDATE_CHECK`, `SCARF_NO_ANALYTICS`, `DO_NOT_TRACK`, `ANONYMIZED_TELEMETRY` off | Upstream's update check and telemetry |
| `HF_HUB_OFFLINE` variable | The embedding model downloads from Hugging Face at first start; `1` afterwards is verified to stop all requests to it |
| `APP_TRAEFIK_SECURITY=sec-2-spa` | The first load requests 224 files at once over one HTTP/2 connection; `sec-2` (burst 50) answered 103 of them with `429` and the web app showed `500: Internal Error`. `sec-2-spa` has the same average rate with a burst of 200 |

## Verification performed (2026-09-21)

Behind Traefik with TLS, with the shipped `acc-private` and the Ollama stack as
the first backend:

- A client outside the access policy's ranges got `403` on the route, over IPv4
  and IPv6
- In a browser the page failed with `500: Internal Error`: the first load
  requested 224 files, and `sec-2`'s rate limit answered 74 of the browser's
  requests with `429`. Replaying the same 224 paths over one HTTP/2 connection:
  103 × `429` under `sec-2`, 224 × `200` under `sec-2-spa`. Headless Chromium
  (Playwright 1.63) on a fresh profile: 65 of 173 requests `429` and the same
  error page under `sec-2`; all 173 `200` and the sign-in page under
  `sec-2-spa`. `.env.example` now ships `sec-2-spa`
- In that browser: signed in as the administrator, attached a text file in the
  chat, asked about it — `llama3.2:3b` answered from the file, citing one
  retrieved source
- Through the route: wrong password `400`, sign-up `403`, `/api/models` `401`
  without a token; the administrator from the environment signed in
- A text file uploaded through `/api/v1/files/`, processed, and a question about
  it answered from its content by `llama3.2:3b`
- Second backend: LiteLLM added through `/openai/config/update` at its route
  with a virtual key; its models were listed and a completion went Open WebUI →
  LiteLLM → Ollama, each hop through Traefik
- The first start downloaded the embedding model's whole Hugging Face
  repository, 888 MB, into `volumes/data/cache` — every format the repository
  carries, not only the one loaded
- `HF_HUB_OFFLINE=1` after the first start: a capture on the `proxy-public`
  bridge saw no outbound connection from the container during the restart
- The log warns `CORS_ALLOW_ORIGIN IS SET TO '*'`; the stack does not set it
- After `docker compose down` and `up -d`: the chat, the file and a session
  token issued before the restart were intact; retrieval answered offline
- Restore as the README described: `volumes/data` without `cache/` and the
  session key, container stopped, restored into an empty directory. Login, chats
  and old session tokens worked; with `HF_HUB_OFFLINE=1` the embedding model did
  not load (`LocalEntryNotFoundError`, `Error loading SentenceTransformer`) while
  the container reported `healthy` — answers ignored the attached document and a
  new upload's processing `failed`. One start with `HF_HUB_OFFLINE=0` downloaded
  it again, and after switching back to `1` retrieval answered. The README now
  says so
- Peak 1.3 GiB of memory, 87 PIDs

**Not yet exercised:** web search.

## Verification performed (2026-09-19)

Against `docker-compose.local.yml` and the production `docker-compose.yml`
(Docker Secrets, `entrypoint.sh`), without Traefik, with a throwaway Ollama
container (`smollm2:135m`) as the OpenAI-compatible backend at `/v1`:

- The pinned image pulled and started as uid 1000 with a read-only root
- The administrator was created from the environment on the empty database
  (once; not again after a restart); login worked, a wrong password returned `400`
- Self-signup returned `403`; `/api/models` without a token returned `401`
- The backend's model was listed and a real chat completion went through Open WebUI
  to the backend
- A chat created through the API was still present after a restart
- With `HF_HUB_OFFLINE=1` and a warm cache the container started with no request to
  Hugging Face
- The production stack: login from a peer container, no published port, the
  secret values absent from the configured environment

## Upgrade checklist

1. Read the release notes: https://github.com/open-webui/open-webui/releases
2. Check the GitHub Security tab for advisories against the current version
3. Back up `volumes/data`
4. Bump `APP_TAG` in `.env.example`
5. `docker compose pull && docker compose up -d`; database migrations run at start
6. Log in and send a message
7. Update **Based on version** above — and add **Last verified** only if the
   upgrade was exercised on a real install
