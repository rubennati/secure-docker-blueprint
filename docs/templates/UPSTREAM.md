# Upstream Reference

## Source

- **Image:** https://hub.docker.com/r/VENDOR/IMAGE
- **GitHub:** https://github.com/VENDOR/REPO
- **Docs:** https://docs.example.com
- **License:** __REPLACE_ME__ (e.g. MIT, Apache 2.0, AGPL-3.0 — see license policy in ROADMAP.md)
- **Based on version:** `__REPLACE_ME__`
- **Last verified:** __REPLACE_ME__ (v__REPLACE_ME__)

## What we use

- Official image, pinned tag
- …

## Architecture

```
Internet → Traefik (TLS, port 443) → App :PORT
```

## What we changed and why

| Change | Reason |
|--------|--------|
| Docker Secrets | Blueprint standard — passwords never in plain environment variables |
| `app-internal: internal: true` | Database and backend services have no direct internet access |
| … | … |

## Upgrade checklist

1. Read the release notes for breaking changes: LINK
2. Check GitHub Security tab for advisories against the current version
3. Back up volumes and database before upgrading
4. Bump `APP_TAG` in `.env`
5. `docker compose pull && docker compose up -d`
6. Verify core function works

## Useful commands

```bash
# Shell into app
docker compose exec app sh

# Tail logs
docker compose logs app --follow
```
