# Upstream Reference

## Source

- **Upstream GitHub:** https://github.com/orion-belt-dev/orion-belt
- **Image registry:** `ghcr.io/orion-belt-dev/orion-belt-server`,
  `ghcr.io/orion-belt-dev/orion-belt-agent` (GHCR)
- **Self-host compose reference:** `docker-compose.prod.yml` and
  `docker-compose.prod.agent.yml` in the upstream repo
- **License:** Apache-2.0 (with Commons Clause)
- **Use restrictions:** Apache-2.0 with the Commons Clause, which withholds the right to Sell — defined as providing to third parties, for a fee or other consideration, a product or service whose value derives entirely or substantially from its functionality, including fees for hosting or for consulting and support related to it — https://github.com/orion-belt-dev/orion-belt/blob/master/LICENSE · checked 2026-09-21
- **Origin:** Individual maintainer · Mohamed Zrouga · no single jurisdiction
- **Domain:** Identity, access and secrets
- **Role:** Privileged access gateway for SSH sessions, from a young single-maintainer project
- **Based on version:** `1.2.0`
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

## License — Commons Clause

Apache-2.0 with a Commons Clause condition: self-hosting and internal
commercial use are explicitly permitted; selling Orion Belt itself, or a
hosted service whose value derives substantially from it, is not. Fine for
this repository's self-hosted, personal-infrastructure scope. Classified
as `source-available` in this repository's sovereignty tooling — see the
one-line addition this required in `scripts/ci/sovereignty-report.py`
(`SOURCE_AVAILABLE` gained `"Commons Clause"`), the smallest change that
correctly reflects a real restriction rather than reporting this as plain
open source.

## What we use

- `ghcr.io/orion-belt-dev/orion-belt-server:1.2.0`
- `postgres:16-alpine`, following upstream's own `docker-compose.prod.yml`
  exactly for this pairing
- The agent (`docker-compose.agent.yml`), documented but not started here
  — it runs on the hosts you want to protect, not alongside the server

## What we changed vs. upstream compose

| Change | Reason |
|--------|--------|
| Docker Secrets for the Postgres password on the database side | Postgres natively supports `POSTGRES_PASSWORD_FILE`; upstream's own compose does not use it, but there is no reason not to on the side that supports it |
| No `_FILE` support on the server's own `POSTGRES_PASSWORD`/`ORION_JWT_SECRET` | Verified directly by reading `/app/entrypoint.sh` inside the image: both are read as plain environment variables and written in clear into a generated config file. No entrypoint wrapper was added — see "What was actually verified" |
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
- **Not yet run on a live host beyond a clean start.**
