# Core

Shared platform and control plane — capabilities whose scope is the installation
rather than one stack: control of Docker, the host or other containers, and shared
network, TLS, identity, DNS, security or secrets.

Scope decides membership here, not dependency. Most of what follows is optional,
and several entries are alternatives to each other — a capability does not stop
being installation-scoped because an installation can do without it. The
categorisation test and the reasoning are in
[`docs/architecture.md`](../docs/architecture.md#directory-structure).

Only Traefik is close to unconditional: anything reachable over a network routes
through it.

## What's here

What has been established about each stack — verified against which version and
when, whether a restore was performed — is in [`LIFECYCLE.md`](../LIFECYCLE.md),
generated from the repository.

### Request path

| Service | Description |
|---|---|
| [Traefik](traefik/) | Reverse proxy with socket proxy, 5 security levels, 3 TLS profiles, access policies |
| [CrowdSec](crowdsec/) | Threat detection engine — log analysis, scenarios, decisions. Enforcement is a separate choice: reverse-proxy or host-firewall remediation |

Planned: **Suricata** (network IDS) and **Coraza** (web application firewall), two
capabilities beside CrowdSec, each with a design question open in
[`ROADMAP.md`](../ROADMAP.md#added--the-held-candidates).

### Shared identity

Pick one. Both are maintained; they solve the same problem differently, and
[`keycloak/README.md`](keycloak/README.md) compares them.

| Service | Description |
|---|---|
| [Authentik](authentik/) | Identity provider for centralised authentication — Forward-Auth, OAuth2 / OIDC / SAML. The reference implementation |
| [Keycloak](keycloak/) | Identity provider for applications that speak OIDC or SAML themselves, with LDAP and AD federation. Two containers, no proxy of its own |

### Shared names and certificates

| Service | Description |
|---|---|
| [dnsmasq](dnsmasq/) | DNS forwarder with wildcard zones for Tailscale / split-DNS setups |
| [acme-certs](acme-certs/) | Certificate tool (acme.sh) for the devices that never pass through Traefik — NAS, routers, mail servers, firewalls |
| [step-ca](step-ca/) | Internal PKI — X.509, ACME and optional SSH certificates for machines and services inside this installation. Not for public web TLS; see its README for the split from Traefik/ACME |

### Shared private network

| Service | Description |
|---|---|
| [headscale](headscale/) | Control server for Tailscale clients — the node registry, keys and policy of a tailnet you run yourself. `acc-tailscale` means this tailnet where it is deployed. Ships closed on `acc-local`; the embedded relay is an opt-in overlay because it needs a published UDP port |

### Shared secrets

| Service | Description |
|---|---|
| [Infisical](infisical/) | Central secret manager — an optional alternative to per-stack Docker Secrets. It holds every other stack's credentials, so it is VPN-only by default |

### Docker control plane

Two independent pairs, each a management UI plus the agent it uses to reach other
hosts. Pick one pair, or neither.

| Service | Description |
|---|---|
| [Dockhand](dockhand/) | Docker management with Git-based stacks — deploy and update by pushing to Git |
| [Hawser](hawser/) | Remote Docker agent for Dockhand. Outbound WebSocket by default, so the managed host publishes no port |
| [Portainer](portainer/) | Docker management UI, community edition. Connects through a filtered socket proxy |
| [Portainer Agent](portainer-agent/) | Remote Docker agent for Portainer. Needs an inbound port on the managed host — [Dockhand + Hawser](hawser/) avoids that |

Planned: none.

### Shared container registry

| Service | Description |
|---|---|
| [zot](zot/) | OCI-native registry for this installation's own build output — self-built images, not a mirror of Docker Hub/GHCR. No database, one binary |

### Privileged access / bastion alternatives

Five different architectures for the same underlying problem — controlled
access to privileged infrastructure. Each solves it a different way and is
kept that way; pick the one whose approach fits, not a feature checklist.
Every one is documented, hardened and pinned the same way the rest of this
repository is; how far each has actually been exercised is in
[`LIFECYCLE.md`](../LIFECYCLE.md), and each stack's own README states
exactly what was and was not verified.

| Service | Description |
|---|---|
| [Warpgate](warpgate/) | Lightweight, multi-protocol proxy (SSH, HTTPS, MySQL, PostgreSQL, Kubernetes, RDP, VNC). No database, no CE/EE split |
| [JumpServer](jumpserver/) | Full-featured, traditional PAM — stored target credentials, session recording, approval workflows. The vendor's own all-in-one image; cannot run under this repository's usual container hardening (documented, not silently accepted) |
| [ShellHub](shellhub/) | Agent-based, reverse-connection SSH access — install an agent on each target, no inbound port needed there. The server component here currently has no stable upstream release tag |
| [Teleport](teleport/) | Identity- and certificate-based access — short-lived certificates instead of standing credentials. Does not sit behind Traefik: its proxy port carries client-certificate TLS Traefik would break. Community Edition's license has real usage limits — read its README first |
| [Orion Belt](orion-belt/) *(experimental)* | Lightweight reverse-agent PAM with JIT approval and ReBAC. Single-maintainer project, a few months old — read its README's maturity assessment before trusting it with real access |

#### Choosing between them

| | Warpgate | JumpServer | ShellHub | Teleport | Orion Belt |
|---|---|---|---|---|---|
| Approach | Session proxy | Stored-credential vault | Reverse-connection agent | Short-lived certificates | Reverse-agent, JIT |
| Protocols | SSH, HTTPS, MySQL, PostgreSQL, Kubernetes, RDP, VNC | SSH, RDP, Kubernetes, databases, web apps | SSH, SCP/SFTP | SSH, Kubernetes, databases, internal web apps | SSH, SCP |
| Session recording | Yes | Yes (terminal + video) | Server-side, scope not exercised here | Not enabled in this config | Yes (encryption optional) |
| MFA | TOTP | TOTP / Passkey / WebAuthn | Not confirmed | TOTP / WebAuthn, required for local users | WebAuthn, optional |
| OIDC / SSO | Yes (native) | Yes — OIDC, SAML 2.0, CAS, LDAP (Community Edition) | SAML confirmed Enterprise-only; OIDC unconfirmed | **Enterprise-only** — no SSO in Community Edition | Not found in documented config |
| JIT / approval | No | Ticket-based workflows | No | No (certificate TTL only) | Yes — the stack's core model |
| Agent required on targets | No | No (agent optional for some protocols) | **Yes** | Only for SSH nodes / Kubernetes / DB access, not core proxy | **Yes** |
| Licence | Apache-2.0 | GPL-3.0 (EE separate, closed) | Apache-2.0 (Enterprise features gated) | AGPL-3.0 source / **commercial CE binaries** | Apache-2.0 + Commons Clause |
| Resource footprint | Smallest — one binary, embedded SQLite | Largest — vendor minimum 4 CPU / 8 GB RAM | Medium — 5 containers, Postgres + Valkey | Small — one binary, embedded backend | Small — one binary + Postgres |
| Typical fit | A small install wanting one lightweight proxy for several protocols | An organisation that wants stored credentials, recording and approval workflows out of the box | Reaching devices without opening inbound ports to them | Certificate-based access without standing SSH keys, where CE's licence terms fit | Trying JIT/ReBAC access patterns, accepting a young project's risk |

No overall recommendation is made here on purpose — the right choice
depends on which architecture and which limitation you can live with, not
a feature count.

### Optional host tooling

[`host-watchdog/`](host-watchdog/) — two independent, host-installed,
opt-in scripts that give the Docker daemon and the Traefik container one
bounded, automatic recovery attempt after a confirmed sustained failure.
Not a stack, not installed by default, and not required by anything above.

## Related

- [`apps/`](../apps/) — user-facing applications, including the operator and
  diagnostic tools that serve their own users rather than other stacks
- [`docs/architecture.md`](../docs/architecture.md) — why the categories are what
  they are, the networking model, and the capability table
