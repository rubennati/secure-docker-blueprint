# Upstream Reference

## Source

- **UniFi Network Application:** https://ui.com/download/unifi
- **LSIO image:** https://docs.linuxserver.io/images/docker-unifi-network-application/
- **LSIO GitHub:** https://github.com/linuxserver/docker-unifi-network-application
- **License:** EULA (Ubiquiti) / GPL-3 (LSIO scripts)
- **Origin:** US · Ubiquiti Inc · non-EU
- **Note:** Proprietary software — not open source. LSIO wrapper scripts are GPL-3. Ubiquiti is a US company; CLOUD Act applies to cloud-managed deployments. Self-hosted (local controller) has no cloud dependency.
- **Based on version:** `latest` (LSIO rolling build)
- **Last checked:** 2026-04-17

## What we use

- LSIO `lscr.io/linuxserver/unifi-network-application`
- Official `mongo:4.4` (highest Mongo version UniFi supports)
- Docker Secrets for Mongo root + application user passwords
- Bind-mount `./volumes/mongodb` and `./volumes/config`
- Custom init script (`./init-mongo.sh`) to create the app user from secrets

## What we changed and why

| Change | Reason |
|--------|--------|
| **Placeholder passwords replaced** — inbox `db-create.sh` had `deinPasswort` / `deinPasswort2` literals and `changeme` / `changeme-app` in compose | Now generated into Docker Secrets; init script reads them via `/run/secrets/` |
| **Hardcoded non-UTC timezone replaced with `${TZ}`** | Prevent leaking author's timezone |
| **Traefik labels added** for the web UI | Inbox exposed port 8443 directly to the host; now via Traefik HTTPS (with `skip-verify@file` for UniFi's self-signed cert). Device-inform + STUN + discovery ports stay direct because they cannot be proxied through L7 |
| **`db-create.sh` renamed to `init-mongo.sh` and parameterized** | Inbox script had literal usernames/passwords. Now reads secrets + env (`UNIFI_APP_USER`, `UNIFI_APP_DB`) for full reusability |
| **`MONGO_INITDB_ROOT_PASSWORD_FILE`** used | MongoDB 4.4+ supports `_FILE` on the root password |
| **`MONGO_PASS` stays inline as `DB_APP_PWD_INLINE`** | LSIO UniFi image has no `_FILE` support for `MONGO_PASS` — blueprint's well-known duplicate-secret-into-env pattern |
| **`app-internal` network (`internal: true`)** | Isolate MongoDB from host |
| **`security_opt: no-new-privileges`** on both services | Baseline hardening |
| **Healthcheck on Mongo changed from `exit 0` stub to `db.runCommand({ping:1})`** | The inbox healthcheck always passed, defeating `depends_on: service_healthy` |
| **Web UI port removed from `ports:`** | Traefik handles TLS termination + hostname routing |
| **Device ports `3478/udp`, `10001/udp`, `8080/tcp` kept on host** | Required for L2 discovery and inform — Traefik cannot proxy these |
| **Optional ports commented out** — inbox had `1900`, `8843`, `8880`, `6789`, `5514` as inactive | Kept as comments; uncomment if using guest portal / mobile speedtest / syslog |
| **`MEM_LIMIT` / `MEM_STARTUP` exposed as `.env`** | Blueprint pattern; includes sizing guidance in comments |
| **Access `acc-tailscale` + security `sec-3` defaults** | UniFi manages your network; VPN-only for the admin UI is standard practice |

## Upgrade checklist

LSIO rolls the UniFi controller as Ubiquiti publishes stable builds. Major UniFi Network versions can also bring DB schema changes.

1. Check the [UniFi release notes](https://community.ui.com/releases) — breaking changes + required firmware versions
2. Back up:
   ```bash
   # Mongo dump
   docker compose exec db sh -c \
     'mongodump --username ${DB_ROOT_USER} --password "$(cat /run/secrets/DB_ROOT_PWD)" \
       --authenticationDatabase admin --archive' \
     > unifi-db-$(date +%Y%m%d).archive
   # Controller config + device backups
   tar czf unifi-config-$(date +%Y%m%d).tgz volumes/config/
   ```
3. Bump `APP_TAG` in `.env` (pin to a specific LSIO build)
4. `docker compose pull && docker compose up -d`
5. Watch logs:
   ```bash
   docker compose logs app --follow
   ```
6. Verify: log in, confirm all devices are online, trigger a firmware check

### Rollback

Restore Mongo archive and `volumes/config/`, revert `APP_TAG`. Device firmware may also need rolling back if the new controller pushed a firmware upgrade.

## Useful commands

```bash
# Shell into the controller
docker compose exec app bash

# Mongo shell (as root)
docker compose exec db mongo -u "${DB_ROOT_USER}" -p "$(cat .secrets/db_root_pwd.txt)" --authenticationDatabase admin

# Manual backup (inside Mongo)
docker compose exec db sh -c \
  'mongodump --username ${DB_ROOT_USER} \
   --password "$(cat /run/secrets/DB_ROOT_PWD)" \
   --authenticationDatabase admin \
   --out /data/db/backup-$(date +%Y%m%d)'

# Reset admin password (as last resort, from controller shell)
docker compose exec app cat /config/data/system.properties
# … then via the UI recovery flow
```

## Constraints

- **MongoDB 4.4 only** — UniFi does not yet support MongoDB 5+ or 6+. Do NOT bump `DB_TAG` past 4.4 until Ubiquiti adds support.
- **Device inform URL** — devices adopted on a previous IP/host keep their old `set-inform` URL. After migrating the controller, either SSH into each device and update it manually or use DHCP option 43 to point new devices at the controller.
