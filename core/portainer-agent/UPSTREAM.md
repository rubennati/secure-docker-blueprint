# Upstream Reference

## Source

- **Project:** Portainer Agent
- **Repo:** https://github.com/portainer/agent
- **Docker Hub:** https://hub.docker.com/r/portainer/agent
- **License:** zlib (https://github.com/portainer/agent/blob/develop/LICENSE)
- **Origin:** Portainer Ltd — official agent for the Portainer management platform
- **Last verified:** 2026-05-05 (v2.39.1)

## What we changed and why

| Change | Reason |
|---|---|
| Edge Mode as default | No inbound port needed — works behind NAT, firewalls, Tailscale. Classic mode documented as alternative in compose comments. |
| Direct Docker socket mount | Portainer Agent requires broad Docker API access (containers, volumes, networks, images, exec, build). A filtered socket proxy would need to allow nearly everything — direct mount is the upstream-recommended and only supported approach. Documented exception in `scripts/ci/check-baseline.py`. |
| `/:/host:ro` bind mount | Required for Portainer to display host volume paths and browse container filesystems in the UI. Read-only. |

## Version alignment

The `APP_TAG` in `.env.example` must stay in sync with the major version of
the central `portainer/portainer-ce` instance (`core/portainer/`).
Portainer CE and the Agent are versioned together — a major mismatch causes
connection failures.

## Upgrade checklist

1. Check [Portainer Agent releases](https://github.com/portainer/agent/releases)
2. Match the version to the central Portainer CE instance
3. Bump `APP_TAG` in `.env` on all remote hosts running this agent
4. `docker compose pull && docker compose up -d`
5. Verify agent appears as connected in Portainer UI → Environments
