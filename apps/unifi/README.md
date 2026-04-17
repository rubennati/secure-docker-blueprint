# UniFi Network Application

> **Status: Draft — not yet live-tested.** First-pass import from inbox material.

Controller for Ubiquiti UniFi access points, switches, and gateways. Runs as an on-prem alternative to UniFi Cloud. Two-service stack: LSIO-built UniFi controller + MongoDB 4.4.

## Architecture

| Service | Image | Purpose |
|---------|-------|---------|
| `app` | `lscr.io/linuxserver/unifi-network-application:latest` | Web UI (port 8443) + device inform (8080) + STUN (3478/udp) + discovery (10001/udp) |
| `db` | `mongo:4.4` | Primary store — UniFi does **not** support MongoDB 5+ |

The web UI goes through Traefik (HTTPS). The L2/L3 device ports are exposed directly on the host because Traefik cannot proxy UDP discovery or device-inform broadcasts.

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
docker compose logs app --follow
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
- **Separate application user** — the controller uses its own MongoDB user (`unifi-app`) with `dbOwner` only on the `unifi` and `unifi_stat` databases. The Mongo root account is used only for one-time init.
- **`DB_APP_PWD_INLINE` duplicates the app-user password** — see Known Issues.
- **`no-new-privileges:true`** on both services.
- **MongoDB on `app-internal` (`internal: true`)** — not reachable from outside.
- **Default access `acc-tailscale` + `sec-3`** — the UniFi controller manages your network infrastructure; VPN-only is the right default. The device ports (3478/udp, 8080/tcp, 10001/udp) are still exposed to the LAN so devices can adopt.
- **Self-signed internal TLS → Traefik skip-verify** — UniFi uses a self-signed cert on its internal 8443. Traefik reverse-proxies HTTPS → HTTPS using the `skip-verify@file` server transport.

## Known Issues

- **Live-tested: no.** Expect minor surprises, especially first-run Mongo init timing.
- **MongoDB is pinned to 4.4** — do NOT bump to 5+. UniFi will refuse to start. Upstream has not yet supported newer Mongo versions.
- **`DB_APP_PWD_INLINE` duplicates the application password** — LSIO's UniFi image reads `MONGO_PASS` from env only. MongoDB side uses the secret file; app needs the same value inline.
- **Adoption requires `STUN` / `inform` ports on the same broadcast domain as the devices** — if your controller is not on the LAN, you must either:
  - Configure each device with `set-inform http://<host>:8080/inform` via SSH, or
  - Use L2 adoption over a VPN (Tailscale subnet router, ZeroTier, etc.)
- **First boot can take 2-3 minutes** — MongoDB init + Java startup.
- **`APP_TAG=latest`** — LSIO publishes rolling builds; pin to `version-X.Y.Z` for reproducibility.

## Details

- [UPSTREAM.md](UPSTREAM.md)
