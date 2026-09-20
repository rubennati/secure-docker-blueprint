# agentgateway

An LLM, MCP and agent gateway: one authenticated endpoint in front of model
providers and MCP servers, with routing, a web UI and a request log. Standalone —
it needs no other stack, and any OpenAI-compatible or MCP backend can sit behind
it. Upstream: [agentgateway](https://github.com/agentgateway/agentgateway).

## Architecture

```text
Internet → Traefik (TLS) → agentgateway :4000   /v1 (LLM) · /mcp (MCP)   ← API key
                         → agentgateway :4001   UI                      ← basic auth
                                   │
                                   └──→ model provider / MCP server (outbound)
```

One container. Configuration is a read-only file; state is a small SQLite
database in `volumes/data`.

## Setup

```bash
cp .env.example .env            # set the two host names
ops/init.sh [ui-user]           # credentials + config/config.yaml
sudo chown 65532:65532 volumes/data
docker compose up -d
```

`ops/init.sh` writes `.secrets/agw_api_key.txt` (the client key),
`.secrets/agw_ui_password.txt` and `.secrets/agw_ui_htpasswd.txt`, and renders
`config/config.yaml` from `config/config.yaml.example`. It prints the credentials
once. It refuses to overwrite existing files.

Then edit `config/config.yaml`: point `llm.models[].params.baseUrl` at a backend
the container can reach, or add a hosted provider. The template ships with
`http://ollama:11434/v1`, which only resolves when an Ollama container shares a
network with this one. Validate a change before restarting:

```bash
docker run --rm -v "$PWD/config/config.yaml:/config/config.yaml:ro" \
  cr.agentgateway.dev/agentgateway:v1.5.0 -f /config/config.yaml --validate-only
```

## Three kinds of credential

| Who | Credential | Where it lives |
|---|---|---|
| Client calling the gateway | Bearer API key | `.secrets/agw_api_key.txt`; the config holds only its SHA-256 (`keyHash`) |
| Operator opening the UI | Basic-auth login | htpasswd file mounted as the Docker Secret `AGW_UI_HTPASSWD` |
| Gateway calling a hosted provider | Provider API key | Not part of this stack's defaults. An Ollama or vLLM backend needs none; for a hosted provider, use upstream's `policies.backendAuth` with a `file:` source pointing at a mounted secret rather than a literal in the config |

Rotating the client key means re-running `init.sh` on a fresh directory state
(or hashing a new key with `printf '%s' KEY | openssl dgst -sha256`) and
restarting.

## Security notes

- **Two gateways, two auth modes.** Port 4000 requires the API key
  (`mode: strict`); port 4001 requires the basic-auth login. A request without
  credentials gets `401`.
- **Metrics stay on loopback.** Upstream's default binds the stats listener to all
  interfaces, which exposes `/metrics` to every container on `proxy-public`. The
  template sets `config.statsAddr: 127.0.0.1:15020`. The readiness port (15021,
  `/healthz/ready`) remains reachable from peers and returns only `ready`.
- **Hardening.** `read_only`, `cap_drop: ALL`, `no-new-privileges`, uid 65532, no
  published ports. The only writable path is `volumes/data`.
- **No healthcheck.** The image is distroless: no shell, no `wget`. The compose file
  carries the marker comment; probe `:15021/healthz/ready` from outside.
- **Egress.** The container sits on `proxy-public`, so it can reach its providers
  and every other container on that network. Restrict the backend list in the
  config to what you intend to route to.

## MCP

The template contains a commented `mcp:` block on the same gateway: an MCP target
is reached under `/mcp` with the same API key. Uncomment it and set the target's
host, port and path.

## Status

`scaffolded` — see [UPSTREAM.md](UPSTREAM.md#verification-performed-2026-09-19).

## Try it locally

```bash
ops/init.sh
mkdir -p volumes/data
docker compose -f docker-compose.local.yml up -d
curl -H "Authorization: Bearer $(cat .secrets/agw_api_key.txt)" http://localhost:4000/v1/models
docker compose -f docker-compose.local.yml down
```

Ports bind to `127.0.0.1`; Traefik and Docker Secrets are not used.

## Backup

Back up `volumes/data` (SQLite: request log and gateway state) and
`config/config.yaml`. The credentials in `.secrets/` are recreated by `init.sh`, but
then clients need the new key — store `agw_api_key.txt` with your other secrets.
Restore by placing both back and running `docker compose up -d`. Stopping the
container first gives a consistent copy of the database.
