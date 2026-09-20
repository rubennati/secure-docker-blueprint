# vLLM

High-throughput, OpenAI-compatible model serving on an NVIDIA GPU. It loads a
model from Hugging Face, batches concurrent requests continuously and serves
`/v1/chat/completions`, `/v1/completions`, `/v1/embeddings` and the rest of the
OpenAI API.

Where [Ollama](../ollama/) is the simple option that also runs on a laptop CPU,
vLLM is built for throughput and concurrency on a GPU host. It is the wrong
tool for a machine with no GPU.

> **Not verified on GPU hardware.** The production file targets the CUDA image,
> which has not been pulled or run in this repository — no GPU was available.
> Everything about the server's behaviour, its authentication and its
> hardening was tested against the **CPU build of the same release**. See
> [What has and has not been verified](#what-has-and-has-not-been-verified).

## Requirements

- An NVIDIA GPU of the Turing generation or newer (the image is built for
  compute capabilities 7.5 to 12.0), the NVIDIA Container Toolkit, and a driver
  that supports CUDA 13.0 — the image's `NVIDIA_REQUIRE_CUDA` names driver
  branches 535, 550, 565, 570 and 575.
- Room for the model: its weights plus the KV cache must fit in VRAM
  (`VLLM_GPU_MEMORY_UTILIZATION` of it).
- Disk for the image (8.7 GB compressed) and for `./volumes/cache`, which holds
  the downloaded weights.

## Architecture

```text
Internet → Traefik (TLS, port 443) → vllm :8000    only paths under /v1/
Other containers on proxy-public   → vllm :8000    every path
```

One container, no database. The model, Hugging Face cache and compiled kernels
live in `./volumes/cache`.

## Setup

```bash
cp .env.example .env
mkdir -p .secrets volumes/cache
sudo chown 1000:1000 volumes/cache                # the container runs as uid 1000
openssl rand -hex 24 > .secrets/vllm_api_key.txt
touch .secrets/hf_token.txt                       # or put a Hugging Face token in it
docker compose up -d
docker compose logs -f vllm
```

Set `APP_TRAEFIK_HOST` and `VLLM_MODEL` in `.env`. The first start downloads the
model and compiles kernels, which takes minutes; the healthcheck waits up to 15
minutes before it starts counting failures.

```bash
curl https://vllm.example.com/v1/chat/completions \
  -H "Authorization: Bearer $(cat .secrets/vllm_api_key.txt)" \
  -H 'Content-Type: application/json' \
  -d '{"model":"default","messages":[{"role":"user","content":"Hello"}]}'
```

## Access model

vLLM's API key does **not** protect the whole server. With a key set, the
`/v1/*` API answers `401` without it — and these paths answer with no
credentials at all (tested against v0.29.0):

| Path | Without a key |
|---|---|
| `POST /invocations` | **runs inference** — a SageMaker-style route to the same engine |
| `POST /tokenize` | tokenises text |
| `GET /metrics`, `/load`, `/version`, `/health` | answers |

Upstream's own security guide lists more unprotected routes (`/pooling`,
`/classify`, `/score`, `/rerank`, and control routes such as `/pause` and
`/update_weights` in some configurations). `/pause` returned `404` in the default
configuration tested here. Upstream states plainly not to rely on `--api-key`
alone.

What this stack does about it:

- **The Traefik router forwards `/v1/` and nothing else.** Through it, `/health`,
  `/metrics`, `/invocations`, `/tokenize`, `/docs` and `/openapi.json` return
  `404`, and so do `/v1/../metrics` and `//metrics`. Encoded traversal such as
  `/v1/..%2fmetrics` reaches vLLM as a `/v1/…` path and gets `401` — tested with
  a Traefik running the same rule in front of a real server. `/health` is not
  reachable from outside on purpose; the container healthcheck uses it.
- **`APP_TRAEFIK_ACCESS` defaults to `acc-private`** (LAN plus VPN), on top of the
  key.

What it cannot do: **every container on `proxy-public` reaches all of vLLM's
paths directly, past Traefik** — including `/invocations`, which needs no key.
Treat the shared network as trusted, or do not put untrusted stacks beside this
one. gRPC is off unless `--grpc-port` is set, and it is not set.

## What has and has not been verified

Verified, against `vllm/vllm-openai-cpu:v0.29.0` (the CPU build of this release)
on an x86_64 Docker VM with six AVX2 cores:

- real inference through `/v1/chat/completions` with a 0.5B model
  (`The capital of Austria is Vienna.`), key supplied through `VLLM_API_KEY`;
- `read_only`, `cap_drop: ALL`, `no-new-privileges` and uid 1000, with every
  cache and temporary file on `/cache`;
- the authentication behaviour and the Traefik allowlist above;
- that Docker's default 64 MiB `/dev/shm` stops the engine from starting, and
  that a `noexec` `/tmp` stops it during kernel compilation — both fixed in the
  compose file, see [`UPSTREAM.md`](UPSTREAM.md#what-we-changed-and-why).

**Not verified — no GPU was available:** the CUDA image itself; the GPU device
reservation and the NVIDIA runtime; whether uid 1000 and a read-only root
filesystem hold on the CUDA build, where Triton and FlashInfer compile GPU
kernels at run time; the Python healthcheck inside the CUDA image; tensor
parallelism across more than one GPU; first-start time and memory sizing for a
real model. The hardened settings are a first-run hypothesis for the CUDA
image, not a result. If the first GPU start fails, the error names the path or
permission at fault — the likely places are directories outside `/cache`. Fix
that path, or as a last resort drop `read_only: true`, and record what you found
in `UPSTREAM.md`.

## Status

`scaffolded`. See above; nothing has run on a GPU, and Traefik routing and TLS
have not been run against a real host. Full log in
[`UPSTREAM.md`](UPSTREAM.md#verification-performed-2026-09-18).

## Try it locally

`docker-compose.local.yml` runs the CPU build so the server can be tried with no
GPU. It is slow: on six AVX2 cores a 0.5B model took about five minutes to
start and about half a minute to answer a short prompt.

```bash
cp .env.local.example .env.local      # set VLLM_API_KEY: openssl rand -hex 24
mkdir -p volumes/local/cache
docker compose -f docker-compose.local.yml --env-file .env.local up -d
curl http://localhost:8000/v1/models -H "Authorization: Bearer $VLLM_API_KEY"
docker compose -f docker-compose.local.yml --env-file .env.local down
```

The CPU build needs no NVIDIA runtime and reports `GPU KV cache` in its logs
even though it uses none — that is upstream's wording.

## Backup

| | |
|---|---|
| **Database** | None |
| **State** | None worth backing up |
| **Reproducible** | `./volumes/cache` — weights, Hugging Face cache and compiled kernels, all re-created on the next start |
| **Secrets** | `.secrets/vllm_api_key.txt`, `.secrets/hf_token.txt` — back them up with the other secrets |
| **Quiescing** | Not needed |

Do not share `./volumes/cache` with another container or restore it from
storage you do not trust: vLLM loads its contents without integrity
checks. **Restore order:** the secrets, then start the container; it downloads
the model again.
