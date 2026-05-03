# Upstream Reference

## Source

- **Image:** https://docs.linuxserver.io/images/docker-heimdall/
- **GitHub (LinuxServer build):** https://github.com/linuxserver/docker-heimdall
- **GitHub (Heimdall upstream):** https://github.com/linuxserver/Heimdall
- **License:** MIT
- **Based on version:** `2.6.3`
- **Last verified:** 2026-05-02 (v2.6.3)

## What we use

- LinuxServer.io `lscr.io/linuxserver/heimdall` image
- LinuxServer.io's s6-overlay + PUID/PGID pattern
- Bind-mount `./config/` for persistent state

## What we changed and why

| Change | Reason |
|--------|--------|
| Traefik labels instead of port `:8004:80` | Blueprint routes via Traefik |
| Pinned `APP_TAG` | Inbox had `:latest` |
| `PUID`/`PGID` as env vars (not via `user:`) | LinuxServer.io / s6-overlay requirement; explicit documentation to prevent the s6 `/run` permission trap |
| `ALLOW_INTERNAL_REQUESTS=false` default | Defence-in-depth; widgets should not probe RFC1918 by default |
| `security_opt: no-new-privileges` | Blueprint baseline |
| Inbox FILE__ secret example removed (`FILE__MYVAR`) | Not used by Heimdall itself; was just an illustration. Reintroduce if a widget or integration actually needs a secret via `_FILE`. |

## Upgrade checklist

LinuxServer.io images get frequent minor bumps (weekly). Major upgrades infrequent.

1. Check [LinuxServer changelog](https://fleet.linuxserver.io/image?name=linuxserver/heimdall)
2. Back up `./config/`:
   ```bash
   tar czf heimdall-config-$(date +%Y%m%d).tgz config/
   ```
3. Bump `APP_TAG`
4. `docker compose pull && docker compose up -d`
5. First start after upgrade may run DB migrations (Laravel); watch logs

## Useful commands

```bash
# Shell
docker compose exec app bash

# LinuxServer.io's "cont-init" runs are logged at container start
docker compose logs app | grep cont-init

# Heimdall uses Laravel — artisan is available
docker compose exec app bash -c 'cd /app/www && php artisan migrate:status'
```
