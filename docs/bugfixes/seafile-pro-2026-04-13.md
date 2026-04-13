# Seafile Pro Bugfixes — 2026-04-13

## Bug #1: notification-server + md-server exit 127 (FIXED)

**Symptom:** Both containers crash with exit code 127 (command not found).

**Root cause:** Entrypoint wrapper set as single `entrypoint:` array. Docker overrides the original CMD when you set entrypoint. `exec "$@"` had nothing to execute.

**Fix:** Split into `entrypoint` (wrapper) + `command` (original CMD).

**Lesson:** Always check original ENTRYPOINT/CMD with `docker inspect`. Don't assume all services use the same pattern.

---

## Bug #2: seadoc + thumbnail "Waiting Nginx" loop (FIXED)

**Symptom:** Containers spam "Waiting Nginx" and never start.

**Root cause:** Images check for Caddy/Nginx proxy before starting. Without Traefik labels + proxy-public network, they never see incoming connections.

**Fix:** Added Traefik labels + proxy-public network (from working CE setup).

**Lesson:** Every service with Caddy labels in the original needs equivalent Traefik labels + proxy-public network.

---

## Bug #3: Docker Secrets not available in app container (FIXED — workaround)

**Symptom:** `docker exec app env | grep JWT` returns empty. All password/key env vars missing.

**Root cause:** Phusion's `my_init` init system clears and re-imports environment variables from `/etc/container_environment/` after each startup script. Our `export` commands in the entrypoint wrapper were lost during this cycle. Even writing to `/etc/container_environment/` didn't reliably work.

**Workaround:** Removed Docker Secrets entirely. Passwords stored directly in `.env` (gitignored). The entrypoint wrapper now only handles `seahub_custom.py` injection.

**Open:** Revisit when Seafile adds native `_FILE` env var support (GitHub issue #150 — open since 2019).

---

## Bug #4: Thumbnail 403 Forbidden (FIXED)

**Symptom:** Browser gets 403 when requesting `/thumbnail/...`.

**Root cause:** Two issues:
1. **Traefik router priority**: Main Seafile router caught all requests including `/thumbnail`. Sub-service routers need higher priority.
2. **Passwords missing**: JWT_PRIVATE_KEY not available in thumbnail container (Bug #3).

**Fix:** 
- Set `priority=1` on main router, `priority=100` on sub-services
- Passwords in .env instead of secrets
- `INNER_SEAHUB_SERVICE_URL=http://app:80`

---

## Bug #5: SeaSearch not indexing / Search returns no results (FIXED)

**Symptom:** File search and Wiki search return "No results matching".

**Root cause:** Three issues:
1. `SS_FIRST_ADMIN_PASSWORD` was empty (secrets wrapper didn't work)
2. `seafevents.conf` had Elasticsearch config instead of SeaSearch
3. SeaSearch uses port 4080, not 9200 (Elasticsearch) or 9999

**Fix:**
- Passwords in .env
- Added `[SEASEARCH]` section in `seafevents.conf` with base64 auth token
- Set `[INDEX FILES] enabled = false`
- Manual initial indexing: `pro.py search --update`

**Lesson:** SeaSearch is NOT a drop-in replacement for Elasticsearch config. It needs its own `[SEASEARCH]` section with different URL, port, and auth mechanism.

---

## Bug #6: ClamAV unreachable from app container (FIXED)

**Symptom:** `clamdscan` in app container couldn't connect to ClamAV daemon.

**Root cause:** ClamAV runs in separate container. `clamdscan` defaults to local Unix socket. Needs TCP configuration to reach ClamAV container.

**Fix:** Created `config/clamd-remote.conf` with `TCPSocket 3310` + `TCPAddr clamav`, mounted as `/etc/clamav/clamd.conf:ro` in app container.

**Verification:** `curl -s https://secure.eicar.org/eicar.com.txt | clamdscan -` → `Eicar-Test-Signature FOUND`

---

## Bug #7: seahub_custom.py not injected on first start (EXPECTED)

**Symptom:** OnlyOffice integration doesn't work after first `docker compose up -d`.

**Root cause:** On first boot, Seafile creates `seahub_settings.py`. Our entrypoint wrapper tries to append custom settings but the file doesn't exist yet during the first run.

**Fix:** `docker compose restart app` after first start. The wrapper injects settings on the second run. Only needed once — documented in UPSTREAM.md.

---

## Lessons Learned

1. **Phusion `my_init` kills exported env vars** — Don't rely on shell `export` surviving `my_init`. Either use `.env` directly or write to `/etc/container_environment/`.

2. **Each Caddy-labeled service needs a Traefik equivalent** — Don't assume the main container routes sub-paths. Check the original and CE reference.

3. **Traefik router priority matters** — When multiple routers match the same Host, use `priority` to ensure PathPrefix routers are preferred over the catch-all.

4. **SeaSearch ≠ Elasticsearch config** — Different port (4080 vs 9200), different config section (`[SEASEARCH]` vs `[INDEX FILES]`), different auth (base64 token vs none).

5. **Start with the original pattern** — We wasted hours on the Secrets wrapper. Should have started with passwords in `.env` (like the original) and added Secrets as enhancement later.

---

## Open Issues / Security Notes

- **Passwords in .env**: Not ideal — `.env` is gitignored but still plain text on disk. Docker Secrets would be better but require solving the `my_init` env var problem. Monitor Seafile GitHub issue #150 for native `_FILE` support.

- **Post-install manual steps**: `seafevents.conf` and `seafile.conf` require manual configuration after first install. Could potentially be automated via the entrypoint wrapper in the future.

- **Notification WebSocket**: Works intermittently. May need WebSocket-specific Traefik middleware or connection upgrade headers. Test further.

- **SeaSearch initial errors**: `seasearch error: {"error":"id not found"}` appears during first indexing — seems to be normal (creates indexes on first run).
