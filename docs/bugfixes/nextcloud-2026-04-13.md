# Nextcloud Bugfixes — 2026-04-13

## Bug #1: config.php Permission Denied (503)

**Symptom:** Browser shows "Can't write into config directory!" with 503.

**Logs:**
```
fopen(/var/www/html/config/config.php): Failed to open stream: Permission denied
chmod(): Operation not permitted
```

**Root cause:** Nextcloud entrypoint creates `config.php` as `root:root`. PHP-FPM runs as `www-data` and cannot write to it. The `security_opt: no-new-privileges` setting prevents the entrypoint from properly managing file ownership.

**Fix:** Remove `no-new-privileges` from the `app` and `cron` containers. Nextcloud's entrypoint needs root privileges to chown/chmod files before PHP-FPM drops to www-data.

**Manual workaround (if it happens again):**
```bash
docker compose exec app chown www-data:www-data /var/www/html/config/config.php
```

**Lesson:** Not every container can use `no-new-privileges`. Apps with entrypoints that manage file permissions as root need to be excluded. Document this per app.

---

## Bug #2: Redis Password Breaks PHP Session Handler

**Symptom:** Login form refreshes without error. POST returns 303 redirect back to login page. Sessions not persisted.

**Logs:**
```
session_start(): Redis connection not available
session_start(): Failed to read session data: redis (path: tcp://redis:6379?auth=MinUkW6wAbixqHCaVCUE9aO+YR+0FYTIWRDVqH7wPrA=)
```

**Root cause:** base64-encoded passwords contain `+` and `=` characters. PHP's Redis session handler passes the password as a URL query parameter (`?auth=...`). The `+` is interpreted as a space, breaking authentication.

**Fix:** Use `openssl rand -hex 32` instead of `openssl rand -base64 32` for Redis passwords. Hex output only contains `[0-9a-f]` — no URL-unsafe characters.

**Lesson:** Any password used in a URL context (Redis session handler, DSN strings) must avoid `+`, `=`, `/`, `&`, `?`. Use hex encoding for these.

---

## Bug #3: Admin User Not Created via _FILE Secrets

**Symptom:** First install completes but admin account has wrong password. Login always fails with 303 redirect.

**Root cause:** `NEXTCLOUD_ADMIN_USER_FILE` and `NEXTCLOUD_ADMIN_PASSWORD_FILE` were added to the compose but the Nextcloud Docker image's auto-install behavior with `_FILE` secrets for admin credentials appears unreliable. The inbox reference (which works) does not use automated admin creation at all.

**Fix:** Removed `NEXTCLOUD_ADMIN_USER_FILE` / `NEXTCLOUD_ADMIN_PASSWORD_FILE` from compose. Admin user is now created manually via the web-based installation wizard on first browser access — matching the inbox pattern.

**Lesson:** Follow the inbox (L2) pattern. Don't add features that weren't in the working reference without testing them first.

---

## Bug #4: Redis Healthcheck Variable Not Resolved

**Symptom:** `nextcloud-redis` marked as unhealthy, all dependent containers fail to start.

**Root cause:** Healthcheck used `$${REDIS_PASSWORD}` (double-dollar escape). This tells Docker Compose to pass the literal `${REDIS_PASSWORD}` string into the container at runtime. But the Redis container has no environment block setting this variable, so it resolves to empty.

**Fix:** Changed to `${REDIS_PASSWORD}` (single-dollar). Compose substitutes the value from `.env` at compose-time before the healthcheck runs.

**Lesson:** Use `$$` only when the variable must be resolved inside the container at runtime (e.g. from the container's own environment). Use `$` when Compose should substitute the value before starting the container.

---

## Bug #5: OnlyOffice "Error while downloading the document file"

**Symptom:** OnlyOffice integration in Nextcloud shows "Error occurred in the document service: Error while downloading the document file to be converted."

**Root cause:** Nextcloud was behind `acc-tailscale` (Tailscale IP allowlist). OnlyOffice calls back to Nextcloud via the public domain (`https://cloud.example.com`) to download documents. This callback comes from OnlyOffice's container IP (not a Tailscale IP), so Traefik's access middleware blocks it.

**Fix:** Changed Nextcloud from `acc-tailscale` to `acc-public`. Any service that receives callbacks from other services via its public domain must be publicly accessible.

**Lesson:** When two services communicate via their public domains (not internal Docker networking), both must be `acc-public`. This applies to any integration where Service A tells Service B to fetch content from Service A's URL (OnlyOffice ↔ Nextcloud, OnlyOffice ↔ Seafile).
