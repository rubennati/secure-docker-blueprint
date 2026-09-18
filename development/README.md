# Development

Where software this repository does not pull from a registry gets deployed —
code a contributor wrote, on its way through the same deploy → secure → operate
→ recover model every other stack follows. `development/` is not a sixth stack
category; it is a Supporting-tier directory, like `docs/` or `scripts/ci/`, that
holds reusable deployment patterns and is checked the same way a stack's compose
files are. [`docs/architecture.md`](../docs/architecture.md#development-is-a-supporting-tier-domain-not-a-sixth-category)
has the reasoning.

## What's here

Two patterns, each a complete, working deployment shape — not a product, and not
an app someone would run for its own sake.

| Pattern | Covers |
|---|---|
| [`static-site/`](static-site/) | A build step producing static files, served by a hardened, non-root nginx. Astro and Vite/React recipes — the build stage is the only part that differs between them. |
| [`web-api/`](web-api/) | A generic backend service: source → build → production image → health endpoint → Traefik. No database, queue or cache — those are added the same way [`apps/_reference`](../apps/_reference/) shows, once a real application needs one. |

Each pattern's own `README.md` covers adoption: copy the directory into `apps/`
or `business/` under the real project's name once the software exists, then
follow [`docs/standards/custom-application.md`](../docs/standards/custom-application.md)
for image identity and [`docs/standards/new-app-checklist.md`](../docs/standards/new-app-checklist.md)
for everything after the image.

## Local deployment validation

Every pattern ships a `docker-compose.local.yml` — the shape
[`compose-structure.md`](../docs/standards/compose-structure.md) defines for any
stack's local test mode: `127.0.0.1` ports, no Traefik, no Docker Secrets. It
proves the built image runs and answers its healthcheck before anything is
deployed behind Traefik.

Framework tooling — `npm run dev`, an IDE, a test runner — stays outside this
repository. What lands here is the production artifact and the compose shape
that validates and deploys it.

## Tools elsewhere in the blueprint

A developer working against this blueprint also reaches for stacks that already
exist under their normal category, not here:

| Tool | Category | For |
|---|---|---|
| [Mailpit](../apps/mailpit/) | `apps/` | Catches outgoing mail from a development stack instead of sending it |
| [Adminer](../apps/adminer/) | `apps/` | Browses a database without a client install |
| [IT-Tools](../apps/it-tools/) | `apps/` | Generators, converters and formatters used while developing |
| [Whoami](../apps/whoami/) | `apps/` | Confirms Traefik routing and TLS reach a container before the real app does |

## Planned

Not deployable here yet. See [`ROADMAP.md`](../ROADMAP.md) for status.

- **GreenMail** — SMTP/IMAP/POP3 test server for automated integration tests
- **Windmill** — script-first workflow automation for developers
