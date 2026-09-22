# Upstream Reference

## Source

- **Image:** https://github.com/BerriAI/litellm/pkgs/container/litellm-non_root
- **GitHub:** https://github.com/BerriAI/litellm
- **Docs:** https://docs.litellm.ai/
- **License:** MIT (core; the `enterprise/` directory is under a separate commercial licence)
- **Use restrictions:** none for the MIT-licensed portion; content under the `enterprise/` directory is under the separate licence in `enterprise/LICENSE` — https://github.com/BerriAI/litellm/blob/main/LICENSE · checked 2026-09-21
- **Decision facts checked:** 2026-09-21
- **Origin:** United States · BerriAI, Inc. · non-EU
- **Domain:** AI and local AI
- **Role:** OpenAI-compatible gateway in front of any model backend, with virtual keys, budgets and a spend log
- **Based on version:** `v1.101.0`

No `Last verified` line yet — see [Verification performed](#verification-performed-2026-09-19)
below. The field asserts Traefik/TLS routing was confirmed on a real host, which
has not happened; this stack stays `scaffolded` until it does.

## What we use

- `ghcr.io/berriai/litellm-non_root:v1.101.0` — upstream's non-root variant with
  a versioned release tag. Upstream's own quick-start pins the floating
  `main-stable`; not used here.
- `postgres:18.6` — LiteLLM's virtual keys, budgets and spend log need a
  database; upstream's Prisma schema targets PostgreSQL.
- One proxy container plus the database. No Redis (only for multi-instance
  rate-limit sharing), no Prometheus sidecar.

## What we changed and why

| Change | Reason |
|--------|--------|
| `config/entrypoint.sh` builds `DATABASE_URL`, `LITELLM_MASTER_KEY`, `LITELLM_SALT_KEY` from Docker Secrets | No `_FILE` variant exists for any of them |
| `read_only: true` with `tmpfs: /tmp` | Verified: migrations, requests and restarts work with nothing else writable |
| `litellm_settings.telemetry: false` | Upstream's anonymous usage telemetry |
| Database on `app-internal` only | It needs no route out; `getent hosts github.com` from it fails |
| Provider keys kept out of `config.yaml` | Added through the admin API and stored encrypted with the salt key |
| `store_model_in_db: true` | `POST /model/new` refuses without it, so the admin-API path for provider credentials needs it |
| Secret files mode `640`, group 65534 | The proxy runs as uid/gid 65534 and Compose mounts the files with their host owner and mode |

## Verification performed (2026-09-19)

Against `docker-compose.local.yml` and the production `docker-compose.yml`
(Docker Secrets, `entrypoint.sh`, `app-internal`), without Traefik, with a
throwaway Ollama container serving `smollm2:135m`:

- The pinned image pulled; migrations applied on an empty database; the proxy
  started under `read_only`
- `/v1/models`: `401` without a key and with a wrong key, `200` with the master key
- A real `/v1/chat/completions` request was routed through the gateway to Ollama
  and returned a completion (local stack and production stack)
- A virtual key restricted to `local-chat` completed a request, got `403` for
  another model and `401` on `POST /key/generate`
- After restarting the proxy the virtual key still worked; the spend log held the
  requests
- The key, salt and database URL are absent from the container's configured environment
- Production: no published ports, `read_only`, uid 65534, database without outbound route

**Not yet exercised:** Traefik routing and TLS; a hosted provider and
credential storage through the admin API; the admin UI login beyond the redirect;
backup and restore of the database.

## Upgrade checklist

1. Read the release notes: https://github.com/BerriAI/litellm/releases
2. Check the GitHub Security tab for advisories against the current version
3. Back up the database and `litellm_salt_key.txt`
4. Bump `APP_TAG` in `.env.example`
5. `docker compose pull && docker compose up -d`; watch the migration in the log
6. Verify `/health/readiness`, then make a real `/v1` request
7. Update **Based on version** above — and add **Last verified** only if the
   upgrade was exercised on a real install

Migrations run at start and are not reversible by downgrading the image; keep the
dump from step 3.
