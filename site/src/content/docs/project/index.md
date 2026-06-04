---
title: Project
description: About Secure Docker Blueprint — goals, license, governance, and contributing.
---

## About

Secure Docker Blueprint is a collection of security-focused Docker Compose configurations for self-hosted infrastructure. The goal is to make hardened, production-ready setups accessible without requiring deep expertise in each service.

## Design principles

- **Repository as source of truth** — compose files, secrets handling, and implementation details live in the repository. This site is the operator-facing view.
- **Opinionated but documented** — defaults are chosen deliberately and trade-offs are explained.
- **Opt-in security layers** — CrowdSec geoblocking, AppSec, SSH detection, and Authentik forward auth are opt-in with documented consequences, not forced defaults.
- **No undocumented deviations** — when an app cannot use Docker Secrets, this is noted explicitly.

## License

[Apache 2.0](https://github.com/rubennati/secure-docker-blueprint/blob/main/LICENSE) — free to use, fork, and modify with attribution.

## Contributing

See [CONTRIBUTING.md](https://github.com/rubennati/secure-docker-blueprint/blob/main/CONTRIBUTING.md) in the repository.

## Roadmap

See [ROADMAP.md](https://github.com/rubennati/secure-docker-blueprint/blob/main/ROADMAP.md) for the planned milestones toward v1.0.
