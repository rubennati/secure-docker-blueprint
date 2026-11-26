# OpenProject — Upstream

- **Last verified:** 2026-11-08 (17.9.6) — over IPv4, a new installation with Postgres 18.6, memcached with cap_drop: the seeder ran the migrations and the demo data, the health checks passed, a work package created through the API v3 found again after `down`/`up`, the refused client answered `403`; a restore through `docker exec` (docs/labs/stack-refresh/2026-11-08-results.md)

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

## License

GPL-3.0 (Community Edition) — self-hosting permitted. Commercial features are in the Enterprise/BIM editions (separate paid images).

CE vs EE notable differences: LDAP/SSO, baselines, and advanced budgeting are EE-only.

## Release notes

https://www.openproject.org/blog/openproject-release-notes/
https://github.com/opf/openproject/releases

## Version notes

- Moved to `17.9.6-slim` on 2026-11-05 (released 2026-10-30). No breaking change listed for 17.8.1 to 17.9.6; the seeder applies
  the migrations. 17.9.0 converts the length settings of number custom fields
  into minimum and maximum values and asks administrators to check them
  afterwards. 17.9.2 fixes fresh 17.9 installations creating projects without a
  work package type and the Docker image falling back to migrations instead of
  loading the structure — do not stop below 17.9.2. New optional setting
  `OPENPROJECT_FOG__DIRECT__UPLOAD__EXPIRES__IN`, only for S3 direct uploads (not
  used here). Advisories fixed: GHSA-4p83-c4wg-59q4, GHSA-c5j2-2mfg-49h7,
  GHSA-r374-cr8p-hmp9 (17.8.1), GHSA-998q-c58p-qf78 (17.9.3),
  GHSA-2qr3-mhmh-xfwj (17.9.5). GHSA-rg3v-wmh9-hhq6 is fixed only in 18.0.0.
- Moved to `17.9.8-slim` (2026-11-19) on 2026-11-23. Advisories fixed in 17.9.7:
  GHSA-9c69-v342-vqr7 (critical, any user who can view a project could call
  zero-argument methods on it through the in-place edit endpoint, deleting it and its
  subprojects; anonymous users on public instances), GHSA-rhcj-h663-7v7w (critical,
  the same through the date picker's `focused_field` on any visible work package),
  GHSA-pggp-67cq-xgrg (high, the same through attribute macros in exports and emails),
  GHSA-q9gv-q2h3-7g3x (medium, second-factor bypass through authentication stages kept
  in the session), GHSA-773c-7fc3-342g (medium, open redirect on `/external_redirect`
  without a session), GHSA-pv79-v2hf-5gg8 (medium, anonymous password-change endpoint
  without a per-account limit), GHSA-vpg6-crgp-fc2h, GHSA-xpmj-x5hg-hq6j,
  GHSA-vjqq-p9g9-42wx (medium, relations, project phases and user names visible
  without permission), GHSA-g75c-9rjg-8cvj (medium, push with read-only access through
  the Apache Git integration, not used here), GHSA-jwhj-v5mg-3f4f (low). Fixed in
  17.9.8: GHSA-hg98-84jc-26px, GHSA-27qw-695p-p8gg, GHSA-gp67-gx74-36wg,
  GHSA-xvh8-793v-rp59, GHSA-m6gr-38w2-w34w (medium; the last only with virus scanning
  and external object storage, neither configured here), GHSA-hrw9-6pqq-mmrq (low,
  SSRF through Subversion and Git repository URLs, which are now checked against the
  SSRF protection when set), GHSA-cm9j-c5pc-q325, GHSA-m4jc-3j97-vrxv (low, shared
  caches showing restricted values). The rest reach every instance whose users log
  in; behind `access-vpn` the anonymous ones reach only clients inside the VPN. No
  breaking change, no new setting; the seeder applies the migrations. Still open:
  GHSA-rg3v-wmh9-hhq6 (low, fixed only in 18.0.0, not released) and
  GHSA-x252-j3fp-j593 (critical, notification emails rendered with the author's
  permissions; no patched version, confirmed on the development branch only).
  Sources: https://github.com/opf/openproject/releases/tag/v17.9.7,
  https://github.com/opf/openproject/releases/tag/v17.9.8,
  https://github.com/opf/openproject/security/advisories
- Moved `postgres` from `17-alpine` to `18.6-alpine` on 2026-11-05. PostgreSQL 18 support: "officially supports PostgreSQL
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
