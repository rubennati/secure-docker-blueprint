# Upstream Reference

## Source

- **Repo:** https://manual.seafile.com/13.0/docker/pro/deploy_seafile_pro_with_docker/
- **Config source:** Official Seafile Pro Docker Compose files (inbox/seafile-pro_original)
- **License:** Commercial
- **Origin:** China · Seafile Ltd · non-EU
- **Note:** Commercial license — self-hosting permitted under the paid plan. Chinese company: data stored on self-hosted instances is under your jurisdiction, but the vendor itself is subject to Chinese law.
- **Based on version:** Seafile Pro 13.0
- **Last checked:** 2026-04-13

## What we use from upstream

| File | Used as | Notes |
|------|---------|-------|
| `seafile-server.yml` | Adapted | Caddy → Traefik, Blueprint naming, ClamAV config mount |
| `seadoc.yml` | Adapted | Caddy labels → Traefik labels |
| `notification-server.yml` | Adapted | Caddy labels → Traefik labels |
| `md-server.yml` | Adapted | Caddy labels removed (internal only) |
| `thumbnail-server.yml` | Adapted | Caddy labels → Traefik labels |
| `seasearch.yml` | Adapted | Blueprint naming |
| `clamav.yml` | Adapted | Blueprint naming |
| `elasticsearch.yml` | Kept as reference | Not in COMPOSE_FILE, use SeaSearch instead |
| `seafile-ai.yml` | Kept as reference | Not in COMPOSE_FILE, enable later |

## What we changed and why

| Change | Reason |
|--------|--------|
| Caddy → Traefik labels | Blueprint uses Traefik, not Caddy |
| Traefik priority=1 on main router, priority=100 on sub-services | Prevents main router from catching /thumbnail, /notification, /sdoc-server paths |
| `seafile-net` → `app-internal` + `proxy-public` | Blueprint network schema |
| Passwords in .env (not Docker Secrets) | Phusion's my_init clears exported env vars; Secrets wrapper failed |
| Container names → variables | Blueprint standard |
| Image names hardcoded, tags as variables | Blueprint standard |
| `security_opt: no-new-privileges` | Blueprint security baseline |
| `restart: always` → `unless-stopped` | Blueprint standard |
| `redis: condition: service_healthy` | CE learning — prevents race conditions |
| `start_period: 180s` for seafile | CE learning — first start takes long |
| Memcached removed | Pro uses Redis only |
| SeaSearch instead of Elasticsearch | Recommended by Seafile, lightweight |
| `seahub_custom.py` Pattern | For OnlyOffice + Metadata + Thumbnail Config |
| `clamd-remote.conf` mounted as `/etc/clamav/clamd.conf` | ClamAV runs in separate container, needs TCP connection |
| Entrypoint wrapper reduced to seahub_custom.py only | Secrets via my_init didn't work, passwords now in .env |

## Known limitations

- **Passwords in .env**: Docker Secrets via entrypoint wrapper didn't work with Phusion's `my_init` init system. Passwords are stored in `.env` (gitignored). TODO: revisit when Seafile adds native `_FILE` support. The same limitation applies to the SMTP password — `SEAFILE_SMTP_PASSWORD` is in `.env`, not a Docker Secret.
- **One restart needed after first start**: `docker compose restart app` triggers automatic config injection for seahub_settings.py, seafevents.conf, and seafile.conf. No manual editing needed.
- **SeaDoc/Thumbnail Nginx check**: These containers check for Nginx/Caddy on startup. With Traefik, they need to be in `proxy-public` network with Traefik labels to pass this check.
- **SEAHUB_DB_NAME is permanent**: Database names are chosen on first init. Changing `SEAHUB_DB_NAME` in `.env` after first start does not rename the database — it causes a mismatch. Migration requires manual database work.
- **`DB_USER` may not control the actual MariaDB username**: On Seafile Pro 13.0, the database user created during first init was `seafile` regardless of the `DB_USER` value in `.env`. Operators setting a custom `DB_USER` (e.g. `seafileu`) should verify the actual MariaDB username after first boot — the configured value may be silently ignored. The `.env.example` defaults to `DB_USER=seafile`, which matches observed behaviour.

## First-time setup

After the very first `docker compose up -d`:

```bash
# 1. Wait until app is healthy
docker compose ps

# 2. Restart app to inject ALL configs automatically:
#    - seahub_settings.py (OnlyOffice + Metadata + Thumbnail)
#    - seafevents.conf (SeaSearch — replaces Elasticsearch)
#    - seafile.conf (ClamAV virus scanning)
docker compose restart app

# 3. Verify all configs were injected
docker exec seafile-pro-app grep "Blueprint" /shared/seafile/conf/seahub_settings.py
docker exec seafile-pro-app grep "SEASEARCH" /shared/seafile/conf/seafevents.conf
docker exec seafile-pro-app grep "virus_scan" /shared/seafile/conf/seafile.conf

# 4. Trigger initial search index
docker exec seafile-pro-app /opt/seafile/seafile-server-latest/pro/pro.py search --update

# 5. Verify everything works
curl -s https://your-domain/notification/ping  # should return {"ret": "pong"}
docker exec seafile-pro-app env | grep JWT_PRIVATE_KEY  # should show the key
docker exec seafile-pro-app bash -c "curl -s https://secure.eicar.org/eicar.com.txt | clamdscan -"  # should show FOUND
```

**Why restart?** On first boot, Seafile creates its config files. Our entrypoint wrapper
detects these files on the second start and injects the Blueprint configs.

**Injection behaviour (important):** `seahub_settings.py` injection is one-time — the
marker `# --- Blueprint custom settings ---` prevents it from running again. This is
different from Seafile CE, which re-injects on every container start.

- Settings that use `os.environ.get()` (OnlyOffice URL, SMTP host, etc.) are evaluated at
  Django startup. Changing those values in `.env` and running `docker compose restart app`
  takes effect immediately — no re-injection needed.
- Adding a brand-new setting that was absent from `config/seahub_custom.py` at injection
  time requires removing the marker line and everything after it from `seahub_settings.py`,
  updating `config/seahub_custom.py` on the host, then restarting.
- `seafevents.conf` and `seafile.conf` injections are also one-time (separate markers).

## OnlyOffice integration

`ONLYOFFICE_HOST` expects a hostname only — no `https://`, no trailing slash. The Compose
file constructs the full URL: `https://${ONLYOFFICE_HOST}`. This becomes `ONLYOFFICE_URL`
in the container environment, and `seahub_custom.py` appends `/web-apps/apps/api/documents/api.js`
to produce the final `ONLYOFFICE_APIJS_URL` written to `seahub_settings.py`.

`ONLYOFFICE_JWT_SECRET` must match the secret on the OnlyOffice server exactly. In this
Blueprint, OnlyOffice's secret lives in `core/onlyoffice/.secrets/jwt_secret.txt`.

**Network requirements:**

| Who | Must reach | Why |
|---|---|---|
| Browser/client | OnlyOffice (`ONLYOFFICE_HOST`) | Loads the editor JS (`api.js`) and communicates with the editor |
| OnlyOffice server | Seafile's configured hostname (`APP_TRAEFIK_HOST`) | Fetches the document to open and saves it back on close |
| Seafile app container | Not required | Integration is browser-mediated; app only writes config |

The OnlyOffice-to-Seafile path can be public internet, Tailscale, or any direct route.
If DNS for `APP_TRAEFIK_HOST` resolves to a Tailscale address on the OnlyOffice server
(split-DNS), traffic will route via Tailscale automatically — no public internet exposure
required on the Seafile side.

**`APP_TRAEFIK_ACCESS` is a Traefik middleware mode, not a network reachability setting.**
`acc-public` removes Traefik's source-IP allowlist; it does not bypass upstream firewalls.
`acc-tailscale` enforces a source-IP allowlist for requests from the Tailscale CGNAT range
(`100.64.0.0/10`) and ULA range (`fd7a::/16`).

**Known caveat — `acc-tailscale` source-IP recognition:**
When Traefik receives a connection through Docker published ports, `docker-proxy` may
replace the original source IP with the Docker bridge gateway (`172.17.0.1`) before
Traefik sees the packet. Traefik then cannot match the Tailscale IP range, and
`acc-tailscale` rejects the request even though the traffic arrived via Tailscale.
The fix is to make `proxy-public` dual-stack so the client's IPv6 source address
survives to the allowlist — `TROUBLESHOOTING.md` §4.4 carries the daemon
prerequisites, the overlay and how to verify it. `acc-public` was the earlier
workaround here; it removes Traefik's IP check for every caller and is only
defensible while an upstream firewall independently blocks public inbound 80/443.

**On the OnlyOffice server**, the Seafile domain must be added to `ONLYOFFICE_ALLOWED_ORIGINS`
so browsers are permitted to embed the editor in an iframe. This is a CSP `frame-ancestors`
directive — any origin not listed is rejected by the browser even if the JWT is valid.
See `core/onlyoffice/.env.example` for the format:

```env
ONLYOFFICE_ALLOWED_ORIGINS=https://files.example.com
```

**Changes to `ONLYOFFICE_ALLOWED_ORIGINS` require container recreation** on the OnlyOffice
server (`docker compose up -d --force-recreate`), not just a restart. The value is embedded
in a Traefik label at container creation time and is not re-read on restart.

## Elasticsearch alternative

If you need Elasticsearch instead of SeaSearch:

1. Replace `seasearch.yml` with `elasticsearch.yml` in `COMPOSE_FILE`
2. Set permissions: `mkdir -p volumes/elasticsearch && chmod 777 volumes/elasticsearch`
3. In `seafevents.conf`: remove `[SEASEARCH]` section, set `[INDEX FILES] enabled = true`
4. See: https://manual.seafile.com/13.0/docker/pro/deploy_seafile_pro_with_docker/

## Upgrade checklist

When bumping the Seafile Pro version:

1. Check [Seafile changelog](https://manual.seafile.com/changelog/server-changelog/)
2. Check [upgrade notes](https://manual.seafile.com/13.0/upgrade/upgrade_docker/)
3. Bump `APP_TAG` and related service tags in `.env`
4. `docker compose pull` → `docker compose up -d`
5. Check `docker compose logs -f app` for migration output
6. Verify login and file access
7. Re-run search index: `docker exec app pro.py search --update`

## Troubleshooting & Verification

### Check all services are running

```bash
docker compose ps
# All containers should be Up/Healthy. No "Restarting" loops.
```

### Verify environment variables reach containers

```bash
# JWT key in app container (must not be empty)
docker exec seafile-pro-app env | grep JWT_PRIVATE_KEY

# Passwords in any container
docker exec seafile-pro-app env | grep -i "password\|secret"

# SeaSearch admin credentials
docker exec seafile-pro-seasearch env | grep SS_FIRST
```

### Check service connectivity

```bash
# SeaSearch reachable from app?
docker exec seafile-pro-app curl -s http://seasearch:4080/version
# Expected: {"version":"v0.0.0",...}

# Notification server reachable from outside?
curl -s https://your-domain/notification/ping
# Expected: {"ret": "pong"}

# Thumbnail server reachable from app?
docker exec seafile-pro-app curl -sI http://thumbnail-server/thumbnail/ping
# Expected: HTTP 405 (Method Not Allowed = server runs, just doesn't accept HEAD)

# ClamAV reachable from app?
docker exec seafile-pro-app bash -c "echo PING | nc -w3 clamav 3310"
# Expected: PONG

# Metadata server reachable from app?
docker exec seafile-pro-app curl -s http://md-server:8084/
```

### Check config files

```bash
# seahub_settings.py — OnlyOffice + Metadata + Thumbnail settings
docker exec seafile-pro-app grep -i "onlyoffice\|metadata\|thumbnail\|Blueprint" /shared/seafile/conf/seahub_settings.py

# seafevents.conf — SeaSearch config
docker exec seafile-pro-app cat /shared/seafile/conf/seafevents.conf | grep -A5 "SEASEARCH"

# seafile.conf — ClamAV config
docker exec seafile-pro-app cat /shared/seafile/conf/seafile.conf | grep -A7 "virus_scan"
```

### Check logs for errors

```bash
# Seafile app logs (main errors)
docker exec seafile-pro-app cat /shared/seafile/logs/seafevents.log | tail -30

# Specific error search
docker exec seafile-pro-app cat /shared/seafile/logs/seafevents.log | grep -i "error\|fail" | tail -10

# Virus scan status
docker exec seafile-pro-app cat /shared/seafile/logs/seafevents.log | grep -i "virus" | tail -10

# SeaSearch logs
docker exec seafile-pro-seasearch cat /opt/seasearch/data/log/seasearch.log | tail -20

# Individual service logs
docker compose logs --tail=20 seadoc
docker compose logs --tail=20 notification-server
docker compose logs --tail=20 md-server
docker compose logs --tail=20 thumbnail-server
docker compose logs --tail=20 seasearch
```

### Test ClamAV virus detection

```bash
# EICAR test (harmless test signature)
docker exec seafile-pro-app bash -c "curl -s https://secure.eicar.org/eicar.com.txt | clamdscan -"
# Expected: stream: Eicar-Test-Signature FOUND
```

### Trigger manual search index

```bash
# Useful after first install or adding many files
docker exec seafile-pro-app /opt/seafile/seafile-server-latest/pro/pro.py search --update
```

### Check original entrypoint/CMD of an image

```bash
# Useful when adding new overlay services
docker inspect --format='{{json .Config.Entrypoint}} {{json .Config.Cmd}}' <image>
```

### Common issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| Service exit code 127 | Wrong entrypoint/command path | Check original CMD with `docker inspect` |
| "Waiting Nginx" loop | Missing Traefik labels + proxy-public | Add labels like CE reference |
| Thumbnail 403 | Router priority or missing JWT | Set priority=100, check env vars |
| Search "No results" | SeaSearch not configured in seafevents.conf | `docker compose restart app` (auto-injects), or check manually with `grep SEASEARCH seafevents.conf` |
| env vars empty in app | my_init clears exports | Use .env directly, not Docker Secrets |
| ClamAV connection refused | Missing clamd-remote.conf mount | Mount config with TCPAddr clamav |
| OnlyOffice not loading | seahub_custom.py not injected | `docker compose restart app` (auto-injects) |
| ClamAV not scanning | virus_scan not in seafile.conf | `docker compose restart app` (auto-injects), or check manually with `grep virus_scan seafile.conf` |
| `acc-tailscale` rejects Tailscale-routed requests | A tailnet client connects over IPv6 and an IPv4-only `proxy-public` loses that source address before the allowlist is evaluated | Enable dual-stack — `TROUBLESHOOTING.md` §4.4 carries the daemon prerequisites and the overlay. `acc-public` was the earlier workaround and removes the IP check for everyone |
| Redis `WARNING Memory overcommit must be enabled` in logs | Host sysctl not tuned | Add `vm.overcommit_memory = 1` to `/etc/sysctl.conf`, then `sysctl -p`; non-blocking until then |
| MariaDB `io_uring_queue_init() failed with EPERM` in logs | Kernel restricts io_uring (`io_uring_disabled=2`) | Non-blocking — MariaDB falls back to libaio automatically; no action needed |

## Upstream diff commands

```bash
# Compare upstream .env with ours
diff inbox/seafile-pro_original/.env apps/seafile-pro/.env.example

# Compare a specific service yml
diff inbox/seafile-pro_original/seafile-server.yml apps/seafile-pro/seafile-server.yml
```
