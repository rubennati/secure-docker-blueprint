# Rclone Web

A browser interface for [rclone](https://rclone.org/): storage remotes, copy and
sync jobs, serves and transfer statistics. `rclone gui` serves the interface —
[Rclone Web](https://github.com/rclone/rclone-web), embedded in the rclone binary
at build time — and rclone's remote control API beside it.

## Architecture

```text
Internet → Traefik (TLS) → rclone-web :5522   interface, at /
                         → rclone-web :5533   remote control API, at /api/
```

One host name. The interface calls the API on the same origin.

## Setup

```bash
cp .env.example .env            # host name
ops/init.sh                     # the login, and the mounted paths
sudo chown -R 1000:1000 volumes/config volumes/data
docker compose up -d
```

The login is the user `admin` (or the name given to `ops/init.sh`) with the
password in `.secrets/gui_pwd.txt`, on the API under `https://<host name>/api`.

## Known limitation — the interface's sign-in

The interface in 1.75.1 has no field for the API address. It reads `url`, `user`
and `pass` from the link it is opened with (`/login?url=…&user=…&pass=…`), signs
in with them and keeps them in the browser's local storage. Given only `url`, it
drops the address again after its first attempt without credentials fails, and
the Connect button stays disabled. With the htpasswd login this stack uses, the
interface can therefore only be opened with the password inside a URL — which
lands in the reverse proxy's access log and in the browser history.

Until that changes upstream, use the API directly; `curl` asks for the password:

```bash
curl -u admin -X POST https://<host name>/api/core/version
curl -u admin -X POST -H 'Content-Type: application/json' \
  -d '{}' https://<host name>/api/config/listremotes
```

## What is mounted

| Path | Holds |
|---|---|
| `volumes/config` → `/config/rclone` | `rclone.conf`: every remote and its credentials |
| `volumes/data` → `/data` | Local files rclone may read and write |

To give rclone other host directories, mount them beside `/data`, owned by
`APP_UID`.

## Security notes

- **The API is the whole of rclone.** Whoever logs in can read and change every
  remote, including its credentials, and read, write and delete files on them.
  `.env.example` ships `APP_TRAEFIK_ACCESS=acc-tailscale`, the VPN only.
- **The login is a htpasswd file.** rclone checks the password against an APR1
  hash in the Docker Secret and never receives the password itself. rclone does
  not accept SHA-512 crypt (`$6$`) hashes.
- **The interface keeps the login in the browser.** Once signed in, it stores the
  API address, the user and the password in the browser's local storage.
- **The dashboard fetches from GitHub.** It requests rclone's changelog and a
  sponsor list from `raw.githubusercontent.com` in the visitor's browser.
- **`rclone.conf` is not encrypted.** rclone obscures the stored passwords,
  which is reversible, so the file and its backups carry the remotes' credentials.
- **Mounts are not available.** A FUSE mount needs `/dev/fuse` and
  `CAP_SYS_ADMIN`, which this stack does not grant.
- **Hardening.** `read_only`, `cap_drop: ALL`, `no-new-privileges`, uid 1000, no
  published port.

## Status

Run behind Traefik with TLS on 2026-09-22 (1.75.1): the API under `/api/` on the
same host name, a remote with an upload and a copy job, the interface, a restart,
and the restore below. The interface can be signed into only with the password in
its URL — see the limitation above. Full log in
[`UPSTREAM.md`](UPSTREAM.md#verification-performed-2026-09-22).

## Try it locally

```bash
cp .env.local.example .env.local
ops/init.sh
sudo chown -R 1000:1000 volumes/config volumes/data
docker compose -f docker-compose.local.yml --env-file .env.local up -d
# http://localhost:5522 — RC URL http://localhost:5533/api
docker compose -f docker-compose.local.yml --env-file .env.local down
```

Both ports bind to `127.0.0.1`; Traefik and the Docker Secrets mechanism are not
used. It mounts the same `volumes/`, so run one at a time.

## Backup

Back up `volumes/config` and `.secrets/`:

```bash
sudo tar -czf rclone-web.tar.gz volumes/config .secrets
```

`volumes/config/rclone.conf` holds the credentials of every remote. The files in
`volumes/data` belong to whatever you put there. Restore by unpacking the archive,
restoring the `1000:1000` ownership and running `docker compose up -d`.
