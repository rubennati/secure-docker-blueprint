# Upstream Reference

## Source

- **Image:** https://hub.docker.com/r/lissy93/dashy
- **GitHub:** https://github.com/Lissy93/dashy
- **Docs:** https://dashy.to/docs
- **Live demo:** https://demo.dashy.to/
- **License:** MIT
- **Decision facts checked:** not yet
- **Origin:** UK · Alicia Sykes (Lissy93) · non-EU
- **Domain:** Dashboards
- **Role:** One page linking everything you run, configured in a single YAML file
- **Based on version:** `4.9.15`
- **Last verified:** 2026-05-02 (v4.0.4)

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
| Access default `access-vpn`, `limit-standard` and `headers-standard` | Personal dashboard pattern |

## Upgrade checklist

1. Check [GitHub releases](https://github.com/Lissy93/dashy/releases) for breaking config changes
2. Bump `APP_TAG`
3. `docker compose pull && docker compose up -d`
4. Watch logs for build errors — bad config syntax will prevent startup

## Version notes

- Moved `lissy93/dashy` to `4.9.15` on 2026-11-05 (pushed 2026-11-02), not run on
  a host at this tag. Upstream publishes a GitHub release only for each minor
  (4.9.0, 2026-10-23); the patch tags 4.8.8 to 4.9.15 are version bumps on `master`.
  Security fixes in the range: config files were readable without login through
  encoded URLs (4.9.0, #2387); auth headers were sent to lookalike origins (4.9.12,
  #2426); header-auth users are now checked against `conf.yml` on the server
  (4.9.15, #2430), so a header-auth user not listed in `conf.yml` is refused. The
  image no longer sets `HOST=0.0.0.0`; Node listens on the unspecified address,
  which accepts IPv4 and IPv6 (4.9.1). Port 8080 and `/app/services/healthcheck.js`
  are unchanged, so the compose files keep their configuration. Other changes: a
  new workspace view, an icon-only colour option, theme and custom-CSS fixes on
  sub-pages, OIDC re-login keeps the requested page. No migration steps. Sources:
  https://github.com/Lissy93/dashy/releases/tag/4.9.0,
  https://github.com/Lissy93/dashy/compare/4.8.7...4.9.15

## Useful commands

```bash
docker compose logs app --follow
# Validate config before restart
docker compose exec app node /app/services/config-validator.js /app/user-data/conf.yml
```
