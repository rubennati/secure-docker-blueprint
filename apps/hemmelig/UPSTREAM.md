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
- **Origin:** Norway · Bjarne Øverli (individual maintainer) · non-EU (EEA, not EU)
- **Domain:** Identity, access and secrets
- **Role:** Ephemeral secret sharing with a built-in request flow
- **Based on version:** `v7.4.8`
- **Verification snapshot:** 2026-09-19 — clean start and one full migration
  cycle, not a full operational verification (see below)

## What we use

- `hemmeligapp/hemmelig:v7.4.8` — single container, SQLite via Prisma, no
  separate database service

## Pin note: the moving tags have not advanced since this release

Verified against Docker Hub's own tag metadata, 2026-09-19: the floating
`v7` and `v7.4` tags resolve to the exact same image digest as the pinned
`v7.4.8` (published 2026-03-23), even though the GitHub repository's `v7`
branch has continued to receive commits through at least 2026-08-27 (feature
work, dependency bumps, i18n). No newer tagged release or rebuilt image has
been published in the roughly six months since `v7.4.8`. This stack is
already pinned to the newest artifact that actually exists on Docker Hub —
there is nothing newer to pin to, and self-building from source is the only
way to get anything past this point. Re-check before the next upgrade
rather than assuming a new tag has appeared.

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

## Upgrade checklist

1. Check the [Hemmelig tags on GitHub](https://github.com/HemmeligOrg/Hemmelig.app/tags)
   and [Docker Hub](https://hub.docker.com/r/hemmeligapp/hemmelig/tags) —
   confirm whether a newer tag/image actually exists (see the pin note above;
   as of this writing, none has for six months)
2. Read the commit history since the current pin for anything migration- or
   auth-related
3. Back up `./volumes/database` and `./volumes/uploads` before upgrading
4. Bump `APP_TAG` in `.env`
5. `docker compose pull && docker compose up -d`
6. Watch `docker compose logs -f` for "All migrations have been successfully
   applied" before assuming the new version is ready

## Known limitations

- **Not an OSI-approved license** — see README.md's License section.
- **No new image published in ~6 months** despite continued source commits —
  see the pin note above. Security fixes landing in source may not be
  reachable via the published image without building it yourself.
- **`read_only: true` is not used** — see the compose file's Security block.
- **The secret-request flow requires a manual, out-of-band step** — the
  decryption key does not reach the requester automatically. See README.md.
- **Not yet run behind a real Traefik host or TLS.**
