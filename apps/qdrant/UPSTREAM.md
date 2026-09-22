# Upstream Reference

## Source

- **Image:** https://hub.docker.com/r/qdrant/qdrant
- **GitHub:** https://github.com/qdrant/qdrant
- **Docs:** https://qdrant.tech/documentation/
- **License:** Apache-2.0
- **Decision facts checked:** not yet
- **Origin:** Germany · Qdrant Solutions GmbH (Berlin) · EU
- **Domain:** AI and local AI
- **Role:** Vector database: collections, similarity search with filters, snapshots
- **Based on version:** `v1.19.1`
- **Last verified:** 2026-09-21 (v1.19.1-unprivileged) — behind Traefik with TLS: the REST API through the route, gRPC with 100,000 points, snapshot recovery, a restart, and the README's restore

## What we use

- Official image, pinned tag: `qdrant/qdrant:v1.19.1-unprivileged` (`amd64` and
  `arm64`, 74 MB). The `-unprivileged` variant runs as `qdrant` (uid/gid 1000);
  the plain tag runs as root.
- Command `./entrypoint.sh` in `/qdrant`, ports `6333` (REST, dashboard) and
  `6334` (gRPC). RUN_MODE is `production`.
- Bash is present, curl and wget are not — the healthcheck uses bash's
  `/dev/tcp` to request `/readyz`.

## Architecture

```text
Internet → Traefik (TLS, port 443) → qdrant :6333
```

## What we changed and why

| Change | Reason |
|--------|--------|
| Docker Secret for the API key, injected by `config/entrypoint.sh` | Qdrant reads `QDRANT__SERVICE__API_KEY` from the environment and has no `_FILE` variant. Without a key every endpoint is open |
| `QDRANT_INIT_FILE_PATH=/qdrant/storage/.qdrant-initialized` | Qdrant writes `.qdrant-initialized` into its working directory. On a read-only root filesystem that write fails and the process **panics at startup** (`Failed to create init file indicator … Read-only file system`). Pointing the file into the storage volume fixes it |
| `read_only: true`, `tmpfs: [/tmp]`, volumes for `/qdrant/storage` and `/qdrant/snapshots` | Verified: search, snapshots and restart all work with nothing else writable |
| `cap_drop: ALL`, `no-new-privileges` | Verified working, no capability added back |
| `QDRANT__TELEMETRY_DISABLED=true` | Qdrant reports anonymous usage by default; the log confirms `Telemetry reporting disabled` |
| No `app-internal` network | Qdrant is the datastore and exposes an API other stacks consume; there is no second service to isolate. It sits on `proxy-public` like the other API services here |

## Authentication

One API key covers the REST API and gRPC. Health endpoints `/healthz`, `/livez`
and `/readyz` answer without it; `/metrics` returned `401` (verified). The
dashboard's static page loads without a key. A separate read-only key exists
(`QDRANT__SERVICE__READ_ONLY_API_KEY`) and is not configured here or tested.
TLS is off inside the container (`TLS disabled for REST API`, `… for gRPC API`);
Traefik terminates it.

## Data egress

Anonymous telemetry, disabled above. No other outbound connection appears in
the log; network traffic itself was not captured.

## Verification performed (2026-09-21)

Behind Traefik with TLS, with the shipped `acc-private` and `sec-2`, and
`./volumes` on a local ext4 filesystem:

- A client outside the access policy's ranges got `403` on the route, over IPv4
  and IPv6
- `healthy` under the same hardening; no FUSE warning in the log
- Through the route: `/healthz`, `/readyz` and `/dashboard/` `200` without a
  key; `/collections` and `/metrics` `401` without a key and with a wrong one;
  a collection created, four points upserted, plain and filtered queries
  returned the expected nearest points
- gRPC: from a peer container, `qdrant-client` with `prefer_grpc=True` created a
  768-dimension collection and upserted 100,000 points in 32 s; indexing
  finished after 168 s; a filtered search answered in 147 ms
- Memory for that collection: 415 MiB peak while indexing, 193 MiB afterwards;
  359 MB in `volumes/storage`
- Read-only key, set through a temporary override
  (`QDRANT__SERVICE__READ_ONLY_API_KEY`): listing, `query` and `count` `200`;
  upsert, collection create, delete and snapshot `403`
- Snapshot of both collections through the API, collection deleted,
  `PUT /collections/demo/snapshots/recover` with
  `{"location":"file:///qdrant/snapshots/demo/<file>"}` — all four points back
- Restore as the README describes: key file and `volumes/snapshots` kept,
  `volumes/storage` replaced by an empty directory, container started, both
  collections recovered from their snapshots (the 375 MB snapshot in 1.7 s),
  counts `4` and `100000`, search results unchanged
- Both collections intact after `docker compose down` and `up -d`

**Not yet exercised:** the read-only key as shipped configuration — the stack
does not set it.

## Verification performed (2026-09-18)

Against the local test stack, and against the production `docker-compose.yml`
on a throwaway `proxy-public` network without Traefik:

- The pinned image pulled and started; the log shows `Distributed mode
  disabled`, both listeners up and `Telemetry reporting disabled`
- `healthy` under `read_only`, `cap_drop: ALL`, `no-new-privileges` and uid
  1000; no privileged container, no published port on the production file;
  the memory and pids limits applied; the API key is absent from the
  container's configured environment
- From a second container by service name: created collection `demo` (4
  dimensions, cosine), upserted four points with payloads, and searched —
  nearest neighbour correct (`0.998`), a `city = Berlin` filter returned exactly
  the two Berlin points, exact count `4`
- A snapshot was written to `/qdrant/snapshots` under `read_only`
- No key and a wrong key both returned `401`; `/healthz`, `/livez` and
  `/readyz` returned `200`; `/metrics` returned `401`
- The collection, points and snapshot were intact after `docker compose restart`
  and again after `docker compose down` followed by `up -d`
- Port `6334` accepted a connection from a peer container
- Without `QDRANT_INIT_FILE_PATH` under `read_only` the process panics at
  startup (reproduced)
- On the macOS test host's virtiofs bind mount Qdrant logs `FUSE filesystems
  may cause data corruption`; a Docker named volume on the VM's disk did not

## Upgrade checklist

1. Read the release notes for breaking changes: https://github.com/qdrant/qdrant/releases
2. Check the GitHub Security tab for advisories against the current version
3. Take a snapshot of every collection and back up `volumes/snapshots`
4. Bump `APP_TAG` in `.env.example` and `.env.local.example`
5. `docker compose pull && docker compose up -d`
6. Verify `/readyz`, then run a search against an existing collection
7. Update **Based on version** above — and add **Last verified** only if the
   upgrade was actually exercised on a real install

The release notes name any version-specific upgrade requirement; read them for
every version between the old pin and the new one.

## Useful commands

```bash
docker compose logs qdrant --follow
curl -H "api-key: $(cat .secrets/qdrant_api_key.txt)" https://qdrant.example.com/collections
```
