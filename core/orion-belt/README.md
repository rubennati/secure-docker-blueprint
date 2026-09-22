# Orion Belt

> **EXPERIMENTAL.** Single-maintainer project, 43 GitHub stars, created
> 2026-01, first stable release 2026-07-14. Read
> [UPSTREAM.md](UPSTREAM.md#experimental--project-maturity-verified-directly)
> before trusting it with real infrastructure access — a PAM tool is
> exactly the kind of software where a project's youth is a real risk to
> weigh, not a formality.

Lightweight, reverse-agent, JIT-approval PAM: agents on protected hosts
dial out to this server, so nothing needs an inbound port; access requests
go through a relationship-based policy (ReBAC) and can require approval.
See the [PAM/bastion comparison](../README.md#privileged-access--bastion-alternatives)
for how it differs from Warpgate, JumpServer, ShellHub and Teleport.

## Architecture

| Service | Image | Purpose |
|---|---|---|
| `db` | `postgres` | Users, agents, access policies, audit trail |
| `server` | `orion-belt-dev/orion-belt-server` | SSH gateway + API/web console |

The agent (`docker-compose.agent.yml`) is not part of this stack — it runs
on each host you want to protect, the same relationship
`monitoring/beszel-agent` has to `monitoring/beszel`.

## Try it locally

Runs on `http://localhost:8080` without Traefik, DNS or a certificate; port 2222 is the SSH entry point.

```bash
cp .env.local.example .env.local
docker compose -f docker-compose.local.yml --env-file .env.local up -d
# http://localhost:8080
docker compose -f docker-compose.local.yml --env-file .env.local down
```

## Setup

```bash
cp .env.example .env
mkdir -p .secrets volumes/postgres volumes/recordings volumes/hostkey
openssl rand -hex 32 > .secrets/db_pwd.txt
openssl rand -hex 32 > .secrets/jwt_secret.txt
```

Copy `.secrets/jwt_secret.txt`'s contents into `.env` as `ORION_JWT_SECRET`,
and `.secrets/db_pwd.txt`'s contents into `.env` as `POSTGRES_PASSWORD` —
see `.env.example`'s Secrets section for why this one value has to match a
Docker Secret's contents by hand rather than reference it directly.

```bash
docker compose up -d
docker compose exec server wget -qO- http://127.0.0.1:8080/health
```

Register your first agent from the web console at
`https://<APP_TRAEFIK_HOST>`, then deploy `docker-compose.agent.yml` on the
target host — see that file's header for the exact steps.

## Network exposure

| Port | Protocol | Reachable from | Through Traefik? |
|---|---|---|---|
| `ORION_SSH_PORT` (2222) | Raw SSH (agent rendezvous + your `ssh` client) | Every host running an agent, and everyone who needs to reach one | No — not HTTP |
| API/console (8080 internally) | HTTPS | `APP_TRAEFIK_ACCESS` policy — VPN-only by default | Yes |

Like ShellHub, the SSH port has to accept connections from both
directions: agents dialing out from protected hosts, and your own SSH
client dialing in.

## Security Model

**What access it gets to target systems.** None held directly — agents on
protected hosts accept connections proxied through this server and act
locally, similar in spirit to ShellHub's model. Compromising this server
does not hand over standing target credentials the way JumpServer's
stored-credential model would.

**Where credentials and keys live.** `./volumes/hostkey` holds this
server's own SSH host key, generated on first run — every agent that has
registered trusts it. `./volumes/postgres` holds user accounts, agent
registrations, access policies and the audit trail. Neither
`POSTGRES_PASSWORD` nor `ORION_JWT_SECRET` is a Docker Secret on the
server side — see UPSTREAM.md for exactly why, verified from the image's
own entrypoint script.

**What compromising this host means.** The ability to impersonate the
server to every registered agent, forge JWTs signed with the exposed
secret (since `ORION_JWT_SECRET` sits in the process environment in
clear), and read the full access-policy/audit database. Given the young
project and unaudited codebase, treat a compromise here as total until
proven otherwise — do not assume any blast-radius containment beyond what
is explicitly documented.

**What session recordings contain.** Not exercised in this deployment.
`ORION_RECORDING_ENCRYPTION_KEY` exists to encrypt them at rest — if you
enable recording in the console, generate and set a real key first, or
recordings are stored unencrypted in `./volumes/recordings`.

**Which ports must be reachable from where.** The SSH gateway from every
protected host (outbound) and from wherever you connect (inbound); the
console from wherever administrators log in.

**MFA / OIDC.** WebAuthn is supported and on by default
(`ORION_WEBAUTHN_ENABLED=true`); MFA is not required by default
(`ORION_MFA_REQUIRED=false` — set to `true` once at least one admin has
enrolled a factor, or you can lock yourself out). **No OIDC/SSO connector
was found in the documented configuration** as of v1.2.0 — neither
`core/authentik` nor `core/keycloak` can front login here on current
evidence.

## Backup

| | |
|---|---|
| **State** | `./volumes/postgres` — users, agent registrations, access policies, audit trail. `./volumes/hostkey` — the SSH host key every agent trusts. `./volumes/recordings` — session recordings, if enabled. |
| **Critical** | `./volumes/hostkey` specifically: losing it without a backup means every already-registered agent's host-key verification breaks on next connect, the same failure mode a lost Warpgate/ShellHub host key produces. |
| **Quiescing** | Not verified. Standard PostgreSQL logical-dump caution applies; see `docs/standards/restore.md`. |

```yaml
postgresql_databases:
  - name: orionbelt
    container: orion-belt-db
source_directories:
    - /srv/docker/core/orion-belt/volumes/hostkey
```

For the general PostgreSQL restore procedure and verification checklist, see
[Restore](../../docs/standards/restore.md).

## Known Issues

- **Experimental — see the top of this file and
  [UPSTREAM.md](UPSTREAM.md#experimental--project-maturity-verified-directly).**
- **No OIDC/SSO connector found** — local WebAuthn/MFA only.
- **No `_FILE` secret support on the server's own credentials** — mitigated
  only by keeping `.env` out of git; see UPSTREAM.md for the documented,
  unbuilt `ORION_CONFIG_FILE` path that could close this.
- **Not yet run on a live host beyond a clean start** — no agent
  registered, no SSH session proxied, no restart or upgrade tested.

## Details

See [UPSTREAM.md](UPSTREAM.md) for exactly what was verified and how, the
upgrade path, and what remains unverified.
