# Upstream Reference

## Source

- **Image:** https://github.com/paperless-ngx/paperless-ngx/pkgs/container/paperless-ngx
- **GitHub:** https://github.com/paperless-ngx/paperless-ngx
- **Docs:** https://docs.paperless-ngx.com/
- **Release notes:** https://github.com/paperless-ngx/paperless-ngx/releases
- **Config reference:** https://docs.paperless-ngx.com/configuration/
- **Based on version:** `2.20.13`
- **Last checked:** 2026-04-16

## What we use

- Official `paperless-ngx` image, pinned tag
- `postgres:16` as primary backend (upstream also supports MariaDB + SQLite; Postgres is the recommended production path)
- `redis:7-alpine` for the Celery broker
- Official `gotenberg/gotenberg` and `apache/tika` images for document conversion + text extraction
- Native `_FILE` secret support (`PAPERLESS_DBPASS_FILE`, `PAPERLESS_SECRET_KEY_FILE`)

## What we changed and why

| Change | Reason |
|--------|--------|
| Five-service layout (app + db + redis + gotenberg + tika) | Upstream recommendation for the full feature set. Without Tika, email/Office file ingestion breaks; without Gotenberg, HTML → PDF breaks. |
| `_FILE` Docker Secrets for DB + SECRET_KEY | Natively supported; keeps credentials out of `.env` and `docker inspect` output |
| `SSO_CLIENT_SECRET` stays in `.env` (not a Docker Secret) | Paperless embeds it inside a JSON string env var (`PAPERLESS_SOCIALACCOUNT_PROVIDERS`); no `_FILE` support for values inside a larger JSON blob. Documented in README. |
| Custom Traefik middleware for `X-Forwarded-Proto` + `X-Forwarded-Host` | Paperless generates absolute URLs from these headers. Without them the UI links to `http://…` inside an `https://` page → Mixed Content errors. |
| Gotenberg flags `--chromium-disable-javascript` + `--chromium-allow-list=file:///tmp/.*` | Defence in depth — the conversion engine never runs JS and can only read from the temp dir we hand it. |
| `PAPERLESS_OCR_USER_ARGS` with `invalidate_digital_signatures` + `continue_on_soft_render_error` | Lets OCR proceed on signed PDFs and on minor render errors instead of failing the whole document |
| `app-internal` network with `internal: true` | DB/Redis/Gotenberg/Tika have no outbound routing |
| `no-new-privileges:true` on every service | Blueprint baseline |
| `USERMAP_UID` + `USERMAP_GID` instead of `user:` | Paperless uses s6-overlay which needs root for early init; it drops to the mapped UID internally |
| Default access `acc-tailscale` + `sec-3` | Personal document store — VPN-only is the right default. Override to `acc-public` consciously if publishing externally. |

## Upgrade checklist

Paperless does schema migrations on every minor bump. The classifier model may also need rebuilding.

1. Release notes: https://github.com/paperless-ngx/paperless-ngx/releases (look for "Breaking changes")
2. Back up:
   ```bash
   # Use Paperless's own exporter — it knows what to include
   docker compose exec -u paperless app \
     document_exporter /usr/src/paperless/export --compare-checksums --use-filename-format
   tar czf paperless-export-$(date +%Y%m%d).tgz volumes/export volumes/media
   # Plus raw Postgres dump
   docker compose exec db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' \
     > paperless-db-$(date +%Y%m%d).sql
   ```
3. Bump `APP_TAG` in `.env`
4. `docker compose pull && docker compose up -d`
5. Watch migrations:
   ```bash
   docker compose logs app --follow
   ```
   Expect `Applying migrations...` and `Listening at: http://0.0.0.0:8000`.
6. Verify:
   - UI loads, document list populated
   - Drop a test PDF in `./volumes/consume/` — it should be consumed within seconds
   - `docker compose exec app python manage.py check` returns no errors

### Rollback

Paperless's Django migrations are forward-only. Rollback = restore the SQL dump + media volume and revert `APP_TAG`.

## Related images to keep in sync

- `postgres:16` — safe to update within 16.x
- `redis:7-alpine` — safe to update within 7.x
- `gotenberg/gotenberg`, `apache/tika` — independent; follow their own release cadence. Bump conservatively; new majors can change HTTP APIs that Paperless calls.

## Useful commands

```bash
# Shell
docker compose exec app bash

# Django shell (inspect models)
docker compose exec app python manage.py shell

# Run a specific management command
docker compose exec app python manage.py <command>

# Common management tasks
docker compose exec app python manage.py createsuperuser
docker compose exec app python manage.py document_thumbnails   # regenerate thumbnails
docker compose exec app python manage.py document_index reindex # rebuild search index
docker compose exec app python manage.py document_retagger      # rerun tag matching

# Full export (human-readable, safe to transfer)
docker compose exec -u paperless app \
  document_exporter /usr/src/paperless/export --compare-checksums --use-filename-format

# Restore from an export
docker compose exec -u paperless app \
  document_importer /usr/src/paperless/export

# Raw DB dump
docker compose exec db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > dump.sql
```
