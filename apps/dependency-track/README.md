# Dependency-Track

Software Composition Analysis (SCA): tracks every software component across
every project in a portfolio over time, ingests SBOMs, and correlates them
against vulnerability and license data as that data changes — not just at
the moment a scan runs.

## What this is not: a container/image scanner

**Trivy** (already used elsewhere in this repository's CI) inspects a
concrete image, filesystem or repository at a point in time and reports
what it finds right now. **Dependency-Track** manages the *inventory* —
components, their SBOMs, their known vulnerabilities and their licenses —
persistently, across every project, and re-evaluates it as new
vulnerability data arrives days, weeks or months after the SBOM was
uploaded. A Trivy scan produces a report; Dependency-Track produces a
history. Neither replaces the other — this repository's own CI keeps using
Trivy for image scanning, and this stack does not change that.

## When this is useful

- You produce or consume software with a real supply chain — your own
  builds, or third-party images/packages — and want to know when a
  component already in use turns out to be vulnerable, not only at build
  time
- CI/CD pipelines that generate CycloneDX SBOMs and want a place to send
  them that keeps history and correlates across projects

## When this is not useful

- A one-off "is this image safe to pull" check — that is what Trivy is for,
  directly against the image, no portfolio to manage
- A single project with no ongoing component-tracking need

## What is sensitive here

- The component/vulnerability database itself — not typically secret, but
  it maps directly to what software your infrastructure runs, which is
  useful reconnaissance for an attacker
- Integration API tokens (Jira, Snyk, OSS Index, etc.), if configured —
  Dependency-Track's own internal secret store, encrypted at rest by the
  KEK below
- **The secret-management KEK** (key encryption key) — see Backup. Losing
  or rotating it outside Dependency-Track's own rotation procedure makes
  every internally-stored secret permanently unreadable

## Architecture

```text
                    ┌─────────────┐
Browser  ─────────→ │  frontend   │  static SPA, no server-side API proxy
   │                 └─────────────┘
   │ (browser calls the API directly — separate origin, CORS-scoped)
   ▼
┌─────────────┐      ┌──────────┐
│  apiserver  │ ───→ │    db    │  PostgreSQL — the only supported database in v5
└─────────────┘      └──────────┘
```

v5 dropped the v4 "bundled" image — `apiserver` and `frontend` are separate
containers, confirmed against upstream's own container-images reference.
The frontend is a static single-page app: it does not proxy API calls
server-side, so the browser calls the API server's own origin directly.
That is why this stack runs two separate Traefik routers on two separate
subdomains rather than one.

## Setup

```bash
cp .env.example .env
# Edit: APP_TRAEFIK_HOST (frontend), APP_TRAEFIK_HOST_API (API server)

mkdir -p .secrets volumes/postgres volumes/data
openssl rand -hex 32 > .secrets/db_pwd.txt
openssl rand -base64 32 | tr -d '\n' > .secrets/dt_kek.txt

docker compose up -d
docker compose logs -f dependency-track-apiserver   # watch migrations complete
```

Visit `https://<APP_TRAEFIK_HOST>` and sign in (default managed-user
credentials are for evaluation only — see Authentication below).

## Authentication: OIDC via Authentik or Keycloak

Local managed users are documented upstream as an evaluation-only path.
Dependency-Track's own OIDC configuration works against any standard OIDC
provider, including both Authentik and Keycloak already in this repository
(`core/authentik/`, `core/keycloak/`) — not configured by default here, a
deliberate follow-on requiring a registered OIDC application at whichever
provider you use. LDAP/Active Directory is a separate, documented path if
that fits better. Nothing in Dependency-Track's Community distribution
gates OIDC or LDAP behind a paid tier — both are confirmed free.

## Backup

| | |
|---|---|
| **Database** | PostgreSQL · container `${COMPOSE_PROJECT_NAME}-db` · database `dtrack` · user `dtrack`. This is where every component, vulnerability finding and secret (encrypted) lives |
| **Password** | `.secrets/db_pwd.txt` |
| **KEK (key encryption key)** | `.secrets/dt_kek.txt` — **back this up separately from the database, with the same discipline as an encryption key, not as ordinary config.** Every internally-stored secret (integration API tokens) is encrypted under it. A database restored without the matching KEK has those secrets present but permanently unreadable; a KEK restored without the matching database decrypts nothing, because nothing to decrypt exists. Restoring only one half recovers neither |
| **State** | `./volumes/postgres` (database) — the entire portfolio: projects, components, SBOMs, findings, policies, encrypted secrets |
| **Artifact storage** | `./volumes/data` — locally-stored SBOM/artifact files (the `local` file-storage provider). A single-instance deployment; a multi-instance one would need this shared |

```yaml
postgresql_databases:
    - name: dtrack
      container: dependency-track-db
      username: dtrack
      password: "{credential file /srv/docker/apps/dependency-track/.secrets/db_pwd.txt}"
files:
    - path: /srv/docker/apps/dependency-track/.secrets/dt_kek.txt
    - path: /srv/docker/apps/dependency-track/volumes/data
```

**Restore order:** database, KEK and artifact storage together as one unit.
Restoring the database alone from an older backup than the KEK (or vice
versa) produces a running instance whose stored integration secrets cannot
be decrypted — not a crash, a silent, permanent loss of those specific
values only, discovered the next time an integration tries to use one.

## Local testing (no Traefik)

```bash
cp .env.local.example .env.local   # fill DB_PASSWORD, DT_KEK
mkdir -p volumes/local/postgres volumes/local/data
docker compose -f docker-compose.local.yml --env-file .env.local up -d
# http://localhost:8080 — frontend; API at http://localhost:8081
docker compose -f docker-compose.local.yml --env-file .env.local down
```

## Verify on first deploy (Preview → Ready gate)

- [x] `docker compose config` clean; `docker compose up -d` — all three healthy — **verified locally, 2026-09-19**
- [x] Real Docker Secrets picked up via Dependency-Track's own `${file::...}` syntax; database migrations and seeding completed; `GET /api/version` returned 200 — **verified locally, 2026-09-19**
- [x] Frontend served the SPA with `API_BASE_URL` correctly baked into `static/config.json` — **verified locally, 2026-09-19**
- [ ] A real BOM upload and vulnerability-analysis pass through the actual UI
- [ ] OIDC sign-in against Authentik or Keycloak
- [ ] TLS and the chosen `APP_TRAEFIK_SECURITY` chain confirmed against the real domain, on both subdomains

## Details

- [UPSTREAM.md](UPSTREAM.md) — source, upgrade checklist, deviations
