# Ollama

A local model runtime. It pulls models from the Ollama registry, keeps them on
disk, loads them on demand and serves them over an HTTP API — the native
`/api/*` endpoints and an OpenAI-compatible `/v1`. Runs on CPU out of the box;
an overlay adds NVIDIA GPU access.

Where [vLLM](../vllm/) is built for throughput on a GPU host, Ollama is the
simple option: one binary, models pulled by name, sensible defaults, and it
works on a machine with no GPU at all.

## Architecture

```text
Internet → Traefik (TLS, port 443) → ollama :11434
Other containers on proxy-public   → ollama :11434
```

One container, no database. Models and the server's key live in
`./volumes/data`.

## Setup

```bash
cp .env.example .env
mkdir -p volumes/data
sudo chown 1000:1000 volumes/data          # the container runs as uid 1000
docker compose up -d
docker compose exec ollama ollama pull smollm2:135m
```

Set `APP_TRAEFIK_HOST` in `.env`, then call it:

```bash
curl https://ollama.example.com/api/generate \
  -d '{"model":"smollm2:135m","prompt":"The capital of France is","stream":false}'
```

Any OpenAI client works against `https://ollama.example.com/v1` with any
non-empty API key string — the server ignores it.

## Access model — there is no authentication

Ollama does not authenticate anyone. Two things follow:

- **The Traefik access policy is the only gate on the route.**
  `APP_TRAEFIK_ACCESS` defaults to `acc-private` (LAN plus VPN). Whoever it
  admits can run inference on your hardware, pull arbitrary models from the
  internet onto your disk, and delete the ones you have.
- **Every container on `proxy-public` reaches the API directly**, past Traefik
  and its policy. Verified: from a second container on that network,
  `DELETE /api/delete` with no credentials returned `200` and the model was
  gone. Do not run stacks you do not trust on the shared network next to it.

If you need per-user access, put an identity-aware layer in front of the route
— [Authentik](../../core/authentik/) forward-auth is the reference
implementation here — rather than widening the access policy.

## CPU and GPU

**CPU** is the default and is what has been tested. With no GPU the server logs
`inference compute id=cpu` and uses every core it is given
(`OLLAMA_CPUS`). Speed depends on the model: a 135M-parameter model answered
immediately on six cores, a multi-billion-parameter one will be slow.

**NVIDIA GPU** is an opt-in overlay, `docker-compose.gpu.yml`, which adds a
device reservation:

```bash
# in .env
COMPOSE_FILE=docker-compose.yml:docker-compose.gpu.yml
```

It needs an NVIDIA driver and the NVIDIA Container Toolkit on the host. The
reservation makes `docker compose up` fail loudly if no GPU is available
instead of silently falling back to CPU. **The overlay has not been run on GPU
hardware in this repository** — it merges cleanly with the base file, and that
is all that has been checked. The image already bundles the CUDA libraries, so
no separate GPU image exists.

## Memory

A loaded model, its context window and the runtime all count against
`OLLAMA_MEMORY` (default `8g`). If a model does not fit, the process is killed
mid-request. Size the limit to the largest model you will run plus one to two
GB, and more for long contexts. `OLLAMA_KEEP_ALIVE` controls how long an idle
model stays resident.

Requests to a model are served one at a time by default
(`OLLAMA_NUM_PARALLEL` is 1): a second request waits until the first has
finished. A 3.2B-parameter model peaked at 2.5 GiB on CPU.

## Network egress

The container needs outbound access to pull models from the registry. That is
why it sits on `proxy-public` rather than an internal network.
`OLLAMA_NO_CLOUD=1` is set, which turns off Ollama's cloud features (remote
inference and web search). The server also logs a scheduled "model
recommendations cache" refresh at start; whether that makes an outbound request
has not been traced.

## Status

Run behind Traefik with TLS on 2026-09-21 (0.34.2): models up to 3.2B
parameters pulled and served through the route on CPU, two concurrent requests,
a restart, and a restore of `volumes/data`. Nothing has run on a GPU. Full log
in [`UPSTREAM.md`](UPSTREAM.md#verification-performed-2026-09-21).

## Try it locally

```bash
cp .env.local.example .env.local
mkdir -p volumes/local/data
docker compose -f docker-compose.local.yml --env-file .env.local up -d
docker compose -f docker-compose.local.yml --env-file .env.local exec ollama ollama pull smollm2:135m
curl http://localhost:11434/api/generate \
  -d '{"model":"smollm2:135m","prompt":"The capital of France is","stream":false}'
docker compose -f docker-compose.local.yml --env-file .env.local down
```

## Backup

| | |
|---|---|
| **Database** | None |
| **State** | `./volumes/data/models` — downloaded models |
| **Reproducible** | Models are, from the registry, by name. Record `ollama list` instead of backing them up unless a model is custom-built or the registry is unreachable |
| **Key** | `./volumes/data/.ollama/id_ed25519` — the server's identity key, regenerated when missing; it matters only if you push models to the registry |
| **Quiescing** | Not needed |

Custom models created with `ollama create` exist only in `volumes/data/models`;
back that directory up if you have any. **Restore order:** put the directory
back, then start the container.
