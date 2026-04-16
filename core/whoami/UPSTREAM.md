# Upstream Reference

## Source

- **Image:** https://hub.docker.com/r/traefik/whoami
- **GitHub:** https://github.com/traefik/whoami
- **Based on version:** `v1.11.0`
- **Last checked:** 2026-04-16

## What we use

- Official `traefik/whoami` image, pinned tag
- Default CMD (binds to `:80`, serves plain text response)
- No configuration files, no environment variables required

## What we changed and why

| Change | Reason |
|--------|--------|
| `read_only: true` + `tmpfs /tmp` | Whoami is a minimal Go binary — it doesn't write anywhere at runtime |
| `cap_drop: ALL` | No capabilities needed; extra defense in depth |
| `sec-5` chain | Static text response, fully CSP-compatible — good test target for the strictest middleware |
| No healthcheck | The image has no `curl` or `wget`. Writing a custom healthcheck for a debug service is over-engineering |

## Upgrade checklist

Whoami is simple and stable. Upgrade is low-risk:

1. Check new release: https://github.com/traefik/whoami/releases
2. Bump `APP_TAG` in `.env`
3. `docker compose pull && docker compose up -d`
4. `curl https://<domain>` — confirm response works

## Useful commands

```bash
# Verify service is reachable from inside the Docker network
docker run --rm --network proxy-public curlimages/curl \
  curl -s http://whoami:80

# Show what Whoami sees as its own environment
docker compose exec app /whoami --help
```
