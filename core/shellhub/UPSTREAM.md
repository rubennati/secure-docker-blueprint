# Upstream Reference

- **Last verified:** 2026-11-09 (v0.29.3) — over IPv4, a new installation: all five services healthy, the UI served through Traefik before and after `down`/`up`, the refused client answered `403`, and the SSH port 2222 answered with its banner and host key from another machine on the LAN; no agent enrolled (docs/labs/stack-refresh/2026-11-08-results.md)

## Source

- **Upstream GitHub:** https://github.com/shellhub-io/shellhub
- **Image registry:** `shellhubio/server`, `shellhubio/ui` (Docker Hub; `shellhubio/gateway` up to v0.29.x)
- **Docs:** https://docs.shellhub.io/
- **Self-host compose reference:** `docker-compose.yml` +
  `docker-compose.postgres.yml` in the upstream repo
- **License:** Apache-2.0 (Community Edition; a `.env.enterprise` file in
  the upstream repo gates a separate Enterprise/Cloud tier — SAML SSO
  confirmed Enterprise-only, see README.md)
- **Decision facts checked:** not yet
- **Origin:** Brazil · O.S. Systems · non-EU
- **Domain:** Identity, access and secrets
- **Role:** SSH access through agents on each target that connect out, so targets open no inbound port
- **Verification snapshot:** 2026-09-19 — full stack started clean, healthchecks
  passing; no agent registered, no SSH session exercised

## What we use

- `shellhubio/server` (with the embedded gateway since v0.30.0) and
  `shellhubio/ui`, both at the same version, matching upstream's single-`${SHELLHUB_VERSION}` model
- `postgres:18.7` and `valkey/valkey:9.1.4-alpine`. Upstream's own
  `docker-compose.postgres.yml` still pins `postgres:18.0`; this stack runs the
  newest 18.x patch release instead (see Version notes)

## What we changed vs. upstream compose

| Change | Reason |
|--------|--------|
| `SHELLHUB_TELEMETRY=false` on `server` | Since v0.28.0 the server sends a start event and a daily usage report to `telemetry.shellhub.io` by default; a self-hosted access tool should not call out unasked |
| Postgres mounted at `/var/lib/postgresql`, not `.../data` | Verified against a live container: Postgres 18 changed its expected layout to a single mount with a version-named subdirectory underneath; the `.../data` path every other Postgres 16 stack in this repository uses fails outright on 18 |
| `cap_add: SETUID, SETGID` on Valkey | Verified against a live container: its entrypoint drops from root via `setpriv`, which fails without these — the same failure mode `apps/_reference` documents for Postgres/Redis |
| Service key `shellhub-server`, Traefik labels on its port 80, no host publish of 80/443, `SHELLHUB_AUTO_SSL=false` | Traefik terminates TLS and fronts the embedded gateway instead of the gateway's own ACME client and published ports |
| `SHELLHUB_PROXY=false`, `SHELLHUB_PROXY_TRUSTED_IPS` set to the Docker address pools | `SHELLHUB_PROXY` turns on the PROXY protocol, which Traefik does not send; the trusted list lets the Traefik hop name the client in `X-Forwarded-For` (tested: a forwarded address from a trusted hop is the recorded client, `X-Real-IP` is ignored) |
| `XDG_DATA_HOME=/data`, `XDG_CONFIG_HOME=/tmp` on `shellhub-server` | Verified: under `read_only: true` the embedded Caddy cannot create `/root/.local` and `/root/.config` (config autosave error, no instance ID) |
| SSH rendezvous port moved from upstream's default 22 to 2222 | Avoids colliding with the host's own SSH daemon |
| Docker Secrets for the SSH host key and API keypair | Native upstream support, verified in the official compose (`PRIVATE_KEY`/`PUBLIC_KEY`/`SSH_HOST_KEY_FILE` already point at `/run/secrets/*`) |
| Plain env var for the Postgres password on the `server` side | Verified: `SHELLHUB_POSTGRES_PASSWORD` has no `_FILE` alternative upstream, even though Postgres itself does — the database side uses `POSTGRES_PASSWORD_FILE`, the consuming side cannot |

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

## Version notes

- Moved from `v0.27.0-rc.11` to `v0.29.3` on 2026-11-05. The first stable tags after the release candidate; server, ui and
  gateway move together. Changes that matter for this stack:
  v0.27.0 removes the namespace-wide device auto-accept (replaced by
  provisioning keys), the pre-authorized pairing code (`SHELLHUB_PAIRING_CODE`
  on the agent), `SHELLHUB_RECORD_URL` and the
  `SHELLHUB_INTERNAL_HTTP_CLIENT_*` variables, and renames
  `SHELLHUB_REQUIRE_VERIFIED_DEVICE_KEY` to
  `SHELLHUB_NAMESPACE_REQUIRE_VERIFIED_DEVICE_KEY`; this stack sets none of
  them. A Community instance now binds to a single namespace; existing
  namespaces stay in legacy mode until an owner upgrades them, once and for
  good. v0.28.0 adds usage telemetry, on by default, through a migration that
  stores the setting; this stack sets `SHELLHUB_TELEMETRY=false` on the server
  so the instance never reaches the collector. Migrations on the way: v0.29.0
  adds `users.onboarding_survey`, v0.29.2 (`054`) drops the creator column from
  API and provisioning keys, v0.29.3 adds an index on devices (`055`, built
  concurrently) and keeps only the newest pending invitation per user and
  namespace (`056`). Back up `./volumes/postgres` before the first start.
  Agents older than v0.29.2 still connect, but only v0.29.2 and later get the
  EOF fix. Source: https://github.com/shellhub-io/shellhub/releases

- `DB_TAG` moved from `18.0` to `18.6` on 2026-11-05. A patch release within 18: no dump and restore (18.5 was never
  released). Manual items from the 18.2 and 18.6 release notes, none expected to
  apply to ShellHub's schema: reindex `ltree` indexes; only `pgoutput` and
  `test_decoding` are allowed as logical decoding plugins; pgcrypto refuses
  ciphers OpenSSL rejects; check `reltuples` after parallel GIN index builds;
  reindex `btree_gist` indexes on float and bit columns. Fixes CVE-2026-2003 to
  CVE-2026-2007 (18.2) and 28 CVEs in 18.6, among them CVE-2026-6471,
  CVE-2026-14663 and CVE-2026-6464 — the full list is in
  https://www.postgresql.org/docs/release/18.6/.

- `VALKEY_TAG` is pinned to `9.1.3-alpine` on 2026-11-05; until then it followed the floating `9.1-alpine`, which now points
  at the same 9.1.3 build. The image the scan had pulled under the floating tag
  carried OpenSSL 3.5.4 (CVE-2026-31789); the 9.1.3 build, on Alpine 3.24.3,
  ships the fixed one.
  CRITICAL findings 1 -> 0. Valkey 9.1.3 is a patch release; no configuration
  change. 9.2 exists only as a release candidate.
  Source: https://github.com/valkey-io/valkey/releases/tag/9.1.3

- Moved from `v0.29.3` to `v0.31.1` on 2026-11-23 (v0.30.0 released 2026-11-09,
  v0.31.0 and v0.31.1 on 2026-11-19). Advisories: GHSA-wp29-95m3-w5pc (medium,
  fixed in v0.30.0) — cross-namespace authorization bypass that let a user invite
  members into a namespace they do not administer. v0.31.0 carries the fixes of
  the November audit without advisory IDs: `ssh -o SetEnv=…` values are no longer
  stored in session events (a migration deletes the stored `env` events, scanning
  `session_events` once on start), `GET /sessions/{uid}` returns exec commands only to
  administrators and owners, email changes need the password, wrong passwords in
  web-terminal re-authentication and `PATCH /api/users` count toward the lockout,
  the console refuses framing, SFTP refuses accounts with a restricted login shell,
  and SSH key approval writes the key only after the terminal code matches.
  `PATCH /api/users/{id}/password` is removed (use `PATCH /api/users` with
  `password` and `current_password`). Breaking changes and what they mean here:
  v0.30.0 moves the gateway into the server process — the `gateway` service is
  gone, and the server, now on the shared Traefik network, is the service
  `shellhub-server` (container name unchanged); it serves the web UI and API on its port 80 (Traefik's target now)
  and keeps the gateway's state in `/data` (`./volumes/gateway`); with
  `SHELLHUB_AUTO_SSL=false` there is no certificate store to carry over. The
  forwarded client address is trusted only from `SHELLHUB_PROXY_TRUSTED_IPS`,
  whose upstream default changed from everyone to empty; `SHELLHUB_PROXY` means
  the PROXY protocol on the gateway's listener and is now `false` here, since
  Traefik does not send it. v0.31.0 reads only `X-Forwarded-For` (right to left,
  first hop outside the trusted list), not `X-Real-IP` — Traefik appends the client
  to `X-Forwarded-For`; `SHELLHUB_BIND_ADDRESS` now defaults to every address,
  IPv6 included, but this stack does not use it and publishes only the SSH port
  on `SHELLHUB_BIND`; agents v0.31.0 and later refuse a plain `http://` server
  address unless `SHELLHUB_ALLOW_INSECURE_SERVER=true` — agents of this stack
  reach the server through Traefik over `https://`, and a Docker agent that
  updated itself to v0.31.0 on `http://` stays in a restart loop until its
  container is recreated (v0.31.1 carries the setting over on self-update).
  Upgrade on an existing host: back up `./volumes/postgres`; in `.env` set
  `SHELLHUB_PROXY=false` and `SHELLHUB_PROXY_TRUSTED_IPS="172.16.0.0/12
  192.168.0.0/16"` (or the edge network's subnet) and drop
  `CONTAINER_NAME_GATEWAY`; `mkdir -p volumes/gateway && sudo chown 0:0
  volumes/gateway`; `docker compose down --remove-orphans` removes the old
  `server` and gateway containers, then `docker compose up -d`. Tested on a v0.29.3 data set (user and namespace kept,
  migrations completed, console and API through the server's port 80, only the SSH
  port published). The images are published for amd64 only. Sources:
  https://github.com/shellhub-io/shellhub/releases/tag/v0.30.0,
  https://github.com/shellhub-io/shellhub/releases/tag/v0.31.0,
  https://github.com/shellhub-io/shellhub/releases/tag/v0.31.1,
  https://github.com/shellhub-io/shellhub/security/advisories,
  https://docs.shellhub.io/selfhosted/upgrade

## Upgrade checklist

1. Check [ShellHub releases](https://github.com/shellhub-io/shellhub/releases)
   for a newer stable tag; skip release candidates
2. Read the "Upgrading?" notes of every release on the way
3. Back up `./volumes/postgres` before upgrading
4. Bump `SHELLHUB_VERSION` in `.env` (all three images share it)
5. `docker compose pull && docker compose up -d`
6. Confirm `docker compose ps` shows all five services healthy

## Known limitations

- **Fast release pace.** Upstream shipped v0.27.0 to v0.29.3 within two
  weeks, each with schema migrations. Read the "Upgrading?" notes before
  every move and back up the database first.
- **SAML SSO confirmed Enterprise-only.** OIDC support in Community
  Edition was not confirmed either way in available documentation —
  verify directly against a running instance before assuming it works.
- **Agent-based architecture means this stack alone proves nothing about
  reaching a real target** — a ShellHub agent has to be installed on each
  machine you want to reach, which is out of this repository's scope the
  same way a Beszel agent on a remote host is.
- **No `_FILE` support for the database password on the consuming side** —
  mitigated only by keeping `.env` out of git.
