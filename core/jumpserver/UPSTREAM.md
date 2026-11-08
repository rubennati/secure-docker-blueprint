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
- **Edition gating:** the Community edition carries LDAP, CAS, OIDC, SAML2, OAuth2 and RADIUS authentication, role and organisation management, asset session monitoring, session command auditing, file-transfer tracking, login audit logs and command filtering. Enterprise adds LDAP high availability, chat-platform integrations, passkey support, cloud asset synchronisation and RemoteApp or VirtualApp delivery — https://www.jumpserver.com/docs/compare-versions · checked 2026-09-21
- **Commercial model:** paid self-hosted edition — https://www.jumpserver.com/docs/compare-versions · checked 2026-09-21
- **Decision facts checked:** 2026-09-21
- **Origin:** China · FIT2CLOUD · non-EU
- **Domain:** Identity, access and secrets
- **Role:** Privileged access management: stored target credentials, session recording, approval workflows
- **Verification snapshot:** 2026-09-19 — clean start only (see below), not a full
  operational verification

## What we use

- `jumpserver/jms_all:v5.1.1` — the vendor's own all-in-one image,
  bundling core (Django), koko (SSH gateway, and from v5 also the graphical
  sessions through its bundled guacd), chen (database web client), kael (AI
  services), lina/luna (web UI), PostgreSQL, Redis and nginx under one
  `supervisord` process tree

## Why this is one container, not a decomposed stack like every other in this repository

Verified directly, not assumed. Component-level images exist on Docker
Hub (`jumpserver/core`, `jumpserver/koko` and others, tagged `-ce`),
suggesting a granular deployment is *possible* — but no official,
first-party `docker-compose.yml` wiring core, koko, Postgres and Redis
together was found for that split. Building one ourselves without a
verified reference would be exactly the "invented configuration" this
repository's standards forbid. `jms_all` is the vendor's own documented,
supported, single-image path, built from those same component images at the
same version.

## What we changed vs. upstream

| Change | Reason |
|--------|--------|
| No `no-new-privileges`, `cap_drop`, or `read_only` | Verified to break the container — see the Security block in `docker-compose.yml` for exactly what fails and why |
| SSH gateway (koko) published directly, not through Traefik | Raw SSH; only the web console is HTTP(S) |
| `access-vpn` + `limit-standard` + `headers-standard`, `tls-strict` named on the console router | A traditional PAM platform holding every credential and recording is not public-default material |
| Resources set to the vendor's stated minimum (4 CPU / 8 GB), not a derived starting value | Upstream states this as a floor for the whole bundle, not a per-service guess |
| No Docker Secrets for `SECRET_KEY` / `BOOTSTRAP_TOKEN` | Verified: no `_FILE`-suffixed alternative exists in the vendor's documented interface |
| Named volume `pgdata` on `/var/lib/postgresql`, beside the `./volumes/` bind mounts | The bundled PostgreSQL cluster lives there, outside the declared `/opt/data` volume; upstream's own run command mounts it the same way. A named volume because Docker seeds it with the cluster the image ships, which the entrypoint only starts and never creates |

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

- **All-in-one, not the component split.** The `-ce` component images
  exist; this deployment uses the `jms_all` image because it is the one path
  with a documented, vendor-supported compose-equivalent shape. Revisit once
  JumpServer publishes an official compose reference for the split, or once
  this repository's own operators have verified one by hand. Upstream notes
  the all-in-one image supports the web (B/S) interface only, not the
  desktop-client features.
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

## Version notes

- Moved to `v5.1.1` on 2026-11-05 (released 2026-10-20), across v5.0.0 and
  v5.1.0, not run on a host at this tag. The scan of 2026-11-05 found 22
  CRITICAL pairs in `v4.10.19`; that is the newest `jms_all` image of the v4
  line — JumpServer released v4.10.20 on 2026-10-23, but no `jms_all` image
  of it exists on Docker Hub — so the pin leaves the v4 line. The v5 image
  stays GPL-3.0 Community Edition and needs no license; the installer's
  minimum upgrade source is v3.10.11, so v4.10.19 upgrades directly.
  Changes in the all-in-one image: Lion is removed and Koko serves graphical
  sessions under `/koko/lion/` with its bundled guacd (now bound to
  `127.0.0.1`); graphical recordings and files left in `/opt/data/lion` are
  not migrated — handle pending ones before the upgrade. Kael, the new AI
  service under `/kael/`, runs under Supervisor and keeps its data in
  `/opt/data/kael`; it does nothing until a model service is configured in
  Core. Kael's signing key for delegated Core API requests is derived from
  `BOOTSTRAP_TOKEN` unless `CHAT_AI_DELEGATION_SECRET` (at least 32
  characters) is set, so `BOOTSTRAP_TOKEN`, like `SECRET_KEY`, must never
  change. Ports 80 and 2222, `/api/health/`, the declared volumes and the
  required environment are unchanged; the database schema migrates on start
  (`jms upgrade_db`).
  Beyond the tag: the bundled PostgreSQL cluster lives in
  `/var/lib/postgresql`, not under `/opt/data` as this stack had assumed, so
  until now it sat in the container layer and was lost on every recreate,
  this tag change included. Upstream's run command mounts it; it is now the
  named volume `pgdata` (`pgdata-local` locally). A v4 deployment started
  without it keeps its database only inside the old container: take a
  logical dump (`pg_dump` inside the container) before recreating, and
  restore it into the new cluster before first login. Both images build on
  Debian trixie, so the cluster's PostgreSQL major should not change; not
  checked inside the images. Advisories: GHSA-6rp5-ff2m-qfrm (access-key
  exposure, high) is fixed from v4.10.19 already; GHSA-vr35-wj7g-3mr2
  (dynamic lookup filtering, medium) lists no patched release.
  Sources: https://github.com/jumpserver/jumpserver/releases/tag/v5.0.0,
  https://github.com/jumpserver/jumpserver/releases/tag/v5.1.0,
  https://github.com/jumpserver/jumpserver/releases/tag/v5.1.1,
  https://github.com/jumpserver/Dockerfile/tree/v5.1.1/allinone,
  https://github.com/jumpserver/installer/blob/v5.1.1/scripts/7_upgrade.sh,
  https://github.com/jumpserver/jumpserver/security/advisories
