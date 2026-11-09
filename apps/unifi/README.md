# UniFi Network Application

Controller for Ubiquiti UniFi access points, switches, and gateways. Runs as an on-prem alternative to UniFi Cloud. Two-service stack: LSIO-built UniFi controller + MongoDB 4.4.

Project, source, licence and origin: [`UPSTREAM.md`](UPSTREAM.md).

## Architecture

| Service | Image | Purpose |
|---------|-------|---------|
| `unifi-app` | `lscr.io/linuxserver/unifi-network-application:10.6.109` | Web UI (port 8443) + device inform (8080) + STUN (3478/udp) + discovery (10001/udp) |
| `db` | `mongo:8.0.34` | Primary store. The image supports 3.6–7.0 from UniFi 8.1, and 8.0 from UniFi 9.0 |

The web UI goes through Traefik (HTTPS). The L2/L3 device ports are exposed directly on the host because Traefik cannot proxy UDP discovery or device-inform broadcasts.

## Try it locally

Runs on `https://localhost:8443` without Traefik, DNS or a certificate.

```bash
# Local settings; the secrets ship empty, so fill the ones this stack needs
cp .env.local.example .env.local
printf 'DB_ROOT_PASSWORD=%s\n' "$(openssl rand -hex 32)" >> .env.local

mkdir -p volumes/local/mongodb volumes/local/config
docker compose -f docker-compose.local.yml --env-file .env.local up -d
# https://localhost:8443
docker compose -f docker-compose.local.yml --env-file .env.local down
```

`.env.local` holds plain values, not Docker Secrets — local only.

## Setup

```bash
# 1. Create .env
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, TZ, PUID/PGID, MEM_LIMIT

# 2. Generate DB secrets
mkdir -p .secrets
openssl rand -base64 32 | tr -d '\n' > .secrets/db_root_pwd.txt
openssl rand -hex 32 > .secrets/db_app_pwd.txt   # alphanumeric for UNIFI's parser

# 3. Sync DB_APP_PWD_INLINE with the secret file
sed -i "s|^DB_APP_PWD_INLINE=.*|DB_APP_PWD_INLINE=$(cat .secrets/db_app_pwd.txt)|" .env

# 4. Create volumes
mkdir -p volumes/mongodb volumes/config

# 5. Start
docker compose up -d

# 6. First-run is slow — MongoDB init script runs, Java heap warms up (~2-3 min)
docker compose logs unifi-app --follow
# Watch for: "UniFi Network Application is now available"

# 7. Open UI and run the setup wizard
# https://<APP_TRAEFIK_HOST>
# Create admin account, adopt your first device
```

## Verify

```bash
docker compose ps                                              # both healthy
curl -fsSIk https://<APP_TRAEFIK_HOST>/manage/account/login    # 200 OK
```

## Security Model

- **`MONGO_INITDB_ROOT_PASSWORD_FILE`** — Mongo root password is a Docker Secret; never lands in `.env`.
- **Separate application user** — the controller uses its own MongoDB user (`unifi-app`) with `dbOwner` only on the `unifi`, `unifi_stat` and `unifi_audit` databases. The Mongo root account is used only for one-time init.
- **`DB_APP_PWD_INLINE` duplicates the app-user password** — see Known Issues.
- **`no-new-privileges:true`** on both services.
- **MongoDB on `app-internal` (`internal: true`)** — not reachable from outside.
- **`access-vpn`, `limit-standard` and `headers-standard` as shipped** — the UniFi controller manages your network infrastructure; VPN-only is the right default. The device ports (3478/udp, 8080/tcp, 10001/udp) are still exposed to the LAN so devices can adopt.
- **Self-signed internal TLS → Traefik skip-verify** — UniFi uses a self-signed cert on its internal 8443. Traefik reverse-proxies HTTPS → HTTPS using the `skip-verify@file` server transport.

## Backup

| | |
|---|---|
| **Database** | MongoDB · container `unifi-db` · database `unifi` |
| **Password** | `.secrets/db_root_pwd.txt` (root) · `.secrets/db_app_pwd.txt` (application) |
| **State** | `./volumes/mongodb` (database) · `./volumes/config` (site configuration, backups, certificates) |
| **Reproducible** | nothing |
| **Quiescing** | Not needed with the MongoDB hook. A file-level copy of `volumes/mongodb` can capture a torn state and must not replace the dump. |

```yaml
mongodb_databases:
    - name: unifi
      container: unifi-db
      username: unifi
      password: "{credential file /srv/docker/apps/unifi/.secrets/db_app_pwd.txt}"
      authentication_database: admin
```

`authentication_database: admin` is required — the user is created in `admin`, so
a dump without it authenticates against the wrong database.

The controller also writes its own periodic `.unf` backups into `volumes/config`.
Those are the supported restore path for the controller itself and are worth
keeping even though the database dump duplicates them: restoring a `.unf` through
the UI is considerably less error-prone than reassembling a Mongo dump.

**Adopted devices keep running while this is down.** What is lost with the
database is the configuration and history, not the network.

**Restore order:** database first, then the app.

## Known Issues

- **Live-tested: no.** Expect minor surprises, especially first-run Mongo init timing.
- **MongoDB is pinned to 8.0, and used to be pinned to 4.4 on a wrong premise.** The image documents 3.6 to 7.0 as supported from UniFi 8.1, and 8.0 as well from UniFi 9.0; this stack runs 10.x. The old note said UniFi refuses anything past 4.4, which was not the case, and 4.4 stopped receiving fixes in February 2024.
- **On x86_64, any MongoDB above 4.4 needs a CPU with AVX support.** Check the host with `grep -o avx /proc/cpuinfo | head -1` before deploying. Without it the database will not start.
- **An existing install cannot go straight from 4.4 to 8.0.** MongoDB upgrades one major version at a time and each step must complete before the next. The path is in `UPSTREAM.md`; a fresh install starts at 8.0 with nothing to migrate.
- **`DB_APP_PWD_INLINE` duplicates the application password** — LSIO's UniFi image reads `MONGO_PASS` from env only. MongoDB side uses the secret file; app needs the same value inline.
- **Adoption requires `STUN` / `inform` ports on the same broadcast domain as the devices** — if your controller is not on the LAN, you must either:
  - Configure each device with `set-inform http://<host>:8080/inform` via SSH, or
  - Use L2 adoption over a VPN (Tailscale subnet router, ZeroTier, etc.)
- **Port 8080 on the host belongs to UniFi.** `core/crowdsec` publishes its LAPI for the host firewall bouncer on `127.0.0.1:8081` for that reason; an older CrowdSec `.env` with `CROWDSEC_LAPI_PORT=8080` makes this stack fail with `Bind for … 8080 … already allocated` — move CrowdSec, as its README describes. Both ran side by side on the lab host (VM) on 2026-11-09.
- **First boot can take 2-3 minutes** — MongoDB init + Java startup.
- **`APP_TAG=latest`** — LSIO publishes rolling builds; pin to `version-X.Y.Z` for reproducibility.

## Open findings

<!-- findings:start — generated by scripts/ci/lifecycle-report.py from upstream-status.json; edit the text around it -->

**Findings in the upstream images** at the pin `10.6.109` — the newest upstream release. Scanned 2026-11-09; counted are findings with a published fix, as CRITICAL · HIGH. They come with the images as upstream publishes them.

| Image | Base system | Libraries | Programs |
|---|---|---|---|
| `lscr.io/linuxserver/unifi-network-application:10.6.109` | 0 · 1 | 11 · 27 | — |
| `mongo:8.0.34` | 0 · 1 | 0 · 3 | 1 · 26 |

<!-- findings:end -->

UniFi Network Application 10.6.109 ships its own Tomcat 10.1.54, Spring Web MVC
6.2.18 and Bouncy Castle 1.84, with 11 CRITICAL vulnerabilities between them
that have published fixes. They are inside Ubiquiti's application, and no newer
release exists yet. The MongoDB image carries one finding in its `gosu` start-up
helper (CVE-2025-68121, Go TLS), which opens no TLS connection.

**Risk:** Tomcat serves the controller's web interface and API, so treat its
flaws as reachable on that port. Keep the controller off the public internet,
reach it over VPN, and watch for the next UniFi Network Application release.

## Details

- [UPSTREAM.md](UPSTREAM.md)
