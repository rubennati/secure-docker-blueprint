# Upstream Reference

## Source

- **Image:** https://hub.docker.com/r/luka1thb/tymeslot
- **GitHub:** https://github.com/tymeslot/tymeslot
- **Docs:** https://tymeslot.app/docs · `README-Docker.md` and `docs/ADMIN.md` in the repository
- **License:** AGPL-3.0
- **Decision facts checked:** not yet
- **Origin:** Estonia · Diletta Luna OÜ (Tallinn) · EU
- **Domain:** Publishing, forms and scheduling
- **Role:** Meeting scheduling with booking pages, calendar sync and video links
- **Based on version:** `1.39.0` (`-slim` tag, digest-pinned)
- **Last verified:** 2026-09-07 (v1.15.1)

What that date covers: a clean install, migrations, the healthcheck, Traefik
routing under `acc-tailscale` and `sec-3`, registration and the LiveView
dashboard from a VPN client, and a verification mail delivered over SMTP. A
booking from a guest's side has not been exercised.

## What we use

- The official `-slim` image: application only, no bundled PostgreSQL. The
  plain tag runs a PostgreSQL server inside the app container.
- `postgres:17.11-alpine` as the database, the shape of upstream's
  `docker-compose.with-postgres.yml`
- The image's own `start-docker.sh` as the command: it validates
  `SECRET_KEY_BASE`, waits for the database, runs the Ecto migrations and
  starts the release as the `app` user. Nothing of it is copied or patched.
- Configuration through the environment variables documented in upstream's
  `.env.example` and read by `config/runtime.exs`

## Architecture

```text
Tailscale client → Traefik (TLS, 443) → tymeslot-app :4000 (Bandit, LiveView over websocket)
                                              │
                                              ├─ db :5432          (tymeslot-internal)
                                              └─ SMTP relay :587  (or apps/mailpit while trying it out)
```

## What we changed and why

| Change | Reason |
|--------|--------|
| `-slim` image + separate `db` service | A database belongs on `app-internal`, not inside a container on `proxy-public`; upstream offers exactly this split |
| `config/entrypoint.sh` in front of `start-docker.sh` | No secret has a `_FILE` variant; the wrapper exports `SECRET_KEY_BASE`, `DATA_ENCRYPTION_KEY`, `POSTGRES_PASSWORD`, `SMTP_PASSWORD` from `/run/secrets/` |
| `DATA_ENCRYPTION_KEY` required, not optional | Set from the first boot; without it stored credentials are tied to `SECRET_KEY_BASE`, and adding it later needs upstream's re-encryption sweep |
| `cap_drop: ALL` + `CHOWN`, `DAC_OVERRIDE`, `SETGID`, `SETUID` | The start script runs as root to prepare `/app/data` and switch user; the set was established by removing one capability at a time (`FOWNER` is not needed) |
| `read_only: true`, tmpfs on `/tmp`, `/run`, `/app/tmp` | The release writes its boot-time `sys.config` copy to `/app/tmp`; everything else goes to `/app/data` |
| Bind mounts instead of named volumes | Blueprint convention. Upstream's warning against a host path concerns the bundled PostgreSQL's `initdb`, which the slim image does not run |
| `bash /dev/tcp` healthcheck | The image ships neither curl nor wget; `/healthcheck` verifies database and job queue |
| Social login off, `WEBHOOK_BASE_URL` unset | Attack surface; the host is not reachable from the public internet, so push channels cannot be registered. Since 1.26.0 the `ENABLE_*_AUTH` variables outrank the admin page, so single sign-on is switched on in the compose file, not at `/admin` |
| Traefik labels, `access-vpn`, `limit-standard`, `headers-standard` | Blueprint standard. A first load is about ten requests, far below the burst of 500; the access policy is the deployment decision the README describes |

## Version notes

- Moved to `1.39.0` on 2026-11-05, not run on a host at this tag; 24 minor releases
  past the verified `1.15.1`, so a host re-run is advised before the stack counts as
  verified again. New index digest
  `sha256:ad7cfda6fe84a5693fb2da0820fb47c54d9f9e52700223430efaa70bf6cac352`, read
  from the registry; confirm it with checklist step 4. Breaking changes upstream:
  1.16.0 moves Zoom meetings on reschedule and needs the `meeting:update:meeting`
  scope, or `ZOOM_UPDATE_SCOPE_ENABLED=false` (Zoom is not configured here). 1.26.0
  lets a set environment variable outrank the value saved on the admin page:
  `REGISTRATION_ENABLED` and the hard-coded `ENABLE_GOOGLE_AUTH`,
  `ENABLE_GITHUB_AUTH` and `ENABLE_OAUTH_AUTH` in the compose file now decide, and
  the toggles at `/admin` no longer override them. 1.27.0 refuses to start when
  `DATA_ENCRYPTION_KEY` is not Base64 or decodes to fewer than 32 bytes; the key the
  README generates (`openssl rand -base64 48`) passes. 1.29.0 retires the Cloudron
  URL package (not used here). `start-docker.sh`, compared per step 2: it now reads
  `/app/data/.env` from the data volume as a layer below the container environment
  (variables set in the compose file still win, and the database-selection keys are
  ignored there), no longer defaults `ENABLE_GOOGLE_AUTH`, `ENABLE_GITHUB_AUTH` and
  `ALLOW_PRIVATE_IPS_FOR_VIDEO`, accepts `DATA_ENCRYPTION_KEYS` after a key rotation,
  and migrates through `Tymeslot.Release.migrate()`; it still forwards the
  environment the wrapper exports. The image moves to Elixir 1.20.4 on OTP
  28.5.0.7, drops Node.js and adds `/app/dotenv-reader.sh`; the `app` user (uid 1000)
  and the paths are unchanged. Migrations run at boot. Security fixes, with no CVE or
  GHSA IDs in the notes: plain-text copies of encrypted secrets and of poll, RSVP and
  free/busy link tokens dropped (1.22.0, 1.27.0), a narrower Content-Security-Policy
  (1.22.0), rate limits that simultaneous requests could slip past and IPv6 clients
  limited per network (1.27.0), Telegram webhooks refused with an empty secret
  (1.18.0), and data encryption key rotation without losing secrets.

## Upgrade checklist

Releases are frequent — eight between 2026-08-29 and 2026-09-06. Move the pin
deliberately, not on every tag.

1. Release notes: https://github.com/tymeslot/tymeslot/releases — migrations run
   automatically at boot, so read for data changes, not for commands
2. Compare `start-docker.sh` between the pinned and the new tag; the entrypoint
   wrapper relies on it forwarding the environment to the release:

   ```bash
   gh api -H "Accept: application/vnd.github.raw" "repos/tymeslot/tymeslot/contents/start-docker.sh?ref=v1.39.0" > /tmp/old.sh
   gh api -H "Accept: application/vnd.github.raw" "repos/tymeslot/tymeslot/contents/start-docker.sh?ref=vX.Y.Z" > /tmp/new.sh
   diff /tmp/old.sh /tmp/new.sh
   ```

3. Back up the database and `volumes/data`
4. New digest: `docker buildx imagetools inspect luka1thb/tymeslot:X.Y.Z-slim`
   → `APP_TAG` in `.env.example` and `.env`
5. `docker compose pull && docker compose up -d`
6. `docker compose logs tymeslot-app | grep -E 'migrations completed|Running TymeslotWeb'`
7. Update **Based on version** — and **Last verified** only after a real booking
   went through

## Diff against upstream

```bash
# The two-container compose file this stack is shaped after
gh api -H "Accept: application/vnd.github.raw" "repos/tymeslot/tymeslot/contents/docker-compose.with-postgres.yml?ref=v1.39.0"
# Every variable the release reads
gh api -H "Accept: application/vnd.github.raw" "repos/tymeslot/tymeslot/contents/.env.example?ref=v1.39.0"
```

## Useful commands

```bash
docker compose logs tymeslot-app --follow
docker compose exec -u 1000 tymeslot-app bin/tymeslot rpc 'Tymeslot.Release.list_admins()'
docker compose exec -u 1000 tymeslot-app bin/tymeslot remote      # IEx on the running node
```
