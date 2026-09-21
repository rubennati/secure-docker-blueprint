# Upstream Reference

## Source

- **Image:** https://github.com/open-webui/open-webui/pkgs/container/open-webui
- **GitHub:** https://github.com/open-webui/open-webui
- **Docs:** https://docs.openwebui.com/
- **License:** Open WebUI License (BSD-3-Clause with an added branding-preservation clause; not OSI-approved)
- **Use restrictions:** the Open WebUI name and branding may not be removed or altered, except for deployments whose end users do not exceed fifty individuals in any rolling thirty-day period, or with prior written permission or an executed enterprise licence — https://github.com/open-webui/open-webui/blob/main/LICENSE · checked 2026-09-21
- **Commercial model:** commercial licence — https://github.com/open-webui/open-webui/blob/main/LICENSE · checked 2026-09-21
- **Origin:** Open WebUI · no country stated in its published terms · no country
- **Domain:** AI and local AI
- **Role:** Chat interface for any OpenAI-compatible endpoint, with accounts, history and document upload
- **Based on version:** `v0.11.3`

No `Last verified` line yet — see [Verification performed](#verification-performed-2026-09-19)
below. The field asserts Traefik/TLS routing was confirmed on a real host, which
has not happened; this stack stays `scaffolded` until it does.

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

**Not yet exercised:** Traefik routing and TLS; the browser UI itself (all checks
went through the API); document upload and retrieval; web search; a backend
other than Ollama; backup and restore.

## Upgrade checklist

1. Read the release notes: https://github.com/open-webui/open-webui/releases
2. Check the GitHub Security tab for advisories against the current version
3. Back up `volumes/data`
4. Bump `APP_TAG` in `.env.example`
5. `docker compose pull && docker compose up -d`; database migrations run at start
6. Log in and send a message
7. Update **Based on version** above — and add **Last verified** only if the
   upgrade was exercised on a real install
