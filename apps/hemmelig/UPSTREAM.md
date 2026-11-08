# Upstream Reference

## Source

- **Image:** https://hub.docker.com/r/hemmeligapp/hemmelig
- **GitHub:** https://github.com/HemmeligOrg/Hemmelig.app
- **Docs:** in-repo `docs/`, e.g. `docs/secret-request.md`
- **License:** O'Saasy License Agreement — a 2025 MIT-derived license with
  one added restriction: no offering the software to third parties as a
  competing hosted/SaaS product. **Not an OSI-approved open-source license**
  (GitHub's own license detector reports `NOASSERTION` for it). Self-hosting
  for your own use is fully permitted. See README.md's License section.
- **Decision facts checked:** not yet
- **Origin:** Norway · Bjarne Øverli (individual maintainer) · non-EU (EEA, not EU)
- **Domain:** Identity, access and secrets
- **Role:** Ephemeral secret sharing with a built-in request flow
- **Verification snapshot:** 2026-09-19 — clean start and one full migration
  cycle, not a full operational verification (see below)

## What we use

- `hemmeligapp/hemmelig:v7.6.1` — single container, SQLite via Prisma, no
  separate database service

## Pin note

Until 2026-09-24 the newest image on Docker Hub was `v7.4.8` (2026-03-23): the
floating `v7` and `v7.4` tags did not advance for six months while the
repository's `v7` branch kept receiving commits. `v7.5.0`, `v7.6.0` and
`v7.6.1` were published on 2026-09-24 and 2026-09-25, and the floating `v7` tag
moved with them. Check Docker Hub, not only the GitHub tags, before the next
bump — the two have drifted apart before.

## What we changed vs. upstream compose

| Change | Reason |
|--------|--------|
| Custom entrypoint wrapper for secrets | Verified: no `_FILE` support anywhere in the image. `config/entrypoint.sh` injects `BETTER_AUTH_SECRET` and `HEMMELIG_ANALYTICS_HMAC_SECRET` from Docker Secrets, then execs the image's own `/app/docker-entrypoint.sh` |
| `cap_drop: ALL` + `cap_add: [CHOWN, DAC_OVERRIDE, FOWNER, SETGID, SETUID]` | Verified against a live container: the entrypoint runs `chown -R app:app /app/database /app/uploads` as root, then `exec gosu app ...`. Without these, `gosu` fails with "operation not permitted" |
| No `read_only: true` (documented, not silently dropped) | Verified against a live container: `npx prisma migrate deploy` downloads a platform-specific `schema-engine` binary into `/home/app/.cache/prisma/...` and then copies it into `/app/node_modules/@prisma/engines/`. A read-only root filesystem breaks the copy step even with `/tmp` and the cache directory mounted as tmpfs, because the copy *target* is inside the read-only `node_modules` tree. This is the same class of case `security-baseline.md` already documents for Ghost and Paperless-ngx ("skip for images that write to the root filesystem") — no `check-baseline.py` exception entry needed, since `read_only` is a recommended control, not a mandatory one |
| No `app-internal` network | No separate database container to isolate — SQLite is a file inside the app container's own volume |

## What was actually verified, and how

- `docker inspect hemmeligapp/hemmelig:v7.4.8` — confirmed the image runs as
  root by default (`User: ""`), with entrypoint `/app/docker-entrypoint.sh`;
  read that script directly (`docker run --entrypoint cat ... /app/docker-entrypoint.sh`)
  to confirm the exact `chown` + `gosu` + `prisma migrate deploy` + `tsx
  server.ts` sequence documented above.
- Ran with `--cap-drop ALL` alone: failed with `error: failed switching to
  "app": operation not permitted`. Added the five capabilities above:
  started cleanly, migrations applied, server listened on port 3000.
- Ran the same configuration additionally under `--read-only`: failed with
  `Error: Could not find schema-engine binary`, even after adding `/tmp` and
  `/home/app/.cache` as tmpfs — traced to the copy destination
  (`/app/node_modules/@prisma/engines/`) itself being read-only.
- Ran the full production Compose file (with the entrypoint wrapper and real
  Docker Secrets) end to end: migrations applied, `GET /api/health/ready`
  returned `{"status":"healthy",...}` with database, storage and memory
  checks all healthy.
- Read `docs/secret-request.md` directly for the exact request/response
  sequence — see README.md's "Secret requests need a manual step" section
  for what it actually requires of the requester and the secret-holder.
- **Not verified:** a full secret-request round trip through the actual web
  UI, TLS/Traefik behind a real domain, upload handling, webhook delivery, or
  behavior across a restart.

## Version notes

- Moved to `v7.6.1` on 2026-11-05, not run on a host at this tag; the
  verification above was against `v7.4.8`. v7.5.0 brings the v2 interface and
  requires `HEMMELIG_TRUSTED_PROXIES` behind a reverse proxy — this stack now
  sets it, see `.env.example`. It also makes `BETTER_AUTH_SECRET` mandatory
  (already injected here), removes the default analytics HMAC secret (already
  generated here), requires the `x-hemmelig-delete-token` header to delete a
  secret and `x-hemmelig-file-token` to download a file through the API, and
  stops accepting plaintext passwords for password-protected secrets from CLI
  and API clients (Go CLI `cli-v1.1.0`, npm CLI `hemmelig@7.1.0`). v7.6.0 runs
  a new database migration at start, accepts API keys on every route, and
  makes `HEMMELIG_INSTANCE_*`, `HEMMELIG_ALLOW_REGISTRATION`,
  `HEMMELIG_ALLOW_PASSWORD_PROTECTION` and `HEMMELIG_ALLOW_IP_RESTRICTION`
  override the dashboard outside managed mode; this stack sets none of them.
  Upstream now supports a read-only root filesystem (`/tmp`, `/app/database`
  and `/app/uploads` writable) with the schema engine baked into the image;
  `read_only` stays off here until that is run. The image entrypoint
  (`chown`, `gosu`, `prisma migrate deploy`) is unchanged, so
  `config/entrypoint.sh` still applies. No GHSA is published; v7.5.0 lists
  security fixes for reveal-token deletes, file download authorization,
  forwarded-IP trust, webhook DNS pinning, bounded request bodies, expired
  secrets and the registration policy.

## Upgrade checklist

1. Check the [Hemmelig tags on GitHub](https://github.com/HemmeligOrg/Hemmelig.app/tags)
   and [Docker Hub](https://hub.docker.com/r/hemmeligapp/hemmelig/tags) —
   confirm whether a newer tag/image actually exists (see the pin note above)
2. Read the commit history since the current pin for anything migration- or
   auth-related
3. Back up `./volumes/database` and `./volumes/uploads` before upgrading
4. Bump `APP_TAG` in `.env`
5. `docker compose pull && docker compose up -d`
6. Watch `docker compose logs -f` for "All migrations have been successfully
   applied" before assuming the new version is ready

## Known limitations

- **Not an OSI-approved license** — see README.md's License section.
- **Images have lagged the source before** — see the pin note above. Security
  fixes landing in source may not reach the published image right away.
- **`read_only: true` is not used** — see the compose file's Security block.
- **The secret-request flow requires a manual, out-of-band step** — the
  decryption key does not reach the requester automatically. See README.md.
- **Not yet run behind a real Traefik host or TLS.**
