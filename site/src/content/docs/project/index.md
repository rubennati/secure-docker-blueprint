---
title: About this project
description: What SecDockBlue and Secure Docker Blueprint each are, what the compose defaults are set to, and how to report a security issue.
---

## Two names

**SecDockBlue** is this site — operator guidance, security knowledge, and the
material that holds whether or not you use any particular configuration file.

**Secure Docker Blueprint** is the repository it stands on: a set of Docker
Compose configurations for self-hosted services. Each service ships with a
reverse proxy setup, secrets handling, network layout and update policy already
written, so those decisions are not made per service. It remains the technical
source of truth — where a page here describes a configuration, the repository is
what it describes, and the repository wins on any disagreement.

The site is allowed to go further than the repository. The security section
does: it describes layers the Compose files do not touch, including some the
project deliberately leaves to you.

It is aimed at homelabs, self-hosted infrastructure and small-team production systems.

[GitHub repository →](https://github.com/rubennati/secure-docker-blueprint)

## The defaults

Set on every service, and checked on every change before it is merged:

- `no-new-privileges`, so a process inside the container cannot gain rights it was not started with. An exception has to record the reason, the alternatives that were weighed, and an explicit acceptance of the remaining risk
- No `privileged` container, and no service with the Docker socket mounted into it — the reverse proxy reads the API through a filtering proxy limited to containers, networks and events
- Databases and caches on `internal` networks, never published to the host
- Every image pinned to an exact version, never `:latest` and never a major-only tag such as `8` or `v2`

Applied wherever the image runs under it, which is not everywhere:

- `read_only` root filesystem, with tmpfs for the paths the image writes to
- `cap_drop: ALL`, adding back only the capabilities the image needs
- Credentials as Docker Secrets, mounted as files and read through `_FILE` variables or an entrypoint wrapper. Some images can only take a credential from the environment; those stacks keep it in a gitignored `.env`, and the stack's own documentation names the deviation and why it stands

Available to every service, switched on per stack:

- Traefik middleware for TLS, security headers, rate limiting and IP allowlisting, and CrowdSec as an added layer

The first group is enforced mechanically, so it holds for whatever is in the
repository. The second describes what the image allows, which differs per
service — each guide opens with the version it was written against, the date it
was verified where one exists, and a line naming what was not exercised. The
[FAQ](/faq/) explains how to read that.

[Security baseline →](https://github.com/rubennati/secure-docker-blueprint/blob/main/docs/standards/security-baseline.md)

## Limits

- The software inside the containers is not reviewed here. Images are pinned and configured; their code is the upstream project's responsibility.
- The host is out of scope. These files configure containers, not the machine they run on.
- For regulated or high-value environments, have the configuration reviewed before deploying it.

## Reporting a security issue

**Not as a public issue.** Use GitHub's private advisory form — the discussion
stays closed until a fix is released, so the report does not become an
advertisement for an unpatched problem.

[Report a vulnerability →](https://github.com/rubennati/secure-docker-blueprint/security/advisories/new)

Useful in a report: which stack and version, what you did, what happened, and
what you expected. A working reproduction is worth more than a severity rating.

Expect acknowledgement within 7 days and an assessment within 14. Machine-readable
contact details are at [`/.well-known/security.txt`](/.well-known/security.txt),
per RFC 9116.

## Reporting a problem with the documentation

Anything that is wrong, out of date or unclear on this site: a normal public
issue is the right place. Every page's footer has a link that opens one with the
page title and URL already filled in.

[Open a documentation issue →](https://github.com/rubennati/secure-docker-blueprint/issues/new)

Particularly worth reporting: a command that does not work as written, a claim a
cited source does not actually support, and a guide whose stated version no
longer matches what the repository pins.

## Contributing

Contributions are welcome. [CONTRIBUTING.md](https://github.com/rubennati/secure-docker-blueprint/blob/main/CONTRIBUTING.md)
covers the workflow, and [ROADMAP.md](https://github.com/rubennati/secure-docker-blueprint/blob/main/ROADMAP.md)
sets out what is planned.

## Licence

The repository's code — Compose files, scripts, configuration — is
[Apache 2.0](https://github.com/rubennati/secure-docker-blueprint/blob/main/LICENSE):
free to use, fork and modify with attribution.

**This site's text and diagrams are a separate question and not yet settled.**
A software licence does not extend to prose by default, and nothing here claims
one until it is chosen. See the [legal notice](/legal/).
