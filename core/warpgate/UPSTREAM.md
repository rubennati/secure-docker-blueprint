# Upstream Reference

- **Last verified:** 2026-11-08 (0.30.4) — lab host (VM), IPv4 LAN, run in a parallel batch: after the servers-transport correction: the admin from the secret file logged in through the API (`201`, `401` for a wrong password) before and after `down`/`up`, the refused client answered `403` (docs/labs/stack-refresh/2026-11-08-results.md)

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
- **Verification snapshot:** 2026-09-19 — hardening only (see below), not a full clean-install run

## What we use

- `ghcr.io/warp-tech/warpgate:0.30.4`, single container, no separate database
- The image's own embedded SQLite for users, sessions and the audit log
- The image's own `warpgate healthcheck` subcommand

## What we changed vs. upstream compose

| Change | Reason |
|--------|--------|
| `unattended-setup` instead of the interactive `setup` wizard | Non-interactive, scriptable, and takes the admin password as an env var consumed once — no plaintext password ever lands in a file this repository writes |
| `cap_drop: ALL` + `read_only: true` + `tmpfs: /tmp` | Verified directly against a live container (see below) |
| SSH and MySQL ports published directly, not through Traefik | Raw TCP protocols; only the admin UI is HTTP(S) — see README.md#network-exposure |
| `access-vpn` + `limit-standard` + `headers-standard`, `tls-strict` named on the admin UI router | An admin console that can create SSO/local users and reach every configured target is not public-default material |
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

## Version notes

- Moved to `0.30.4` on 2026-11-05, not run on a host at this tag; the
  verification below was against `0.29.0`. Since 0.30.0 the runtime image is
  distroless (`gcr.io/distroless/cc`): no shell, no package manager, so the
  `bash`/`wget`/`cat` noted below are gone. The `warpgate` user (UID 1000),
  `/data`, the entrypoint `/usr/local/bin/warpgate` and the exec-form image
  healthcheck `warpgate healthcheck` stay, so this stack's healthcheck and the
  `run --rm … unattended-setup` setup need no shell. The session cookie is now
  always `Secure`, and `X-Forwarded-For`/`-Host`/`-Proto` use the last value.
  Schema migrations run on start. Advisories fixed: GHSA-qcwp-cwqv-g428,
  GHSA-fhwh-r27p-hvg5, GHSA-rm54-2mgh-59g9, GHSA-2cwg-f83j-xjgx,
  GHSA-g5wc-qprw-44ph (0.30.0); GHSA-hp22-gfvj-7m8r, GHSA-cj29-mv44-r3g2,
  GHSA-rccx-x2f2-qggp, GHSA-wv8f-pg5h-j86g, GHSA-9cmw-ff3v-ggc9,
  GHSA-2xj4-4766-4xwx, GHSA-jgwh-2q6f-w7g6, GHSA-4434-xwvf-cvq7 (0.30.1);
  GHSA-hhq8-x2xc-95qx, GHSA-fxfw-2m4j-xmc8, GHSA-r7rf-j762-2xxv (0.30.4).
  GHSA-r7rf-j762-2xxv advises an explicit TLS mode (enabled or disabled)
  instead of "Preferred" on MySQL and PostgreSQL targets.

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
