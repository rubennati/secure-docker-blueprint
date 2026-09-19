# Upstream Reference

## Source

- **Image:** https://github.com/agentgateway/agentgateway/pkgs/container/agentgateway
- **GitHub:** https://github.com/agentgateway/agentgateway
- **Docs:** https://agentgateway.dev/docs/
- **License:** Apache-2.0
- **Origin:** United States · Linux Foundation project (contributed by Solo.io) · non-EU
- **Domain:** AI and local AI
- **Role:** LLM and MCP gateway: one authenticated endpoint in front of model providers and MCP servers
- **Based on version:** `v1.5.0`

No `Last verified` line yet — see [Verification performed](#verification-performed-2026-09-19)
below. The field asserts Traefik/TLS routing was confirmed on a real host, which
has not happened; this stack stays `scaffolded` until it does.

## What we use

- `cr.agentgateway.dev/agentgateway:v1.5.0` — a versioned tag of upstream's own
  registry. Distroless, uid 65532, no shell.
- The simplified `llm:` and `ui:` configuration modes (and an optional `mcp:` mode)
  rather than the full binds/listeners/routes schema.
- One container; SQLite at `/data/data.db` for the request log.

## What we changed and why

| Change | Reason |
|--------|--------|
| API key stored as `keyHash: sha256:…` | The `apiKey` policy takes the key inline or as a hash; there is no file reference for the key itself, and the image has no shell for an entrypoint wrapper. The plaintext key lives only in `.secrets/` |
| UI login via `htpasswd.file` on a Docker Secret | Upstream reads htpasswd from a file; `init.sh` creates it with `openssl passwd -apr1` |
| `config.statsAddr: 127.0.0.1:15020` | The default binds metrics to all interfaces |
| Secret and config files are mode 644 | Compose bind-mounts keep host permissions and the container runs as uid 65532. The files hold only hashes |
| No healthcheck | Distroless image; marker comment in the compose file |
| `read_only: true`, `cap_drop: ALL` | Verified compatible; SQLite writes only to `/data` |

## Verification performed (2026-09-19)

Against `docker-compose.local.yml` on v1.5.0, with a throwaway Ollama container
serving `smollm2:135m` as the backend:

- `--validate-only` accepted the rendered config; the container started and
  loaded it
- `/v1/models`: `401` without a key, `200` with the key, `401` with a wrong key
- A real `/v1/chat/completions` request was routed to Ollama and returned a
  completion with token usage
- UI: `401` without credentials, redirect (`308`) with the generated login
- An MCP server (a small Python test server) was reached through the gateway with
  the API key in an earlier run; the request listed and called a tool
- `read_only` root filesystem, `cap_drop: ALL` and uid 65532 held; SQLite created
  `data.db` in `volumes/data`; the key does not appear in the container environment

- Production `docker-compose.yml` on a throwaway `proxy-public` network, without Traefik: Docker Secret mounted, `/v1` `401`/`200`, UI `401`/`308`, metrics port unreachable from a peer container, no published ports

**Not yet exercised:** Traefik routing and TLS; hosted
providers and `backendAuth`; restore from backup.

## Upgrade checklist

1. Read the release notes: https://github.com/agentgateway/agentgateway/releases
2. Check the GitHub Security tab for advisories against the current version
3. Back up `volumes/data` and `config/config.yaml`
4. Bump `APP_TAG` in `.env.example`
5. Validate the config with `--validate-only` against the new image
6. `docker compose pull && docker compose up -d`; make a real `/v1` request
7. Update **Based on version** above — and add **Last verified** only if the
   upgrade was exercised on a real install
