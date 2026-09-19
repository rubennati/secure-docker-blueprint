# Teleport

Identity- and certificate-based infrastructure access: no standing SSH
keys, short-lived certificates instead, with SSH, Kubernetes, database and
internal web app access all issued the same way. See the [PAM/bastion
comparison](../README.md#privileged-access--bastion-alternatives) for how
it differs from Warpgate, JumpServer, ShellHub and Orion Belt — and read
the license section below before choosing it.

## License — read this first

Community Edition's compiled images (this one included) are under a
**commercial license since Teleport 16, not Apache-2.0/AGPL**: unrestricted
for individuals' personal/hobby use; free for companies only under 100
employees **and** under $10M annual recurring revenue; otherwise Teleport
requires an Enterprise agreement. See
[UPSTREAM.md](UPSTREAM.md#community-edition-license--read-before-deploying-this)
for the verified detail. This is the most significant upstream risk among
the five PAM/bastion stacks in this repository.

## Architecture

| Service | Image | Purpose |
|---|---|---|
| `teleport` | `gravitational/teleport-distroless` | `auth` + `proxy` combined, one process, embedded BoltDB backend |

No Traefik, no separate database — the smallest possible single-node
Teleport, and the only one of the five PAM/bastion stacks here that does
not use this repository's reverse proxy at all. See "Network exposure".

## Setup

Generate the config once, before the first real start — this is not
automated inside the container, the same way Warpgate's setup is a
separate one-time step:

```bash
cp .env.example .env
mkdir -p config volumes/data
docker run --rm --entrypoint=/usr/local/bin/teleport \
  -v "$(pwd)/config:/etc/teleport" \
  public.ecr.aws/gravitational/teleport-distroless:18.11.0 \
  configure --roles=proxy,auth > config/teleport.yaml
```

This generates a self-signed certificate and a working `auth`+`proxy`
config with `proxy_listener_mode: multiplex` — verified directly, no
further edits are required for a first start.

```bash
docker compose up -d
docker compose exec teleport /usr/local/bin/teleport debug readyz -c /etc/teleport/teleport.yaml
```

Create the first local user (Community Edition has no SSO — see Security
Model):

```bash
docker compose exec teleport /usr/local/bin/tctl users add myuser --roles=editor,access --logins=root
```

Follow the printed URL to `https://<host>:3080/web/invite/<token>` to set a
password and enroll MFA (local users require MFA by default). Replace the
self-signed certificate with one from a real CA before relying on this for
anything beyond a first look — see UPSTREAM.md's upgrade/config notes.

## Network exposure

| Port | Protocol | Reachable from | Through Traefik? |
|---|---|---|---|
| `TELEPORT_AUTH_PORT` (3025) | Teleport's own mTLS | Nodes/agents joining the cluster | No |
| `TELEPORT_PROXY_PORT` (3080) | HTTPS, multiplexed with SSH/Kubernetes/database protocols behind Teleport's own certificate-based TLS | Anyone using the web UI, `tsh`, or a proxied protocol | **No — never.** See below. |

Every other stack in this repository puts its HTTP(S) interface behind
Traefik. This one does not, deliberately: Teleport's proxy port is not
"an HTTP service" in the way Traefik expects — it multiplexes plain HTTPS
for the browser UI with raw TLS carrying `tsh`, SSH, Kubernetes and
database client connections, all authenticated by client certificates
Teleport itself issues and verifies. A TLS-terminating reverse proxy in
front would decrypt exactly the handshake that certificate authentication
needs to see, breaking every client except a browser. Publish 3080 (and
3025) directly, and use your host firewall or VPN to bound who can reach
them — the same reasoning this repository already applies to raw-TCP
services, just for a port that happens to also serve a browser UI.

## Security Model

**What access it gets to target systems.** None held in advance — Teleport
issues short-lived certificates that a client presents directly to a
target (an SSH node running the Teleport agent, a database, a Kubernetes
API server). This server does not store target-system passwords at all;
its blast radius is the certificate authority, not a credential vault.

**Where credentials and keys live.** `./volumes/data`'s BoltDB backend
holds the cluster's certificate authorities — compromising this is
equivalent to being able to mint a valid certificate for anything the
cluster trusts, which is a materially different (and arguably larger, in
the wrong hands) risk than a stolen password: it does not require the
attacker to also compromise a target, only to be trusted by one.

**What compromising this host means.** Full control of the certificate
authority: the ability to issue certificates impersonating any user or
host the cluster would otherwise trust, until the CA is rotated and every
existing certificate invalidated. Treat this host like you would a private
CA, because that is what it is.

**What session recordings contain.** Not configured in this deployment
(the generated config does not enable session recording by default;
`ssh_service.enabled: "no"` — this single-node config runs auth+proxy
only, not an SSH node, so there is nothing local to record yet). If you add
node/session recording, the same rule as every other bastion in this
repository applies: terminal keystrokes and output, storage requiring the
same protection as the CA itself.

**Which ports must be reachable from where.** 3025 from every node/agent
that needs to join; 3080 from wherever users, `tsh`, and proxied clients
connect. Neither needs to be reachable from a protected target's own
network beyond the target's own outbound join connection.

**MFA / OIDC.** Local users require MFA (TOTP/WebAuthn) by default —
verified in the setup flow above. **OIDC and SAML SSO are confirmed
Enterprise-only** in Community Edition, verified from multiple independent
sources. Neither `core/authentik` nor `core/keycloak` can front login here
under the Community Edition license — this is the sharpest capability
boundary among the five PAM/bastion stacks in this repository.

## Backup

| | |
|---|---|
| **State** | `./config/teleport.yaml` (config, not secret by itself) and `./volumes/data` (the BoltDB backend: cluster CA, every issued host/user certificate, cluster configuration) |
| **Critical** | `./volumes/data` entirely. Losing the CA without a backup means every node has to be re-joined and every user re-enrolled from scratch — there is no smaller-scope recovery. |
| **Quiescing** | Not verified. BoltDB is a single-file embedded database; a live file-level copy risks the same torn-write concern any embedded database has under write load — stop the container for a consistent backup until this is exercised. |

```yaml
source_directories:
    - /srv/docker/core/teleport/config
    - /srv/docker/core/teleport/volumes/data
```

For the general restore procedure and verification checklist, see
[Restore](../../docs/standards/restore.md).

## Known Issues

- **License requires your own judgment** — see the top of this file and
  [UPSTREAM.md](UPSTREAM.md#community-edition-license--read-before-deploying-this).
- **No OIDC/SAML in Community Edition** — see Security Model.
- **Not yet run on a live host beyond a clean start** — no real node join,
  no `tsh` session, no restart or upgrade tested. See
  [UPSTREAM.md](UPSTREAM.md#what-was-actually-verified-and-how).
- **Self-signed certificate by default** — replace it with one from a real
  CA before relying on this for anything beyond a first look.

## Details

See [UPSTREAM.md](UPSTREAM.md) for exactly what was verified and how, the
upgrade path, and what remains unverified.
