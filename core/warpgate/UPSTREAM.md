# Upstream Reference

## Source

- **Upstream GitHub:** https://github.com/warp-tech/warpgate
- **Image registry:** `ghcr.io/warp-tech/warpgate` (GHCR)
- **Docs:** https://warpgate.null.page/
- **Self-host compose reference:** `docker/docker-compose.yml` in the upstream repo
- **License:** Apache-2.0
- **Decision facts checked:** not yet
- **Origin:** Germany · Eugen Pankov Softwareentwicklung · EU
- **Domain:** Identity, access and secrets
- **Role:** Lightweight access proxy for SSH, HTTPS, databases, Kubernetes, RDP and VNC
- **Based on version:** `0.29.0`
- **Verification snapshot:** 2026-09-19 — hardening only (see below), not a full clean-install run

## What we use

- `ghcr.io/warp-tech/warpgate:0.29.0`, single container, no separate database
- The image's own embedded SQLite for users, sessions and the audit log
- The image's own `warpgate healthcheck` subcommand

## What we changed vs. upstream compose

| Change | Reason |
|--------|--------|
| `unattended-setup` instead of the interactive `setup` wizard | Non-interactive, scriptable, and takes the admin password as an env var consumed once — no plaintext password ever lands in a file this repository writes |
| `cap_drop: ALL` + `read_only: true` + `tmpfs: /tmp` | Verified directly against a live container (see below) |
| SSH and MySQL ports published directly, not through Traefik | Raw TCP protocols; only the admin UI is HTTP(S) — see README.md#network-exposure |
| `acc-tailscale` + `sec-3` + `tls-modern` default on the admin UI | An admin console that can create SSO/local users and reach every configured target is not public-default material |
| No Docker Secrets section | Verified: the image has no `_FILE`-style secret input at all — the admin password is consumed once by `unattended-setup`, not by the long-running service |

## What was actually verified, and how

Run directly against `ghcr.io/warp-tech/warpgate:0.29.0` before writing this
stack, not assumed from the README:

- `docker inspect` — confirmed `User: "warpgate"` (UID 1000, fixed, not an
  init-system image), the image's own `Healthcheck` (`warpgate healthcheck`),
  and Debian bookworm base with `bash`/`wget`/`cat` present, no `curl`.
- `unattended-setup --data-path /data --http-port 8888 --ssh-port 2222 ...`
  with `WARPGATE_ADMIN_PASSWORD` set, under `--cap-drop=ALL
  --security-opt=no-new-privileges:true --read-only --tmpfs /tmp` — failed
  with `Permission denied` until `./volumes/data` was `chown 1000:1000`,
  then completed fully: config, CA, SSH host/client keys, TLS certificate,
  admin user all generated with zero capabilities re-added.
- `run` against the generated config, same hardening flags — started
  cleanly, bound both listeners, and `warpgate healthcheck` exited 0 against
  the running container.
- **Not verified:** an actual SSH or HTTPS session through the proxy to a
  real target, the admin UI behind Traefik with
  `http.trust_x_forwarded_headers: true`, and anything beyond a single
  clean start — no restart, no upgrade, no host reboot.

## Upgrade checklist

1. Watch [Warpgate releases](https://github.com/warp-tech/warpgate/releases)
2. Read the changelog — a schema migration runs automatically on next start,
   but a config format change would not
3. Back up `./volumes/data` before upgrading — it holds the entire database
   and every key/certificate
4. Bump `APP_TAG` in `.env`
5. `docker compose pull && docker compose up -d`
6. Confirm with `docker compose logs -f` and `warpgate healthcheck`

## Known limitations

- **No CE/EE split** — Warpgate is a single Apache-2.0 project, the simplest
  licensing situation of the five PAM/bastion candidates evaluated alongside
  this one.
- **Session recording exists but its storage/retention behaviour has not
  been exercised here** — `unattended-setup --record-sessions` enables it;
  what recordings contain and where they live is in README.md's security
  section.
- **Reverse-proxy interaction with Warpgate's own TLS is documented upstream
  (`http.trust_x_forwarded_headers`) but not exercised on a live host from
  this repository.**
