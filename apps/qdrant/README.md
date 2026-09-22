# Qdrant

A standalone vector database. It stores collections of vectors with JSON
payloads and answers nearest-neighbour searches, optionally filtered on the
payload — the storage half of semantic search and retrieval-augmented
generation, usable by any client that speaks its REST or gRPC API.

Independent of the other AI stacks here: nothing needs Ollama or vLLM to use
it, and it does not call them.

## Architecture

```text
Internet → Traefik (TLS, port 443) → qdrant :6333   (REST API, /dashboard)
Other containers on proxy-public   → qdrant :6333   REST
                                   → qdrant :6334   gRPC
```

One container, no separate database — Qdrant is the datastore. Data lives in
`./volumes/storage` and snapshots in `./volumes/snapshots`.

## Setup

```bash
cp .env.example .env
mkdir -p .secrets volumes/storage volumes/snapshots
sudo chown 1000:1000 volumes/storage volumes/snapshots   # the image runs as uid 1000
openssl rand -hex 24 > .secrets/qdrant_api_key.txt
docker compose up -d
```

Set `APP_TRAEFIK_HOST` in `.env`. Every request must carry the key as the
`api-key` header:

```bash
curl -H "api-key: $(cat .secrets/qdrant_api_key.txt)" https://qdrant.example.com/collections
```

Only `/healthz`, `/livez` and `/readyz` answer without it; `/metrics` and the
whole API return `401`. The `/dashboard` page itself loads without a key; the API calls it
makes need one.

## Access model

- **The API key is the control.** Without one Qdrant is fully open, which is why
  the stack refuses to start without the secret file.
- **The Traefik policy narrows who can try.** `APP_TRAEFIK_ACCESS` defaults to
  `acc-private` (LAN plus VPN).
- **Other stacks reach it directly on `proxy-public`**, by service name, on both
  ports, past Traefik — still with the key. gRPC (`6334`) is enabled by default
  and is not routed through Traefik; it is reachable from any container on the
  shared network and needs the same key.
- **The key is all-or-nothing.** One key grants full access, including deleting
  collections. Qdrant also supports a separate read-only key
  (`QDRANT__SERVICE__READ_ONLY_API_KEY`); this stack does not configure it.
- **Telemetry is off** (`QDRANT__TELEMETRY_DISABLED=true`); by default Qdrant
  reports anonymous usage.

## Storage filesystem

Qdrant checks the storage path at start and logs `FUSE filesystems may cause
data corruption due to caching issues` when it sits on a FUSE or network
filesystem. Use a local disk. The message appeared on the macOS test host, where
Docker bind mounts go through virtiofs, and was absent with a Docker named
volume on the VM's own disk. On a normal Linux host with a local filesystem
under `./volumes` it does not appear.

## Status

Run behind Traefik with TLS on 2026-09-21 (v1.19.1): the REST API
through the route, gRPC from a peer container with a 100,000-point collection,
the read-only key through an override, snapshot recovery, a restart, and the
restore below. Full log in
[`UPSTREAM.md`](UPSTREAM.md#verification-performed-2026-09-21).

## Try it locally

```bash
cp .env.local.example .env.local       # set QDRANT_API_KEY: openssl rand -hex 24
mkdir -p volumes/local/storage volumes/local/snapshots
docker compose -f docker-compose.local.yml --env-file .env.local up -d
curl -H "api-key: $QDRANT_API_KEY" http://localhost:6333/collections
docker compose -f docker-compose.local.yml --env-file .env.local down
```

## Backup

| | |
|---|---|
| **Database** | Qdrant itself — no separate engine |
| **State** | `./volumes/storage` (collections, indexes, raft state) and `./volumes/snapshots` |
| **Secret** | `.secrets/qdrant_api_key.txt` — back it up with the other secrets |
| **Reproducible** | Only if every vector can be regenerated from the source data; embedding again costs model time |
| **Quiescing** | Do not copy `volumes/storage` while the container is writing. Take a snapshot instead |

Create a consistent snapshot through the API, then back up `volumes/snapshots`:

```bash
curl -X POST -H "api-key: $(cat .secrets/qdrant_api_key.txt)" \
  https://qdrant.example.com/collections/<name>/snapshots
```

Add `./volumes/snapshots` to the borgmatic source list; the key belongs in the
same repository as the other `.secrets/` files.

**Restore order:** put the key file and `volumes/snapshots` back, start the
container, then recover each collection from its snapshot:

```bash
curl -X PUT -H "api-key: $(cat .secrets/qdrant_api_key.txt)" \
  -H 'Content-Type: application/json' \
  https://qdrant.example.com/collections/<name>/snapshots/recover \
  -d '{"location":"file:///qdrant/snapshots/<name>/<snapshot-file>"}'
```

Copying a stopped instance's `volumes/storage` back also works when nothing was
writing at the time. Full architecture: [`backup/README.md`](../../backup/README.md).
