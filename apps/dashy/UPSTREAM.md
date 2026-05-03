# Upstream Reference

## Source

- **Image:** https://hub.docker.com/r/lissy93/dashy
- **GitHub:** https://github.com/Lissy93/dashy
- **Docs:** https://dashy.to/docs
- **Live demo:** https://demo.dashy.to/
- **License:** MIT
- **Based on version:** `4.0.4`
- **Last checked:** 2026-05-02

## What we use

- Official `lissy93/dashy` image
- Single config file mounted as `/app/user-data/conf.yml`

## What we changed and why

| Change | Reason |
|--------|--------|
| Traefik labels instead of port `:8003:8080` | Blueprint routes via Traefik |
| Pinned `APP_TAG` | Inbox used implicit `:latest` |
| `security_opt: no-new-privileges` | Blueprint baseline |
| `TZ` env var | Consistent with blueprint |
| `./config/conf.example.yml` preserved from inbox as starter | Gives new users a working starting point |
| Access default `acc-tailscale` + security `sec-3` | Personal dashboard pattern |

## Upgrade checklist

1. Check [GitHub releases](https://github.com/Lissy93/dashy/releases) for breaking config changes
2. Bump `APP_TAG`
3. `docker compose pull && docker compose up -d`
4. Watch logs for build errors — bad config syntax will prevent startup

## Useful commands

```bash
docker compose logs app --follow
# Validate config before restart
docker compose exec app node /app/services/config-validator.js /app/user-data/conf.yml
```
