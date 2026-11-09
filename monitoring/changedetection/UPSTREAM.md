# Upstream Reference

## Source

- **Project:** https://changedetection.io
- **GitHub:** https://github.com/dgtlmoon/changedetection.io
- **Registry:** `ghcr.io/dgtlmoon/changedetection.io`
- **License:** Apache-2.0
- **Decision facts checked:** not yet
- **Origin:** Australia · dgtlmoon · non-EU
- **Domain:** Monitoring
- **Role:** Watches web pages for changes: restocks, prices, terms
- **Last verified:** 2026-11-08 (0.70.2) — over IPv4: moved from 0.70.1, a watch added through the API with the key from the datastore and checked, the two example watches the README names present, all three kept after `down`/`up`, the refused client answered `403` (docs/labs/stack-refresh/2026-11-08-results.md)

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
| **`access-vpn` default access** | Change tracking targets may include internal services |
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

## Version notes

- Moved to `0.70.2` on 2026-11-08. A patch release;
  no configuration change.
- Moved to `0.60.10` on 2026-10-31. Between `0.60.4` and `0.60.10` upstream labels no breaking change,
  migration or variable change. `0.60.9` moves Apprise from 1.13.1 to 2.0.1, a
  major release of the notification library — the ntfy notification verified on
  2026-09-13 is the thing to re-check — and `0.60.10` builds with uv. No advisory
  in the range; the three of `0.60.2` are behind the previous pin.
- Moved to `0.70.1` on 2026-11-05. There is no `0.70.0`. Upstream labels no breaking change,
  migration or variable change, and the Dockerfile is unchanged. New: an MCP
  server at `/mcp` with an OAuth 2.1 sign-in and consent form, and `GET
  /api/v1/changes`; both sit behind the router like the rest of the application,
  and whether they refuse a request without the application password is the thing
  a host run has to check. `llm_prefilter` is removed. No advisory in the range;
  the bump clears CRITICAL findings of the image scan.
  https://github.com/dgtlmoon/changedetection.io/releases/tag/0.70.1

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
