# Upstream Reference

## Source

- **Image:** https://github.com/gethomepage/homepage/pkgs/container/homepage
- **GitHub:** https://github.com/gethomepage/homepage
- **Docs:** https://gethomepage.dev/
- **License:** GPL-3.0
- **Based on version:** `v0.10.9`
- **Last checked:** 2026-04-17

## What we use

- Official `ghcr.io/gethomepage/homepage` image
- File-based YAML config in `./config/` (bind mount)
- Example configs copied from inbox source as `*.example.yaml`

## What we changed and why

| Change | Reason |
|--------|--------|
| Traefik labels instead of port `:8002:3000` | Blueprint routes via Traefik |
| Pinned `APP_TAG` | Inbox had `:latest` |
| `HOMEPAGE_ALLOWED_HOSTS` derived from `${APP_TRAEFIK_HOST}` | **Inbox source had a hardcoded RFC1918 IP address** pointing to the author's private lab. Rebased on the TLS hostname so this file is safe to share. |
| Docker socket mount commented out + socket-proxy pattern documented | Default socket mount gives read/write Docker access to a web-facing app — risk too high for default-on |
| `security_opt: no-new-privileges` | Blueprint baseline |
| Access `acc-tailscale` + security `sec-3` defaults | Personal dashboard pattern |
| Config files renamed to `*.example.yaml`, Setup step bootstraps actual files from examples | `.gitignore` excludes non-example YAMLs so user state never ends up in commits |

## Upgrade checklist

Homepage breaks config-schema changes occasionally (usually with a migration note).

1. [GitHub releases](https://github.com/gethomepage/homepage/releases) — read breaking changes
2. Back up `./config/`:
   ```bash
   tar czf homepage-config-$(date +%Y%m%d).tgz config/
   ```
3. Bump `APP_TAG`
4. `docker compose pull && docker compose up -d`
5. Watch logs — schema errors surface immediately

## Useful commands

```bash
# Validate config
docker compose exec app sh -c 'cat /app/config/settings.yaml | yq .'

# Trigger config reload (usually automatic, but just in case)
docker compose restart app
```
