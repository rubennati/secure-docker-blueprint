# Whoami

Tiny HTTP debug service from Traefik Labs. Echoes the full HTTP request back to the client — headers, client IP, TLS info, routing path.

Used to verify that Traefik routing, TLS termination, and middleware chains work as expected. Not a production service — deploy temporarily, test, then disable.

## What it shows

A response like:

```
Hostname: 18e4b3f5d92a
IP: 172.20.0.3
RemoteAddr: 172.20.0.2:47028
GET / HTTP/1.1
Host: whoami.example.com
User-Agent: curl/8.0.1
X-Forwarded-For: 192.0.2.1
X-Forwarded-Proto: https
X-Real-Ip: 192.0.2.1
```

This lets you confirm:

- The router matched the expected hostname
- Traefik is setting `X-Forwarded-*` headers
- Middlewares are seeing the correct client IP (important when CrowdSec or IP allowlists are active)
- TLS terminated correctly at Traefik (no request reached the backend over plain HTTP)

## Setup

```bash
# 1. Create .env
cp .env.example .env
# Edit: APP_TRAEFIK_HOST

# 2. Start
docker compose up -d

# 3. Test
curl https://<APP_TRAEFIK_HOST>
```

Default access policy is `acc-tailscale` + `sec-5` (strictest, because Whoami is static and CSP-compatible).

## Common tests

```bash
# Is the router reachable at all?
curl -v https://whoami.example.com

# Are forwarded headers correct?
curl https://whoami.example.com | grep -i forwarded

# Is the certresolver serving the expected cert?
openssl s_client -servername whoami.example.com -connect whoami.example.com:443 < /dev/null | grep -i subject

# Does the security level chain what you expect?
curl -sI https://whoami.example.com | grep -iE "strict-transport|content-security|x-frame"
```

## Security Model

Whoami runs with the full hardening set:

- `read_only: true` with `tmpfs /tmp`
- `cap_drop: ALL` (no capabilities at all)
- `no-new-privileges: true`
- No network access beyond `proxy-public`
- No database, no secrets, no persistent state

Ideal candidate for `sec-5` (maximum chain including CSP enforce) because it serves only a static text response.

## When to disable

Whoami is a diagnostic tool. After the Traefik setup is validated:

```bash
# Stop and remove
docker compose down

# Or comment out the service in this repo if you may need it again later
```

Keeping a public `whoami` endpoint running long-term leaks information useful to attackers (internal network IDs, header names, TLS termination details).

## Details

- [UPSTREAM.md](UPSTREAM.md) — source, upgrade checklist
