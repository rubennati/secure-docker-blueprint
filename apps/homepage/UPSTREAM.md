# Upstream Reference

## Source

- **Image:** https://github.com/gethomepage/homepage/pkgs/container/homepage
- **GitHub:** https://github.com/gethomepage/homepage
- **Docs:** https://gethomepage.dev/
- **License:** GPL-3.0
- **Decision facts checked:** not yet
- **Origin:** US · community (gethomepage) · non-EU
- **Domain:** Dashboards
- **Role:** Dashboard configured with YAML files
- **Last verified:** 2026-11-08 (2.7.0) — lab host (VM), IPv4 LAN: the dashboard behind the basicAuth gate (`401` without, `200` with the credentials) before and after `down`/`up`, the refused client answered `403` (docs/labs/stack-refresh/2026-11-08-results.md)

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
| Access `access-vpn`, `limit-standard` and `headers-standard` defaults | Personal dashboard pattern |
| Config files renamed to `*.example.yaml`, Setup step bootstraps actual files from examples | `.gitignore` excludes non-example YAMLs so user state never ends up in commits |

## Version / tag notes

- **`v1.13.2` → `v2.3.0` crosses a major.** v2.0.0 introduces homepage's own
  authentication as a breaking change; a 1.x configuration does not carry over unchanged.
  Read https://github.com/gethomepage/homepage/releases/tag/v2.0.0 before deploying.
- The bump also closes a medium advisory: the service proxy accepted client-controlled
  methods and bodies to configured targets, fixed in 2.2.0. Moved on 2026-09-13.
- Moved to `v2.7.0` on 2026-11-05, not run on a host at this tag. `v2.6.0` fixes
  GHSA-qxcr-4rv3-v23r (high): an authentication gate bypass via the Next.js
  on-demand revalidation header, relevant where homepage's own authentication is
  on. `v2.6.0` also keeps `$` sequences in environment and file secrets as
  written. `v2.7.0` moves the image to Node 24 and the Next.js middleware to
  `proxy`; host validation is unchanged, so `HOMEPAGE_ALLOWED_HOSTS` and the
  healthcheck against `127.0.0.1:3000` keep working. No variable or configuration
  change. https://github.com/gethomepage/homepage/releases

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
