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
- **Last verified:** 2026-11-08 (1.108.3) — over IPv4: moved from v1.108.0, a model added through the admin API with its credential stored encrypted, a virtual key restricted to it listing only that model, the UI served, both kept after `down`/`up`, the refused client answered `403`; no completion through a real provider (docs/labs/stack-refresh/2026-11-08-results.md)

## What we use

- `ghcr.io/berriai/litellm-non_root:v1.108.3` — upstream's non-root variant with
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
| Database on `app-internal` only | It needs no route out; `getent hosts github.com` from it fails |
| Provider keys kept out of `config.yaml` | Added through the admin API and stored encrypted with the salt key |
| `store_model_in_db: true` | `POST /model/new` refuses without it, so the admin-API path for provider credentials needs it |
| Secret files mode `640`, group 65534 | The proxy runs as uid/gid 65534 and Compose mounts the files with their host owner and mode |

## Verification performed (2026-09-21)

Behind Traefik with TLS, with the shipped `acc-private` and `sec-2`, and the
Ollama stack as the backend:

- A client outside the access policy's ranges got `403` on the route, over IPv4
  and IPv6
- The proxy did not start with `ops/init.sh`'s owner-only secret files: it runs
  as uid/gid 65534, Compose mounts the files with the host's owner and mode, and
  the entrypoint looped on `cat: can't open '/run/secrets/DB_PWD': Permission
  denied`. With group 65534 and mode `640` it started; the README and
  `init.sh` now say so
- Unauthenticated: `/health/liveliness`, `/health/readiness`, `/routes`,
  `/openapi.json` `200`; `/v1/models`, `/health`, `/metrics` `401`
- The shipped `local-chat` entry answered through the route
- `POST /model/new` answered `Set 'STORE_MODEL_IN_DB='True'' in your env to
  enable this feature` with the shipped config. With `store_model_in_db: true`
  in `general_settings` (now in `config/config.yaml`) a model was added with
  `api_base` set to the Ollama route and a placeholder `api_key`; in
  `LiteLLM_ProxyModelTable` both fields are stored encrypted and the key's
  plaintext does not occur
- A virtual key limited to that model: a completion `200`, another model `403`,
  `POST /key/generate` `401`, `/v1/models` listing only its model
- Admin login: `POST /login` with user `admin` and the master key `303` to
  `/ui` with a session cookie; a wrong password `401`. The redirect `Location`
  carries `http://` for the routed host; `strict-transport-security` from the
  security chain keeps browsers on HTTPS
- Headless Chromium (Playwright 1.63): the login form and, after signing in
  with the master key, the dashboard listing the virtual keys — 160 requests,
  none answered `429` under `sec-2`
- After `docker compose down` and `up -d` the virtual key still completed
- Restore as the README describes: `pg_dump` while running, `volumes/postgres`
  replaced by an empty directory, the database container started alone, the
  dump loaded with `psql -v ON_ERROR_STOP=1`, the proxy started: the virtual key
  completed against the stored model, so the credential decrypted with the
  unchanged salt key
- Peak 593 MiB for the proxy, 61 MiB for the database

**Outside this verification:** a hosted provider's own check of the credential — none
was available; a placeholder key reached the Ollama route.

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

## Version notes

- Moved to `v1.108.3` on 2026-11-08, the digest re-
  resolved. 1.108.1 to 1.108.3 are fixes; upstream: "No action needed to
  upgrade".
- Moved to `v1.108.0` on 2026-11-05 (released 2026-11-04). Breaking changes on the way from v1.101.4:
  v1.104.0 refuses to start with an unset, empty or publicly known master key
  (the key here is generated by `ops/init.sh`) and defaults to the v2
  migration resolver with the migration check enforced; v1.103.0 refuses
  runtime writes to settings the config file owns and re-checks budgets on
  router fallback targets; v1.104.0 moves the Langfuse callback to the
  Langfuse v4 SDK; v1.106.0 disables stdio MCP servers by default, returns only
  data from SQL tracing and retires the ROI calculator. The non-root image is
  unchanged in what this stack relies on: uid 65534,
  `/app/docker/prod_entrypoint.sh`, port 4000, Python 3.13. The
  `litellm_settings.telemetry` flag was removed from the config: upstream
  (PR #42071) documents it as a no-op since 2024, accepted but ignored.
  Advisories: GHSA-7hp6-4w63-5g45 (critical, salt-key reuse) affected only
  v1.101.0 up to v1.101.3, so the previous pin was already outside it;
  GHSA-w4c7-34wj-hqm8 (critical, master key leak, fixed in v1.103.10 and
  later) affects only proxies with an Enterprise licence.
- **The 1.107.0 release was compromised.** On 2026-10-21 `litellm==1.107.0`
  on PyPI and the `latest`, `main-latest` and `main-stable` images carried a
  credential stealer and a code loader, built after attackers used stolen
  maintainer tokens (upstream issue BerriAI/litellm#47826 and its incident
  post). Upstream withdrew them, replaced the image signing key, and v1.107.0
  never became a stable release; this pin skips that line. Verify an image
  before moving to it, with the key pinned to the commit that introduced it:

  ```bash
  cosign verify \
    --key https://raw.githubusercontent.com/BerriAI/litellm/e82a3c646908ba0a6ee0beddc4310d7a6cac4065/cosign.pub \
    ghcr.io/berriai/litellm-non_root:v1.108.0
  ```

  Run on 2026-11-05 for this pin: the signature verified against that key,
  for the index digest
  `sha256:08d313a00c46509c875d84f60c1448a260c478f399ade3c2abb940d358d5b724`,
  which `APP_TAG` now pins, so a re-pushed tag cannot change the image.

## Upgrade checklist

1. Read the release notes: https://github.com/BerriAI/litellm/releases
2. Check the GitHub Security tab for advisories against the current version
3. Back up the database and `litellm_salt_key.txt`
4. Bump `APP_TAG` in `.env.example`
5. `docker compose pull && docker compose up -d`; watch the migration in the log
6. Verify `/health/readiness`, then make a real `/v1` request
7. Add **Last verified** only if the
   upgrade was exercised on a real install

Migrations run at start and are not reversible by downgrading the image; keep the
dump from step 3.
