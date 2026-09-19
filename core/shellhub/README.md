# ShellHub

Agent-based, reverse-connection SSH access. Install a ShellHub agent on each
machine you want to reach; the agent dials out to the server here, so
nothing on the target needs an inbound port, a public IP, or a firewall
change. See the [PAM/bastion comparison](../README.md#privileged-access--bastion-alternatives)
for how it differs from Warpgate, JumpServer, Teleport and Orion Belt.

## Architecture

| Service | Image | Purpose |
|---|---|---|
| `db` | `postgres` | Device registry, users, sessions |
| `valkey` | `valkey/valkey` | Job queue + cache, no persistence |
| `server` | `shellhubio/server` | API + the SSH rendezvous point agents dial into |
| `ui` | `shellhubio/ui` | Web frontend, reached only through `gateway` |
| `gateway` | `shellhubio/gateway` | Reverse proxy in front of `server` + `ui` — this is what Traefik fronts |

The devices you actually connect to are not part of this stack — they run
the ShellHub agent separately, the same relationship `monitoring/beszel` has
to `monitoring/beszel-agent`.

## Setup

```bash
cp .env.example .env
mkdir -p .secrets volumes/postgres
openssl rand -hex 32 > .secrets/db_pwd.txt
ssh-keygen -t rsa -b 4096 -m PEM -f .secrets/ssh_private_key -N ""
openssl genrsa -out .secrets/api_private_key 4096
openssl rsa -in .secrets/api_private_key -pubout -out .secrets/api_public_key
```

Copy `.secrets/db_pwd.txt`'s contents into `.env` as
`SHELLHUB_POSTGRES_PASSWORD` — see `.env.example`'s Secrets section for why
this one value cannot be a Docker Secret on the `server`/`gateway` side even
though the database itself uses one.

```bash
docker compose up -d
docker compose ps    # all five services should reach "healthy"
```

Log in at `https://<APP_TRAEFIK_HOST>` to create the first account, then
install an agent on a target machine and register it from the UI.

## Network exposure

| Port | Protocol | Reachable from | Through Traefik? |
|---|---|---|---|
| `SHELLHUB_SSH_PORT` (2222) | Raw SSH (agent rendezvous + your `ssh` client) | Every device running an agent, and everyone who needs to connect to one | No — not HTTP |
| Gateway (80 internally) | HTTPS | `APP_TRAEFIK_ACCESS` policy — VPN-only by default | Yes |

The SSH port has to be reachable from both directions this repository
normally keeps separate: agents on target machines dial *out* to it, and
your own SSH client dials *in* to reach a device. It cannot be restricted to
your VPN range the way the web UI is, unless every device you manage is
also on that VPN.

## Security Model

**What access it gets to target systems.** None held by this server
directly — the agent on each target opens the connection and proxies
whatever the connecting user's own SSH key or password authorizes on that
device. Compromising this server does not hand over target credentials the
way JumpServer's stored-credential model would; it hands over the ability
to see which devices are registered and to intercept or redirect sessions
in transit.

**Where credentials and keys live.** The SSH host key and API keypair are
Docker Secrets (`.secrets/`); device registration tokens and session
metadata live in `./volumes/postgres`. There are no target-system
credentials stored here at all — that is the architectural difference from
JumpServer.

**What compromising this host means.** An attacker gains the rendezvous
point every agent trusts — they could impersonate the server to agents,
or observe/redirect sessions in transit, but do not automatically gain
standing credentials to every target the way a compromised credential-vault
PAM would.

**What session recordings contain.** Confirmed by upstream docs: session
recordings and audit logs are kept server-side, with the same scope as any
SSH session recorder — keystrokes and terminal output for what was
recorded. Exact retention/storage behavior was not exercised here.

**Which ports must be reachable from where.** The SSH port from every
managed device's network (outbound) and from wherever you connect (inbound)
— see "Network exposure" above; the gateway from wherever users log in to
the web UI.

**MFA / OIDC.** SAML SSO is confirmed Enterprise-only. OIDC support in
Community Edition was not confirmed either way in available upstream
documentation as of this writing — verify directly against a running
instance before assuming `core/authentik` or `core/keycloak` can front
login here.

## Backup

| | |
|---|---|
| **State** | `./volumes/postgres` — device registry, user accounts, session metadata. `.secrets/` — the SSH host key and API keypair, needed to keep every already-registered agent trusting this server without re-enrollment. |
| **Critical** | Both. Losing the SSH host key specifically means every agent's host-key verification fails on next connect, even if the database survives intact. |
| **Quiescing** | Not verified here — standard PostgreSQL logical-dump caution applies; see `docs/standards/restore.md`. |

```yaml
postgresql_databases:
  - name: shellhub
    container: shellhub-db
source_directories:
    - /srv/docker/core/shellhub/.secrets
```

For the general PostgreSQL restore procedure and verification checklist, see
[Restore](../../docs/standards/restore.md).

## Known Issues

- **`server` has no stable Docker Hub tag as of this writing** — this
  deployment pins the newest release candidate; see
  [UPSTREAM.md](UPSTREAM.md#known-limitations) and check for a stable
  release before every deploy.
- **Not yet exercised beyond a clean start** — no agent registered, no SSH
  session proxied, no restart or upgrade tested.
- **OIDC-in-Community-Edition status unconfirmed** — see Security Model.

## Details

See [UPSTREAM.md](UPSTREAM.md) for exactly what was verified and how, the
upgrade path, and what remains unverified.
