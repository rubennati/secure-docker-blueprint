# Upstream Reference

## Source

- **Image:** https://hub.docker.com/r/luka1thb/tymeslot
- **GitHub:** https://github.com/tymeslot/tymeslot
- **Docs:** https://tymeslot.app/docs · `README-Docker.md` and `docs/ADMIN.md` in the repository
- **License:** AGPL-3.0
- **Origin:** Estonia · Diletta Luna OÜ (Tallinn) · EU
- **Based on version:** `1.15.1` (`-slim` tag, digest-pinned)
- **Last verified:** 2026-09-07 (v1.15.1)

What that date covers: a clean install, migrations, the healthcheck, Traefik
routing under `acc-tailscale` and `sec-3`, registration and the LiveView
dashboard from a VPN client, and a verification mail delivered over SMTP. A
booking from a guest's side has not been exercised.

## What we use

- The official `-slim` image: application only, no bundled PostgreSQL. The
  plain tag runs a PostgreSQL server inside the app container.
- `postgres:17-alpine` as the database, the shape of upstream's
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
| Social login off, `WEBHOOK_BASE_URL` unset | Attack surface; the host is not reachable from the public internet, so push channels cannot be registered |
| Traefik labels, `acc-tailscale`, `sec-3` | Blueprint standard. A first load is about ten requests, far below the soft burst; the access policy is the deployment decision the README describes |

## Upgrade checklist

Releases are frequent — eight between 2026-08-29 and 2026-09-06. Move the pin
deliberately, not on every tag.

1. Release notes: https://github.com/tymeslot/tymeslot/releases — migrations run
   automatically at boot, so read for data changes, not for commands
2. Compare `start-docker.sh` between the pinned and the new tag; the entrypoint
   wrapper relies on it forwarding the environment to the release:

   ```bash
   gh api -H "Accept: application/vnd.github.raw" "repos/tymeslot/tymeslot/contents/start-docker.sh?ref=v1.15.1" > /tmp/old.sh
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
gh api -H "Accept: application/vnd.github.raw" "repos/tymeslot/tymeslot/contents/docker-compose.with-postgres.yml?ref=v1.15.1"
# Every variable the release reads
gh api -H "Accept: application/vnd.github.raw" "repos/tymeslot/tymeslot/contents/.env.example?ref=v1.15.1"
```

## Useful commands

```bash
docker compose logs tymeslot-app --follow
docker compose exec -u 1000 tymeslot-app bin/tymeslot rpc 'Tymeslot.Release.list_admins()'
docker compose exec -u 1000 tymeslot-app bin/tymeslot remote      # IEx on the running node
```
