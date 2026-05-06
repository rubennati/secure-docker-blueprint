# Vikunja — Upstream

**Last verified: 2026-05-06 (v2.3.0)**

## Source

- **Repository:** https://github.com/go-vikunja/vikunja
- **Docker Hub:** https://hub.docker.com/r/vikunja/vikunja
- **Docs:** https://vikunja.io/docs/

## License

AGPL-3.0 — fully open source, self-hosting permitted without restrictions.

## Release notes

https://github.com/go-vikunja/vikunja/releases

## Upgrade checklist

1. Read the release notes for breaking changes or migration steps
2. Check if the database schema migration runs automatically (it does — Vikunja auto-migrates on startup)
3. Bump `APP_TAG` in `.env`
4. `docker compose pull && docker compose up -d`
5. Verify the UI loads and existing tasks are intact
6. Update `Last verified` date and version in this file
