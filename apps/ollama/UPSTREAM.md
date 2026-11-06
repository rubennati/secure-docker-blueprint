# Upstream Reference

## Source

- **Image:** https://hub.docker.com/r/ollama/ollama
- **GitHub:** https://github.com/ollama/ollama
- **Docs:** https://docs.ollama.com/
- **License:** MIT
- **Decision facts checked:** not yet
- **Origin:** United States · Ollama Inc. (California) · non-EU
- **Domain:** AI and local AI
- **Role:** Local model runtime that pulls models by name and serves them on CPU or an NVIDIA GPU
- **Based on version:** `0.40.14`
- **Last verified:** 2026-09-21 (0.34.2) — behind Traefik with TLS: models to 3.2B parameters pulled and served through the route on CPU, concurrent requests, a restart, and a restore of `volumes/data`

## What we use

- Official image, pinned tag: `ollama/ollama:0.40.14` (3.4 GB, `amd64` and
  `arm64`). It bundles the CUDA libraries, so the same image serves CPU and
  GPU hosts.
- Entrypoint `/bin/ollama`, command `serve`, port `11434`. The image sets
  `OLLAMA_HOST=0.0.0.0:11434`; the compose file repeats it.
- No curl or wget in the image. The healthcheck is `ollama list`, which
  connects to the running server and exits non-zero when it is down.

## Architecture

```text
Internet → Traefik (TLS, port 443) → ollama :11434
```

## What we changed and why

| Change | Reason |
|--------|--------|
| `user: 1000:1000`, `HOME=/data`, `OLLAMA_MODELS=/data/models` | The image runs as root by default. With an explicit uid and both paths on the data volume, the server, pulls and inference ran unchanged. If the volume is not writable by that uid the server exits with `could not create directory mkdir /data/.ollama: permission denied` — hence the `chown` in the README |
| `read_only: true`, `tmpfs: [/tmp]` | Verified: pull and CPU inference work with a read-only root filesystem. Docker's tmpfs is `noexec`; inference did not need to execute from it |
| `cap_drop: ALL`, `no-new-privileges` | Verified working, no capability added back |
| `OLLAMA_NO_CLOUD=1` | Turns off Ollama's cloud features (remote inference, web search), which are outbound calls this stack has no use for. The server logs `Ollama cloud disabled: true` |
| GPU access is a separate overlay file | A device reservation fails on a host with no NVIDIA runtime, so it cannot live in the base file |
| No `app-internal` network | There is no database or internal service to isolate |
| Traefik router defaults to `access-trusted-vpn` | Ollama has no authentication; the route's access policy is the only control |

## Authentication

There is none. `OLLAMA_ORIGINS` restricts browser cross-origin requests and
nothing else. On 2026-09-18 a second container on `proxy-public` called
`DELETE /api/delete` with no credentials and received `200`; the model was
removed. The same network reaches the pull, create and generate endpoints.

## Data egress

- Model pulls go to the Ollama registry.
- At start the server logs `model recommendations cache sleep scheduled`
  (`model_recommendations.go`). Whether this makes an outbound request was not
  traced.
- Cloud features are disabled by `OLLAMA_NO_CLOUD`.

## Verification performed (2026-09-21)

Behind Traefik with TLS, with the shipped `acc-private` and `sec-2`, on CPU
without a GPU:

- A client outside the access policy's ranges got `403` on the route, over IPv4
  and IPv6
- Set up from a copy of `.env.example` and the README's `chown`; `healthy` under
  the same hardening, with `memory` 8 GiB, `memswap_limit` equal to it and
  `pids` 512 in force
- Through the route: `qwen2.5:0.5b` (494M parameters) and `llama3.2:3b` (3.2B)
  pulled with `POST /api/pull`; `/api/chat` and `/v1/chat/completions` answered;
  a model created with `POST /api/create` from `qwen2.5:0.5b` answered with its
  system prompt
- Two concurrent `/api/generate` requests to the 3.2B model both completed, one
  after the other: the server reports `OLLAMA_NUM_PARALLEL:1`, and the second
  request took 25 s against 14 s for the first
- Peak with the 3.2B model loaded: 2.5 GiB of memory, four cores (403 % CPU),
  43 PIDs
- After `docker compose down` and `up -d` all three models were listed and
  answered
- Restore: `volumes/data` archived with the container stopped, the directory
  removed, the archive extracted into an empty `volumes/data`, the container
  started — all three models listed, and the custom model answered

**Not yet exercised:** any GPU — the overlay only merges cleanly.

## Verification performed (2026-09-18)

Against the local test stack, and against the production `docker-compose.yml`
on a throwaway `proxy-public` network without Traefik. The host is an x86_64
Docker VM with six CPUs and 12 GB of memory and no GPU:

- The pinned image pulled and started; the server reported
  `inference compute id=cpu` and `Ollama cloud disabled: true`
- `healthy` under `read_only`, `cap_drop: ALL`, `no-new-privileges` and uid
  1000; no privileged container, no published port on the production file;
  the memory, swap and pids limits applied as configured
- `ollama pull smollm2:135m` succeeded (270 MB, about 36 seconds)
- `POST /api/generate` returned `The capital of France is Paris.`;
  `POST /v1/chat/completions` returned a completion
- A separate container on `proxy-public` reached `ollama:11434` by service name
- The model was still listed after a container restart
- The unauthenticated `DELETE` described above

## Version notes

- Moved `ollama/ollama` to `0.40.14` on 2026-11-05 (released 2026-11-03), across
  0.34.3 to 0.40.14, not run on a host at this tag; the `-rc` tags of 0.40.15 are
  pre-releases and were not taken. The run-as-non-root, `read_only`, `cap_drop: ALL`
  and noexec `/tmp` hardening was verified against 0.34.2 and has not been re-run;
  0.40 runs models on llama.cpp (llama-server), so check on the first start that
  inference still works under this configuration before relying on it. Model
  storage: from 0.40.2, models pulled with an earlier version are upgraded in the
  background the first time they run, and the original copy is kept as a backup, so
  `volumes/data/models` temporarily holds both — leave room on the disk. A downgrade
  below 0.40 needs those models pulled again unless the backups are kept; the
  release notes give a command to delete the backups. Behaviour changes: OpenAI-
  compatible endpoints no longer override a model's packaged sampler defaults when a
  client sends no `temperature` or `top_p` (0.40.14); new decision-model endpoint
  `/v1/systemone` (0.35.0); `ollama show` and `/api/show` report thinking controls,
  renderer, parser and template source. Cloud usage and balance APIs are proxied
  (0.40.1); `OLLAMA_NO_CLOUD=1` stays set. No advisories are published for the
  range, no environment variable was removed, and port 11434 and the entrypoint are
  unchanged, so the compose files keep their configuration. The image shrinks from
  3.7 GB to 3.4 GB (`amd64`). Sources: https://github.com/ollama/ollama/releases
  (v0.34.3 to v0.40.14), https://github.com/ollama/ollama/releases/tag/v0.40.2

## Upgrade checklist

1. Read the release notes for breaking changes: https://github.com/ollama/ollama/releases
2. Check the GitHub Security tab for advisories against the current version
3. Bump `APP_TAG` in `.env.example` and `.env.local.example`
4. `docker compose pull && docker compose up -d`
5. Verify `ollama list` still shows the models, then run one request
6. Update **Based on version** above — and add **Last verified** only if the
   upgrade was actually exercised on a real install

## Useful commands

```bash
docker compose logs ollama --follow
docker compose exec ollama ollama list
docker compose exec ollama ollama pull <model>
docker compose exec ollama ollama rm <model>
```
