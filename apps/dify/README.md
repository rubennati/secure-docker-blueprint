# Dify

An application platform for LLM apps: chat and workflow builders, knowledge bases
with retrieval, a service API per app, and a plugin system for model providers and
tools. Standalone — model providers are plugins installed from its own console, and
any OpenAI-compatible endpoint (or a hosted provider) can be the backend; no other
stack is required or assumed. Upstream: [Dify](https://github.com/langgenius/dify).

## Architecture

```text
Browser / API clients → Traefik (TLS) ─┬→ web :3000            (console, apps)
                                       └→ api :5001            (/console/api, /v1, /files, …)
                                            │
                          app-internal (internal: true)
                                            │
  worker · worker-beat · plugin-daemon · sandbox · ssrf-proxy
  PostgreSQL · pgvector · Redis
                                            │
            app-egress: ssrf-proxy, plugin-daemon → marketplace, PyPI, model backends
```

Ten services, following upstream's Docker Compose deployment: `api`, `worker` and
`worker-beat` (one image, three modes), `web`, `plugin-daemon` (runs the plugins),
`sandbox` (isolated code nodes), `ssrf-proxy` (Squid), PostgreSQL, a separate
pgvector database as the vector store, and Redis. One host name serves everything;
Traefik routes upstream's nginx paths.

## Setup

```bash
cp .env.example .env            # host name
ops/init.sh                     # nine secrets in .secrets/
mkdir -p volumes/{storage,plugin_daemon,db,pgvector,redis}
sudo chown 1001:1001 volumes/storage volumes/plugin_daemon
sudo chown 999:999 volumes/redis
docker compose up -d
```

The first start runs the database migrations; the API reports healthy after about a
minute. Open `https://<host>/install` from a client the access policy admits
(`acc-private` as shipped), enter the setup password from
`.secrets/init_password.txt`, then create the administrator account. The setup
password is what guards that step: until the account exists, anyone who reaches
`/install` can try to become the administrator, and without the password
`/console/api/setup` answers `401`.

### Add a model

In the console: *Plugins* → install `openai_api_compatible` (or another provider)
from the marketplace → *Settings → Model Provider* → add the model with its
endpoint URL. The plugin daemon makes the call, so the endpoint must be reachable
from `plugin-daemon`: a hosted provider works as is; a server in another container
needs a network shared with `plugin-daemon` (add it under that service's
`networks`). Knowledge bases also need an embedding model.

## Credentials

| Who | Credential | Where it lives |
|---|---|---|
| Administrator and members | E-mail + password | Database. The first account is created through `/install`, guarded by `INIT_PASSWORD` |
| App API clients | Per-app `app-…` key | Created in the console, stored in the database |
| Knowledge-base API clients | `dataset-…` key | Same |
| Stored provider credentials | Encrypted with `SECRET_KEY` | Docker Secret. Do not change it once credentials are stored |
| Service-to-service | Sandbox key, plugin-daemon key, inner API key | Docker Secrets |

## Security notes

- **Secrets.** None of the images reads a secret from a file. `config/entrypoint.sh`
  exports each `NAME__FILE` variable's file as `NAME`; the values are absent from
  `docker inspect`. Redis's password goes into a tmpfs config file, not a
  command-line argument. `.secrets/` is mode 700 with world-readable files inside,
  because containers with different uids read them through bind mounts.
- **Hardening.** `api`, `worker`, `worker-beat`, `web` and `redis` run unprivileged,
  `read_only`, `cap_drop: ALL`. `plugin-daemon` runs as uid 1001, read-only, all
  capabilities dropped. Three services need more, each for a reason recorded in
  [UPSTREAM.md](UPSTREAM.md): `sandbox` (five capabilities), `ssrf-proxy` (root with
  five capabilities, writable root) and the two PostgreSQL containers (as elsewhere).
- **Outbound requests.** Requests users can trigger (HTTP nodes, tools, code nodes,
  file fetches) go through Squid, which refuses private destinations: a code node
  got `200` from a public site and `403` for the database and the API.
- **Egress that remains.** `api` and `web` are on `proxy-public`, so they can reach
  the internet directly. `plugin-daemon` is on `app-egress` and calls model backends
  itself.
- **Not routed.** Upstream's nginx also forwards `/e/` (plugin endpoints and
  webhooks) and `/socket.io/` (workflow collaboration); neither is routed here.
  Webhook-style plugin endpoints and collaborative editing therefore do not work.
- **Access policy.** Applications published from Dify and their API keys are served
  from the same host as the console, so `APP_TRAEFIK_ACCESS` has to include their
  consumers.
- **Marketplace.** `MARKETPLACE_ENABLED=true` lets the console install plugins from
  `marketplace.dify.ai`; plugin signatures are verified. Set it to `false` to accept
  only plugins you upload.

## Resources

Limits are starting values: api and worker 2 GB each, plugin-daemon 2 GB, PostgreSQL
and pgvector 1 GB each, the rest 256–512 MB.

## Status

Run behind Traefik with TLS on 2026-09-22 (1.17.1): the first-account
setup through `/install`, the console in a browser, a marketplace plugin and a
model provider, a workflow with code, HTTP and LLM nodes through the service API,
a restart, and the restore above. Full log in
[`UPSTREAM.md`](UPSTREAM.md#verification-performed-2026-09-22).

## Try it locally

```bash
ops/init.sh
mkdir -p volumes/{storage,plugin_daemon,db,pgvector,redis}
sudo chown 1001:1001 volumes/storage volumes/plugin_daemon; sudo chown 999:999 volumes/redis
docker compose -f docker-compose.local.yml up -d
# http://localhost:3000/install — setup password in .secrets/init_password.txt
docker compose -f docker-compose.local.yml down
```

Ports 3000 (console) and 5001 (API) bind to `127.0.0.1`; the console talks to the API
by absolute URL. Traefik and the Docker Secrets mechanism are not used.

## Backup

Three data sets and the secrets:

```bash
docker exec dify-db pg_dump -U postgres dify > dify.sql
docker exec dify-db pg_dump -U postgres dify_plugin > dify_plugin.sql
docker exec dify-pgvector pg_dump -U postgres dify > dify_vectors.sql
docker compose stop dify-api worker worker-beat plugin-daemon
tar -C volumes -czf dify-volumes.tar.gz storage plugin_daemon
docker compose start dify-api worker worker-beat plugin-daemon
```

`storage` holds uploaded files, `plugin_daemon` the installed plugin packages. Keep
`.secrets/secret_key.txt` with the dumps: without it stored provider credentials
cannot be decrypted. The API service is `dify-api`; `docker compose stop` skips an
unknown name without an error, so a misspelt name leaves it writing during the
archive.

Restore into empty volumes, with the secrets put back unchanged:

```bash
mkdir -p volumes/{storage,plugin_daemon,db,pgvector,redis}
sudo chown 1001:1001 volumes/storage volumes/plugin_daemon
sudo chown 999:999 volumes/redis
docker compose up -d db pgvector
docker exec -i dify-db psql -U postgres -d dify < dify.sql
docker exec -i dify-db psql -U postgres -d dify_plugin < dify_plugin.sql
docker exec -i dify-pgvector psql -U postgres -d dify < dify_vectors.sql
sudo tar -C volumes -xzf dify-volumes.tar.gz
docker compose up -d
```

The first start of `db` creates both `dify` and `dify_plugin`, so the dumps load
into existing, empty databases.
