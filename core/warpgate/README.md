# Warpgate

Lightweight, multi-protocol bastion / PAM. One binary proxies SSH, HTTPS,
MySQL, PostgreSQL, Kubernetes, RDP and VNC to targets you register in its
admin UI — no client-side software or SSH wrapper needed. See the [PAM/bastion
comparison](../README.md#privileged-access--bastion-alternatives) for how it
differs from JumpServer, ShellHub, Teleport and Orion Belt.

## Architecture

| Service | Image | Purpose |
|---|---|---|
| `warpgate` | `warp-tech/warpgate` | Proxy for every protocol + embedded SQLite (users, sessions, audit log) + admin web UI |

No separate database, no separate secrets service — everything lives in one
container and one bind mount. This is the simplest of the five PAM/bastion
stacks in this repository, by design: it is the "lightweight" role.

## Try it locally

Runs on `http://localhost:8888` without Traefik, DNS or a certificate; port 2222 is published too.

```bash
cp .env.local.example .env.local
docker compose -f docker-compose.local.yml --env-file .env.local up -d
# http://localhost:8888
docker compose -f docker-compose.local.yml --env-file .env.local down
```

## Setup

```bash
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, APP_TRAEFIK_ACCESS if not VPN-only
mkdir -p volumes/data .secrets
openssl rand -base64 24 | tr -d '\n' > .secrets/admin_password.txt
```

Warpgate's data directory has to be owned by the container's fixed UID
(1000) before the first start — verified directly: `unattended-setup` fails
with `Permission denied` otherwise, and there is no init-perms sidecar here
because a single bind mount does not justify one:

```bash
sudo chown -R 1000:1000 volumes/data
```

Run the non-interactive setup once. This generates `warpgate.yaml`, a CA,
SSH host/client keys, a self-signed TLS certificate and the admin user —
verified end to end under this stack's full hardening (`cap_drop: ALL`,
`read_only`, `no-new-privileges`):

```bash
docker compose run --rm \
  -e WARPGATE_ADMIN_PASSWORD="$(cat .secrets/admin_password.txt)" \
  warpgate unattended-setup \
    --data-path /data --http-port 8888 --ssh-port 2222 \
    --external-host "$(grep ^APP_TRAEFIK_HOST= .env | cut -d= -f2)" \
    --record-sessions \
    --host-key-verification auto-accept
```

`--host-key-verification auto-accept` trusts a target's SSH host key on
first connection (TOFU — the common SSH default) and flags a *change*
afterwards. Use `auto-reject` instead if you would rather approve every new
target's host key by hand before the first connection succeeds.

```bash
docker compose up -d
```

The admin UI answers at `https://<APP_TRAEFIK_HOST>` (VPN-only by default) —
log in as `admin` with the password you generated, and register your first
SSH/HTTP/database target there. Warpgate needs
`http.trust_x_forwarded_headers: true` in `volumes/data/warpgate.yaml` to
construct correct redirect URLs behind Traefik — set it and
`docker compose restart warpgate` before relying on SSO login through it;
this has not been exercised on a live host from this repository (see
UPSTREAM.md).

## Network exposure

Three different port types, and only one of them is Traefik's business:

| Port | Protocol | Reachable from | Through Traefik? |
|---|---|---|---|
| `WARPGATE_SSH_PORT` (2222) | Raw SSH | Anyone with a Warpgate account who needs an SSH target | No — SSH is not HTTP |
| `WARPGATE_MYSQL_PORT` (33306) | Raw MySQL wire protocol | Anyone with a Warpgate account who needs a MySQL target | No |
| Admin UI (8888 internally) | HTTPS | `APP_TRAEFIK_ACCESS` policy — VPN-only by default | Yes |

Do not attempt to route the SSH or MySQL ports through Traefik — they are
not HTTP(S), and forcing them through a reverse proxy neither works cleanly
nor gains anything. Publish them directly, on whatever host interface your
access policy actually requires, and use your host firewall or VPN to bound
who can reach them — the same reasoning `docs/standards/networking.md`
already applies to `core/dnsmasq`'s host-network exception.

## Security Model

A bastion is itself a high-value target: it holds working credentials or
trust relationships to every system it proxies. Read this before deploying
it in front of anything real.

**What access it gets to target systems.** None held in advance. Warpgate
proxies a session as it happens — it does not store target-system passwords
unless you configure "credential vaulting" for a target (not covered by
this deployment; leave targets on user-supplied or key-based auth unless you
have a specific reason to trust Warpgate with a target's own credentials
too). Compromise of Warpgate itself grants an attacker the same reach a
compromised jump host normally would: everything a legitimate user can
currently reach through it, for as long as sessions stay valid.

**Where credentials and keys live.** `volumes/data/warpgate.yaml` (config
and its own SSH client/host keys) and the embedded SQLite database in the
same directory (users, password hashes, per-target settings, the audit log).
There is no separate secrets store to compromise independently — this one
directory is the whole blast radius.

**What compromising this host means.** Full impersonation of every user who
can log in, and full audit-log tampering ability, until the compromise is
found and every credential/key in `volumes/data` is rotated. Treat this host
like a domain controller, not like a normal application server: same
patch cadence, same access restriction (`acc-tailscale`, not `acc-public`),
same "who has shell on this box" discipline.

**What session recordings contain.** Everything the recorded protocol
carries — for SSH, every keystroke and every byte of terminal output,
which can include passwords typed into a remote prompt, file contents
`cat`ted to the terminal, and anything else a session displays. Recordings
are enabled by `--record-sessions` above and stored in the same data
directory as the rest of the state; back them up with the same care as the
credential database, not as an afterthought.

**Which ports must be reachable from where.** The SSH/database proxy ports
from wherever your users actually connect from (typically your VPN range,
matching `APP_TRAEFIK_ACCESS`'s intent even though these ports bypass
Traefik itself); the admin UI from wherever administrators log in. Neither
needs to be reachable from the target systems' own network — Warpgate
initiates the connection *to* targets, not the reverse.

**MFA / OIDC.** Native support, confirmed in the upstream README: TOTP for
local accounts, and OpenID Connect for SSO. Both `core/authentik` and
`core/keycloak` in this repository are usable OIDC providers — point
Warpgate's SSO configuration at either. Not exercised end to end from this
repository; configure and verify against your own instance before relying
on it.

## Backup

| | |
|---|---|
| **State** | `./volumes/data` — `warpgate.yaml`, the SQLite database (users, sessions, per-target config, audit log), the CA, SSH host/client keys, session recordings (if enabled), and the TLS key until replaced with a real certificate |
| **Critical** | All of it — there is no secondary store. Losing this directory without a backup means recreating every user, every target and every key from scratch |
| **Quiescing** | Not verified. SQLite generally tolerates a live file-level copy poorly under write load; stop the container for a consistent backup, or verify WAL-mode safety before trusting a live copy |

```yaml
sqlite_databases:
    - name: warpgate
      path: /srv/docker/core/warpgate/volumes/data/db.sqlite3
source_directories:
    - /srv/docker/core/warpgate/volumes/data
```

For the general SQLite restore procedure and verification checklist, see
[Restore](../../docs/standards/restore.md). Restoring `volumes/data` restores
the admin password hash, every registered target and every key — a new
deployment does not need `unattended-setup` run again after a restore.

## Known Issues

- **Not yet run on a live host.** Setup and a bare `run` were verified
  against the hardening flags this compose file uses; an actual proxied
  session, the reverse-proxy/OIDC path, and a restart or upgrade were not.
- **`WARPGATE_MYSQL_PORT` is published even with no MySQL target
  configured.** Comment the line out in `docker-compose.yml` if you have no
  MySQL target and would rather not publish an unused port.

## Details

See [UPSTREAM.md](UPSTREAM.md) for exactly what was verified and how, the
upgrade path, and what remains unverified.
