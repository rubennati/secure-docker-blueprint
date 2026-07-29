# Troubleshooting Guide

Systematic approach to debugging Docker services behind Traefik.
Based on real issues found during live testing of this blueprint.

---

## Debugging Strategy

Always work **inside out** — start at the container, then move outward through
each layer until you find where things break:

```text
Container (app itself)
  -> Docker Network (can services reach each other?)
    -> Traefik Router (is the route configured?)
      -> Traefik Middlewares (is something blocking?)
        -> TLS / Certificate (is HTTPS working?)
          -> DNS / Client (is the request reaching the server?)
```

---

## Layer 1: Is the Container Running?

### Check container status

```bash
docker ps --format "table {{.Names}}\t{{.Status}}" | grep <app>
```

**What to look for:**

- `Up X minutes (healthy)` — good
- `Up X seconds (health: starting)` — still booting, wait for `start_period`
- `Restarting` or `exited with code X` — broken, check logs
- Not listed at all — container failed to start

### Check logs

```bash
# Live logs (follow mode)
docker compose logs -f

# Specific service only
docker compose logs -f app

# Last 50 lines
docker compose logs --tail 50 app
```

> **Traefik is an exception — `docker compose logs traefik` shows nothing.**
> `core/traefik` configures `log.filePath` / `accessLog.filePath` in
> `traefik.yml`, so Traefik writes to files inside the container
> (`/var/log/traefik/traefik.log`, `/var/log/traefik/access.log`), not to
> stdout. `docker compose logs` only captures stdout/stderr — for Traefik,
> read the files instead:
>
> ```bash
> docker exec traefik-core cat /var/log/traefik/traefik.log    # startup, ACME, errors
> docker exec traefik-core cat /var/log/traefik/access.log     # HTTP requests (JSON)
> # or directly from the host (bind-mounted):
> cat core/traefik/volumes/logs/traefik.log
> ```
>
> `access.log` is additionally buffered (`TRAEFIK_ACCESSLOG_BUFFER`, default
> 100 entries) — it may not show very recent requests until the buffer
> flushes. `traefik.log` is not buffered the same way.

**Common log patterns and what they mean:**

| Log message | Cause | Fix |
|---|---|---|
| `password authentication failed` | DB password mismatch (often trailing newline) | Strip newlines from secrets, recreate DB volume |
| `Connection refused` on port X | Dependency not ready or wrong hostname | Check `depends_on` with health condition |
| `_FILE` variable ignored silently | Image doesn't support `_FILE` convention | Use entrypoint wrapper pattern |
| `s6-overlay: /run belongs to uid 0` | `user:` directive conflicts with s6-overlay | Remove `user:`, use `USERMAP_UID` env var |
| `FATAL: role "xxx" does not exist` | DB user not created (wrong env var name) | Check image docs for correct env var |
| `exec format error` | Wrong platform (ARM image on AMD64 or vice versa) | Pull correct architecture |

### Test the app directly (bypass Traefik)

```bash
# HTTP status code from inside the container
docker exec <container> curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:<port>/
```

**Why:** If this returns 200/302, the app works — the problem is in Traefik or
the network. If it fails, the problem is in the app itself.

**Note:** Some minimal images don't have `curl`. Alternatives:

```bash
# wget (Alpine-based images)
docker exec <container> wget -qO- http://127.0.0.1:<port>/ 2>&1 | head -5

# Check what's available
docker exec <container> which curl wget
```

---

## Layer 2: Docker Network

### Can services reach each other?

```bash
# From app container, can it reach the database?
docker exec <app-container> ping -c 1 database

# Or test the actual port
docker exec <app-container> curl -s telnet://database:5432
```

### Check which networks a container is in

```bash
docker inspect <container> --format='{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}'
```

**Why:** If the app is in `proxy-public` but the database is only in
`app-internal`, they can't communicate unless the app is in both networks.

### List all containers in a network

```bash
docker network inspect proxy-public --format='{{range .Containers}}{{.Name}} {{end}}'
```

---

## Layer 3: Traefik Router

### Check if Traefik sees the container

```bash
# Are the labels correct on the running container?
docker inspect <container> --format='{{json .Config.Labels}}' | python3 -m json.tool | grep traefik
```

**Why:** Traefik reads labels from running containers. If you changed
`docker-compose.yml` but didn't recreate the container, the old labels are
still active.

### Check Traefik dashboard

Open `https://<traefik-dashboard>/dashboard/` and look for:

- **HTTP Routers** — is the app's router listed? Status green?
- **HTTP Middlewares** — are all referenced middlewares found?
- **HTTP Services** — is the service healthy?

### Common router problems

| Symptom | Cause | Fix |
|---|---|---|
| Router not listed | `traefik.enable=true` missing or container not in `proxy-public` | Add label, check network |
| Router shows error | Middleware reference broken (wrong name or suffix) | Fix `@file` / `@docker` suffix |
| Router OK but 404 | Wrong `Host()` rule or service port | Check `APP_TRAEFIK_HOST` and port |

---

## Layer 4: Traefik Middlewares

This is the most common source of 403 errors.

### Check what middlewares the router uses

```bash
docker inspect <container> --format='{{json .Config.Labels}}' | python3 -m json.tool | grep middlewares
```

### Provider suffix rules

Middlewares defined in **file config** (e.g. `security.yml`, `access.yml`) need
`@file`. Middlewares defined in **Docker labels** need `@docker`.

```yaml
# File-provider middleware — needs @file
- "traefik.http.routers.app.middlewares=acc-tailscale@file,sec-2@file"

# Docker-provider middleware (defined in same compose labels) — needs @docker
- "traefik.http.routers.app.middlewares=app-headers@docker,acc-tailscale@file"

# WRONG — missing suffix, Traefik can't find it → 403
- "traefik.http.routers.app.middlewares=app-headers,acc-tailscale@file"
```

**Rule:** If a middleware in the chain can't be found, the **entire chain fails**
and Traefik returns **403 Forbidden** — not a helpful error message.

### Check middleware definitions in file provider

```bash
# Access control (ipAllowList)
cat /path/to/secure-docker-blueprint/core/traefik/config/dynamic/access.yml

# Security headers, rate limits, chains
cat /path/to/secure-docker-blueprint/core/traefik/config/dynamic/security.yml

# TLS profiles
cat /path/to/secure-docker-blueprint/core/traefik/config/dynamic/tls-profiles.yml
```

---

## Layer 5: Access Control (IP Allow Lists)

### Check which IP Traefik sees for your request

Look at Traefik's **access log**:

```bash
docker exec <traefik-container> cat /var/log/traefik/access.log | grep <app> | tail -5
```

**Key fields in the JSON log:**

| Field | Meaning |
|---|---|
| `ClientHost` | The IP Traefik uses for ipAllowList matching |
| `DownstreamStatus` | HTTP status returned to client (403 = blocked) |
| `OriginStatus` | HTTP status from the backend (0 = never reached backend) |
| `RouterName` | Which router handled the request |

**If `OriginStatus` is 0 and `DownstreamStatus` is 403:** Traefik blocked the
request before it reached the container. This is a middleware issue (usually
`acc-tailscale` IP allowlist).

### Tailscale IP ranges

```yaml
# /path/to/secure-docker-blueprint/core/traefik/config/dynamic/access.yml
acc-tailscale:
  ipAllowList:
    sourceRange:
      - "100.64.0.0/10"       # Tailscale IPv4 (CGNAT range)
      - "fd7a:115c:a1e0::/48" # Tailscale IPv6
```

### Common IP problems

| You see | Meaning | Fix |
|---|---|---|
| `ClientHost: 100.x.x.x` | Tailscale IPv4 — should pass `acc-tailscale` | Check IP range in access.yml |
| `ClientHost: fd7a:...` | Tailscale IPv6 — should pass `acc-tailscale` (default range already covers it) | If still blocked, check `TAILSCALE_CIDR_V6` wasn't overridden to something narrower in `.env` |
| `ClientHost: 178.x.x.x` (public IP) | Traffic goes over internet, not VPN | DNS resolves to public IP, not Tailscale IP |
| `ClientHost: 172.x.x.x` (Docker bridge gateway) — request from a **remote** client | The real client IP was lost before Traefik saw it — almost always a Tailscale **IPv6** client hitting an **IPv4-only** `proxy-public` network. Docker's userland-proxy bridged the IPv6 host connection into the IPv4-only bridge and re-sourced it from the gateway address. | Not a `forwardedHeaders` issue (that's for the Cloudflare path only). Fix is network-level: dual-stack `proxy-public` + Docker daemon prerequisites. See [`core/traefik/docs/ipv6-dual-stack.md`](../../core/traefik/docs/ipv6-dual-stack.md) and [`docs/bugfixes/traefik-ipv6-dualstack-2026-06-19.md`](../bugfixes/traefik-ipv6-dualstack-2026-06-19.md). Do **not** "fix" this by allowlisting `172.x.x.x/32` — see "why this is a workaround, not a fix" in that doc. |
| `ClientHost: 172.x.x.x` (Docker bridge gateway) — request run **on the Traefik host itself** (e.g. `curl` over SSH on the same server) | **Not the bug above — a different, unrelated Docker behavior.** A process on the Docker host connecting to the host's own published port (loopback/hairpin) gets NAT'd through the bridge gateway address, regardless of whether `proxy-public` is dual-stack and regardless of IPv4/IPv6. This happens even on a fully-fixed, correctly dual-stack network. | Nothing to fix. Don't test client-IP preservation by curling from the Traefik host itself — test from a genuinely remote client (another machine on the tailnet, or a real browser/Cloudflare request). A 403 here with `ClientHost: 172.x.x.x` from a self-curl is expected and does not indicate the dual-stack fix failed. |
| Cloudflare edge IP in `ClientAddr`, real client IP in `ClientHost` | Cloudflare path working correctly | Nothing to fix — this is the expected good state. If `ClientHost` instead shows the Cloudflare edge IP too, `forwardedHeaders.trustedIPs` is missing or doesn't cover the connecting edge IP — see [Trusted Proxy Headers](traefik-security.md#trusted-proxy-headers-traefikyml--forwardedheaders) |

### IPv4 vs. IPv6 — isolating which layer is broken

Test both address families directly against the domain, independent of
which client/network you're on:

```bash
# Force IPv4
curl -4 -v https://<app-domain>/

# Force IPv6
curl -6 -v https://<app-domain>/
```

If `-4` works and `-6` doesn't (or vice versa), the problem is specific to
that address family — check it at each layer outward from the host:

```bash
# Is the public Docker network actually dual-stack?
# (EnableIPv6 should be true, IPAM.Config should show both an IPv4 and
# an IPv6 subnet if dual-stack was intended)
docker network inspect proxy-public

# Is the Traefik container itself attached with an IPv6 address?
docker inspect traefik-core --format \
  '{{range .NetworkSettings.Networks}}{{.IPAddress}} {{.GlobalIPv6Address}}{{end}}'

# Is the host actually listening on both families for 80/443?
# Look for both 0.0.0.0:80/443 (IPv4) and :::80/443 or [::]:80/443 (IPv6)
sudo ss -ltnp | grep -E ':80|:443'

# Is docker-proxy still bridging host ports into the container network?
# (expected to be ABSENT once userland-proxy: false is set in
# /etc/docker/daemon.json — its presence here means the daemon prerequisite
# wasn't applied, or the daemon wasn't restarted after editing daemon.json)
ps aux | grep docker-proxy
```

Cross-reference container name and network name with your actual `.env`
values — `traefik-core` / `proxy-public` are this blueprint's defaults
(`TRAEFIK_CONTAINER_NAME` / `PUBLIC_NETWORK`).

### DNS vs Tailscale

If your domain `app.example.com` resolves to the server's **public IP**, your
browser connects over the internet — even if Tailscale is running. The
`acc-tailscale` middleware then blocks you because your source IP is public,
not Tailscale.

**Solutions:**

- Use Tailscale MagicDNS or Split-DNS to resolve domains to Tailscale IPs
- Use `acc-public` for services that need internet access
- Access via Tailscale IP directly (e.g. `https://100.x.x.x`)

---

## Layer 6: TLS / Mixed Content

### Certificate problems

```bash
# Check which certificate Traefik serves
openssl s_client -connect <domain>:443 -servername <domain> 2>/dev/null | openssl x509 -noout -subject -dates
```

### Mixed Content (HTTPS page loads HTTP resources)

**Symptom:** Browser console shows:

```text
Mixed Content: The page at 'https://...' was loaded over HTTPS,
but requested an insecure XMLHttpRequest endpoint 'http://...'
```

**Cause:** The backend generates `http://` URLs because it doesn't know it's
behind a TLS-terminating proxy.

**Fix:** Add `X-Forwarded-Proto` middleware:

```yaml
- "traefik.http.middlewares.${COMPOSE_PROJECT_NAME}-proto.headers.customrequestheaders.X-Forwarded-Proto=https"
- "traefik.http.middlewares.${COMPOSE_PROJECT_NAME}-proto.headers.customrequestheaders.X-Forwarded-Host=${APP_TRAEFIK_HOST}"
```

**Why it happens:** Traefik terminates TLS and forwards plain HTTP to the
container on port 80. Without `X-Forwarded-Proto: https`, the backend thinks
the client connected via HTTP and generates HTTP URLs.

---

## Layer 7: Iframe Embedding

### X-Frame-Options blocking iframes

**Symptom:** Blank white iframe, browser console:

```text
Refused to display 'https://...' in a frame because it set 'X-Frame-Options' to 'deny'
```

**Cause:** All `sec-*` security middleware levels include `frameDeny: true`.

**Fix:** Don't use `sec-*` for iframe-embedded services. Create a custom
Docker-level middleware with `frame-ancestors` CSP instead of `frameDeny`.
See OnlyOffice in `core/onlyoffice/docker-compose.yml` for the pattern.

---

## Quick Command Reference

### Container Inspection

```bash
# Status of all containers for an app
docker compose ps

# Full logs (follow)
docker compose logs -f

# Resource usage
docker stats --no-stream | grep <app>

# Find original ENTRYPOINT and CMD of an image
docker inspect --format='{{json .Config.Entrypoint}} {{json .Config.Cmd}}' <image>

# Shell into a running container
docker exec -it <container> /bin/sh    # Alpine
docker exec -it <container> /bin/bash  # Debian/Ubuntu
```

### Traefik Inspection

```bash
# Access log (shows client IPs, status codes, router names)
docker exec <traefik-container> cat /var/log/traefik/access.log | grep <app> | tail -10

# Traefik's own log (config errors, middleware failures)
docker exec <traefik-container> cat /var/log/traefik/traefik.log | tail -20

# Check dynamic config files
ls /path/to/secure-docker-blueprint/core/traefik/config/dynamic/

# Validate compose config (catches missing env vars)
docker compose config

# Same, but redacted — docker compose config resolves and PRINTS every
# ${VAR}, including secrets like CF_DNS_API_TOKEN. Redact before pasting
# output anywhere (issue, chat, support request):
docker compose config | sed -E 's/(CF_DNS_API_TOKEN: ).*/\1***REDACTED***/'
```

### Secret Debugging

```bash
# Check if a secret file has trailing newline
xxd secrets/db_pwd.txt | tail -1
# If last bytes are "0a" → newline present

# Strip newlines from all secrets
cd secrets && for f in *.txt; do printf '%s' "$(cat "$f")" > "$f"; done && cd ..

# Verify a secret is mounted inside the container
docker exec <container> cat /run/secrets/<SECRET_NAME>
```

### Network Debugging

```bash
# Which networks is this container in?
docker inspect <container> --format='{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}'

# What IP does a container have?
docker inspect <container> --format='{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}'

# List all containers in a network
docker network inspect <network> --format='{{range .Containers}}{{.Name}} {{end}}'
```

---

## Debugging Flowchart

```text
Browser shows error
│
├─ "Connection refused" / "Site can't be reached"
│  └─ Is the container running? → docker compose ps
│     ├─ No → Check logs: docker compose logs
│     └─ Yes → Is it in proxy-public network? → docker inspect
│        └─ Is the Traefik router listed? → Check dashboard
│
├─ "403 Forbidden"
│  └─ Check Traefik access log → ClientHost field
│     ├─ Public IP (not Tailscale) → DNS routes over internet, not VPN
│     ├─ Tailscale IP but still 403 → Check acc-tailscale IP ranges
│     └─ OriginStatus: 0 → Middleware blocking before reaching app
│        └─ Check middleware chain for broken @file/@docker references
│
├─ "502 Bad Gateway"
│  └─ Container running but Traefik can't reach it
│     ├─ Wrong port in loadbalancer.server.port?
│     ├─ App still starting? (check start_period)
│     └─ Wrong Docker network? (traefik.docker.network label)
│
├─ "404 Not Found"
│  └─ Router Host() rule doesn't match domain
│     └─ Check APP_TRAEFIK_HOST in .env
│
├─ Blank iframe / "Refused to display in frame"
│  └─ X-Frame-Options: DENY from sec-* middleware
│     └─ Use custom Docker middleware with frame-ancestors CSP
│
├─ "Download failed" / "Mixed Content"
│  └─ Backend generates http:// URLs
│     └─ Add X-Forwarded-Proto=https middleware
│
└─ "Password authentication failed"
   └─ Trailing newline in secret file
      └─ Strip with: printf '%s' "$(cat secret.txt)" > secret.txt
         Then recreate DB volume
```
