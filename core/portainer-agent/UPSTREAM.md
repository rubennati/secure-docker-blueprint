# Upstream Reference

## Source

- **Project:** Portainer Agent
- **Repo:** https://github.com/portainer/agent
- **Releases:** https://github.com/portainer/portainer/releases — the agent's versions follow Portainer's; its own repository has published no release since 2020
- **Docker Hub:** https://hub.docker.com/r/portainer/agent
- **License:** zlib (https://github.com/portainer/agent/blob/develop/LICENSE)
- **Decision facts checked:** not yet
- **Origin:** New Zealand · Portainer.io Ltd · non-EU (official agent for the Portainer platform)
- **Domain:** Infrastructure
- **Role:** Remote Docker agent for Portainer
- **Last verified:** 2026-11-08 (2.45.3) — the Edge agent on a remote Docker host, managed from Portainer 2.45.3: connected through the tunnel on port 8000 after the Edge identifier was associated, containers listed, created, started, logged, stopped and removed, reconnected by itself after Portainer's `down`/`up`; no port published on the agent host (docs/labs/stack-refresh/2026-11-08-results.md)

## What we changed and why

| Change | Reason |
|---|---|
| Edge Mode as default | No inbound port needed — works behind NAT, firewalls, Tailscale. Classic mode documented as alternative in compose comments. |
| Direct Docker socket mount | Portainer Agent requires broad Docker API access (containers, volumes, networks, images, exec, build). A filtered socket proxy would need to allow nearly everything — direct mount is the upstream-recommended and only supported approach. Documented exception in `scripts/ci/check-baseline.py`. |
| `/:/host:ro` bind mount | **Commented out.** Upstream marks it optional — the agent runs without it, and it is needed only for Portainer's host-management views. It grants read access to every file on the host, `.env` and `.secrets/` of every stack included. Uncomment deliberately if you use those views. |

## Version alignment

The `APP_TAG` in `.env.example` must stay in sync with the major version of
the central `portainer/portainer-ce` instance (`core/portainer/`).
Portainer CE and the Agent are versioned together — a major mismatch causes
connection failures.

## Version notes

- Moved `portainer/agent` to `2.45.3` on 2026-11-05, together with the central
  `portainer/portainer-ce` in `core/portainer/`. The
  automatic proposal `3.0.1` was not taken: Docker Hub carries agent tags `3.0.0` and
  `3.0.1` under the `sts` tag, but there is no Portainer CE 3.x release or image to
  pair them with (the newest server release is 2.45.3 LTS, 2026-10-21), and this
  stack keeps the agent on the server's version. Changes for agents in the range:
  2.45.3 fixes starting a container with an empty request body on agent
  environments and agent version detection on Docker engines newer than API 1.47;
  2.45.2 enforces TLS verification of in-cluster Kubernetes API connections on the
  agent. No compose change. Sources:
  https://github.com/portainer/portainer/releases/tag/2.45.3,
  https://github.com/portainer/portainer/releases/tag/2.45.2

## Upgrade checklist

1. Check [Portainer Agent releases](https://github.com/portainer/agent/releases)
2. Match the version to the central Portainer CE instance
3. Bump `APP_TAG` in `.env` on all remote hosts running this agent
4. `docker compose pull && docker compose up -d`
5. Verify agent appears as connected in Portainer UI → Environments
