# OpenProject — Upstream

**Last verified: 2026-05-06 (v17.3.1)**

## Source

- **Repository:** https://github.com/opf/openproject
- **Docker Compose repo:** https://github.com/opf/openproject-docker-compose
- **Docker Hub:** https://hub.docker.com/r/openproject/openproject
- **Docs:** https://www.openproject.org/docs/installation-and-operations/installation/docker-compose/
- **License:** GPL-3.0 (Community Edition; Enterprise features are separately licensed)
- **Edition gating:** single sign-on through SAML, OpenID Connect, CAS or Kerberos is an Enterprise feature from the Professional plan upwards, and LDAP group synchronisation from the Corporate plan; two-factor authentication, plain LDAP authentication, user groups and permissions, and custom workflows are in the Community edition — https://www.openproject.org/pricing/ · checked 2026-09-21
- **Commercial model:** paid self-hosted edition — https://www.openproject.org/pricing/ · checked 2026-09-21
- **Decision facts checked:** 2026-09-21
- **Origin:** Germany · OpenProject GmbH · EU
- **Domain:** Business operations
- **Role:** Project management with work packages, boards and Gantt planning
- **Based on version:** `17.9.6-slim`

## License

GPL-3.0 (Community Edition) — self-hosting permitted. Commercial features are in the Enterprise/BIM editions (separate paid images).

CE vs EE notable differences: LDAP/SSO, baselines, and advanced budgeting are EE-only.

## Release notes

https://www.openproject.org/blog/openproject-release-notes/
https://github.com/opf/openproject/releases

## Version notes

- Moved to `17.9.6-slim` on 2026-11-05 (released 2026-10-30), not run on a host
  at this tag. No breaking change listed for 17.8.1 to 17.9.6; the seeder applies
  the migrations. 17.9.0 converts the length settings of number custom fields
  into minimum and maximum values and asks administrators to check them
  afterwards. 17.9.2 fixes fresh 17.9 installations creating projects without a
  work package type and the Docker image falling back to migrations instead of
  loading the structure — do not stop below 17.9.2. New optional setting
  `OPENPROJECT_FOG__DIRECT__UPLOAD__EXPIRES__IN`, only for S3 direct uploads (not
  used here). Advisories fixed: GHSA-4p83-c4wg-59q4, GHSA-c5j2-2mfg-49h7,
  GHSA-r374-cr8p-hmp9 (17.8.1), GHSA-998q-c58p-qf78 (17.9.3),
  GHSA-2qr3-mhmh-xfwj (17.9.5). GHSA-rg3v-wmh9-hhq6 is fixed only in 18.0.0.
- Moved `postgres` from `17-alpine` to `18-alpine` on 2026-11-05, not run on a
  host at this tag. PostgreSQL 18 support: "officially supports PostgreSQL
  version 16 or above" since 16.0.0
  (https://www.openproject.org/docs/installation-and-operations/system-requirements/);
  upstream's packaged installs still ship 17. The 18 image keeps its cluster
  under `/var/lib/postgresql/18/docker`; `PGDATA: /var/lib/postgresql/data` in
  both compose files keeps it on the existing mount. A new major does not read
  the old cluster, so existing data moves by dump and restore: before the tag
  changes, `docker compose exec db sh -c 'pg_dumpall -U "$POSTGRES_USER"' >
  dump.sql`; `docker compose down`; remove the `db_data` volume once the dump is
  checked; set the new tag; `docker compose up -d db`; `docker compose exec -T
  db sh -c 'psql -U "$POSTGRES_USER" -d postgres' < dump.sql` (errors that the
  bootstrap role and database already exist are expected); then `docker compose
  up -d`. A return to the old major is only a restore of that dump.

## Upgrade checklist

1. Read the release notes — OpenProject occasionally requires manual migration steps between minor versions
2. Check if PostgreSQL version needs upgrading (OpenProject recommends PG 17 for new installs; PG 13 is still supported but will be dropped)
3. Bump `APP_TAG` in `.env` to the new `X.Y.Z-slim` tag
4. `docker compose pull`
5. `docker compose up -d` — seeder runs automatically and applies migrations
6. Monitor seeder logs: `docker compose logs -f seeder`
7. Verify the UI and core functions after upgrade
8. Update `Last verified` date and version in this file
