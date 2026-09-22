# Upstream Reference

## Source

- **Image:** https://hub.docker.com/r/rclone/rclone
- **GitHub:** https://github.com/rclone/rclone-web (interface), https://github.com/rclone/rclone
- **Docs:** https://rclone.org/gui/
- **License:** MIT
- **Origin:** UK · Nick Craig-Wood (rclone) · non-EU
- **Decision facts checked:** 2026-09-21
- **Domain:** Backup
- **Role:** Browser interface for rclone: storage remotes, copy and sync jobs, serves and transfer statistics
- **Based on version:** `1.75.1`

No `Last verified` line: behind Traefik, the interface can be signed into only with
the password inside its URL — see
[Known limitation](#known-limitation-the-interfaces-sign-in).

The origin is the rclone project's author and copyright holder, located in
Guildford, UK. rclone and Rclone Web are both MIT.

## What we use

- `rclone/rclone:1.75.1` — the official image. `rclone gui` serves the Rclone Web
  release embedded at build time (1.1.11 in this tag) and needs no download at
  runtime. Upstream's README runs `rclone/rclone:latest`.
- Interface on port 5522, remote control API on port 5533, as upstream's example.

## What we changed and why

| Change | Reason |
|--------|--------|
| API under `/api/` on the same host (`--rc-baseurl=/api`) | Upstream exposes two ports for the browser to reach. The interface joins the RC URL and the method path as strings, so a base path works — read from the interface's code — and one host name serves both |
| Login through `--rc-htpasswd` | Upstream passes `--user` and `--pass` on the command line, where `docker inspect` shows them. Set through `RCLONE_RC_PASS` instead, the password appeared in `rclone gui`'s start log — measured. With a htpasswd file, rclone never holds the password |
| APR1 hash | rclone refused the correct password against a SHA-512 crypt (`$6$`) hash — measured |
| `user: 1000:1000`, `read_only`, `cap_drop: ALL` | The image runs as root; rclone works unprivileged when its directories belong to the uid |
| No published ports | Traefik reaches both over `proxy-public` |
| No FUSE | Mounts need `/dev/fuse` and `CAP_SYS_ADMIN` |
| `APP_TRAEFIK_ACCESS=acc-tailscale` | The API reads and changes every remote, credentials included |

## Known limitation: the interface's sign-in

Rclone Web 1.75.1 (`src/pages/Login.tsx`) takes the API address only from the
query string of `/login`, together with `user` and `pass`, and removes the three
from the address bar before it signs in. When the sign-in fails, the address is
reset to what the browser had stored — nothing, on a first visit — so `?url=`
alone ends at "URL is not configured" with Connect disabled. Only a link carrying
the password works, and that link reaches the proxy's access log and the browser
history. The API itself is unaffected. The way out — a field for the address, or
keeping it after a failed attempt — is a change upstream.

## Verification performed (2026-09-22)

Behind Traefik with TLS, with the shipped `acc-tailscale` and `sec-2`:

- A client outside the access policy's ranges got `403` on `/` and on
  `/api/core/version`, over IPv4 and IPv6
- The interface at `/` and the API under `/api/` on the same host name: the API
  `401` without credentials and with a wrong password, `200` with the htpasswd
  login; `/api` without the trailing slash reached the interface's server instead
  (`405` to a `POST`), which the interface never calls
- Through the API: an `alias` remote on `/data` created and listed, a directory
  made, a file uploaded (`operations/uploadfile`), an asynchronous `sync/copy`
  job finished with `success: true`, and the copy listed
- The interface: the login page loaded in 4 requests; `?url=` alone left Connect
  disabled. With `url`, `user` and `pass` handed to the page in the browser
  without a request carrying them, it signed in: the dashboard showed the remote
  and the transferred bytes, the remotes page listed it. The page polls
  `job/status` for jobs rclone has already expired and gets `500`
  ("job not found"); it requested `raw.githubusercontent.com` for the changelog
  and a sponsor list. The login, password included, was in local storage
- The start log showed no login link in this run
- Remote and copied file unchanged after `docker compose down` and `up`
- Backup as the README describes; restore of `volumes/config` into place with the
  ownership restored — the remote back
- Peak 22 MiB (limit 1 GiB)

**Not yet exercised:** a remote at a real storage provider; transfers of size;
serves.

## Verification performed (2026-09-21)

Against the production `docker-compose.yml` (Docker Secret, read-only, uid 1000) on
a throwaway `proxy-public` network without Traefik, with `volumes/config` and
`volumes/data` as Docker volumes owned by uid 1000:

- The container came up healthy; the interface answered 200 at `/` and `/login`
- The API under `/api/` answered 401 without credentials and with a wrong
  password, and 200 with the htpasswd login. The login link in the start log
  carried generated credentials, which were refused
- Through the API: a remote created, listed, a directory created on it and
  listed; `rclone.conf` written with mode 600 by uid 1000
- After `docker compose down` and `up`, the remote was still configured
- Hardening from `docker inspect`: `read_only`, uid 1000 for every process,
  `cap_drop: ALL`, no capability added, no published port; the password in
  neither the command nor the environment
- `docker-compose.local.yml` started read-only as uid 1000; the interface
  answered, the API took the htpasswd login and refused a wrong one, and a
  preflight from `http://localhost:5522` was answered with that origin and the
  `Authorization` header allowed

**Not yet exercised:** Traefik routing and TLS; the interface in a browser; a
remote at a real storage provider; transfers of size; serves; backup and restore.

## Upgrade checklist

1. Read the release notes: https://github.com/rclone/rclone/releases — the
   interface follows the rclone release that embeds it
2. Back up `volumes/config` and `.secrets/`
3. Bump `APP_TAG` in `.env.example`
4. `docker compose pull && docker compose up -d`
5. Log in and list the remotes
6. Update **Based on version** above — and add **Last verified** only if the
   upgrade was exercised on a real install
