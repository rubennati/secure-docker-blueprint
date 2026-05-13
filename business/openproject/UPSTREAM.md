# OpenProject — Upstream

**Last verified: 2026-05-06 (v17.3.1)**

## Source

- **Repository:** https://github.com/opf/openproject
- **Docker Compose repo:** https://github.com/opf/openproject-docker-compose
- **Docker Hub:** https://hub.docker.com/r/openproject/openproject
- **Docs:** https://www.openproject.org/docs/installation-and-operations/installation/docker-compose/

## License

GPL-3.0 (Community Edition) — self-hosting permitted. Commercial features are in the Enterprise/BIM editions (separate paid images).

CE vs EE notable differences: LDAP/SSO, baselines, and advanced budgeting are EE-only.

## Release notes

https://www.openproject.org/blog/openproject-release-notes/
https://github.com/opf/openproject/releases

## Upgrade checklist

1. Read the release notes — OpenProject occasionally requires manual migration steps between minor versions
2. Check if PostgreSQL version needs upgrading (OpenProject recommends PG 17 for new installs; PG 13 is still supported but will be dropped)
3. Bump `APP_TAG` in `.env` to the new `X.Y.Z-slim` tag
4. `docker compose pull`
5. `docker compose up -d` — seeder runs automatically and applies migrations
6. Monitor seeder logs: `docker compose logs -f seeder`
7. Verify the UI and core functions after upgrade
8. Update `Last verified` date and version in this file
