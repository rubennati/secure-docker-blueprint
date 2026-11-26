# Upstream Reference

- **Last verified:** 2026-11-08 (1.4.0) — over IPv4: the app wrote its SSH host key and served `/health` through the route before and after `down`/`up`, the refused client answered `403`; no session recorded (docs/labs/stack-refresh/2026-11-08-results.md)

## Source

- **Upstream GitHub:** https://github.com/orion-belt-dev/orion-belt
- **Image registry:** `ghcr.io/orion-belt-dev/orion-belt-server`,
  `ghcr.io/orion-belt-dev/orion-belt-agent` (GHCR)
- **Self-host compose reference:** `docker-compose.prod.yml` and
  `docker-compose.prod.agent.yml` in the upstream repo
- **License:** AGPL-3.0
- **Use restrictions:** none for self-hosting; since 1.5.0 the project is licensed AGPL-3.0-only, and distributing it or offering a modified version over a network requires publishing the source under the same licence — https://github.com/orion-belt-dev/orion-belt/blob/master/LICENSE · checked 2026-11-23
- **Decision facts checked:** 2026-09-21
- **Origin:** Individual maintainer · Mohamed Zrouga · no single jurisdiction
- **Domain:** Identity, access and secrets
- **Role:** Privileged access gateway for SSH sessions, from a young single-maintainer project
- **Verification snapshot:** 2026-09-19 — clean start and hardening only, see below

## EXPERIMENTAL — project maturity, verified directly

This is the youngest and smallest of the five PAM/bastion candidates
evaluated together with this one, by a wide margin. Verified via the
GitHub API, not estimated:

- Repository created **2026-01-01**; ten releases between 2026-07-11 and
  2026-07-31, then none since (as of 2026-09-19) despite commits as recent
  as 2026-09-18 — active development, but no new tagged release in seven
  weeks.
- **43 stars, 2 forks, 121 commits, 56 open issues.**
- Single named author on every release (`@zrougamed`) — a
  single-maintainer project, with everything that implies for continuity,
  security response time, and code review depth.
- A related, smaller repository (`zrougamed/orion-belt`, 34 stars) exists
  under the same author's personal account, describing the same tool —
  the `orion-belt-dev` organization appears to be where the more complete,
  GHCR-published, documented `v1.x` line actually lives.

None of this means the tool does not work — it started cleanly and passed
every check run against it here. Trusting a brand-new, single-maintainer
project with privileged access to real infrastructure carries an
operational risk that a feature list does not capture. Re-evaluate this
status at the next update to this stack rather than carrying it forward
unexamined.

## License

AGPL-3.0-only since 1.5.0, replacing Apache-2.0 with the Commons Clause.
Using, modifying and running it is free, commercial use included. Distributing
it, or offering a modified version over a network, requires publishing the
source under the same licence. Fine for this repository's self-hosted scope.

## What we use

- `ghcr.io/orion-belt-dev/orion-belt-server:1.5.0`
- `postgres:16.16-alpine`, following upstream's own `docker-compose.prod.yml`
  exactly for this pairing
- The agent (`docker-compose.agent.yml`), documented but not started here
  — it runs on the hosts you want to protect, not alongside the server

## What we changed vs. upstream compose

| Change | Reason |
|--------|--------|
| Docker Secrets for the Postgres password on the database side | Postgres natively supports `POSTGRES_PASSWORD_FILE`; upstream's own compose does not use it, but there is no reason not to on the side that supports it |
| No `_FILE` support on the server's own `POSTGRES_PASSWORD`/`ORION_JWT_SECRET` | Verified directly by reading `/app/entrypoint.sh` inside the image: both are read as plain environment variables and written in clear into a generated config file. No entrypoint wrapper was added — see "What was actually verified" |
| `user: "10001:10001"` | Since 1.5.0 the entrypoint, started as root, chowns the state directories and switches to `orionbelt` with `su-exec`; under `cap_drop: ALL` the chown fails and the container restarts in a loop (tested). Started as `orionbelt`, it skips that step; the bind-mounted `recordings` and `hostkey` directories belong to 10001:10001 |
| `tmpfs: /var/log/orion-belt` added | Verified against a live container: the bundled audit-logger plugin fails to configure under `read_only: true` without it |
| `cap_add: CHOWN, DAC_OVERRIDE, FOWNER, SETGID, SETUID` on Postgres | The same documented, previously-verified requirement `apps/_reference` states for Postgres startup under `cap_drop: ALL` |
| SSH gateway published directly, not through Traefik | Raw SSH; only the API/console is HTTP(S) |

## What was actually verified, and how

- `docker inspect` — confirmed the image's entrypoint is `/app/entrypoint.sh`,
  its declared ports (`2222/tcp`, `8080/tcp`), and that it is Alpine-based
  with `wget`/`nc` present.
- **Read the entrypoint script directly** (`docker run --entrypoint /bin/cat
  ... /app/entrypoint.sh`) rather than assuming its behavior: confirmed it
  generates an SSH host key on first run if absent, requires
  `ORION_JWT_SECRET` and `POSTGRES_PASSWORD` as plain environment variables
  (`: "${VAR:?...}"` — fails loudly if unset, does not silently default),
  and templates them directly into a generated `config.generated.yaml`
  inside the container. It also supports `ORION_CONFIG_FILE` to skip this
  templating entirely and mount a hand-written config instead — a real
  escape hatch to keep secrets out of the process environment, **not
  built here**: doing so properly needs a maintained config schema this
  deployment does not have the basis to author without inventing one. Left
  as documented, deferred work rather than a half-built pipeline.
- Full stack (`db`, `server`) started together under this compose file's
  exact hardening — `cap_drop: ALL` on both, `read_only: true` +
  `cap_add: SETUID/SETGID`-class fix pattern where a live failure demanded
  it. Both reached a healthy/running state; `GET /health` on the server
  returned `{"service":"orion-belt-api","status":"healthy",...}`.
- **Not verified:** registering and connecting a real agent, an actual SSH
  session, WebAuthn enrollment, the JIT/approval workflow, ReBAC policy
  behavior, session recording end to end, backup/restore, or behavior
  across a restart or upgrade.

## Version notes

- Moved to `1.4.0` on 2026-11-05; the agent
  example (`.env.agent.example`) moved with it. 1.4.0 adds RDP, VNC and
  just-in-time Kubernetes access through the agents and migrates the database
  schema on start (`permission_history`, risk signals, `risk_policy`). A
  `both` grant now means ssh + scp only; SSH and SCP behaviour is unchanged.
  Agents older than 1.4.0 keep working for SSH. The new
  `ORION_TRUSTED_PROXIES` (read into `server.trusted_proxies`) defaults to
  trusting no proxy, so behind Traefik every web client would appear as Traefik's
  address — this stack now sets it, see `.env.example`. No GHSA in the range;
  1.2.1 hardens authentication, authorization and proxy handling, 1.3.0 moves
  to Go 1.27.3 for reported vulnerabilities, lets users delete only their own
  SSH keys and validates admin-set plugin URLs and mail headers, and 1.4.0
  audits key, token and WebAuthn logins that were not audited before.
- Moved from `1.4.0` to `1.5.0` on 2026-11-23 (released 2026-11-15); the agent
  example (`.env.agent.example`) moved with it. No GHSA published; the release
  carries the fixes of the project's 2026-11-02 security audit: MFA backup codes can
  no longer be reused; `ocp` downloads reject path traversal in remote file names;
  with a Host CA configured, agents no longer trust a gateway that omits its
  certificate; the API server has timeouts, a request body limit and security
  headers; rate-limiter and live-session memory leaks are fixed; agent registration,
  credential changes and file-browser actions are audited; the generated agent
  install script verifies downloads against the signed `checksums.txt`. Built with
  Go 1.27.4 (GO-2026-6859). Breaking changes and what they mean here: the server
  container runs as `orionbelt` (10001) — under this stack's `cap_drop: ALL` the
  entrypoint's root-time chown of the state directories fails, so the compose now
  starts it as `user: "10001:10001"` and the `recordings` and `hostkey` directories
  must be chowned to 10001:10001 once (host key and data kept, tested on a 1.4.0
  data set); the server refuses the example JWT secret and any shorter than 32 bytes
  (`openssl rand -hex 32`, as in `.env.example`, gives 64); the first start converts
  timestamp columns to `TIMESTAMPTZ`, rewriting each table once under a lock — a
  large `audit_logs` table means a pause, and a non-UTC host whose time zone cannot
  be detected needs `ORION_DB_LEGACY_TIMEZONE`; the licence is now AGPL-3.0-only (see
  [License](#license)). Sources:
  https://github.com/orion-belt-dev/orion-belt/releases/tag/v1.5.0,
  https://github.com/orion-belt-dev/orion-belt/blob/master/docs/DEPLOYMENT_HARDENING.md

## Upgrade checklist

1. Watch [Orion Belt releases](https://github.com/orion-belt-dev/orion-belt/releases)
   — re-check star count, commit recency and maintainer count at the same
   time; this status assessment has a shelf life
2. Read the changelog for breaking changes
3. Back up `./volumes/postgres` and `./volumes/hostkey` before upgrading —
   the host key identifies this server to every agent that has already
   trusted it
4. Bump `APP_TAG` in `.env`
5. `docker compose pull && docker compose up -d`
6. Confirm `GET /health` and re-run the rehearsal in README.md before
   trusting the new version

## Known limitations

- **No OIDC/SSO connector found in the documented configuration** as of
  v1.2.0 — local WebAuthn/MFA only. Neither `core/authentik` nor
  `core/keycloak` can front login here on current evidence.
- **No `_FILE` secret support on the server's own credentials** — see
  above; `ORION_CONFIG_FILE` is the documented, unbuilt path to close this.
- **Single-maintainer, pre-1.x-in-spirit project** — see "EXPERIMENTAL"
  above.
- **Audit-log plugin writes to ephemeral storage** under this stack's
  `read_only` hardening — see the `tmpfs` comment in `docker-compose.yml`.
