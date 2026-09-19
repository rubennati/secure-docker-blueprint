# Upstream Reference

## Source

- **Upstream GitHub:** https://github.com/shellhub-io/shellhub
- **Image registry:** `shellhubio/server`, `shellhubio/ui`, `shellhubio/gateway` (Docker Hub)
- **Docs:** https://docs.shellhub.io/
- **Self-host compose reference:** `docker-compose.yml` +
  `docker-compose.postgres.yml` in the upstream repo
- **License:** Apache-2.0 (Community Edition; a `.env.enterprise` file in
  the upstream repo gates a separate Enterprise/Cloud tier — SAML SSO
  confirmed Enterprise-only, see README.md)
- **Origin:** Brazil · O.S. Systems · non-EU
- **Domain:** Identity, access and secrets
- **Role:** SSH access through agents on each target that connect out, so targets open no inbound port
- **Based on version:** `v0.27.0-rc.11` (server, ui, gateway)
- **Verification snapshot:** 2026-09-19 — full stack started clean, healthchecks
  passing; no agent registered, no SSH session exercised

## What we use

- `shellhubio/server`, `shellhubio/ui`, `shellhubio/gateway`, all at the
  same version, matching upstream's single-`${SHELLHUB_VERSION}` model
- `postgres:18.0` and `valkey/valkey:9.1-alpine` — the exact versions
  upstream's own `docker-compose.postgres.yml` and `docker-compose.yml` pin

## What we changed vs. upstream compose

| Change | Reason |
|--------|--------|
| `server` pinned to a release candidate, not a stable tag | Verified: `shellhubio/server` currently publishes only `v0.27.0-rc.*` tags on Docker Hub — no stable tag exists. `ui`/`gateway` do have a stable `v0.26.0`, but mixing an old UI with a newer core risks an unverified API mismatch, so all three are pinned to the same RC instead. See "Known limitations" |
| Postgres mounted at `/var/lib/postgresql`, not `.../data` | Verified against a live container: Postgres 18 changed its expected layout to a single mount with a version-named subdirectory underneath; the `.../data` path every other Postgres 16 stack in this repository uses fails outright on 18 |
| `cap_add: SETUID, SETGID` on Valkey | Verified against a live container: its entrypoint drops from root via `setpriv`, which fails without these — the same failure mode `apps/_reference` documents for Postgres/Redis |
| `SHELLHUB_PROXY=true` + `SHELLHUB_PROXY_TRUSTED_IPS` set, `SHELLHUB_AUTO_SSL=false` | Puts Traefik in front instead of the gateway's own ACME client — both are real upstream env vars for exactly this |
| SSH rendezvous port moved from upstream's default 22 to 2222 | Avoids colliding with the host's own SSH daemon |
| Docker Secrets for the SSH host key and API keypair | Native upstream support, verified in the official compose (`PRIVATE_KEY`/`PUBLIC_KEY`/`SSH_HOST_KEY_FILE` already point at `/run/secrets/*`) |
| Plain env var for the Postgres password on the `server`/`gateway` side | Verified: `SHELLHUB_POSTGRES_PASSWORD` has no `_FILE` alternative upstream, even though Postgres itself does — the database side uses `POSTGRES_PASSWORD_FILE`, the consuming side cannot |

## What was actually verified, and how

- `docker inspect` on all three images — `server`/`gateway` run as root by
  image default with a minimal entrypoint (`/server server`, `/gateway`);
  `ui` and `gateway` are Alpine-based with `curl`/`wget`/`nc`; `server` is
  Alpine-based with the same tools.
- Full stack (`db`, `valkey`, `server`, `ui`, `gateway`) started together
  under this compose file's exact hardening — `cap_drop: ALL` everywhere,
  `read_only: true` on `valkey`/`server`/`ui`/`gateway`, `cap_add` only
  where a live failure demanded it. All five reached a healthy state.
- Healthchecks are upstream's own, taken directly from its compose file —
  not invented for this deployment.
- **Not verified:** registering and connecting a real ShellHub agent, an
  actual SSH session through the server, the web UI login flow, OIDC/SAML
  against Authentik or Keycloak (SAML confirmed Enterprise-only; OIDC in
  Community Edition not confirmed either way), backup/restore, or behavior
  across a restart or upgrade.

## Upgrade checklist

1. Watch [ShellHub releases](https://github.com/shellhub-io/shellhub/releases)
   for the first stable `v0.27.0` tag — move off the release candidate as
   soon as one exists: https://hub.docker.com/r/shellhubio/server/tags
2. Read the changelog for breaking changes
3. Back up `./volumes/postgres` before upgrading
4. Bump `SHELLHUB_VERSION` in `.env` (all three images share it)
5. `docker compose pull && docker compose up -d`
6. Confirm `docker compose ps` shows all five services healthy

## Known limitations

- **No stable `server` tag exists at time of writing.** This is the
  single largest upstream risk in this stack — verify
  https://hub.docker.com/r/shellhubio/server/tags before every deploy and
  move to a stable release the moment one is published.
- **SAML SSO confirmed Enterprise-only.** OIDC support in Community
  Edition was not confirmed either way in available documentation —
  verify directly against a running instance before assuming it works.
- **Agent-based architecture means this stack alone proves nothing about
  reaching a real target** — a ShellHub agent has to be installed on each
  machine you want to reach, which is out of this repository's scope the
  same way a Beszel agent on a remote host is.
- **No `_FILE` support for the database password on the consuming side** —
  mitigated only by keeping `.env` out of git.
