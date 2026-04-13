# Upstream Reference

## Source

- **Repo:** https://manual.seafile.com/13.0/docker/pro/deploy_seafile_pro_with_docker/
- **Config source:** Official Seafile Pro Docker Compose files (inbox/seafile-pro_original)
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

- **Passwords in .env**: Docker Secrets via entrypoint wrapper didn't work with Phusion's `my_init` init system. Passwords are stored in `.env` (gitignored). TODO: revisit when Seafile adds native `_FILE` support.
- **Manual post-install config**: `seafevents.conf` and `seafile.conf` must be configured manually after first start (see below).
- **SeaDoc/Thumbnail Nginx check**: These containers check for Nginx/Caddy on startup. With Traefik, they need to be in `proxy-public` network with Traefik labels to pass this check.

## First-time setup

After the very first `docker compose up -d`:

```bash
# 1. Wait until app is healthy
docker compose ps

# 2. Restart app to inject seahub_custom.py (OnlyOffice + Metadata + Thumbnail)
docker compose restart app

# 3. Verify settings were injected
docker exec seafile-pro-app grep "Blueprint" /shared/seafile/conf/seahub_settings.py

# 4. Configure SeaSearch in seafevents.conf
#    Generate auth token:
echo -n '<SEAFILE_ADMIN_EMAIL>:<INIT_SEAFILE_ADMIN_PASSWORD>' | base64

#    Add to seafevents.conf:
docker exec -it seafile-pro-app bash -c "cat >> /shared/seafile/conf/seafevents.conf << 'CONF'

[SEASEARCH]
enabled = true
seasearch_url = http://seasearch:4080
seasearch_token = <YOUR_BASE64_TOKEN>
interval = 10m
index_office_pdf = true
CONF"

#    Disable old Elasticsearch config:
docker exec -it seafile-pro-app bash -c "sed -i '/^\[INDEX FILES\]/,/^$/{s/^enabled = true/enabled = false/}' /shared/seafile/conf/seafevents.conf"

# 5. Configure ClamAV virus scanning in seafile.conf
docker exec -it seafile-pro-app bash -c "cat >> /shared/seafile/conf/seafile.conf << 'CONF'

[virus_scan]
scan_command = clamdscan
virus_code = 1
nonvirus_code = 0
scan_interval = 5
scan_size_limit = 20
threads = 2
CONF"

# 6. Restart app to apply all config changes
docker compose restart app

# 7. Trigger initial search index
docker exec seafile-pro-app /opt/seafile/seafile-server-latest/pro/pro.py search --update

# 8. Verify everything works
curl -s https://your-domain/notification/ping  # should return {"ret": "pong"}
docker exec seafile-pro-app env | grep JWT_PRIVATE_KEY  # should show the key
docker exec seafile-pro-app bash -c "curl -s https://secure.eicar.org/eicar.com.txt | clamdscan -"  # should show FOUND
```

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
| Search "No results" | SeaSearch not configured in seafevents.conf | Add [SEASEARCH] section |
| env vars empty in app | my_init clears exports | Use .env directly, not Docker Secrets |
| ClamAV connection refused | Missing clamd-remote.conf mount | Mount config with TCPAddr clamav |
| OnlyOffice not loading | seahub_custom.py not injected | `docker compose restart app` |

## Upstream diff commands

```bash
# Compare upstream .env with ours
diff inbox/seafile-pro_original/.env apps/seafile-pro/.env.example

# Compare a specific service yml
diff inbox/seafile-pro_original/seafile-server.yml apps/seafile-pro/seafile-server.yml
```
