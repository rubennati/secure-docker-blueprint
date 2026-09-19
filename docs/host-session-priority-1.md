# Host session — the Priority 1 stacks

What is left before the stacks added in the Priority 1 expansion can carry a
`Last verified` line: each was run against its own real dependencies, none has run
behind Traefik with TLS on a real host, and none has had a restore performed. This is
that work in one ordered run. Every block is independent; if one fails, note it and
move on.

> Add `Last verified` to a stack's `UPSTREAM.md` only after its block's Traefik/TLS
> check passed, and update `docs/maintenance-log.md` as you go, not afterwards.

---

## Before you start

- [ ] Traefik running on the host, `proxy-public` present, the certificate strategy
  selected
- [ ] A DNS name per stack under a domain you control, pointing at the host
- [ ] A client that satisfies each stack's access class (`acc-private` or
  `acc-tailscale`), and one that does not — the second must be refused
- [ ] Enough disk: the AI images total roughly 30 GB; Dify alone is about 10 GB

## Every stack — the same five checks

1. `cp .env.example .env`, set the host name, run `ops/init.sh` where the stack has one
2. `docker compose up -d`; every service reaches `healthy`
3. Through the real host name: valid certificate, and the refused client gets a
   `403`, not a page
4. The stack's own smoke test (below), through Traefik
5. `docker compose down && docker compose up -d`, then the smoke test again; then the
   restore procedure from the stack's README `## Backup`

## Block 1 · Model and vector services (~60 min)

- [ ] **`apps/ollama`** — pull a model larger than 135M parameters, chat through the
  route; two concurrent requests; on a GPU host, the overlay reserves the device
- [ ] **`apps/vllm`** — GPU host only. The CUDA image starts as uid 1000 with a
  read-only root; the wrapper feeds the running server; a real `/v1` completion through
  Traefik; `/invocations` is not reachable through the router
- [ ] **`apps/qdrant`** — create a collection through the route; a gRPC call; the
  read-only key; snapshot, delete the collection, `snapshots/recover`; note memory for
  a collection of realistic size; confirm `./volumes` works on the host's filesystem

## Block 2 · Gateways and chat (~75 min)

- [ ] **`apps/litellm`** — add a hosted provider through the admin API (the credential
  is stored encrypted); a virtual key restricted to it; log in to `/ui` with the master
  key; dump and restore the database, keeping `litellm_salt_key.txt`
- [ ] **`apps/agentgateway`** — a hosted provider with `backendAuth`; an MCP target
  through `/mcp`; restore `volumes/data` and the config
- [ ] **`apps/open-webui`** — log in through the browser, upload a document and ask
  about it; a second backend (LiteLLM or another OpenAI-compatible endpoint); set
  `HF_HUB_OFFLINE=1` after the first start; restore `volumes/data`

## Block 3 · Dify and Langfuse (~90 min)

- [ ] **`apps/dify`** — keep the router at `acc-deny` until `/install` is done; the
  console in a browser; a workflow app with a code node and an HTTP node; a hosted
  model provider; `volumes/plugin_daemon` owned by uid 1001 and a plugin install
  succeeding; the three database dumps restored into empty volumes
- [ ] **`monitoring/langfuse`** — the browser UI; an SDK client (not only
  OpenTelemetry) sending to the routed host; a prompt saved and fetched; the ClickHouse
  and MinIO volumes plus the PostgreSQL dump restored; note resource use with a real
  application sending traces

## Block 4 · Automation and test tools (~60 min)

- [ ] **`apps/windmill`** — run `ops/bootstrap-admin.sh`; a Python and a native job
  through Traefik; the native worker making an outbound call; on a bare-metal host,
  whether NSJAIL (`DISABLE_NSJAIL=false`) runs under `cap_drop: ALL`; restore Postgres
- [ ] **`apps/greenmail`** — the API through the route; SMTPS `:3465` and POP3S `:3995`
  with a TLS client
- [ ] **`apps/docling-serve`** — convert a real PDF through the route; the entrypoint
  wrapper injects the key

## Block 5 · Close

- [ ] For each stack that passed: add `Last verified` (date, version) to `UPSTREAM.md`,
  run `python3 scripts/ci/lifecycle-report.py --write`, commit
- [ ] For each that did not: write the reason into the stack's README status line and
  leave it `scaffolded`
- [ ] Log the run in `docs/maintenance-log.md`

## What "done" means

A stack is done when its route answers over TLS, its refused client is refused, its
smoke test passes before and after a restart, and its restore has produced a working
instance. Anything short of that stays `scaffolded`, with the missing step named.
