<div align="center">

# Secure Docker Blueprint

**Security-hardened Docker Compose patterns for self-hosted software — deploy, secure, operate, recover — for existing open-source projects and applications you build yourself.**

[![CI](https://github.com/rubennati/secure-docker-blueprint/actions/workflows/ci.yml/badge.svg)](https://github.com/rubennati/secure-docker-blueprint/actions/workflows/ci.yml)
[![Trivy](https://github.com/rubennati/secure-docker-blueprint/actions/workflows/trivy.yml/badge.svg)](https://github.com/rubennati/secure-docker-blueprint/actions/workflows/trivy.yml)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/rubennati/secure-docker-blueprint/badge)](https://scorecard.dev/viewer/?uri=github.com/rubennati/secure-docker-blueprint)
[![OpenSSF Best Practices](https://www.bestpractices.dev/projects/13091/badge)](https://www.bestpractices.dev/projects/13091)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-v0.9.0-blue)](CHANGELOG.md)
[![Status](https://img.shields.io/badge/status-pre--1.0-yellow)](ROADMAP.md)

</div>

> **Reading rather than deploying?** [SecDockBlue](https://secdockblue.rubennati.at) is the operator-facing site: guided documentation, and a security section that stands on its own. This repository stays the technical source of truth — the Compose files, the secrets handling, the defaults.

## What this is

Hardened Docker Compose stacks for 60+ self-hosted services, all following one
standard: Docker Secrets instead of environment variables, databases on internal
networks that publish no port, an explicit resource and swap policy per service,
pinned image versions, and Traefik in front with access policies and TLS profiles.

The problem it solves is that the hardening is the part nobody writes down. Getting
a service running is a `docker compose up`; getting it running without a database
reachable from the internet, a credential in a process listing, a container that can
take the host down, or a backup nobody has restored takes decisions that are the
same every time. They are made once here and enforced in CI.

Two kinds of software go through the same model: existing open-source projects with
a published image, and applications built here —
[`docs/standards/custom-application.md`](docs/standards/custom-application.md) covers
where a self-built image comes from and what pins it.

## Deploy → secure → operate → recover

The four phases are what a stack is judged against. All four exist for the
repository as a pattern; what has been established for any individual stack is in
[`LIFECYCLE.md`](LIFECYCLE.md).

| Phase | What it means here |
|---|---|
| **Deploy** | One Compose shape for every stack — [`apps/_reference/`](apps/_reference/) is the canonical structure, and `.env.example` names every value that has to be set before first start |
| **Secure** | A baseline enforced by CI, not documented and hoped for: no privilege escalation, no direct Docker socket, secrets as files, internal networks for datastores, capabilities dropped where the image allows it |
| **Operate** | Healthchecks, resource and swap limits, monitoring stacks, and per-stack `Last verified` evidence that a pin was actually run rather than only written |
| **Recover** | Borgmatic with database-aware dumps, restore playbooks per persistence pattern, and the position that a backup nobody restored is a hypothesis |

## Status

**Pre-1.0.** The structure is stable and the core services are ready to use, but
paths, environment variables and defaults can still change. v1.0 requires both this
repository and the operator site to be ready — see
[ROADMAP.md](ROADMAP.md#v10--complete-and-hand-off-ready).

Per-stack status is not summarised here, because a summary would be a third copy of
a fact each stack already owns. [`LIFECYCLE.md`](LIFECYCLE.md) is generated from the
stacks themselves and states, per stack, which version was verified and when, and
what has not been exercised.

## Architecture at a glance

One reverse proxy at the front, two networks per application, credentials as files,
access decided in one place. Five top-level categories, split by **how** a stack
accesses the system rather than by who uses it:

| Directory | Scope |
|---|---|
| [`core/`](core/) | Shared platform and control plane — capabilities scoped to the installation rather than one stack: Docker and host control, network, TLS, identity, DNS, security, secrets. Most are optional, and several are alternatives to each other |
| [`apps/`](apps/) | General-purpose applications, equally useful to a homelab and a company — including operator and diagnostic tooling |
| [`business/`](business/) | Applications that need a company to be useful — invoicing, helpdesk, newsletter, compliance |
| [`monitoring/`](monitoring/) | Observability — uptime, metrics, content changes, disk health |
| [`backup/`](backup/) | Backup in both directions: this host outward, your own devices inward. Separate because it needs privileged access and remote targets |

Only Traefik is close to unconditional. Everything else is opt-in, and the stacks
do not depend on each other unless a README says so.
[`docs/architecture.md`](docs/architecture.md) has the networking model, the
capability table, and why the categories are what they are.

## Start here

This reaches a working Traefik with TLS, which every networked stack routes through.
The application itself is installed from its own README — the steps differ per stack.

Requirements: Docker 24.0+ with Compose v2, a Linux host (tested on Debian 12/13),
`envsubst` (`gettext-base`), and a domain with a
[Traefik-supported DNS provider](https://doc.traefik.io/traefik/https/acme/#providers).

```bash
git clone https://github.com/rubennati/secure-docker-blueprint.git
cd secure-docker-blueprint/core/traefik
cp .env.example .env
```

Set `ACME_EMAIL`, `TRAEFIK_DASHBOARD_HOST` and the DNS provider token for your
certificate resolver — `CF_DNS_API_TOKEN` ships as `__REPLACE_ME__` and DNS-01
fails until it holds a real token.
[`core/traefik/README.md`](core/traefik/README.md#setup) lists every variable.

```bash
bash ops/scripts/validate.sh    # required variables present
bash ops/scripts/render.sh      # .tmpl → config files
bash ops/scripts/validate.sh    # nothing left unresolved
docker compose up -d
```

The dashboard answers at `https://<TRAEFIK_DASHBOARD_HOST>`, over the VPN only by
default. Then pick a stack and follow its README —
[Vaultwarden](apps/vaultwarden/README.md) and
[Nextcloud](apps/nextcloud/README.md) are good first ones. If something returns 403
or 404, [TROUBLESHOOTING.md](TROUBLESHOOTING.md) lists the symptom, the cause and the
fix. `./scripts/overview.sh` prints what is configured and running.

## Where to go next

| For | Read |
|---|---|
| Every stack, by category | [`core/`](core/) · [`apps/`](apps/) · [`business/`](business/) · [`monitoring/`](monitoring/) · [`backup/`](backup/) |
| What has actually been verified, per stack | [`LIFECYCLE.md`](LIFECYCLE.md) — generated |
| Why the system is shaped this way | [`docs/architecture.md`](docs/architecture.md) |
| The rules every stack follows | [`docs/standards/`](docs/standards/) — [security baseline](docs/standards/security-baseline.md), [compose](docs/standards/compose-structure.md), [env](docs/standards/env-structure.md), [secrets](docs/standards/secrets.md), [networking](docs/standards/networking.md), [Traefik labels](docs/standards/traefik-labels.md), [restore](docs/standards/restore.md) |
| Reporting a vulnerability | [SECURITY.md](SECURITY.md) |
| Adding a stack, or contributing | [CONTRIBUTING.md](CONTRIBUTING.md) and [`docs/standards/new-app-checklist.md`](docs/standards/new-app-checklist.md) |
| Keeping the repository consistent | [`docs/maintenance.md`](docs/maintenance.md) |
| What is planned, and what is out of scope | [ROADMAP.md](ROADMAP.md) |
| What has shipped | [CHANGELOG.md](CHANGELOG.md) |
| Operator-facing guides | [SecDockBlue](https://secdockblue.rubennati.at) |

## License

[Apache License 2.0](LICENSE)
