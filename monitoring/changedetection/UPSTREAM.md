# Upstream Reference

## Source

- **Project:** https://changedetection.io
- **GitHub:** https://github.com/dgtlmoon/changedetection.io
- **Registry:** `ghcr.io/dgtlmoon/changedetection.io`
- **License:** Apache-2.0
- **Origin:** Australia · dgtlmoon · non-EU
- **Based on version:** `0.60.3`
- **Last verified:** 2026-09-08 (0.60.3) — v0.8.0 host session: clean start, password set in the UI, a watch on a page on the Docker network (after lifting the private-address guard), the ntfy notification through Apprise; a deliberate change on that page produced the notification on an iPhone within half a minute.

## What we use

- Official `ghcr.io/dgtlmoon/changedetection.io` image
- Built-in datastore (JSON files in `./volumes/data/`, mounted at `/datastore`)
- Optional browser/Playwright service for JavaScript-rendered pages (commented out by default)
- Traefik labels for HTTPS routing

## What we changed vs. upstream examples

| Change from upstream | Reason |
|---|---|
| **Traefik labels instead of `-p 5000:5000`** | Blueprint routing standard |
| **`security_opt: no-new-privileges:true`** | Baseline hardening |
| **`acc-tailscale` default access** | Change tracking targets may include internal services |
| **Browser service commented out** | Optional — only needed for JS-heavy sites; adds ~1 GB RAM |

## Browser / Playwright support

For sites that require JavaScript rendering (SPAs, dynamic content), uncomment the `browser` service in `docker-compose.yml`:

```yaml
browser:
  image: dgtlmoon/sockpuppetbrowser:latest
  # or use playwright:
  # image: mcr.microsoft.com/playwright:latest
```

Then set **"Request via browser steps"** in the watch settings for affected URLs.

## Upgrade checklist

1. Check [changedetection.io releases](https://github.com/dgtlmoon/changedetection.io/releases)
2. Back up:

   ```bash
   cp -r volumes/data/ changedetection-backup-$(date +%Y%m%d)/
   ```

3. Bump `APP_TAG` in `.env`
4. `docker compose pull && docker compose up -d`
5. Verify: existing watches are intact, notifications still fire

## Useful commands

```bash
# Shell into the container
docker compose exec app bash

# Export all watches as OPML (for backup/migration)
# Available in the UI: Settings → Export
```
