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
