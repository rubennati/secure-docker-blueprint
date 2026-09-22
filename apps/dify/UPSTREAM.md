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
- **Last verified:** 2026-09-22 (1.17.1) — behind Traefik with TLS: the setup through `/install`, a marketplace plugin with a model provider, a workflow with code, HTTP and LLM nodes, a restart, and a restore from its three dumps

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
| `dify-web`: `HOSTNAME: 0.0.0.0`, healthcheck on `127.0.0.1` | Next.js listens on the address `HOSTNAME` resolves to; Docker's container ID can resolve to the `app-internal` address, and Traefik then gets `502` while the healthcheck on `$(hostname)` passes |
| `APP_TRAEFIK_SECURITY=sec-2-spa` | Sign-in, the app list and the workflow editor load over 160 script chunks; `sec-2`'s burst of 50 answered part of them with `429` and the editor stayed on its spinner |
| Web and plugin-daemon healthchecks | `web` probes its own hostname address (it does not bind loopback). The plugin daemon, worker, beat and Squid have no meaningful probe; marker comments in the compose file |

## Verification performed (2026-09-22)

Behind Traefik with TLS, with the Ollama stack's route as the model endpoint:

- A client outside the access policy's ranges got `403` on the route, over IPv4
  and IPv6
- `worker-beat` restarted in a loop: the app factory creates its storage
  directory at start, and beat — read-only, with no storage mount — stopped with
  `OSError: [Errno 30] Read-only file system: 'storage'`. With
  `./volumes/storage` mounted as for `dify-api` and `worker` it ran; the compose
  file now mounts it
- Setup while the router was `acc-deny` (every route path `403`): through the
  API inside `dify-api` — `/console/api/setup` `401` before `/console/api/init`,
  `/init` `401` with a wrong setup password and `201` with the right one,
  `/setup` `201`, step `finished`. The README's sequence — keep `acc-deny`, then
  open `/install` in a browser — could not be followed, because `acc-deny`
  refuses the browser as well. The README now opens `/install` through the
  shipped `acc-private`, with the setup password as the guard: on a fresh
  instance in headless Chromium, `/install` led to `/init`, a wrong setup
  password stayed there, the right one opened the account form, and the console
  followed
- After switching to `acc-private`: `dify-web` answered `502` after one
  recreation. Next.js listens on the address `HOSTNAME` resolves to; Docker sets
  it to the container ID, which resolved to the `app-internal` address, where
  Traefik does not connect, and the healthcheck probed the same address and
  stayed `healthy`. `HOSTNAME: 0.0.0.0` and a healthcheck on `127.0.0.1` are now
  in the compose file
- Headless Chromium (Playwright 1.63): sign-in and the app list under `sec-2`
  without `429`; opening the workflow editor once got 4 × `429` on script chunks
  and stayed on its loading spinner. Replaying the 164 script chunks of sign-in,
  app list and editor over one HTTP/2 connection: 64 × `429` under `sec-2`, none
  under `sec-2-spa`, which `.env.example` now ships. The editor showed the Code,
  HTTP Request and LLM nodes
- The console login API expects the password Base64-encoded, as the web app
  sends it (`FieldEncryption.decrypt_field`)
- `langgenius/openai_api_compatible` 0.0.66 installed from the marketplace;
  `volumes/plugin_daemon`, owned by uid 1001, received the package, its `cwd`
  and a `uv` cache. A model added with the Ollama route as endpoint was
  validated `active`
- A workflow imported from DSL (start → code → HTTP → LLM → end), published, run
  through `/v1/workflows/run` with an app key: `succeeded`, the code node's
  output, `http_status` `200` for a public site through Squid, and the LLM's
  reply; a wrong app key `401`
- After `docker compose down` and `up -d` the workflow ran again
- Backup as the README describes: `docker compose stop api …` exits `0` and
  leaves `dify-api` running — Compose skips the unknown name; the README now
  names `dify-api`
- Restore into empty volumes: the three dumps loaded with `ON_ERROR_STOP` and no
  error, the archive unpacked, the stack started — sign-in, the plugin, the
  model (`active`, its credential decrypted with the unchanged `SECRET_KEY`) and
  the workflow run all came back, with no container restart
- Peaks: `dify-api` 575 MiB, `worker` 411 MiB, `worker-beat` 408 MiB of its
  512 MiB, `plugin-daemon` 245 MiB, `dify-web` 180 MiB, `sandbox` 147 MiB,
  PostgreSQL 93 MiB, pgvector 69 MiB

**Not yet exercised:** webhooks and `/e/`; workflow collaboration over `/socket.io/`, which is not
routed; an Agent app; upgrade from an earlier Dify.

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
