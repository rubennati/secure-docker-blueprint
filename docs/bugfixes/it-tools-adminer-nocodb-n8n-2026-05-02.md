# IT-Tools, Adminer, NocoDB, n8n — Live-Test Bugfixes

**Date:** 2026-05-02

---

# IT-Tools — Container crash-loop after start

**App:** `apps/it-tools/`  
**Image:** `ghcr.io/corentinth/it-tools`

## Symptom

Two separate issues found before the container stabilised.

**Issue 1 — tag not found:**
```
Error response from daemon: manifest unknown
```
Docker could not pull the image. The tag `2025.7.18-a0bc346` does not exist on GHCR.

**Issue 2 — cap_drop crash-loop (after tag fix):**
```
nginx: [emerg] chown("/var/cache/nginx/client_temp", 101) failed (1: Operation not permitted)
```
Container entered a crash-loop immediately after start.

## Root Causes

**Issue 1:** The `.env.example` contained a future/invented tag. Latest release at test time was `2024.10.22-7ca5933`.

**Issue 2:** The `cap_drop: ALL` hardening block dropped `CAP_CHOWN`. The nginx entrypoint runs as root briefly to `chown` its working directories (`/var/cache/nginx/*`) before dropping privileges to UID 101. Without `CAP_CHOWN` the entrypoint aborts.

## Fixes

- **Tag:** corrected to `2024.10.22-7ca5933` in `.env.example`.
- **cap_drop:** removed `cap_drop: ALL`. Filesystem hardening retained via `read_only: true` and `tmpfs` mounts for `/tmp`, `/var/cache/nginx`, `/var/run`.

```yaml
# cap_drop: ALL not set — nginx entrypoint requires CAP_CHOWN to
# set up /var/cache/nginx at startup. Without it the container crash-loops.
read_only: true
tmpfs:
  - /tmp
  - /var/cache/nginx
  - /var/run
```

---

# Adminer — Healthcheck always unhealthy

**App:** `apps/adminer/`  
**Image:** `adminer`

## Symptom

```
docker ps → STATUS: unhealthy
```
Container served the UI correctly but never passed its healthcheck.

## Root Cause

The original healthcheck used `curl -fso /dev/null http://127.0.0.1:8080`. The official `adminer` image ships no `curl` and no `wget` — only `php`. The check command failed with `executable file not found in $PATH` on every interval, keeping the container permanently `unhealthy`.

## Fix

Replaced the check with a PHP one-liner that opens a TCP socket to confirm the port is listening:

```yaml
healthcheck:
  test: ["CMD", "php", "-r", "exit(stream_socket_client('tcp://127.0.0.1:8080')?0:1);"]
```

`stream_socket_client` returns `false` on failure, which maps to exit code 1 (unhealthy). The function call contains no `$variables`, avoiding Docker Compose variable interpolation.

---

# NocoDB — HTTP 429 on first page load

**App:** `apps/nocodb/`  
**Image:** `nocodb/nocodb`

## Symptom

Browser returned `429 Too Many Requests` on the first visit. The NocoDB UI never rendered.

```
GET /0.js 429
GET /1.js 429
GET /2.js 429
... (100+ requests)
```

## Root Cause

NocoDB is a Vue SPA that loads 100+ JavaScript chunks simultaneously on the first page visit. The Traefik `sec-3` middleware chain includes `rl-soft` (average: 100 req/s, burst: 50). The parallel chunk requests saturated the burst allowance instantly.

## Fix

Changed `APP_TRAEFIK_SECURITY` from `sec-3` to `sec-1`. The `sec-1` profile sets basic security headers (`hdr-basic`, `compress`) without any rate-limit middleware. This is acceptable because the app is VPN-only (`acc-tailscale`).

```
# sec-3 → sec-1: NocoDB loads 100+ JS chunks simultaneously on first visit.
# Rate-limit middleware triggers 429 on initial page load.
APP_TRAEFIK_SECURITY=sec-1
```

The same pattern applies to any heavy SPA deployed behind `acc-tailscale`.

---

# NocoDB — First signup blocked by email verification

**App:** `apps/nocodb/`

## Symptom

Clicking "Sign up" on a fresh install showed:

```
Email Plugin not configured or active
```

Registration could not complete. The error message was misleading — there is no broken plugin.

## Root Cause

NocoDB requires email verification for new sign-ups by default. With no SMTP configured, the verification email cannot be sent and signup is blocked. The correct solution is to pre-create the super-admin account at container startup using `NC_ADMIN_EMAIL` and `NC_ADMIN_PASSWORD`.

The compose file originally used the wrong env var names (`NC_SUPER_ADMIN_EMAIL` / `NC_SUPER_ADMIN_PASSWORD`), which do not exist in NocoDB's environment. Verified against NocoDB source code.

## Fix

Added the correct env vars to `docker-compose.yml` and `.env.example`:

```yaml
NC_ADMIN_EMAIL: ${NC_ADMIN_EMAIL:-}
NC_ADMIN_PASSWORD: ${NC_ADMIN_PASSWORD:-}
```

The `:-` default means neither variable is required — leave both empty to create the admin interactively via the signup page once an SMTP relay is configured. Password requirements: minimum 8 characters, one uppercase letter, one number, one special character.

---

# n8n — HTTP 429 on first page load

**App:** `apps/n8n/`  
**Image:** `docker.n8n.io/n8nio/n8n`

## Symptom

Identical to the NocoDB issue: browser returned `429 Too Many Requests` on the first visit. The n8n editor never loaded.

## Root Cause and Fix

Same root cause as NocoDB: n8n is also a heavy SPA (React + many asset chunks). Changed `APP_TRAEFIK_SECURITY` from `sec-3` to `sec-1`. VPN-only access (`acc-tailscale`) justifies no rate-limit at the Traefik layer.

---

# n8n — Deprecated `N8N_RUNNERS_ENABLED` env var

**App:** `apps/n8n/`  
**n8n version:** 2.19.2

## Symptom

```
There is a deprecation related to your environment variables:
 - N8N_RUNNERS_ENABLED -> Remove this environment variable; it is no longer needed.
```

## Fix

Removed `N8N_RUNNERS_ENABLED` from `docker-compose.yml`. The task runner feature is always active in 2.19.2 and the env var no longer has any effect.

---

# n8n — `ERR_ERL_UNEXPECTED_X_FORWARDED_FOR` in logs

**App:** `apps/n8n/`

## Symptom

```
ValidationError: The 'X-Forwarded-For' header is set but the Express 'trust proxy'
setting is false (default). ERR_ERL_UNEXPECTED_X_FORWARDED_FOR
```

Logged on every incoming request. The app functioned correctly but n8n's internal rate-limiter could not accurately identify client IPs.

## Root Cause

n8n runs its own Express-based rate-limiter (`express-rate-limit`). When deployed behind Traefik, the `X-Forwarded-For` header is present but Express's `trust proxy` is not configured — the rate-limiter raises a validation error because it cannot safely determine the real client IP.

## Fix

Added `N8N_PROXY_HOPS: "1"` to `docker-compose.yml`. This tells n8n to trust one reverse-proxy hop (Traefik) for `X-Forwarded-For` resolution.

```yaml
N8N_PROXY_HOPS: "1"
```

Source: [n8n-io/n8n#9172](https://github.com/n8n-io/n8n/issues/9172) — confirmed by n8n contributor.
