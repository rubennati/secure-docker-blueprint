# docling-serve

Document understanding as an API — layout, structure, tables, and Markdown/JSON
export, aimed at RAG and other AI-pipeline consumers. Standalone: no other
stack in this repository calls it, and Paperless-ngx keeps its own embedded
Tika and Gotenberg unchanged.

## Architecture

```text
Internet → Traefik (TLS, port 443) → docling-serve :5001
```

Single service, no database, no queue. Stateless per request. ML models
(layout detection, OCR, figure classification) ship baked into the image —
no download on first boot.

## Setup

```bash
cp .env.example .env
mkdir -p .secrets
openssl rand -base64 32 | tr -d '\n' > .secrets/docling_api_key.txt
docker compose up -d
```

Set `APP_TRAEFIK_HOST` in `.env` to the real hostname. Every request then
needs the API key:

```bash
curl -X POST "https://$(grep APP_TRAEFIK_HOST .env | cut -d= -f2)/v1/convert/source" \
  -H "X-Api-Key: $(cat .secrets/docling_api_key.txt)" \
  -H 'Content-Type: application/json' \
  -d '{"sources": [{"kind": "http", "url": "https://arxiv.org/pdf/2501.17887"}]}'
```

The full API reference is at `/docs` on the running instance; the interactive
`/ui` playground is off by default (`DOCLING_ENABLE_UI=0`) and gated by
`APP_TRAEFIK_ACCESS`, which defaults to `acc-private`.

## Status

Run behind Traefik with TLS on 2026-09-22 (v1.34.0): the API key from
the Docker Secret, a real PDF converted through the route, a URL conversion,
and a restart. Full log in
[`UPSTREAM.md`](UPSTREAM.md#verification-performed-2026-09-22).

## Try it locally

```bash
cp .env.local.example .env.local
docker compose -f docker-compose.local.yml --env-file .env.local up -d
curl http://localhost:8099/health
docker compose -f docker-compose.local.yml --env-file .env.local down
```

No API key locally — an empty `DOCLING_SERVE_API_KEY` disables auth entirely,
which is upstream's own default, not a weakening this repository introduces.

## Backup

No state to protect. Every result is computed from the request; nothing
persists between conversions. If a consumer needs the converted output kept,
that consumer's own stack backs it up.
