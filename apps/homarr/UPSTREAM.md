# Upstream Reference

## Source

- **Image:** https://github.com/homarr-labs/homarr/pkgs/container/homarr
- **GitHub:** https://github.com/homarr-labs/homarr
- **Docs:** https://homarr.dev/
- **License:** MIT (fork heritage: originally forked from `ajnart/homarr`; current maintainer `homarr-labs`)
- **Based on version:** `1.39.0`
- **Last checked:** 2026-04-17

## What we use

- Official `ghcr.io/homarr-labs/homarr` image
- Built-in SQLite (no external DB)
- Bind-mount `./volumes/appdata/` for persistent state

## What we changed and why

| Change | Reason |
|--------|--------|
| Traefik labels instead of port `:8001:7575` | Blueprint routes via Traefik |
| Pinned `APP_TAG` | Inbox had `:latest` |
| `SECRET_ENCRYPTION_KEY` moved to `.env` variable (placeholder `__REPLACE_ME__`) | Inbox source had a hardcoded key value — that would have been a backdoor if copied verbatim. Every instance needs its own key. |
| Docker socket mount commented out | Direct `/var/run/docker.sock` mount gives Homarr full Docker control, a risk unreasonable for a dashboard. Socket-proxy pattern recommended; documented in README. |
| `security_opt: no-new-privileges` | Blueprint baseline |
| Access default `acc-tailscale` + security `sec-3` | Personal dashboard pattern |

## Upgrade checklist

1. Check [GitHub releases](https://github.com/homarr-labs/homarr/releases) — breaking changes and DB migration notes
2. Back up `./volumes/appdata/`:
   ```bash
   tar czf homarr-appdata-$(date +%Y%m%d).tgz volumes/appdata/
   ```
3. Bump `APP_TAG`
4. `docker compose pull && docker compose up -d`
5. Next.js migrations run on start; watch logs

### Rollback

Restore appdata tarball, revert `APP_TAG`.

## Useful commands

```bash
# Shell
docker compose exec app sh

# Regenerate SECRET_ENCRYPTION_KEY (destroys stored integration creds!)
openssl rand -hex 32
# Update .env, docker compose restart app
```
