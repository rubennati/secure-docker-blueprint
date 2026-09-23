# Kopia (repository server)

A repository other machines back up into. Each machine runs its own Kopia
client with its own account; the client sends deduplicated, encrypted data over
gRPC and never sees the repository password or the storage credentials.
Upstream: [kopia/kopia](https://github.com/kopia/kopia).

This is the one shape of a containerised backup service
[`backup/README.md`](../README.md#where-the-backup-agent-belongs) allows: the
agent that reads a machine's files stays on that machine, and nothing of this
host is mounted here. It is the same split as [`backup/urbackup`](../urbackup/).

## Architecture

```text
Client machines ──gRPC over TLS──→ Traefik ──https──→ kopia-server :51515
(their own accounts)                                        │
                                              volumes/repository (the data)
                                              volumes/config    (cert, repository.config)
```

The repository can sit on this host's disk (`volumes/repository`, the default)
or on a remote provider — S3, B2, SFTP and the rest are a different
`repository create` line, after which the volume only holds cache and
configuration.

## Setup

```bash
cp .env.example .env            # host name, the two account names
ops/init.sh                     # passwords, the server certificate, the repository
docker compose up -d
docker compose logs kopia-server --follow    # watch for: SERVER ADDRESS: https://[::]:51515
```

`ops/init.sh` writes the three secrets, generates the server's own certificate
and creates the repository. It refuses to overwrite anything that exists, so it
is safe to run twice.

**Back up `.secrets/kopia_repository_password.txt` somewhere this host cannot
reach.** Kopia derives the encryption key from it and stores nothing that can
recover it: without that file every snapshot in the repository is unreadable —
the same rule [`backup/README.md`](../README.md) states for Borg's key.

### Adding a machine

```bash
# On this host — through the entrypoint, which is what holds the repository
# password. A plain `docker compose exec … /bin/kopia …` prompts for it instead.
docker compose exec kopia-server /bin/sh /config/entrypoint.sh \
    /bin/kopia server user add laptop@alice

docker compose restart kopia-server     # credentials take effect on restart
```

On the machine itself, with Kopia installed there:

```bash
kopia repository connect server \
    --url https://kopia.example.com \
    --override-username laptop --override-hostname alice
kopia snapshot create /home/alice
```

No certificate fingerprint is needed through Traefik: the client verifies the
public certificate Traefik serves. A client that reaches the container directly
— on the LAN, or the local variant below — pins the container's own certificate
instead:

```bash
docker compose exec kopia-server openssl x509 -in /app/config/tls.crt \
    -noout -fingerprint -sha256        # pass it as --server-cert-fingerprint
```

### Limiting what a machine may do

By default a client has full rights over its own snapshots, deletion included —
which is worth changing for a machine you are protecting against ransomware:

```bash
docker compose exec kopia-server /bin/sh /config/entrypoint.sh \
    /bin/kopia server acl add --user "laptop@alice" --target "type=snapshot" --access APPEND
```

`kopia server acl list` shows what is in force. `APPEND` lets the client write
new snapshots and read its own; it does not let it remove them.

## Try it locally

Runs on `https://localhost:51515` without Traefik. The certificate is the
server's own, so a browser warns.

```bash
cp .env.local.example .env.local
COMPOSE_FILE=docker-compose.local.yml ENV_FILE=.env.local ops/init.sh
docker compose -f docker-compose.local.yml --env-file .env.local up -d
# https://localhost:51515 — sign in as the user in .env.local
docker compose -f docker-compose.local.yml --env-file .env.local down
```

## Security model

- **Three passwords, three jobs.** The repository password is the encryption
  key; the server password is the web interface's login; the control password
  belongs to the API that `kopia server refresh` and the status commands use.
  All three are Docker Secrets, exported by `config/entrypoint.sh` because
  Kopia reads them from the environment and has no `_FILE` variant.
- **A client never holds the repository password.** It authenticates with its
  own account, and the server does the encryption.
- **`read_only: true`, `cap_drop: ALL`, `no-new-privileges`, non-root** —
  verified against 0.23.1; the four mounted directories are the only writable
  paths.
- **Every path needs the login.** Measured: `/` answers 401 without
  credentials, including `/metrics`.
- **TLS to the container, not only to Traefik.** Kopia's clients speak gRPC,
  which needs HTTP/2 with TLS the whole way, so the container serves its own
  certificate and Traefik forwards over HTTPS without verifying it —
  `backend-selfsigned@file`, see
  [`traefik-security.md`](../../docs/standards/traefik-security.md). That entry
  has to exist in `core/traefik`: without it the router answers nothing and
  Traefik logs "servers transport not found".
- **`acc-tailscale` by default**, because every machine that backs up here has
  to reach this host and the VPN is where those machines are.

## Known limits

- **The rate limit is not measured.** The chain ships `sec-2`. A client's
  traffic is a handful of long-lived gRPC requests rather than many short ones,
  so it is unlikely to bite — but no backup window has been measured through it.
- **The certificate is generated once** by `ops/init.sh`, with ten years of
  validity. Kopia's own `--tls-generate-cert` cannot do it on every start: it
  refuses when the file exists, which is why the command in the compose file
  does not carry it.
- **Still 0.x.** Upstream has not declared a 1.0.
- **Nothing here has run behind this repository's Traefik yet.** The stack is
  `scaffolded`. A client did reach it through a Traefik configured the same way
  — see `UPSTREAM.md` — but not through `core/traefik` on a host.

## Backup

Backing up the backup server means two different things, and only one of them
is this stack's job.

| | |
|---|---|
| **The repository** | `./volumes/repository` — the snapshots themselves, already encrypted and deduplicated. Copy it to a second location rather than backing it up again; Kopia's own `kopia repository sync-to` is built for that |
| **The key** | `.secrets/kopia_repository_password.txt` — keep a copy off this host. Without it the repository cannot be read |
| **State** | `./volumes/config` — `repository.config` (which repository, and the storage credentials for a remote one) and the server certificate |
| **Reproducible** | `./volumes/cache` and `./volumes/logs` |
| **Quiescing** | Stop the server before copying `volumes/repository`; a client writing during the copy produces a half-written blob |

```yaml
# /etc/borgmatic/config.yaml
source_directories:
  - /srv/secure-docker-blueprint/backup/kopia/volumes/config
  # volumes/repository only if it is not synced elsewhere — it is large, and
  # already encrypted and deduplicated
```

Restore: put `volumes/config` and `volumes/repository` back with their
ownership at `APP_UID:APP_GID`, restore the password file, start the container.
Client accounts and ACL rules live inside the repository and come back with it.
