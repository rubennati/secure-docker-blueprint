---
title: Project
description: What Secure Docker Blueprint is, what its defaults are set to, and how to report a security issue.
---

Secure Docker Blueprint is a set of Docker Compose configurations for self-hosted services. Each service ships with a reverse proxy setup, secrets handling, network layout and update policy already written, so those decisions are not made per service.

It is aimed at homelabs, self-hosted infrastructure and small-team production systems.

[GitHub repository →](https://github.com/rubennati/secure-docker-blueprint)

## The defaults

What the compose files are set to, across services:

- `cap_drop: ALL` and `no-new-privileges`, plus `read_only` where the image runs under it
- Credentials as Docker Secrets — mounted as files, read via `_FILE` variables or an entrypoint wrapper, not set in `environment:`
- Databases and backends on `internal` networks; Traefik is the only service published to the host
- Every image on a pinned version tag, never `:latest`
- Traefik middleware for TLS, security headers, rate limiting and IP allowlisting; CrowdSec available as an added layer

Whether a given service holds all of this is what its status label says. What each label means, and how far each service has come, is in the [FAQ](/faq/).

[Security baseline →](https://github.com/rubennati/secure-docker-blueprint/blob/main/docs/standards/security-baseline.md)

## Limits

- The software inside the containers is not reviewed here. Images are pinned and configured; their code is the upstream project's responsibility.
- The host is out of scope. These files configure containers, not the machine they run on.
- For regulated or high-value environments, have the configuration reviewed before deploying it.

## Reporting a security issue

Please do not open a public issue for a vulnerability. Use GitHub's private advisory form — the discussion stays closed until a fix is released.

[Report a vulnerability →](https://github.com/rubennati/secure-docker-blueprint/security/advisories/new)

Expect acknowledgement within 7 days and an assessment within 14. Machine-readable contact details are at [`/.well-known/security.txt`](/.well-known/security.txt).

## License and contributing

[Apache 2.0](https://github.com/rubennati/secure-docker-blueprint/blob/main/LICENSE) — free to use, fork and modify with attribution.

Contributions are welcome. [CONTRIBUTING.md](https://github.com/rubennati/secure-docker-blueprint/blob/main/CONTRIBUTING.md) covers the workflow, and [ROADMAP.md](https://github.com/rubennati/secure-docker-blueprint/blob/main/ROADMAP.md) sets out what is planned.
