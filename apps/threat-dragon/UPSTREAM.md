# Upstream Reference

## Source

- **Image:** https://hub.docker.com/r/owasp/threat-dragon
- **GitHub:** https://github.com/OWASP/threat-dragon
- **Docs:** in-repo `docs/`, published at the project's GitHub Pages site
- **License:** Apache-2.0
- **Decision facts checked:** not yet
- **Origin:** United States · OWASP Foundation (nonprofit) · non-EU
- **Domain:** Security operations
- **Role:** Threat modelling: data-flow diagrams, trust boundaries, threats and mitigations
- **Based on version:** `v2.6.2`
- **Verification snapshot:** 2026-09-19 — local Compose stack booted and
  exercised with real Docker Secrets (see README.md's Preview → Ready gate);
  not yet run behind a real Traefik host

## What we use

- `owasp/threat-dragon:v2.6.2` — single stateless container, no database

## The built-in healthcheck is broken in this release

Verified directly against a live container, not assumed from the Dockerfile:
the image's baked-in `HEALTHCHECK` runs
`/nodejs/bin/node ./td.server/dist/healthcheck.js`, but `/nodejs/bin/node`
does not exist in the image — the actual binary is at
`/usr/local/bin/node` (confirmed via `docker inspect` and `which node`
inside the container). Correcting the path alone still fails: the health
check script itself has a bundling defect —
`require('env/Env.js')` inside `healthcheck.js` is missing the `./` prefix
that would make it a relative import, so Node treats it as a bare package
name and fails with `MODULE_NOT_FOUND` even when invoked with the right
binary path. Both issues were confirmed independently with
`docker exec`.

This stack's `healthcheck:` block does not use the image's baked-in check at
all — it uses a plain HTTP probe against the app's own port (the same
`node -e "require('http')..."` pattern this repository already uses for
`core/infisical`), confirmed to return exit 0 against a running container.

## What we changed vs. upstream

| Change | Reason |
|--------|--------|
| Custom `healthcheck:` overriding the image's baked-in one | See above — the built-in check does not work at all in this release |
| `read_only: true` + `cap_drop: ALL` with **no** `cap_add` | Verified against a live container — the image already runs as a fixed non-root user (Node's standard `node` user) with no root-start entrypoint, and the app is stateless |
| `SERVER_API_PROTOCOL: https` | This stack sits behind Traefik's TLS termination |
| No Git-provider OAuth configured | Deliberate — see README.md. Local-storage mode needs none of it |

## What was actually verified, and how

- `docker inspect owasp/threat-dragon:v2.6.2` — confirmed `User: "node"`,
  `ExposedPorts: null` (no `EXPOSE` in this build, matches `SERVER_API_PROTOCOL`-driven config rather than a fixed port declaration), and the broken
  `Healthcheck` described above.
- Read `td.server/src/env/Env.js` at the `main` branch directly (the
  generic env-provider base class every config category — Encryption,
  Github, Gitlab, Bitbucket, Google — extends) to confirm `_FILE` support is
  a real, generic mechanism (`tryReadFromFile`), not specific to one
  variable.
- Ran the full production Compose file with three real Docker Secrets
  (`ENCRYPTION_KEYS_FILE`, `ENCRYPTION_JWT_SIGNING_KEY_FILE`,
  `ENCRYPTION_JWT_REFRESH_SIGNING_KEY_FILE`) under
  `--cap-drop=ALL --security-opt=no-new-privileges:true --read-only`: started
  cleanly with zero capabilities re-added, `Express server listening at ::
  on port 3000`, and a `GET /` returned 302 (a redirect to the SPA, not an
  error).
- Observed one non-fatal upstream warning in the logs on every start:
  `ERR_ERL_PERMISSIVE_TRUST_PROXY` from `express-rate-limit`, stating the
  app's Express `trust proxy` setting is permissive (trusts
  `X-Forwarded-For` from any hop). The app does not crash and continues
  serving. No environment variable to narrow this was found in the env
  providers read above — see Known limitations.
- **Not verified:** a threat model actually created and saved (local-storage
  or Git-backed), any of the three Git-provider OAuth integrations,
  TLS/Traefik behind a real domain, or behavior across a restart.

## Upgrade checklist

1. Watch [Threat Dragon releases](https://github.com/OWASP/threat-dragon/releases)
2. Read the changelog — this is an actively developed OWASP flagship
   project with frequent releases
3. Nothing to back up in the default local-storage mode — see README.md#backup
4. Bump `APP_TAG` in `.env`
5. `docker compose pull && docker compose up -d`
6. Confirm the healthcheck passes and re-check whether the built-in
   healthcheck has been fixed upstream — if so, the override in this
   stack's compose file can likely be removed

## Known limitations

- **The image's own baked-in `HEALTHCHECK` is broken** — see above. Watch
  upstream releases for a fix; until then this stack supplies its own.
- **`ERR_ERL_PERMISSIVE_TRUST_PROXY` warning on every start** — Express's
  `trust proxy` setting accepts `X-Forwarded-For` from any hop. Not exploitable
  in this deployment shape, where Traefik on `proxy-public` is the only path
  in and the container has no host-published port; would matter if this
  container were ever reachable a different way.
- **Git-provider OAuth (GitHub/GitLab/Bitbucket/Google) is not configured or
  exercised** — see README.md.
- **Not yet run behind a real Traefik host or TLS.**
