# Langfuse

LLM observability: traces, generations, scores, prompts and evaluations from any
application that uses a Langfuse SDK or sends OpenTelemetry. Standalone — it does
not depend on, or assume, any model server, gateway or chat application; whatever
instruments its code to send traces is the client. Upstream:
[Langfuse](https://github.com/langfuse/langfuse).

## Architecture

```text
SDK / OpenTelemetry clients ─┐
Browser ─────────────────────┴→ Traefik (TLS) → langfuse-web :3000
                                                    │
                                     app-internal (internal: true)
                                                    │
   langfuse-worker ── PostgreSQL · ClickHouse · Redis · MinIO
```

Six services, every one required by upstream's supported setup: the web service
(UI and API), the worker (asynchronous ingestion), PostgreSQL (accounts, projects,
prompts), ClickHouse (traces and observations), Redis (queue and cache) and MinIO
(event payloads). Only `langfuse-web` is on `proxy-public`; the rest have no route
out.

## Setup

```bash
cp .env.example .env            # host name, admin e-mail
ops/init.sh admin@example.com   # nine secrets in .secrets/
mkdir -p volumes/{postgres,clickhouse,redis,minio}
sudo chown 101:101 volumes/clickhouse
sudo chown 999:999 volumes/redis
sudo chown 1000:1000 volumes/minio
docker compose up -d
```

The first start runs the PostgreSQL and ClickHouse migrations and takes a few
minutes; the web service reports healthy after that. Log in at the configured host
with `INIT_USER_EMAIL` and `.secrets/admin_password.txt`. The same first start
creates an organisation, a project and its API key pair from
`.secrets/project_public_key.txt` and `.secrets/project_secret_key.txt`.

Point an application at it with those two keys and the host as the base URL.
OpenTelemetry clients send to `https://<host>/api/public/otel/v1/traces` with HTTP
Basic auth (public key as user, secret key as password) and the header
`x-langfuse-ingestion-version: 4`.

## Credentials

| Who | Credential | Where it lives |
|---|---|---|
| Administrator | E-mail + password | Created once on the first start of an empty database from `INIT_USER_EMAIL` and the Docker Secret `ADMIN_PASSWORD`. Changing either later does not change the account |
| Other users | Invited by the administrator | Database. Self-signup is off (`AUTH_DISABLE_SIGNUP`) |
| SDK / OTel client | Project public + secret key | Provisioned from Docker Secrets; more pairs are created in the UI |
| Stored LLM credentials | Encrypted with `ENCRYPTION_KEY` | Docker Secret. Do not change it once credentials are stored |
| API-key hashing | `SALT` | Docker Secret. Do not change it: existing keys stop working |
| Sessions | Signed with `NEXTAUTH_SECRET` | Docker Secret |

## Security notes

- **Secrets.** None of the images reads a secret from a file. `config/entrypoint.sh`
  exports each `NAME__FILE` variable's file as `NAME`; the values are absent from
  `docker inspect`. Redis reads its password from a config file written to tmpfs
  rather than a command-line argument.
- **`.secrets/` permissions.** Six containers with different uids read the files
  through bind mounts, so the files are mode 644 inside a mode 700 directory. Keep
  the directory closed to other host users.
- **Hardening.** Every service but PostgreSQL runs as an unprivileged uid with
  `read_only`, `cap_drop: ALL` and `no-new-privileges`; PostgreSQL keeps the five
  capabilities its entrypoint needs. No port is published. Only tmpfs mounts,
  the four data directories and ClickHouse's user-definition path are writable.
- **Network.** The five data services and the worker are on an internal network
  with no route out. `TELEMETRY_ENABLED=false`.
- **Media uploads.** MinIO is not routed, because SDK media uploads use
  pre-signed MinIO URLs that a client would have to reach directly. Text traces,
  scores and prompts are unaffected; uploading images or audio through the SDK's
  media API is not supported by this stack.
- **Access policy.** SDK clients send to the same host as the UI, so
  `APP_TRAEFIK_ACCESS` must include wherever the instrumented applications run.
  Requests to the API still need a project key (`401` without).

## Resources

Node's default heap (about 512 MB) is exhausted while `langfuse-web` starts; the
service is set to a 2 GB limit with `--max-old-space-size=1536`. ClickHouse creates
many threads, so its PID limit is 2000. With a single instrumented test
application, the six services together used roughly 1.9 GB after start.

## Status

`scaffolded` — see [UPSTREAM.md](UPSTREAM.md#verification-performed-2026-09-19).

## Local deployment validation

```bash
cp .env.local.example .env.local
ops/init.sh
mkdir -p volumes/{postgres,clickhouse,redis,minio}
sudo chown 101:101 volumes/clickhouse; sudo chown 999:999 volumes/redis; sudo chown 1000:1000 volumes/minio
docker compose -f docker-compose.local.yml --env-file .env.local up -d
# http://localhost:3000 — INIT_USER_EMAIL with .secrets/admin_password.txt
docker compose -f docker-compose.local.yml --env-file .env.local down
```

Port 3000 binds to `127.0.0.1`; Traefik and the Docker Secrets mechanism are not used.

## Backup

Back up all four data stores and the secrets. PostgreSQL and ClickHouse hold the
data; MinIO holds the raw event payloads; Redis holds only a queue.

```bash
docker exec langfuse-db pg_dump -U langfuse langfuse > langfuse-postgres.sql
docker compose stop langfuse-web langfuse-worker
tar -C volumes -czf langfuse-volumes.tar.gz clickhouse minio
docker compose start langfuse-web langfuse-worker
```

Keep `.secrets/salt.txt` and `.secrets/encryption_key.txt` with the dump: without
them API keys and stored credentials from the restored data no longer work.
Restore into empty volumes with `psql` and by unpacking the archive, place the
secrets back unchanged and run `docker compose up -d`. Restore is not exercised
here.
