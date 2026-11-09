# Upstream Reference

## Source

- **Image:** https://github.com/agentgateway/agentgateway/pkgs/container/agentgateway
- **GitHub:** https://github.com/agentgateway/agentgateway
- **Docs:** https://agentgateway.dev/docs/
- **License:** Apache-2.0
- **Decision facts checked:** not yet
- **Origin:** United States · Linux Foundation project (contributed by Solo.io) · non-EU
- **Domain:** AI and local AI
- **Role:** LLM and MCP gateway: one authenticated endpoint in front of model providers and MCP servers
- **Last verified:** 2026-11-08 (1.7.0) — lab host (VM), IPv4 LAN: `ops/init.sh` rendered the config, which validated once the README's command mounted the UI htpasswd (corrected), `/v1/models` answered with the client key and `401` without it before and after `down`/`up`, the UI behind its basicAuth gate, the refused client answered `403`; no completion through a backend (docs/labs/stack-refresh/2026-11-08-results.md)

## What we use

- `cr.agentgateway.dev/agentgateway:v1.7.0` — a versioned tag of upstream's own
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

## Verification performed (2026-09-21)

Behind Traefik with TLS, both routes on the shipped `acc-private` and `sec-2`:

- A client outside the access policy's ranges got `403` on both routes, over
  IPv4 and IPv6
- `/v1/models`: `401` without a key and with a wrong key, `200` with the key; a
  chat completion through the shipped `"*"` model to `http://ollama:11434/v1`
- UI route: `401` without credentials and with a wrong password, `200` with the
  generated login; in headless Chromium (Playwright 1.63) the UI loaded with
  12 requests, all `200`; the metrics port unreachable from a peer container,
  `:15021/healthz/ready` answered `ready`
- Provider credential: a model with `auth: {key: {file: /run/secrets/AGW_PROVIDER_KEY}}`,
  the file mounted as an additional Docker Secret (group 65532, mode 640)
  through an override. An echo provider logged `Authorization: Bearer` followed
  by the provider key; the client's gateway key did not reach it.
  `--validate-only` fails with `failed to read from file` unless the secret file
  is mounted into the validation run as well
- A provider over TLS: a model with `baseUrl` set to the Ollama stack's route
  answered through Traefik
- MCP: the template's `mcp:` block with one streamable-HTTP target (a Python MCP
  SDK 1.x server): `401` without the key; `initialize`, `tools/list` and
  `tools/call` through the route with it
- After `docker compose down` and `up -d` the provider answered
- Restore: `volumes/data` and `config/config.yaml` archived with the container
  stopped — `data.db` keeps its `-wal` and `-shm` files after the stop, and the
  archive holds all three — then removed, extracted and started: requests
  answered, and the request log continued from four to five rows
- Peak 8.8 MiB of memory, 16 PIDs

**Not yet exercised:** a hosted provider's own check of the credential — none
was available; the injection was proven against the echo provider.

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

## Version notes

- Moved to `v1.7.0` on 2026-11-05 (released 2026-10-27), across v1.6.0, not run
  on a host at this tag. Breaking in v1.6.0: Anthropic Messages requests now
  prefer the OpenAI Responses format over Chat Completions; a provider base URL
  without a path now means `/` (the template's `http://ollama:11434/v1` already
  carries its path); the standalone `llm` mode matches standard LLM paths only
  exactly; a built-in model catalog now prices requests, so USD budgets and
  `llm.cost` expressions can start to apply; unquoted YAML values such as `no`
  stay strings; `AGENTGATEWAY_LEGACY_LLM_USAGE_TOKEN_SEMANTICS` is removed.
  Breaking in v1.7.0: standalone always encrypts MCP sessions, generating the
  key into the config file or the database, whichever is writable (here the
  database under `/data`); prompt guards inspect tool outputs by default; CEL
  header lookups return a list for a repeated header; dynamic backends refuse
  loopback and link-local destinations; error responses no longer carry
  internal details; `AGENTGATEWAY_MESSAGES_PREFER_COMPLETIONS` is removed. The
  SQLite request log gains analytics columns, backfilled at the first start.
  Advisories fixed: GHSA-h7hp-2f8r-9g9c (v1.6.0), GHSA-qm3r-hhvc-62cp and
  GHSA-7hv4-jgp9-mgx2 (v1.7.0), all MCP-related and medium.
- Upstream's recommendation since v1.6.0, not applied to the template: use the
  `openAI` provider only for the OpenAI API, and reach other OpenAI-compatible
  servers, such as the template's Ollama backend, through a custom provider
  that advertises only the formats the server implements — Chat Completions
  only if it lacks `/v1/responses` or clients need extended-thinking history.
  The template still routes `*` through `provider: openAI`; it affects clients
  that send Anthropic Messages, which are now converted to Responses.

## Upgrade checklist

1. Read the release notes: https://github.com/agentgateway/agentgateway/releases
2. Check the GitHub Security tab for advisories against the current version
3. Back up `volumes/data` and `config/config.yaml`
4. Bump `APP_TAG` in `.env.example`
5. Validate the config with `--validate-only` against the new image
6. `docker compose pull && docker compose up -d`; make a real `/v1` request
7. Add **Last verified** only if the
   upgrade was exercised on a real install
