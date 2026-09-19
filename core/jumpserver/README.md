# JumpServer

Full-featured, traditional PAM platform: SSH/RDP/database/Kubernetes access,
session recording, approval workflows and audit, all through one web
console. See the [PAM/bastion comparison](../README.md#privileged-access--bastion-alternatives)
for how it differs from Warpgate, ShellHub, Teleport and Orion Belt.

## Architecture

| Service | Image | Purpose |
|---|---|---|
| `jumpserver` | `jumpserver/jms_all` | Core (Django) + koko (SSH/RDP gateway) + web UI + bundled PostgreSQL + Redis + nginx, one container |

This is the vendor's own all-in-one image, not a decomposition into
per-service containers the way every other stack in this repository is
built — see [UPSTREAM.md](UPSTREAM.md#why-this-is-one-container-not-a-decomposed-stack-like-every-other-in-this-repository)
for why no granular alternative exists yet.

## Setup

```bash
cp .env.example .env
mkdir -p volumes/data volumes/download .secrets
openssl rand -base64 32 | tr -d '\n' > .secrets/secret_key.txt
openssl rand -base64 16 | tr -d '\n' > .secrets/bootstrap_token.txt
```

Copy both generated values into `.env` as `SECRET_KEY` and `BOOTSTRAP_TOKEN`
— see `.env.example`'s Secrets section for why these cannot be Docker
Secrets here.

```bash
docker compose up -d
docker compose logs -f    # first boot applies database migrations, ~90s
```

Log in at `https://<APP_TRAEFIK_HOST>` as `admin` / `ChangeMe` and **change
the password immediately** — this default is documented by the vendor, not
a placeholder this repository invented.

## Network exposure

| Port | Protocol | Reachable from | Through Traefik? |
|---|---|---|---|
| `JUMPSERVER_SSH_PORT` (2222) | Raw SSH/RDP (koko gateway) | Anyone with a JumpServer account and an SSH/RDP target | No — not HTTP |
| Web console (80 internally) | HTTPS | `APP_TRAEFIK_ACCESS` policy — VPN-only by default | Yes |

Do not route the SSH/RDP gateway through Traefik. Publish it directly and
bound who can reach it with your host firewall or VPN, the same as every
other raw-TCP service in this repository.

## Security Model

**What access it gets to target systems.** JumpServer is designed to *hold*
target credentials on the user's behalf — that is its core PAM function, not
an incidental risk. Assets are registered with stored credentials (password,
SSH key, or looked up from a vault), and JumpServer authenticates to them
using those stored credentials when a user connects. This is a materially
larger blast radius than Warpgate's session-only proxying: compromising this
host can mean direct, standing access to every registered target, not just
active sessions.

**Where credentials and keys live.** In the bundled PostgreSQL database
under `./volumes/data`, encrypted at rest with a key derived from
`SECRET_KEY`. Compromising `SECRET_KEY` and the database together is
equivalent to compromising every stored credential.

**What compromising this host means.** Full read access to every stored
target credential, full session-recording archive, and the ability to
authenticate as JumpServer to any registered asset. Treat this host with the
same access discipline as a credential vault, because it is one.

**What session recordings contain.** For terminal sessions, every keystroke
and all terminal output — the same scope as any SSH session recorder.
RDP/graphical sessions are recorded as video. Stored under `./volumes/data`
alongside the database; back them up with equal care.

**Which ports must be reachable from where.** The SSH/RDP gateway from
wherever your users connect (typically your VPN range); the web console
from wherever administrators and approvers log in. Neither needs to be
reachable from target systems' own networks — JumpServer initiates outbound
connections to targets, not the reverse.

**MFA / OIDC.** Confirmed available in the Community Edition (GPL-3.0), not
gated to Enterprise: local TOTP/Passkey/WebAuthn MFA, plus OIDC, SAML 2.0,
CAS and LDAP/AD SSO. Both `core/authentik` and `core/keycloak` in this
repository are usable OIDC providers. Not exercised end to end from this
repository — configure and verify against your own instance.

## Backup

| | |
|---|---|
| **State** | `./volumes/data` — the bundled PostgreSQL data directory, stored credentials, session recordings, and application state. `./volumes/download` is regenerable export/report cache. |
| **Critical** | `./volumes/data` entirely. It is one container's worth of what would normally be three or four separate backup targets in this repository's usual model. |
| **Quiescing** | Not verified. The bundled Postgres is a normal PostgreSQL instance; a file-level copy of a live data directory risks the same torn-write problem `docs/standards/restore.md` describes for any database — a logical dump from inside the container (`docker compose exec jumpserver ...`) is the safer, unverified-here alternative. |

For the general restore procedure and verification checklist, see
[Restore](../../docs/standards/restore.md). This stack's single-container
shape means there is no separate database container to target a
`postgresql_databases:` hook at — a full `source_directories` capture of
`./volumes/data` is the only verified-shape option until a logical-dump
path is exercised.

## Known Issues

- **Not yet run on a live host beyond a clean start** — see
  [UPSTREAM.md](UPSTREAM.md#what-was-actually-verified-and-how) for exactly
  what was and was not exercised.
- **Cannot run under this repository's usual hardening** —
  `no-new-privileges`, `cap_drop`, and `read_only` all break this image;
  see `docker-compose.yml`'s Security block for the verified reason for
  each.
- **One major version behind upstream's newest (v5) architecture** — see
  [UPSTREAM.md](UPSTREAM.md#known-limitations).
- **4 CPU / 8 GB RAM minimum** (vendor-stated) makes this the heaviest of
  the five PAM/bastion stacks evaluated together with this one.

## Details

See [UPSTREAM.md](UPSTREAM.md) for exactly what was verified and how, the
upgrade path, and what remains unverified.
