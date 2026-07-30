# Upstream Reference

## Source

- **Upstream GitHub:** https://github.com/documenso/documenso
- **Image registry:** `documenso/documenso` (Docker Hub)
- **Docs:** https://docs.documenso.com/developers/self-hosting
- **Self-host compose reference:** `docker/production/compose.yml` in the upstream repo
- **License:** AGPL-3.0
- **Origin:** US · Documenso Inc · non-EU (development largely from Hamburg, Germany)
- **Based on version:** `v2.15.0`
- **Last verified:** — (config authored 2026-07-26; not yet run on a live server)

## What we use

- `documenso/documenso:v2.15.0` (Remix app; CMD `sh start.sh` runs Prisma migrations on boot)
- `postgres:16-alpine`
- Custom `config/entrypoint.sh` to inject secrets from Docker Secret files (no `_FILE` support)

## What we changed vs. upstream compose

| Change | Reason |
|--------|--------|
| Custom entrypoint for secret injection | Documenso reads `NEXT_PRIVATE_*` from env; entrypoint builds the DB URL and exports keys/passphrase from `/run/secrets/`, then execs `sh start.sh` |
| `working_dir: /app/apps/remix` | The image CMD `sh start.sh` is relative to that dir |
| `app-internal` network (`internal: true`) | Postgres not reachable from host |
| `no-new-privileges:true` + `cap_drop: ALL` | Security baseline |
| `deploy.resources` (memory/cpus/pids) | Bound a compromised container |
| Postgres pinned to `16-alpine` | Upstream sample uses `postgres:15`; blueprint prefers a current line |
| DB password generated as hex | URL-safe in the connection URL |
| Signing `.p12` mounted `:ro`, passphrase as Docker Secret | Keep the signing key off `.env` and out of git |

## Upgrade checklist

1. Watch [Documenso releases](https://github.com/documenso/documenso/releases)
2. Read the changelog for breaking changes / required env
3. Back up the database before upgrading:

   ```bash
   docker compose exec db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > documenso-$(date +%Y%m%d).sql
   ```

4. Bump `APP_TAG` in `.env` (prefer a digest pin — see `apps/caldiy`)
5. `docker compose pull && docker compose up -d`; watch migrations: `docker compose logs app --follow`

## Known limitations

- **No `_FILE` support** — mitigated via the custom entrypoint
- **Not yet live-verified** — see the README "Verify on first deploy" gate before marking ✅
- **Requires a signing certificate** — Documenso ships none; a self-signed `.p12` is generated at setup
