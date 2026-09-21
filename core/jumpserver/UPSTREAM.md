# Upstream Reference

## Source

- **Upstream GitHub:** https://github.com/jumpserver/jumpserver
- **Image registry:** `jumpserver/jms_all` (Docker Hub)
- **Docs:** https://www.jumpserver.com/docs
- **Self-host reference:** vendor `quick_start.sh` installer, or the
  documented all-in-one image used directly here — no official multi-service
  compose file exists (see below)
- **License:** GPL-3.0 (Community Edition; Enterprise Edition is a separate
  closed-source product from the same vendor)
- **Decision facts checked:** not yet
- **Origin:** China · FIT2CLOUD · non-EU
- **Domain:** Identity, access and secrets
- **Role:** Privileged access management: stored target credentials, session recording, approval workflows
- **Based on version:** `v4.10.19`
- **Verification snapshot:** 2026-09-19 — clean start only (see below), not a full
  operational verification

## What we use

- `jumpserver/jms_all:v4.10.19` — the vendor's own all-in-one image,
  bundling core (Django), koko (SSH/RDP gateway), lina/luna (web UI),
  PostgreSQL, Redis and nginx under one `supervisord` process tree

## Why this is one container, not a decomposed stack like every other in this repository

Verified directly, not assumed. Two component-level images exist on Docker
Hub (`jumpserver/core`, currently at `v5.0.0-ce`; `jumpserver/jms_koko` and
others), suggesting a granular deployment is *possible* — but no official,
first-party `docker-compose.yml` wiring core, koko, Postgres and Redis
together was found for that newer split. Building one ourselves without a
verified reference would be exactly the "invented configuration" this
repository's standards forbid. `jms_all` is the vendor's own documented,
supported, single-image path, currently one major version behind the
component images (`v4.10.19` vs. `v5.0.0-ce`) — see "Known limitations".

## What we changed vs. upstream

| Change | Reason |
|--------|--------|
| No `no-new-privileges`, `cap_drop`, or `read_only` | Verified to break the container — see the Security block in `docker-compose.yml` for exactly what fails and why |
| SSH gateway (koko) published directly, not through Traefik | Raw SSH; only the web console is HTTP(S) |
| `acc-tailscale` + `sec-3` + `tls-modern` on the console | A traditional PAM platform holding every credential and recording is not public-default material |
| Resources set to the vendor's stated minimum (4 CPU / 8 GB), not a derived starting value | Upstream states this as a floor for the whole bundle, not a per-service guess |
| No Docker Secrets for `SECRET_KEY` / `BOOTSTRAP_TOKEN` | Verified: no `_FILE`-suffixed alternative exists in the vendor's documented interface |

## What was actually verified, and how

- `docker inspect` — confirmed the image's declared volumes (`/opt/data`,
  `/opt/download`, `/var/log/nginx`), that it ships `curl`, `wget` and
  `bash`, and that its entrypoint chain is `supervisord`-based (a
  `USERMAP_UID`/`PGID`-style image per `docs/standards/new-app-checklist.md`'s
  init-system table — do not add `user:`).
- Ran with `--cap-drop=ALL --security-opt=no-new-privileges:true`: failed —
  `sudo: setresuid(...): Operation not permitted`, then a cascade of
  permission errors (Redis config, Postgres data directory) and the bundled
  Postgres never starting, so core waited on a database connection
  indefinitely.
- Ran with default (unhardened) settings: started cleanly, applied its own
  database migrations, and answered `/api/health/` over HTTP once fully up —
  a 502 while the internal services were still starting, then a clean 200;
  a little over two minutes cold start in this environment.
- **Not verified:** a real SSH session through koko, login via the web
  console, OIDC/SAML/LDAP against Authentik or Keycloak, backup/restore, or
  behavior across a restart or upgrade.

## Upgrade checklist

1. Watch [JumpServer releases](https://github.com/jumpserver/jumpserver/releases)
2. Read the changelog — JumpServer documents required upgrade paths between
   non-adjacent minor versions; do not skip versions without checking
3. Back up `./volumes/data` before upgrading — it holds the bundled
   Postgres data directory as well as application state
4. Bump `APP_TAG` in `.env`
5. `docker compose pull && docker compose up -d`
6. Watch `docker compose logs -f` for migration completion before assuming
   the new version is ready

## Known limitations

- **One major version behind upstream's newest architecture.** `v5.0.0-ce`
  component images exist; this deployment uses the `v4.10.x` all-in-one
  line because it is the one path with a documented, vendor-supported
  compose-equivalent shape. Revisit once JumpServer publishes an official
  compose reference for the v5 split, or once this repository's own
  operators have verified one by hand.
- **No `_FILE` secret support** — `SECRET_KEY` and `BOOTSTRAP_TOKEN` sit in
  the process environment in plain form, mitigated only by keeping `.env`
  out of git and off shared filesystems.
- **Cannot run under this repository's normal container hardening** — see
  the Security block in `docker-compose.yml`. This is the single largest
  deviation from house baseline anywhere in the five PAM/bastion stacks
  evaluated together with this one.
- **Default admin credentials** — first login is `admin` / `ChangeMe`, per
  vendor documentation. Change it immediately; see README.md.
- **Not yet run on a live host beyond a clean start.**
