<div align="center">

# Secure Docker Blueprint

**Security-hardened Docker Compose patterns for self-hosted software — deploy, secure, operate, recover — for existing open-source projects and applications you build yourself.**

Hardened configurations for 80+ services — standardized security baseline, Docker Secrets, Traefik routing, CrowdSec integration, and network isolation out of the box. A reference pattern for software you build yourself does not exist yet — see [docs/architecture.md](docs/architecture.md#physical-layout-conceptual-domains-and-navigation-are-three-different-layers).

[![CI](https://github.com/rubennati/secure-docker-blueprint/actions/workflows/ci.yml/badge.svg)](https://github.com/rubennati/secure-docker-blueprint/actions/workflows/ci.yml)
[![Trivy](https://github.com/rubennati/secure-docker-blueprint/actions/workflows/trivy.yml/badge.svg)](https://github.com/rubennati/secure-docker-blueprint/actions/workflows/trivy.yml)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/rubennati/secure-docker-blueprint/badge)](https://scorecard.dev/viewer/?uri=github.com/rubennati/secure-docker-blueprint)
[![OpenSSF Best Practices](https://www.bestpractices.dev/projects/13091/badge)](https://www.bestpractices.dev/projects/13091)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-v0.9.1-blue)](CHANGELOG.md)

**[Architecture](docs/architecture.md) · [Standards](docs/standards/) · [Verified status](LIFECYCLE.md) · [SecDockBlue](https://secdockblue.rubennati.at)**

</div>

Run self-hosted software without getting the security details wrong each time. Every
stack shares one hardened baseline: credentials as Docker Secrets instead of environment
variables, datastores isolated on internal networks with no published port, pinned image
versions, memory and PID limits, and Traefik in front handling TLS and access control.

Quick Navigation: [Getting started](#getting-started) · [Repository layout](#repository-layout)

## Stacks

99 stacks in five categories. Each category below links to its full list.

| Browse | Stacks | Examples |
|---|---|---|
| [**`core/`** — proxy, identity, threat detection, secrets, Docker management](core/) | 19 | Traefik · Authentik · Keycloak · CrowdSec · Infisical · dnsmasq · Portainer |
| [**`apps/`** — general self-hosted applications](apps/) | 54 | Nextcloud · Immich · Paperless-ngx · Vaultwarden · Ollama · Windmill · Ghost · n8n · Mailpit |
| [**`business/`** — invoicing, project management, helpdesk, analytics, e-signature](business/) | 16 | Invoice Ninja · OpenProject · Vikunja · Zammad · Matomo · Documenso |
| [**`monitoring/`** — uptime, metrics, notifications](monitoring/) | 8 | Uptime Kuma · Gatus · Beszel · Healthchecks · ntfy · Langfuse |
| [**`backup/`** — this host outward, your devices inward](backup/) | 2 | Borgmatic · UrBackup |

Where several tools solve the same problem, more than one is included.

## Getting started

Traefik goes up first — every stack reachable over the network routes through it.
Each stack is then installed from its own README.

**Requirements:** Docker 24.0+ with Compose v2, a Linux host (tested on Debian 12/13),
`envsubst` (`gettext-base`), and a domain on a
[DNS provider Traefik supports](https://doc.traefik.io/traefik/https/acme/#providers).

```bash
git clone https://github.com/rubennati/secure-docker-blueprint.git
cd secure-docker-blueprint
git checkout "$(git tag --sort=-v:refname | head -n1)"   # the newest release
cd core/traefik
cp .env.example .env
```

Deploy from a tag rather than the default branch: `main` is where work lands between
releases, and the combination of stacks on it at any moment is not one anybody has
operated. [`docs/standards/deployment-lifecycle.md`](docs/standards/deployment-lifecycle.md)
covers the rest of the cycle — deployment order, updating the blueprint as against
updating an upstream image, rollback, and how a host states which release it runs.

Set `ACME_EMAIL`, `TRAEFIK_DASHBOARD_HOST`, and the DNS token for your certificate
resolver — `CF_DNS_API_TOKEN` ships as `__REPLACE_ME__`, and DNS-01 fails until it holds
a real token. [`core/traefik/README.md`](core/traefik/README.md#setup) documents every
variable.

```bash
bash ops/scripts/validate.sh    # required variables present
bash ops/scripts/render.sh      # .tmpl → config files
bash ops/scripts/validate.sh    # nothing left unresolved
docker compose up -d
```

The dashboard answers at `https://<TRAEFIK_DASHBOARD_HOST>`, over the VPN only by
default. Then pick a stack — [Vaultwarden](apps/vaultwarden/README.md) and
[Nextcloud](apps/nextcloud/README.md) are straightforward first ones. On a 403 or 404,
[TROUBLESHOOTING.md](TROUBLESHOOTING.md) maps the symptom to its cause.
`./scripts/overview.sh` lists what is configured and running.

## Repository layout

```text
core/         shared infrastructure and control plane
apps/         general self-hosted applications
business/     business applications
monitoring/   monitoring and observability
backup/       backup and recovery
development/  reusable patterns for software you build yourself
docs/         architecture and standards
scripts/      CI checks and the overview script
site/         SecDockBlue source
```

Each stack directory holds `docker-compose.yml`, `.env.example`, a `README.md` with the
setup procedure, and an `UPSTREAM.md` recording the pinned version and upgrade path.
[`apps/_reference/`](apps/_reference/) is the structure they all follow.

## Deploy → secure → operate → recover

Four phases, and the repository covers all of them:

- **Deploy** — one Compose shape across every stack, with every value that has to be set named in `.env.example`
- **Secure** — `no-new-privileges`, no direct Docker socket access, secrets as files, datastores unreachable from the host network, memory, PID and swap limits — checked on every pull request; capabilities dropped and a read-only root filesystem wherever the image allows it
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
