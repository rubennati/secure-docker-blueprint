# Upstream Reference

- **Last verified:** 2026-11-08 (3.2.0) — over IPv4: the site served and its job queue running before and after `down`/`up`, the refused client answered `403`; the administrator's login was not driven (docs/labs/stack-refresh/2026-11-08-results.md)

## Source

- **Image:** https://github.com/requarks/wiki/pkgs/container/wiki
- **GitHub:** https://github.com/requarks/wiki
- **Docs:** https://docs.requarks.io/
- **License:** AGPL-3.0
- **Decision facts checked:** 2026-09-23
- **Use restrictions:** none — https://github.com/requarks/wiki/blob/main/LICENSE · checked 2026-09-23
- **Origin:** Canada · Requarks · non-EU
- **Domain:** Files, wiki and collaboration
- **Role:** Wiki with Markdown and visual editors, per-page permissions and about twenty authentication modules

## Which version line, and why it matters

3.x is a rewrite of backend and frontend, stable since `3.0.1` (2026-11-01).
The 2.x line, published from https://github.com/requarks/wiki-v2 since
`2.5.316`, has no release after `2.5.317` (2026-10-23), so the CRITICAL image
findings at that pin have no fix on 2.x. This stack moved to 3.x; see
"Version notes" for what that changed.

- **PostgreSQL only** — 17 or 18, with the `ltree` and `pg_trgm` extensions,
  which Wiki.js creates itself at its first start. The stack was on
  PostgreSQL from the start for this reason.
- **No in-place upgrade.** 3.x refuses to start on a database that holds 2.x
  tables in its schema; content moves through an export package from 2.x and
  an import into a fresh 3.x instance.

## What we use

- `ghcr.io/requarks/wiki:3.6.0` — upstream's own registry. Debian-based
  `node:26` with tini as init, uid 1000 (`node`), about 850 MB because it
  carries a headless Chrome for optional server-side rendering.
- `postgres:18.7-alpine` for the database.
- Two containers. Pages, uploaded files, users and settings live in the
  database (schema `wiki`); the data volume holds caches and the optional Git
  content mirror.

## What we changed and why

| Change | Reason |
|--------|--------|
| `PGDATA: /var/lib/postgresql/data` on the database | PostgreSQL 18 keeps its cluster under `/var/lib/postgresql/<major>` and refuses to start when a volume sits on the old path. Measured here: without it the container restart-loops with "there appears to be PostgreSQL data in /var/lib/postgresql/data (unused mount/volume)". Same pattern as `apps/defectdojo` |
| `DB_PASS_FILE` instead of `DB_PASS` | Wiki.js reads the file itself and trims it, so no wrapper is needed and no password reaches `docker inspect` |
| `ADMIN_EMAIL` plus the `ADMIN_PWD` secret through `ops/entrypoint.sh` | 3.x has no setup wizard: the first start creates the root administrator from `ADMIN_EMAIL` and `ADMIN_PASS`, and without `ADMIN_PASS` uses the published default `12345678`. There is no `ADMIN_PASS_FILE`, so the wrapper reads the secret into `ADMIN_PASS` and refuses to start without it, then runs the image's own `tini -s -- node --no-experimental-webstorage backend` |
| No `SSL_ACTIVE`, `HA_ACTIVE`, `DB_TYPE` | Removed in 3.x — the image's `config.yml` reads none of them. TLS is off unless `config.yml` enables it, which suits Traefik terminating TLS |
| `read_only: true`, `cap_drop: ALL`, `tmpfs: /tmp` | Verified against 2.5.315; not yet re-run on 3.x, where the data path is still `/wiki/data`. Installing an extension from the administration area writes under `/wiki/backend` and fails on the read-only root; the Puppeteer extension is already in the image |
| No `user:` line | The image already runs as uid 1000 (`node`); `./volumes/data` has to belong to that uid |
| Healthcheck on `/_ready` | 3.x has no `/healthz`; the graceful-server readiness endpoint answers 200 without a session once start-up has finished, and `curl` is in the image. The image ships no healthcheck of its own |
| `APP_TRAEFIK_ACCESS=access-vpn` | Until the operator has signed in, set the site hostname and turned on the trusted proxy headers, nobody else should reach it |
| Database on `app-internal` (`internal: true`) | The baseline's network rule: a datastore has no route out and none in from other stacks |

## Verified on the image (2026-09-23)

Not a host verification: this ran the stack's own `docker-compose.local.yml`,
without Traefik and without TLS.

- Both containers healthy with `read_only`, `cap_drop: ALL`,
  `no-new-privileges`, the application as uid 1000.
- `DB_PASS_FILE` took effect — the application connected to PostgreSQL 18.6 and
  ran its migrations.
- The setup wizard completed over its own endpoint and created the
  administrator; the home page then answered 200.
- A login through the GraphQL API returned a session token.
- Idle memory right after setup: application 241 MiB, database 103 MiB.
- The setup bundle carries `telemetry: true`, so the checkbox in the wizard is
  ticked unless the operator unticks it.

What a host run still has to establish: the route behind Traefik with TLS, a
refused client outside the access policy, the first-load request count against
the rate limit, a restart, and the restore in the README.

## Upgrade checklist

1. Read the release notes — https://github.com/requarks/wiki/releases and the
   upgrade guide https://docs.js.wiki/setup/upgrade
2. Raise `APP_TAG` in `.env` and in `.env.local.example`
3. `docker compose pull && docker compose up -d`
4. `docker compose logs wikijs-app` — migrations first, then `HTTP Server: [ RUNNING ]`
5. Sign in, open a page, edit it, and check *Administration → System Info*
6. Record the result in `Last verified` once it ran behind Traefik

Within 3.x upstream's upgrade guide asks for a database backup first: a schema
upgraded by a newer version cannot be run by an older one.

## Diff against upstream

```bash
# Upstream's compose example: https://docs.js.wiki/setup/installation

# The configuration template the image ships, with its env placeholders
curl -s https://raw.githubusercontent.com/requarks/wiki/3.1.0/dev/build/config.yml

# The image build
curl -s https://raw.githubusercontent.com/requarks/wiki/3.1.0/dev/build/Dockerfile
```

## Version notes

- Moved to `3.6.0` on 2026-11-23 (released 2026-11-22), across `3.3.0`,
  `3.3.1`, `3.4.0` and `3.5.0`. Fixes the advisories that reach `3.2.0`:
  critical GHSA-jp85-8jq5-9gv6 (stored XSS in the map block's marker label
  lets any account that can edit a page become administrator, `3.4.0`); high
  GHSA-6m8p-37cv-c4f5 (asset writes past folder rules, `3.3.0`),
  GHSA-848h-794v-rmq9 (a feedback board created above protected pages
  bypasses their rules, `3.4.0`) and GHSA-h9p4-jmp2-c54v (stored XSS in the
  page history view, `3.6.0`); medium GHSA-pq85-v5r4-w5xj,
  GHSA-87m5-mch4-5f2q (page move and creation into denied branches, `3.3.0`),
  GHSA-x6q9-c4vx-rf3g (a symlink in a synced Git storage repository writes
  into `.git` and runs code, `3.3.1`; reaches only sites with Git storage),
  GHSA-5539-6c4x-464h, GHSA-35c7-6872-jrh6, GHSA-gv55-77xw-q5v3,
  GHSA-47c8-3859-4ccf and GHSA-74j8-43gw-p2pr (page-existence and source
  disclosure, asset and locale rule bypasses, `3.4.0`); low
  GHSA-74gh-jx9m-95qj (thumbnails served without the read check, `3.4.0`).
  The XSS and rule-bypass advisories need an account that can edit pages or
  assets; with `access-vpn` every route answers VPN clients only. No breaking change, no new variable;
  the image, its entrypoint, port 3000 and `/_ready` are unchanged, so the
  compose files keep their configuration. Twelve database migrations run on
  the first start (`20261114090330_cookie-consent` to
  `20261122082450_page-templates`); back up the database before. New in this
  range: group-level 2FA enforcement and page locks (`3.3.0`), a management
  CLI, maintenance mode and a plain OAuth2 strategy (`3.4.0`), Confluence,
  DokuWiki and XWiki importers (`3.5.0`), page templates (`3.6.0`) —
  https://github.com/requarks/wiki/releases,
  https://github.com/requarks/wiki/security/advisories.
- Moved to `3.2.0` on 2026-11-08. 3.1.1 and 3.2.0
  fix GHSA-p5rv-hmh3-wrv8, GHSA-7mf7-wprw-7fjm and GHSA-fxw3-8676-67fm; no
  configuration change.
- Moved to `2.5.317` on 2026-10-31: `2.5.316` (2026-10-02)
  adds the export utility for Wiki.js 3.x, `2.5.317` (2026-10-23) is a rebuild
  with Node security updates. No breaking change, migration or advisory.
- Moved to `3.1.0` on 2026-11-05 (released 2026-11-05), from `2.5.317` across
  `3.0.1` (2026-11-01, the first stable 3.x) and `3.0.2`. The image scan of 2026-11-05 found CRITICAL findings at `2.5.317`,
  and the 2.x line has no newer release.
  Breaking: a new application with its own schema and configuration. No
  in-place upgrade — 3.x exits when it finds 2.x tables in its schema. No setup
  wizard: the root administrator comes from `ADMIN_EMAIL`/`ADMIN_PASS` at the
  first start (handled here by `ops/entrypoint.sh` and the `ADMIN_PWD` secret).
  `DB_TYPE`, `SSL_ACTIVE` and `HA_ACTIVE` are gone; `LOG_LEVEL` knows `debug`,
  `info`, `warn`, `error` (no `verbose`); `/healthz` is gone (healthcheck now on
  `/_ready`); Node 26 in the image; PostgreSQL 17 or 18 only, with `ltree` and
  `pg_trgm`. `DB_PASS_FILE` was not read in the 3.0 betas and works again since
  `3.0.1`. The version check calls `api.github.com`; there is no telemetry
  setting any more. Behind a proxy, *Administration → Security → Trust
  X-Forwarded-\* Proxy Headers* has to be turned on.
  Migration, with the old pin still running:
  1. On `2.5.317`: *Administration → Utilities → Export for Wiki.js 3.x*, all
     boxes ticked, *Create Package*, download the `.wkbackup`.
  2. `docker compose down`; move `volumes/postgres` and `volumes/data` aside
     (they are the rollback, with `APP_TAG=2.5.317`); create them empty again,
     `volumes/data` owned by uid 1000.
  3. Create `.secrets/admin_pwd.txt`, set `ADMIN_EMAIL`, raise `APP_TAG`, then
     `docker compose up -d`.
  4. Sign in as `ADMIN_EMAIL`; *Administration → Utilities → Import from
     Wiki.js 2.x*, select the package, *Start Import*. Re-running skips
     existing items.
  5. Set again what the package does not carry: authentication, storage,
     comment and analytics modules, security settings, site logo and site
     hostname (`APP_TRAEFIK_HOST`). Pages using admonitions, diagram code
     blocks, Draw.io diagrams, inline KaTeX/MathJax, relative links or tabsets
     need manual edits.
  Advisories fixed in 3.x up to this tag: GHSA-f865-6hp9-6w47 (sessions not
  revoked on deactivation, `3.0.2`), GHSA-35r7-33j8-ghwg,
  GHSA-3c74-j8g3-p255, GHSA-m4c7-x7x7-3ppw, GHSA-jf48-pw92-vgrx (navigation
  link targets, client-side sanitising, `/_files` CSP and SVG scanning,
  unpublished pages exposed through tree and backlinks; all `3.1.0`).
  Sources: https://github.com/requarks/wiki/releases,
  https://docs.js.wiki/setup/upgrade, https://docs.js.wiki/setup/installation,
  https://docs.js.wiki/setup/requirements
