# Upstream Reference

## Source

- **Image:** https://hub.docker.com/r/privatebin/nginx-fpm-alpine
- **GitHub:** https://github.com/PrivateBin/PrivateBin
- **Docker build repo:** https://github.com/PrivateBin/docker-nginx-fpm-alpine
- **Docs:** https://github.com/PrivateBin/PrivateBin/wiki
- **License:** zlib (core application, by Sébastien Sauvage / PrivateBin
  contributors). Bundled front-end assets carry their own separate licenses
  (MIT, BSD-3-Clause, Apache-2.0, GPL-2.0 for one vendored library, CC-BY-4.0
  for icons) — all permissive, none affecting self-hosted use.
- **Origin:** Community project, no single company, maintained collectively on GitHub · no single jurisdiction
- **Domain:** Identity, access and secrets
- **Role:** Zero-knowledge paste service for text and secrets
- **Based on version:** `2.0.6`
- **Verification snapshot:** 2026-09-19 — local Compose stack booted and
  exercised (see README.md's Preview → Ready gate); not yet run behind a
  real Traefik host

## What we use

- `privatebin/nginx-fpm-alpine:2.0.6` — single container, nginx + php-fpm,
  filesystem storage backend (the upstream default; database and S3/GCS
  backends exist but are not used here — nothing about this deployment
  needs them)

## What we changed vs. upstream

| Change | Reason |
|--------|--------|
| `read_only: true` + `cap_drop: ALL` with **no** `cap_add` | Verified against a live container — the image already runs as fixed UID/GID `65534:82` with no root-start entrypoint |
| `tmpfs: /tmp:exec` and `/run:exec,mode=1777` (explicit exec permission) | Verified against a live container, and the actual root cause behind it — see below. Not documented anywhere in the upstream image's own README |
| No Docker Secrets section | Verified: PrivateBin has no admin account and no server-side encryption key of its own with the filesystem backend |

## The tmpfs exec finding, in detail

The image is s6-overlay based. Its entrypoint (`/etc/init.d/rc.local`) runs
`cp -r /etc/s6/services /run` before starting `s6-svscan /run/services` —
service-supervision scripts are copied into `/run` fresh on every container
start, rather than living permanently on the image's own filesystem.

Mounting `/run` as a plain `tmpfs` (Docker's default, no explicit mount
options) let the copy succeed with correct ownership and executable
permission bits — `ls -la` inside the container showed `-rwxr-xr-x` on the
copied `run` scripts — but `s6-supervise` still failed with `unable to spawn
./run (waiting 60 seconds): Permission denied`. The container reported
"Up" and never crashed, but nginx and php-fpm never actually started, and
`GET /` timed out. Traced to the tmpfs mount itself carrying an implicit
`noexec` flag in this environment; adding `exec` explicitly
(`tmpfs: /run:exec,mode=1777`) fixed it immediately, confirmed by nginx and
php-fpm both logging their normal startup messages and a real `GET /`
returning 200 milliseconds later.

The container reports "Up" in `docker ps` output until the healthcheck's own
`start_period` elapses, and the copied scripts' permissions are correctly
`rwxr-xr-x` throughout — neither symptom points at the mount option as the
cause.

## What was actually verified, and how

- `docker inspect privatebin/nginx-fpm-alpine:2.0.6` — confirmed
  `User: "65534:82"` and entrypoint `/etc/init.d/rc.local`; read that file
  directly to find the `cp -r /etc/s6/services /run` step.
- Ran with `--cap-drop ALL --read-only --tmpfs /tmp --tmpfs /run` (default,
  no exec option): container stayed "Up" but `s6-supervise` logged
  `Permission denied` for both services and `GET /` never answered.
- Re-ran with `--tmpfs /tmp:exec --tmpfs /run:exec,mode=1777`: started
  cleanly, both services logged normal startup, `GET /` returned 200.
- Confirmed the identical result through the actual `docker-compose.yml` —
  not just the equivalent `docker run` flags.
- **Not verified:** an actual paste created and decrypted through the web
  UI, burn-after-read behavior, TLS/Traefik behind a real domain, and the
  database or S3/GCS storage backend options.

## Upgrade checklist

1. Watch [PrivateBin releases](https://github.com/PrivateBin/PrivateBin/releases)
2. Read the changelog for storage-format or configuration changes
3. Back up `./volumes/data` before upgrading — see README.md#backup
4. Bump `APP_TAG` in `.env`
5. `docker compose pull && docker compose up -d`
6. Confirm the healthcheck passes and a test paste round-trips

## Known limitations

- **Not yet run behind a real Traefik host or TLS.**
- **The data-directory ownership requirement (`65534:82`) has only been
  confirmed on a local Docker Desktop volume**, not on a production host's
  filesystem — permissions handling can differ (e.g. on a filesystem
  without POSIX ownership semantics, or across a bind mount from a
  different host).
- **Filesystem backend only** — no database or S3/GCS backend configured.
