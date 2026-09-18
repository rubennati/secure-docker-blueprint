# Upstream Reference

## Source

- **Image:** https://hub.docker.com/r/vllm/vllm-openai (CUDA) ·
  https://hub.docker.com/r/vllm/vllm-openai-cpu (CPU, used for local validation)
- **GitHub:** https://github.com/vllm-project/vllm
- **Docs:** https://docs.vllm.ai/
- **License:** Apache-2.0
- **Origin:** United States · vLLM project (originated at the UC Berkeley Sky Computing Lab) · non-EU
- **Based on version:** `v0.29.0`

No `Last verified` line yet — see [Verification performed](#verification-performed-2026-09-18)
below for exactly what has been exercised and what has not. The field
asserts the production file ran on a real host; it has not run on a GPU or
behind Traefik. This stack stays `scaffolded` until that happens.

## What we use

- Official image, pinned tag: `vllm/vllm-openai:v0.29.0` — CUDA 13.0.2, `amd64`
  and `arm64`, 8.67 GB compressed for `amd64`. Read from the registry
  (`docker buildx imagetools inspect`), **never pulled or run here**: it is
  larger than the free disk of the test VM and needs a GPU.
- From that config: no `USER` (root), entrypoint `vllm serve`, workdir
  `/vllm-workspace`, no exposed ports declared, `NVIDIA_VISIBLE_DEVICES=all`,
  `TORCH_CUDA_ARCH_LIST=7.5 8.0 8.6 8.9 9.0 10.0 12.0`.
- Local validation runs `vllm/vllm-openai-cpu:v0.29.0` (1.84 GB compressed):
  the same release and entrypoint, root by default, Python 3.12, with `curl`,
  `wget` and `bash`. It reports `0.29.0+cpu`.
- Configuration is by `vllm serve` arguments and `VLLM_*` variables. The API
  key is `--api-key` or `VLLM_API_KEY`; the compose file uses the variable so the
  key stays out of the process arguments.

## Architecture

```text
Internet → Traefik (TLS, port 443, path /v1/ only) → vllm :8000
```

## What we changed and why

| Change | Reason |
|--------|--------|
| Docker Secret for the API key (and an optional Hugging Face token), injected by `config/entrypoint.sh` | vLLM reads `VLLM_API_KEY` and `HF_TOKEN` from the environment; there is no `_FILE` variant |
| `shm_size: ${VLLM_SHM_SIZE}` (default `8g`) | With Docker's default 64 MiB `/dev/shm` the engine does not start: `Insufficient space in /dev/shm: 160 MiB required, 64 MiB free.` Reproduced on the CPU build with a 0.5B model and a single process |
| `TMPDIR`, `HOME`, `HF_HOME`, `VLLM_CACHE_ROOT`, `TORCHINDUCTOR_CACHE_DIR`, `TRITON_CACHE_DIR` all under `/cache` | With a read-only root filesystem the caches need a writable home (`OSError: [Errno 30] Read-only file system: '/cache/torchinductor'`). Docker's `tmpfs` is `noexec`, and TorchInductor writes generated code to a temporary `.so` and then loads it: `OSError: /tmp/….so: failed to map segment from shared object`. A volume is exec-capable. Both reproduced on the CPU build |
| `user: 1000:1000`, `read_only: true`, `cap_drop: ALL`, `no-new-privileges` | Held on the CPU build with real inference. **Not run on the CUDA image**, where Triton and FlashInfer compile GPU kernels at run time — see the README |
| `VLLM_NO_USAGE_STATS=1`, `DO_NOT_TRACK=1` | Turns off vLLM's usage reporting. The image sets `VLLM_USAGE_SOURCE=production-docker-image`, which tags that reporting |
| Traefik rule `Host(…) && PathPrefix(`/v1/`)` | `--api-key` covers only `/v1`, `/v2` and `/inference`; the rest of the server answers without it — see below |
| Healthcheck in Python, `start_period: 900s` | The CUDA image's tools are unknown; Python is in both builds. A first start downloads the model and compiles |
| GPU as a compose device reservation (`count: ${VLLM_GPU_COUNT}`) | Fails loudly on a host with no NVIDIA runtime instead of silently starting on CPU. `docker compose config` accepts `count: 1` from the variable |
| No `app-internal` network | There is no database or internal service to isolate |

## Authentication

Verified against the CPU build of v0.29.0 with a key set, no credentials sent:

| Request | Result |
|---|---|
| `GET /v1/models` | `401` without the key, `200` with it, `401` with a wrong one |
| `POST /v1/chat/completions` | `401` without the key |
| `GET /health`, `/version`, `/metrics`, `/load` | `200` |
| `POST /tokenize` | `200` |
| `POST /invocations` | `200`, **and it ran inference** |
| `GET /is_paused`, `POST /pause`, `POST /resume` | `404` in this configuration |

Upstream's security page names `/pooling`, `/classify`, `/score`, `/rerank`,
`/generative_scoring`, further control routes (`/abort_requests`,
`/update_weights`, `/scale_elastic_ep`) and, behind `--enable-tokenizer-info-endpoint`,
`/tokenizer_info` as unprotected too, and says not to rely on `--api-key` alone.
Those were not probed individually. The gRPC interface, off unless `--grpc-port`
is given, has no authentication at all.

Through a Traefik running the same router rule in front of a hardened server:
`/v1/models` → `401` without the key and `200` with it; `/health`, `/version`,
`/metrics`, `/load`, `/tokenize`, `/docs`, `/openapi.json`, `POST /invocations`,
`/v1/../metrics` and `//metrics` → `404` (Traefik); `/V1/models` → `404`; a
different `Host` → `404`. `/v1/..%2fmetrics`, `/v1/%2e%2e%2fmetrics` and
`/v1/..%2finvocations` → `401` — they reach vLLM as `/v1/…` paths. Sent directly
to vLLM they also returned `401`, so the server does not decode them into the
unprotected routes.

## Data egress

- Model weights, tokenizer files and config come from Hugging Face on first
  start (`HF_HOME` on the cache volume). Gated models send the token.
- Usage reporting is disabled above.

## Verification performed (2026-09-18)

Against the CPU build (`vllm/vllm-openai-cpu:v0.29.0`), on an x86_64 Docker VM
with six AVX2-only cores and 12 GB of memory, with `Qwen/Qwen2.5-0.5B-Instruct`
in float32:

- Registry metadata and manifest sizes for both images; `docker compose config`
  on both compose files, including the GPU reservation
- Started as root first: real inference worked; the engine needed about five
  minutes to initialise on this CPU
- Started hardened — `--user 1000:1000 --read-only --tmpfs /tmp --cap-drop ALL
  --security-opt no-new-privileges`, key in `VLLM_API_KEY`, all caches and
  `TMPDIR` on one writable volume — reached `healthy`, answered
  `The capital of Austria is Vienna.` through `/v1/chat/completions` (34 s) and
  passed the compose healthcheck command
- `config/entrypoint.sh` run against the image with the secrets mounted at
  `/run/secrets/`: the key is exported as `VLLM_API_KEY`; an empty
  `HF_TOKEN` file leaves `HF_TOKEN` unset and a non-empty one exports it; a
  missing key file exits `1` without running the command
- The endpoint-by-endpoint authentication results and the Traefik allowlist
  results above
- The two startup failures above, reproduced and fixed

**Not exercised:** the CUDA image, any GPU, the NVIDIA runtime, tensor
parallelism, the GPU device reservation on a real host, uid 1000 and a
read-only root on the CUDA build, the wrapper feeding a running server (the
served runs passed the key as an environment variable), downloading a gated
model with a token, Traefik with the repository's real middlewares and TLS, models
larger than 0.5B, concurrent requests, and the local compose file's first-start
duration on other hardware.

## Upgrade checklist

1. Read the release notes for breaking changes: https://github.com/vllm-project/vllm/releases
2. Check the GitHub Security tab for advisories against the current version
3. Bump `APP_TAG` in `.env.example` and `.env.local.example`
4. `docker compose pull && docker compose up -d` — expect a fresh kernel compile;
   clear `volumes/cache/vllm`, `volumes/cache/torchinductor` and
   `volumes/cache/triton` if a start fails after an upgrade
5. Verify `/v1/models` with the key, then one request
6. Re-check which paths answer without the key; the list changes between releases
7. Update **Based on version** above — and add **Last verified** only if the
   upgrade was actually exercised on a real install

## Useful commands

```bash
docker compose logs vllm --follow
docker compose exec vllm python3 -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/version').read())"
```
