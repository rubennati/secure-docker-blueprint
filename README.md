<div align="center">

# Secure Docker Blueprint

**Security-hardened Docker Compose patterns for self-hosted software — deploy, secure, operate, recover — for existing open-source projects and applications you build yourself.**

Hardened deployment configurations for **120+ self-hosting stacks** — a consistent
security baseline, file-based secret patterns, Traefik routing and network
isolation, with CrowdSec available as an optional security layer.

For applications you build yourself, [`development/`](development/) provides two
deployment patterns: a **static site** and a **web API**, following the same
**deploy → secure → operate → recover** approach.

[![CI](https://github.com/rubennati/secure-docker-blueprint/actions/workflows/ci.yml/badge.svg)](https://github.com/rubennati/secure-docker-blueprint/actions/workflows/ci.yml)
[![Trivy](https://github.com/rubennati/secure-docker-blueprint/actions/workflows/trivy.yml/badge.svg)](https://github.com/rubennati/secure-docker-blueprint/actions/workflows/trivy.yml)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/rubennati/secure-docker-blueprint/badge)](https://scorecard.dev/viewer/?uri=github.com/rubennati/secure-docker-blueprint)
[![OpenSSF Best Practices](https://www.bestpractices.dev/projects/13091/badge)](https://www.bestpractices.dev/projects/13091)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-v0.9.7-blue)](CHANGELOG.md)

**[Architecture](docs/architecture.md) · [Standards](docs/standards/) · [Verified status](LIFECYCLE.md) · [SecDockBlue](https://secdockblue.rubennati.at)**

</div>

Run self-hosted software without getting the security details wrong each time.
The shared security baseline uses file-based Docker Secrets where supported,
isolates datastores on internal networks without published ports, pins images,
and sets memory and PID limits. Traefik handles TLS and access control. Each stack
records deviations from the baseline in its own documentation.

[CrowdSec](core/crowdsec/) adds optional threat detection. Its
[AppSec component](core/crowdsec/docs/appsec.md) is opt-in and ships without the
OWASP Core Rule Set.

Quick Navigation: [Stacks](#stacks) · [Getting started](#getting-started) · [Overview](#how-the-pieces-fit) · [Repository layout](#repository-layout)

## Stacks

121 stacks in five categories. Each stack groups the configuration for an
application or infrastructure component; it may contain several containers or
run as a host tool. Each category below links to its full list.

| Browse | Stacks | Examples |
|---|---|---|
| [**`core/`** — proxy, identity, threat detection, secrets, Docker management](core/) | 21 | Traefik · Authentik · Keycloak · Authelia · CrowdSec · Infisical · dnsmasq · Portainer |
| [**`apps/`** — general self-hosted applications](apps/) | 63 | Nextcloud · Immich · Paperless-ngx · Vaultwarden · Stalwart · Ollama · Windmill · Ghost · n8n |
| [**`business/`** — invoicing, project management, helpdesk, analytics, e-signature](business/) | 19 | Invoice Ninja · OpenProject · Vikunja · Zammad · Matomo · Documenso |
| [**`monitoring/`** — uptime, metrics, notifications](monitoring/) | 14 | Uptime Kuma · Gatus · Beszel · Healthchecks · ntfy · Langfuse |
| [**`backup/`** — this host outward, your devices inward](backup/) | 4 | Borgmatic · UrBackup |

Where several tools solve the same problem, more than one is included.

## How the pieces fit

A typical HTTPS application follows this path. Traefik applies the stack's access
policy; the database or cache, where needed, stays on its internal network.

```mermaid
flowchart LR
  CLIENT["Browser / VPN client"] --> PROXY["Traefik<br/>HTTPS and access policy"]
  PROXY --> APP["Application<br/>own edge network"]
  APP --> DATA["Database / cache<br/>(where needed; internal network)"]
```

[Architecture](docs/architecture.md) covers optional integrations, host controls
and the boundaries between them.

## Getting started

Install Traefik before the application stacks that use its HTTPS routing.
Each stack is then installed from its own README. Services with additional
protocols, such as [mail](apps/docker-mailserver/README.md#architecture), may
publish their own ports through an opt-in overlay; their guides describe those
ports and prerequisites.

**Requirements:** Docker Engine 28.0+ with Compose 2.33.1+, a Linux host (tested on Debian 12/13),
`envsubst` (`gettext-base`), and a domain whose DNS you control. The shipped DNS-01
resolver uses Cloudflare; HTTP-01 and TLS-ALPN-01 work with other DNS providers.
The dashboard is VPN-only by default, so prepare a working VPN and DNS resolution
from its clients before expecting dashboard access.

A host checks out only the stacks it runs. `/srv/docker` is the recommended location,
not a required one:

```bash
sudo mkdir -p /srv/docker && sudo chown "$USER" /srv/docker   # an empty directory you own
git clone --sparse --no-checkout https://github.com/rubennati/secure-docker-blueprint.git /srv/docker
cd /srv/docker
git checkout "$(git tag --sort=-v:refname | head -n1)"   # the newest release
git sparse-checkout set scripts docs/standards
cp stacks.example stacks                 # the stacks on this host, one per line
scripts/stacks.sh apply                  # check out what stacks lists
cd core/traefik
cp .env.example .env
```

`stacks` starts with Traefik, CrowdSec and the `whoami` test target; add or remove lines
and apply again. Apply refuses to remove a stack that still has `.env` or data, because
Git would delete them with the directory. `scripts/stacks.sh update <tag>` previews a
release for just these stacks before taking it — see
[stacks on a host](docs/standards/deployment-lifecycle.md#2--choose-a-release-and-the-stacks).

Deploy from a tag rather than the default branch: `main` is where work lands between
releases, and the combination of stacks on it at any moment is not one anybody has
operated. [`docs/standards/deployment-lifecycle.md`](docs/standards/deployment-lifecycle.md)
covers the rest of the cycle — deployment order, updating the blueprint as against
updating an upstream image, rollback, and how a host states which release it runs.

Continue with **[Traefik setup](core/traefik/README.md#setup)** before starting
containers. It covers the required choices: IPv4-only or dual-stack (including a
real IPv6 subnet and Docker daemon prerequisites), certificate strategy, and VPN
access. The example intentionally leaves the certificate strategy unselected and
uses an IPv6 documentation prefix that validation refuses.

Once Traefik is running and its checks are complete, install an application from
its own README — for example [Vaultwarden](apps/vaultwarden/README.md) or
[Nextcloud](apps/nextcloud/README.md). On a 403 or 404,
[TROUBLESHOOTING.md](TROUBLESHOOTING.md) maps the symptom to its cause.
Run `./scripts/overview.sh` **from the repository root** to list what is configured
and running.

## Repository layout

```text
core/         shared infrastructure and control plane
apps/         general self-hosted applications
business/     business applications
monitoring/   monitoring and observability
backup/       backup and recovery
development/  reusable patterns for software you build yourself
docs/         architecture and standards
scripts/      CI checks, the overview script and the stack list tool
site/         SecDockBlue source
```

Compose-based stacks normally contain `docker-compose.yml`, `.env.example`, a
`README.md` with setup instructions, and an `UPSTREAM.md` recording image pins,
upgrade notes and verification. [`apps/_reference/`](apps/_reference/) provides
the application template. Host-installed components such as
[Borgmatic](backup/borgmatic/) and the optional [Host Watchdog](core/host-watchdog/)
have their own installation layout.

## Deploy → secure → operate → recover

Four phases, and the repository covers all of them:

- **Deploy** — a shared structure for Compose stacks, with configurable values documented in `.env.example`; host-installed tools have their own setup guides
- **Secure** — `no-new-privileges`, Docker socket proxies, file-based secrets with documented exceptions, datastores unreachable from the host network, memory, PID and swap limits — checked on every pull request; capabilities dropped and a read-only root filesystem wherever the image allows it
- **Operate** — healthchecks, resource and swap limits, monitoring stacks, and a recorded version each stack was last verified against
- **Recover** — Borgmatic with database-aware dumps, and restore playbooks per persistence pattern

[`docs/architecture.md`](docs/architecture.md) covers the networking model and how the
five categories are divided. [`docs/standards/`](docs/standards/) holds the rules each
stack is checked against.

## Status

**Pre-1.0** — paths, variable names and defaults can still change.

Verification depth varies by stack. [`LIFECYCLE.md`](LIFECYCLE.md) records what has been
run, against which version, and what remains unverified.

## Documentation

| | |
|---|---|
| Every stack, by category | [core/](core/) · [apps/](apps/) · [business/](business/) · [monitoring/](monitoring/) · [backup/](backup/) |
| Verification status per stack | [LIFECYCLE.md](LIFECYCLE.md) |
| Networking model, categories, capabilities | [docs/architecture.md](docs/architecture.md) |
| Compose, env, secrets, networking, restore rules | [docs/standards/](docs/standards/) |
| Applications you build yourself | [development/](development/) (patterns) · [docs/standards/custom-application.md](docs/standards/custom-application.md) (rules) |
| Symptom-to-cause troubleshooting | [TROUBLESHOOTING.md](TROUBLESHOOTING.md) |
| Adding a stack, contributing | [CONTRIBUTING.md](CONTRIBUTING.md) · [new-app checklist](docs/standards/new-app-checklist.md) |
| Reporting a vulnerability | [SECURITY.md](SECURITY.md) |
| Repository maintenance process | [docs/maintenance.md](docs/maintenance.md) |
| Planned work and what is out of scope | [ROADMAP.md](ROADMAP.md) |
| Release history | [CHANGELOG.md](CHANGELOG.md) |
| Guided operator documentation | [SecDockBlue](https://secdockblue.rubennati.at) |

## License

[Apache License 2.0](LICENSE)
