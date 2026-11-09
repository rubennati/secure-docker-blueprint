# DFIR-IRIS

Collaborative incident-response case management: cases, IOCs, evidence,
timelines, notes and templates, shared across a response team.

Project, source, licence and origin: [`UPSTREAM.md`](UPSTREAM.md).

## What security problem this solves

A shared, structured place for incident data during and after a real
response — instead of a spreadsheet, a chat thread and a folder of loose
files each analyst keeps their own copy of. Cases, assets, IOCs and
evidence stay linked, timestamped and attributable to who added them.

## When this is useful

- More than one person works incidents and needs a shared, structured
  record rather than a shared document
- You want case templates, IOC/asset tracking and an audit trail that
  survives past the incident itself

## When this is not useful

- A single person handling occasional, informal incidents with no need for
  structured case data or a second reviewer
- As a substitute for the actual forensic tooling that produces the
  evidence in the first place — see [Velociraptor](../velociraptor/) for
  endpoint collection; IRIS is where the findings get organized, not where
  they get collected

## What this does not replace

Not a SIEM, not a ticketing system for routine IT work, and not a forensic
collection tool itself — it manages the case record, not the raw telemetry
or artifacts a collection tool like Velociraptor produces (though it can
hold references to and copies of that evidence as case attachments).

## Security model — read this before deploying

**This holds real incident data, IOCs, evidence attachments and
potentially personal data (names, systems, timelines involving specific
people) once in use.** Treat it accordingly:

- **Access**: `access-vpn` by default (this `.env.example`) — a case
  management tool holding active-incident detail has no reason to be
  publicly reachable.
- **No non-root user in the upstream image** (verified: no dedicated
  service account exists in `/etc/passwd` beyond root, and the entrypoint
  never drops privilege) — a documented deviation from this repository's
  usual baseline, the same class already carried for JumpServer's vendor
  image. `cap_drop: ALL` still applies and restricts what root itself can
  do.
- **No `read_only`** on `app`/`worker` (documented, not silently dropped)
  — the app writes case attachments, generated reports and templates
  under its own install tree beyond the three named volumes, and this has
  not been narrowly verified enough to isolate without risking a silent
  write failure on an untested code path. See UPSTREAM.md.
- **Backups contain everything sensitive this stack holds** — see Backup.
  Encrypt the backup archive itself; this stack does not do that for you.
- **MFA**: available per-user in IRIS's own settings (TOTP), not enforced
  centrally by this stack.
- **SSO**: OIDC and LDAP both exist in the Community edition — see
  Authentication below. Neither is Enterprise-gated.

## Architecture — nginx replaced by Traefik

Upstream ships `nginx` in front of `app`. This stack does not include it —
verified by reading nginx's actual templated config (`nginx.conf`, not the
unused placeholder `conf.d/default.conf` the base image also ships)
directly from a live container: its job is TLS termination, security
headers, and a plain reverse proxy to `app:8000`, including the
`/socket.io` WebSocket path. None of that is IRIS-specific — Traefik
already does all of it, and has passed WebSocket upgrades through natively
since v1.29.

**What was not carried over 1:1, and why that's acceptable:**

- nginx's security headers (CSP, `X-Frame-Options: DENY`, HSTS, strict
  cache-control) are replaced by this stack's `APP_TRAEFIK_SECURITY` chain
  rather than reproduced label-for-label. nginx's own CSP allowlisted
  `analytics.dfir-iris.org` for an optional upstream analytics beacon; this
  stack's headers do not carry that allowance forward, so any such call
  fails closed here — a narrower default than upstream's own, not a gap.
- nginx gave two upload paths (`/manage/cases/upload_files`,
  `/datastore/file/add*`) a 10-minute timeout and unbuffered request
  bodies, for large evidence-file uploads. This stack has not yet verified
  whether Traefik's own default timeouts are generous enough for a
  comparably large upload — see UPSTREAM.md and README.md's Preview →
  Ready gate. If large evidence uploads time out in practice, this is the
  first place to look.

**What was not changed:** app, worker, db and rabbitmq are all present,
unmodified in function — no upstream component was dropped to make this
stack look smaller.

## Authentication

Local accounts are the default. IRIS's Community edition also supports
LDAP and OIDC natively (confirmed against upstream's own `.env.model` —
neither is gated to a paid tier). Wiring either to Authentik or Keycloak
(`core/authentik/`, `core/keycloak/`) needs a handful of additional
`OIDC_*` variables added to `dfir-iris-app`'s `environment:` block — not
included by default here, a deliberate follow-on.

## Setup

```bash
cp .env.example .env
# Edit: APP_TRAEFIK_HOST

mkdir -p .secrets volumes/postgres volumes/rabbitmq volumes/downloads volumes/templates volumes/server_data
openssl rand -hex 32 > .secrets/db_pwd.txt
openssl rand -hex 32 > .secrets/db_admin_pwd.txt
openssl rand -base64 48 | tr -d '\n' > .secrets/iris_secret_key.txt
openssl rand -base64 32 | tr -d '\n' > .secrets/iris_security_password_salt.txt

docker compose up -d
docker compose logs -f dfir-iris-app   # watch for "IRIS IS READY" and the generated admin password
```

The initial administrator password is printed **once**, in the `app`
container's logs on first start — capture it immediately, the same way
this repository already handles a first-run generated credential
elsewhere (e.g. Hemmelig's provisioner password).

## Backup

**Everything below is one coherent set — a partial restore produces a
database that references evidence files that don't exist, or files with
no case record pointing at them.**

| | |
|---|---|
| **Database** | PostgreSQL · container `${COMPOSE_PROJECT_NAME}-db` · database `iris_db`. Every case, IOC, note, user account and much of the audit trail lives here |
| **Passwords** | `.secrets/db_pwd.txt`, `.secrets/db_admin_pwd.txt` |
| **Signing key / salt** | `.secrets/iris_secret_key.txt`, `.secrets/iris_security_password_salt.txt` — session signing and password hashing. Rotating either invalidates active sessions; check IRIS's own behavior before rotating the salt specifically, since it can affect how existing password hashes validate |
| **Evidence & attachments** | `./volumes/downloads`, `./volumes/server_data` — case attachments, generated reports, uploaded evidence files referenced by the database |
| **Templates** | `./volumes/templates` — custom case/report templates |
| **Message queue** | `./volumes/rabbitmq` — in-flight task state only, safe to lose; nothing here is a permanent record |

```yaml
postgresql_databases:
    - name: iris_db
      username: postgres
      # The server's own client, inside its container (FA-03)
      pg_dump_command: docker exec dfir-iris-db pg_dump
      pg_restore_command: docker exec -i dfir-iris-db pg_restore
      psql_command: docker exec -i dfir-iris-db psql
files:
    - path: /srv/docker/apps/dfir-iris/.secrets
    - path: /srv/docker/apps/dfir-iris/volumes/downloads
    - path: /srv/docker/apps/dfir-iris/volumes/server_data
    - path: /srv/docker/apps/dfir-iris/volumes/templates
```

**Retention:** this stack does not set a retention/deletion policy — case
data persists until an operator removes it. Decide your own retention
rule for closed cases before this holds real data; IRIS does not decide
that for you.

**Restore order:** database, evidence/attachment volumes and templates
together, then start the stack. RabbitMQ's volume can be restored last or
skipped entirely — it holds no data worth keeping past a restart.

## Try it locally

```bash
cp .env.local.example .env.local   # fill DB_PASSWORD, DB_ADMIN_PASSWORD, IRIS_SECRET_KEY, IRIS_SECURITY_PASSWORD_SALT
mkdir -p volumes/local/{postgres,rabbitmq,downloads,templates,server_data}
docker compose -f docker-compose.local.yml --env-file .env.local up -d
# http://localhost:8080
docker compose -f docker-compose.local.yml --env-file .env.local down
```

## Verify on first deploy (Preview → Ready gate)

- [x] `docker compose config` clean; `docker compose up -d` — all four services running, three with healthchecks passing — **verified locally, 2026-09-19**
- [x] Real Docker Secrets picked up by db, app and worker; database migrations, module registration and post-init all completed; the generated admin password was printed once as expected — **verified locally, 2026-09-19**
- [x] The app served the real login page (not an error page) through its own port — **verified locally, 2026-09-19**
- [ ] A large evidence-file upload through Traefik, to confirm the timeout behavior nginx specially handled — see Architecture above
- [ ] OIDC or LDAP sign-in against Authentik or Keycloak
- [ ] A real case created, an IOC added, and a restore rehearsal from a backup
- [ ] TLS and the router's four middleware positions (`APP_TRAEFIK_ACCESS`, `APP_TRAEFIK_LIMIT`, `APP_TRAEFIK_HEADERS`, `APP_TRAEFIK_AUTH`) confirmed against the real domain

## Open findings

<!-- findings:start — generated by scripts/ci/lifecycle-report.py from upstream-status.json; edit the text around it -->

**Findings in the upstream images** at the pin `v2.4.29` — the newest upstream release. Scanned 2026-11-08; counted are findings with a published fix, as CRITICAL · HIGH. They come with the images as upstream publishes them.

| Image | Base system | Libraries | Programs |
|---|---|---|---|
| `ghcr.io/dfir-iris/iriswebapp_app:v2.4.29` | 15 · 762 | 7 · 69 | — |
| `ghcr.io/dfir-iris/iriswebapp_db:v2.4.29` | 2 · 25 | — | 4 · 56 |
| `rabbitmq:3.13.7-management-alpine` | 1 · 34 | — | — |

<!-- findings:end -->

The IRIS application image, `iriswebapp_app:v2.4.29`, carries 22 CRITICAL findings that have published fixes: Debian 13 packages (glib, brotli, GnuTLS, Perl, libunbound, kernel headers) and Python packages (Pillow 11.3.0, PyJWT 2.4.0, certifi). The database image, `iriswebapp_db:v2.4.29`, carries 6 more in an old Alpine base and an old `gosu` build (OpenSSL, libxml2, Go). v2.4.29 is the newest IRIS release, and upstream has not rebuilt it.

**Risk:** Pillow may be reached through uploaded files, so restrict uploads to trusted analysts and keep IRIS off the public internet. The database findings are 32-bit-only OpenSSL, schema validation PostgreSQL does not do by default, and Go code gosu does not use. Move with the next release.

The RabbitMQ image carries one CRITICAL OpenSSL finding, CVE-2026-31789. The application has not documented support for RabbitMQ 4, the only line that is still rebuilt, so the broker stays on the last 3.x release.

**Risk:** the flaw affects only 32-bit platforms. Keep the broker on the internal network.

## Details

- [UPSTREAM.md](UPSTREAM.md) — source, upgrade checklist, deviations
