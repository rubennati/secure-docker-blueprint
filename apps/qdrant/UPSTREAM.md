# Upstream Reference

## Source

- **Image:** https://hub.docker.com/r/qdrant/qdrant
- **GitHub:** https://github.com/qdrant/qdrant
- **Docs:** https://qdrant.tech/documentation/
- **License:** Apache-2.0
- **Origin:** Germany · Qdrant Solutions GmbH (Berlin) · EU
- **Based on version:** `v1.19.1`

No `Last verified` line yet — see [Verification performed](#verification-performed-2026-09-18)
below for exactly what has been exercised and what has not. The field
asserts Traefik/TLS routing was confirmed on a real host, which this session
could not do; setting it early would claim evidence that does not exist. This
stack stays `scaffolded` until that happens.

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

**Not yet exercised:** Traefik routing, TLS and the dashboard through it;
gRPC calls (only that the port accepts a connection); the read-only key;
snapshot recovery (`snapshots/recover`); collections large enough to size
memory; a real Linux host filesystem under `./volumes`.

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
