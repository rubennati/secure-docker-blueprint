# Upstream Reference

## Source

- **Image:** https://github.com/CorentinTh/it-tools/pkgs/container/it-tools
- **GitHub:** https://github.com/CorentinTh/it-tools
- **Live demo:** https://it-tools.tech/
- **License:** GNU GPL v3.0
- **Decision facts checked:** not yet
- **Origin:** France · CorentinTh · EU
- **Domain:** Developer tools
- **Role:** Collection of small utilities: converters, generators and formatters
- **Based on version:** `2024.10.22-7ca5933` (upstream uses date + commit hash, not semver)
- **Last verified:** 2026-11-02 (v2024.10.22-7ca5933) — step 8 lab host behind Traefik 3.7.17: healthy, the tool list's page and its JavaScript and CSS assets through the route; moved from the shared network to its edge network and back (docs/labs/ingress/2026-11-01-results.md)

## What we use

- Official `ghcr.io/corentinth/it-tools` image
- Fully static SPA served by the included Nginx
- No customisation — upstream defaults work out of the box

## What we changed and why

| Change | Reason |
|--------|--------|
| Traefik labels instead of port mapping | Inbox source used `ports: "8007:80"`; blueprint uses Traefik for all HTTP routing |
| `read_only: true` + `tmpfs` for Nginx runtime dirs | Defence in depth — the static SPA doesn't need a writable filesystem at all |
| `security_opt: no-new-privileges` | Blueprint baseline |
| Access policy defaults to `access-vpn` | Personal toolbox pattern; flip to public only when you want to share |
| `limit-standard` and `headers-standard` | The standard counter and headers fit a static SPA |
| Pinned image tag instead of `:latest` | Reproducible; inbox used `:latest` |

## Upgrade checklist

Upstream uses calendar-versioned tags (`YYYY.M.D-<hash>`) rather than semver, so "upgrading" means picking a newer commit-tagged build.

1. Check [upstream releases](https://github.com/CorentinTh/it-tools/releases) for the latest tag
2. Bump `APP_TAG` in `.env`
3. `docker compose pull && docker compose up -d`
4. Visit the UI; upstream occasionally removes/renames tools — check if a tool you rely on still exists

No data migration ever — the container holds no user state.

## Related images

None. IT-Tools is a self-contained static build.

## Useful commands

```bash
# Container shell (for diagnosing Nginx issues)
docker compose exec app sh

# Nginx access logs
docker compose logs app --follow

# Check image version baked in
docker compose exec app sh -c 'cat /usr/share/nginx/html/index.html | grep -oE "it-tools-[0-9.]+"'
```
