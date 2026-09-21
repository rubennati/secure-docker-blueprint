# Upstream Reference

## Source

- **Image:** https://github.com/docling-project/docling-serve/pkgs/container/docling-serve-cpu
- **GitHub:** https://github.com/docling-project/docling-serve
- **Docs:** https://docling-project.github.io/docling-serve/
- **License:** MIT
- **Decision facts checked:** not yet
- **Origin:** LF AI & Data Foundation (US non-profit) · originated at IBM Research Zurich, Switzerland · non-EU
- **Domain:** AI and local AI
- **Role:** Document understanding as an API: layout, tables and Markdown or JSON export for AI pipelines
- **Based on version:** `v1.34.0`

No `Last verified` line yet — see [Verification performed](#verification-performed-2026-09-18)
below for exactly what has been exercised and what has not. The field
asserts Traefik/TLS routing was confirmed on a real host, which this session
could not do; setting it early would claim evidence that does not exist. This
stack stays `scaffolded` until that happens.

## What we use

- Official image, pinned tag: `ghcr.io/docling-project/docling-serve-cpu:v1.34.0` —
  the CPU-only variant. `-cu128`/`-cu130` exist for NVIDIA GPU hosts; not used
  here, this blueprint assumes no GPU by default.
- Runs as uid 1001 by upstream default (verified via `docker inspect`) — no
  `user:` override in compose.
- ML models (layout, OCR, figure classification, ~870 MB) ship baked into the
  image — confirmed by inspecting `/opt/app-root/src/.cache/docling/models`
  inside the pulled image. No model download at first boot.

## Architecture

```text
Internet → Traefik (TLS, port 443) → docling-serve :5001
```

Stateless per request (`DOCLING_SERVE_SINGLE_USE_RESULTS=1` upstream default)
— no database, no queue. `/tmp` is the only writable path at runtime, for
per-conversion scratch files.

## What we changed and why

| Change | Reason |
|--------|--------|
| Docker Secret for `DOCLING_SERVE_API_KEY`, injected by `config/entrypoint.sh` | Upstream defaults this to an empty string, which disables auth entirely (`docling_serve/auth.py`) — the blueprint standard is a secret, not an open endpoint |
| `read_only: true` + `tmpfs: [/tmp]` | Verified working against a real conversion (`POST /v1/convert/source` against a live PDF) — see below |
| `app-internal` network not added | No database or internal service to isolate — same reasoning as `development/web-api/`'s base pattern |

## Verification performed (2026-09-18)

Against the local test stack, without Traefik:

- `docker pull ghcr.io/docling-project/docling-serve-cpu:v1.34.0` — succeeds
- Booted with `no-new-privileges`, `cap_drop: ALL`, `read_only`, `tmpfs: [/tmp]`
  — reached `healthy` in ~40s warm-cache (`GET /health`, `GET /ready` both
  return `{"status":"ok"}`)
- `POST /v1/convert/source` against a real PDF (`https://arxiv.org/pdf/2501.17887`)
  under the same hardened flags — completed successfully, confirming `/tmp`
  alone is sufficient scratch space under `read_only`
- No API key set → any request succeeds (upstream's documented default); a
  Docker Secret set via `config/entrypoint.sh` requires `X-Api-Key` on every
  request

**Not yet exercised:** the production `docker-compose.yml` against a real
Traefik instance — TLS termination, the access/security middleware chain, and
the entrypoint wrapper's secret injection have not been run end-to-end.

## Upgrade checklist

1. Read the release notes for breaking changes: https://github.com/docling-project/docling-serve/blob/main/CHANGELOG.md
2. Check the GitHub Security tab for advisories against the current version
3. Bump `APP_TAG` in `.env.example` and `.env.local.example`
4. `docker compose pull && docker compose up -d`
5. Verify `/health` and a real conversion still work
6. Update **Based on version** above — and **Last verified** only if the
   upgrade was actually exercised on a real install

## Useful commands

```bash
# Tail logs
docker compose logs docling-serve --follow

# Swagger UI (behind Traefik, or locally at :8099/docs)
curl http://localhost:8099/docs

# A conversion, with the API key set
curl -X POST 'https://docling.example.com/v1/convert/source' \
  -H "X-Api-Key: $(cat .secrets/docling_api_key.txt)" \
  -H 'Content-Type: application/json' \
  -d '{"sources": [{"kind": "http", "url": "https://arxiv.org/pdf/2501.17887"}]}'
```
