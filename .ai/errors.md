# Recurring Failure Patterns

Patterns that have cost time more than once, condensed from `docs/bugfixes/`. Each
individual incident keeps its own document; this file is the index of what tends to
go wrong so it can be avoided rather than rediscovered.

## Image and tag

- **A tag that does not exist.** Verify on the registry before pinning — several
  apps were pinned to versions upstream never published.
- **Rolling tags that move.** `latest`, `main`, `2.5.x`, bare majors. Pin the digest
  where upstream publishes no exact version, and re-resolve it on every upgrade.
- **Assuming a tool is in the image.** A healthcheck using `curl` fails silently
  when the image ships only `wget`, or neither. Check first:
  `docker run --rm <image> which curl wget`.

## Secrets

- **Trailing newline in a secret file.** `openssl rand … > file` writes one;
  services that trim it and services that do not will disagree about the password.
  Always `| tr -d '\n'`.
- **Special characters in URL-embedded passwords.** Base64 output contains `/`, `+`
  and `=`, which break connection-string parsers. Use hex for anything that lands
  in a URL, and URL-encode in the entrypoint.
- **No `_FILE` support.** Many images cannot read a secret from a file. The pattern
  is an entrypoint wrapper that reads `/run/secrets/` and execs the original
  command — never a password in `environment:`.

## Container runtime

- **`user:` with an s6-overlay or supervisord image.** The init system must start as
  root and drop privileges itself. Setting `user:` breaks startup. Use the image's
  own UID/GID variables.
- **Read-only filesystem without tmpfs.** Anything the application writes at runtime
  needs an explicit tmpfs mount, or it fails in ways that look unrelated.

## Traefik and routing

- **Missing `@file` suffix** on middleware and TLS options defined in the file
  provider — the reference silently does not resolve.
- **Router priority** — a path-scoped router needs a higher priority than the
  catch-all router for the same host, or it never matches.
- **Code-split single-page applications** fire many parallel requests on first load
  and exhaust a normal rate limit. They need a dedicated limit, or a split router
  for static assets.
- **HTTP URLs behind a TLS-terminating proxy** — applications that generate absolute
  URLs need `X-Forwarded-Proto`, or they redirect in a loop.
- **Loopback and split-DNS traps** — an access policy based on source IP behaves
  differently for requests that leave and re-enter the host.

## Databases

- **File-level copies of a running database** can capture a torn state. The backup
  reports success and the problem appears at restore. Always dump.
- **Aborted connections under load** — a database container with default limits and
  a connection-heavy application produces intermittent, hard-to-attribute failures.
- **Redis persistence across a major upgrade.** An RDB file written by an older
  Redis is not read by a newer major version; the container starts and the cache is
  silently empty, or it refuses to start. Plan `docker compose down --volumes` for
  the cache volume as part of a Redis major bump — and make sure that volume really
  holds only cache.

## Process

- **Many changes at once.** A single broken line looks like everything is broken.
  Phases with verification between them exist for this reason.
- **A hook that fails quietly.** A dump command that errors while the backup
  continues produces an archive that looks complete and restores nothing.
- **Documentation deferred.** The reasons that are obvious while writing are gone
  two weeks later. Same change set, not later.
