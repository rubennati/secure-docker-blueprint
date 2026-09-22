# Upstream Reference

## Source

- **Image:** https://hub.docker.com/r/langgenius/dify-api
- **GitHub:** https://github.com/langgenius/dify
- **Docs:** https://docs.dify.ai/
- **License:** Dify Open Source License (Apache-2.0 with additional conditions: no multi-tenant service without written authorisation, frontend logo and copyright preserved; not OSI-approved)
- **Use restrictions:** operating a multi-tenant environment requires written commercial permission, and the LOGO and copyright information in the console and applications may not be removed or modified; the branding condition applies to the frontend, meaning the `web/` directory and the web image — https://github.com/langgenius/dify/blob/main/LICENSE · checked 2026-09-21
- **Commercial model:** commercial licence — https://github.com/langgenius/dify/blob/main/LICENSE · checked 2026-09-21
- **Decision facts checked:** 2026-09-21
- **Origin:** LangGenius · no country stated in its published terms · no country
- **Domain:** AI and local AI
- **Role:** LLM application platform: chat and workflow apps, knowledge bases, plugin-based model providers
- **Based on version:** `1.17.1`

No `Last verified` line yet — see [Verification performed](#verification-performed-2026-09-19)
below. The field asserts Traefik/TLS routing was confirmed on a real host, which
has not happened; this stack stays `scaffolded` until it does.

## What we use

Upstream's Docker Compose deployment (`docker/docker-compose.yaml`, tag `1.17.1`),
PostgreSQL profile, pgvector as the vector store, minus what is listed below:

- `langgenius/dify-api:1.17.1` (three services: `MODE=api`, `worker`, `beat`),
  `langgenius/dify-web:1.17.1`, `langgenius/dify-plugin-daemon:0.6.10-local`,
  `langgenius/dify-sandbox:0.2.15`
- `ubuntu/squid:6.6-24.04_edge` — upstream uses `:latest`; a versioned tag of the
  same image
- `postgres:15.14-alpine` (upstream: `15-alpine`), `pgvector/pgvector:0.8.1-pg16`
  (upstream: `pg16`), `redis:7.4-alpine` (upstream: `6-alpine`)
- pgvector, not Weaviate: upstream supports both, and pgvector is one more
  PostgreSQL rather than a different product. No other stack (Qdrant included) is
  embedded; Dify can use any vector store it supports.

## Not carried, and why

| Upstream component | Why not |
|---|---|
| nginx and certbot | Traefik is this repository's reverse proxy; its path rules are translated to Traefik routers |
| `api_websocket` | Profile `collaboration` (workflow co-editing); needs `/socket.io/` routed |
| `agent_backend`, `local_sandbox`, `agent_ssrf_proxy` | The 1.17 Agent runtime and its own sandbox and proxy. The chat, knowledge-base and code-execution paths run without them (verified below); Agent apps were not tested with or without them. Adding them follows upstream's compose file |
| `init_permissions` | A one-shot `chown`; replaced by the documented `chown` of `volumes/storage` |
| The other vector stores and databases (Weaviate, Milvus, MySQL, …) | Alternatives, not requirements |
| Port 5003 (plugin remote debugging) | The listener is bound to loopback inside the container and not published |
| `/e/` and `/socket.io/` routes | See README |

## What we changed and why

| Change | Reason |
|--------|--------|
| `config/entrypoint.sh` exports `NAME__FILE` into `NAME` | None of the images has `_FILE` variants; upstream sets secrets as plain environment variables. The Celery broker URL contains the Redis password, so it is its own secret file |
| Redis password in a tmpfs config file | `--requirepass` on the command line shows in the process list |
| `INIT_PASSWORD` as a Docker Secret | Verified: `/console/api/setup` returns `401` until `/console/api/init` has accepted the password |
| `MIGRATION_ENABLED=false` on worker and beat | The api container migrates; upstream runs it from every container that shares the environment file |
| `api`, `worker`, `worker-beat`, `web`: `read_only`, `cap_drop: ALL` | Verified: start, migrate, index and serve with only `/tmp` and `storage` writable |
| `plugin-daemon`: `user: 1001:1001`, `read_only`, `cap_drop: ALL`, `HOME=/tmp` | The image runs as root; three marketplace plugins installed and loaded, model calls worked, with this in place. The Compose volume must belong to uid 1001 |
| `PLUGIN_REMOTE_INSTALLING_HOST=127.0.0.1` | The daemon refuses to start with an empty host; upstream's default `0.0.0.0` with a published port is a remote-install listener |
| `sandbox`: `cap_add` CHOWN, SETUID, SETGID, SYS_CHROOT, DAC_OVERRIDE | With `cap_drop: ALL` alone a code node fails with `chown script to uid 10000: operation not permitted`. Removing each of the five in turn made the run fail; FOWNER, tried in the same probe, is not needed. Root, writable root: the sandbox chroots and drops to its own users per run |
| `ssrf-proxy`: root, five capabilities, writable root | Squid's entrypoint writes `/etc/squid` and the cache at start and Squid drops privileges itself. Not narrowed further |
| Two networks besides `proxy-public` | `app-internal` (no route out) for everything; `app-egress` for the SSRF proxy and the plugin daemon, the two services that must reach the internet |
| `CHECK_UPDATE_URL=""` | Upstream's update check |
| `worker-beat` mounts `./volumes/storage` | The app factory creates the storage directory at start, beat included; on the read-only root without the mount it stopped with `OSError: [Errno 30]` and restarted in a loop |
| `dify-web`: `HOSTNAME: 0.0.0.0`, healthcheck on `127.0.0.1` | Next.js listens on the address `HOSTNAME` resolves to; Docker's container ID resolved to the `app-internal` address after a recreation, and Traefik got `502` while the healthcheck on `$(hostname)` passed |
| `APP_TRAEFIK_SECURITY=sec-2-spa` | Sign-in, the app list and the workflow editor load over 160 script chunks; `sec-2`'s burst of 50 answered part of them with `429` and the editor stayed on its spinner |
| Web and plugin-daemon healthchecks | `web` probes its own hostname address (it does not bind loopback). The plugin daemon, worker, beat and Squid have no meaningful probe; marker comments in the compose file |

## Verification performed (2026-09-19)

Production `docker-compose.yml` (Docker Secrets, wrappers, three networks) on a
throwaway `proxy-public` network without Traefik, and `docker-compose.local.yml` on
empty volumes, with a throwaway Ollama container (`smollm2:135m`, `all-minilm`) as
the model backend:

- All services started; migrations applied; the plugin daemon created and used its own
  database
- Setup gate: `/console/api/setup` `401` without the setup password, `201` after
  `/console/api/init` accepted it; login with a wrong password `401`
- The `openai_api_compatible` plugin installed from the marketplace through the daemon
  (download via the SSRF proxy); a model and an embedding model added with an Ollama
  endpoint
- A chat app answered a real request through its service API (`200`, a completion from
  Ollama); a wrong app key returned `401`
- A knowledge base on pgvector: a document was split, embedded through the plugin,
  indexed by the worker and retrieved semantically; the vector extension and the
  embedding table exist in the pgvector database
- Sandbox: `401` without or with a wrong key, `print(21*2)` returned `42`; a code node
  reached a public site through Squid (`200`) and was refused (`403`) for the database
  and the API
- After `docker compose down` and `up` the login, the app key and the knowledge base
  were intact and the setup step read `finished`
- Hardening from `docker inspect` as documented; no published port; the secret values
  absent from the configured environment of api, worker, plugin-daemon and sandbox
- Two further plugins installed while the plugin daemon ran as uid 1001 with a
  read-only root

**Not yet exercised:** Traefik routing and TLS (the router rules are validated by
`docker compose config` only); the browser console (all steps used the API); workflow
and Agent apps; webhooks and `/e/`; workflow collaboration; a hosted model provider;
resource use under load; backup and restore; the plugin daemon's volume ownership on
Linux (the test volumes were world-writable); upgrade from an earlier Dify.

## Upgrade checklist

1. Read the release notes: https://github.com/langgenius/dify/releases
2. Check the GitHub Security tab for advisories against the current version
3. Back up the three databases, `storage`, `plugin_daemon` and the secrets
4. Bump `APP_TAG` (api, worker, web move together); check `PLUGIN_TAG` and `SANDBOX_TAG`
   against upstream's compose file for the same release
5. `docker compose pull && docker compose up -d`; the api migrates at start
6. Open the console, run a chat, then check that installed plugins load
7. Update **Based on version** above — and add **Last verified** only if the
   upgrade was exercised on a real install
