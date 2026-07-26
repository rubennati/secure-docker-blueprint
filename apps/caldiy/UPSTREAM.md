# Upstream Reference

## Source

- **Project site:** https://cal.diy/
- **Upstream (ultimate):** https://github.com/calcom/cal.diy — the community edition our fork's `main` mirrors 1:1
- **Fork (image source):** https://github.com/rubennati/cal.diy — **cal.forte**, a security-first, review-gated fork
- **Image registry:** `ghcr.io/rubennati/cal.diy`
- **Docs:** https://cal.diy/docs
- **License:** MIT
- **Relationship:** Community-edition spin-out of Cal.com (2026, after Cal.com moved its production code behind a closed-source licence). This blueprint consumes the **hardened fork**, not upstream directly.
- **Based on version:** `v6.2.0` (fork release `v6.2.0-4`)
- **Last verified:** 2026-07-26 (v6.2.0-3)

## Why a fork?

Two reasons — and the second reshaped the fork in 2026:

1. **Reliable images.** Upstream (`calcom/cal.diy`) does not publish a dependable pre-built
   Docker image. The fork builds versioned images and pushes them to `ghcr.io/rubennati/cal.diy`.
2. **Security control.** After a compromise on a live instance (the SMTP credential was
   exfiltrated), the fork was restructured as **cal.forte** — a security-first, **review-gated**
   fork. Every upstream change is reviewed before it can reach a deployable image, so the
   blueprint no longer rides on the upstream community's security cadence.

Governance lives in the fork — read these before cutting a release: `FORK_PROCESS.md` (branch
contract + allowed divergence), `UPSTREAM_SYNC.md` (security-first sync rules), `SECURITY_REVIEW.md`
(the review gate), `IMAGE_BUILD.md`, `RELEASE_PROCESS.md`.

Branch model of the fork:

| Branch | Purpose |
|--------|---------|
| `main` | Untouched 1:1 mirror of `calcom/cal.diy` — **not deployable** |
| `develop` | Integration & review branch — upstream changes land and are reviewed here; **not deployable** |
| `release` | Reviewed source for image publication — every `v*` tag here triggers a Docker image build |

Consume **only** a reviewed tag or digest from `release` — never `latest`.

## What we use

- `ghcr.io/rubennati/cal.diy:v6.2.0-4` — built from the `rubennati/cal.diy` (cal.forte) fork's `release` branch
- `postgres:17.4` as primary backend
- `redis:7.4-alpine` for session cache and job queue (required by upstream)
- Custom entrypoint (`config/entrypoint.sh`) injects all secrets from Docker Secret files
  at runtime — Cal.diy has no native `_FILE` support for any of its secrets

## What we changed vs. upstream examples

| Change | Reason |
|--------|--------|
| Custom entrypoint for secret injection | Cal.diy has no `_FILE` support; entrypoint reads `/run/secrets/` files at runtime — no secrets in `.env` |
| `app-internal` network (`internal: true`) | DB and Redis not reachable from host |
| `no-new-privileges:true` on all services | Baseline |
| `read_only: true` + `cap_drop: ALL` + `tmpfs` + `pids_limit: 50` on Redis | Redis writes only to mounted `/data` volume; ephemeral paths served from tmpfs |
| `cap_drop: ALL` + `pids_limit` on all services | Limits Linux capabilities and process count on app (200), db (100), redis (50) |
| `VAPID_PRIVATE_KEY` as Docker Secret | Private key injected from `/run/secrets/` via entrypoint; not visible in `docker inspect` |
| Healthcheck-gated `depends_on` | Prevents app startup before Postgres is ready |
| `DATABASE_HOST: db:5432` | Required by `start.sh` for wait-for-it gate before Prisma migrations |
| `ALLOWED_HOSTNAMES` set to deployment hostname | Prevents host header injection |
| `CRON_API_KEY` randomised | Upstream default is a public string — protects `/api/cron/*` endpoints |
| Telemetry disabled (`CALCOM_TELEMETRY_DISABLED=1`) | Blueprint default |
| `NEXTAUTH_URL` set to `https://${host}/api/auth` | Without `/api/auth` path the container gets `CLIENT_FETCH_ERROR` |
| VAPID keys in `.env.example` | Required env vars — without them Cal.diy logs an error on every boot |
| Branding vars exposed | `NEXT_PUBLIC_APP_NAME`, `NEXT_PUBLIC_COMPANY_NAME`, `NEXT_PUBLIC_SUPPORT_MAIL_ADDRESS` |
| Logger level set to 3 | Info+ is appropriate for production; default is unset (verbose) |

## Why Cal.diy exists and why we ship it

Cal.com, Inc. announced in 2026 that they split their codebase:

- **Closed-source production core** — rewritten authentication, data handling, commercial billing. Stays with Cal.com, Inc. under a proprietary licence.
- **Cal.diy** — a stripped community edition under MIT, community-maintained, explicitly labelled "strictly for personal, non-production use." No security guarantees from Cal.com, Inc.

For a self-hosting blueprint that explicitly targets OSS-first deployments, Cal.diy is the honest option for users who want a fully OSS path and accept the "non-production" framing.

## Upgrade checklist

When upstream releases a new version, follow the fork's `UPSTREAM_SYNC.md` + `SECURITY_REVIEW.md`:

1. Watch [Cal.diy GitHub releases](https://github.com/calcom/cal.diy/releases)
2. In the `rubennati/cal.diy` (cal.forte) fork:
   - **Sync `main`** from upstream (1:1 mirror, no edits)
   - `git checkout develop && git merge main` → **review the diff per `SECURITY_REVIEW.md`**, adjust CI/`.github` as needed
   - Promote `develop → release` only once the review gate passes
   - `git checkout release && git pull && git tag v6.2.0-5 && git push origin v6.2.0-5` → image built automatically
   - Fork release tags carry a `-N` suffix (`v6.2.0-4`, `v6.2.0-5`, …) so a fork rebuild is distinct from the upstream base version
3. Back up before upgrading:
   ```bash
   docker compose exec db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' \
     > caldiy-$(date +%Y%m%d).sql
   ```
4. Bump `APP_TAG` in `.env` to the new reviewed tag (or pin the digest — see `.env.example`)
5. `docker compose pull && docker compose up -d`
6. Watch Prisma migrations on first boot:
   ```bash
   docker compose logs app --follow
   ```

### Rollback

Restore DB dump, revert `APP_TAG`. Prisma migrations are forward-only.

## Useful commands

```bash
# Shell into app
docker compose exec app sh

# Manual DB dump
docker compose exec db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > dump.sql

# Restore DB
cat dump.sql | docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'

# Check app logs
docker compose logs app --follow --tail 50
```

## Known limitations

- **No `_FILE` support** — mitigated via custom entrypoint; all secrets stay in `.secrets/` and never touch `.env`
- **Feature set is reduced vs. Cal.com** — Teams, Organisations, advanced Insights, SSO/SAML, Workflows removed
- **Community-maintained security cadence** — no dedicated security team; watch [releases](https://github.com/calcom/cal.diy/releases) manually

## Known gotchas (v6.2.0)

### 1. Base64/special-character passwords break the `postgresql://` URL

Cal.diy builds the database URL in the entrypoint as `postgresql://user:password@host/db`.
If the password was generated with `openssl rand -base64 32`, it will contain `/`, `+`, and `=`
characters — all of which break `pg-connection-string`'s URL parser, causing `ECONNREFUSED` to
`localhost:5432` rather than the actual database host.

**Workaround (applied in this blueprint):**

1. Generate the DB password with hex instead of base64 to avoid special characters entirely:
   ```bash
   openssl rand -hex 32 > .secrets/db_pwd.txt
   ```
2. The custom `config/entrypoint.sh` additionally URL-encodes the password before building
   `DATABASE_URL`, so it is safe with any generator:
   ```sh
   _enc_pwd="$(printf '%s' "${_raw_pwd}" | sed 's/%/%25/g; s/+/%2B/g; s|/|%2F|g; s/=/%3D/g')"
   ```

**Upstream status:** reported to [rubennati/cal.diy](https://github.com/rubennati/cal.diy) — the
upstream image's entrypoint does not URL-encode the password.

### 2. `/api/health` returns HTTP 500

The `/api/health` endpoint throws `TypeError: controller[kState].transformAlgorithm is not a function`
due to a Node.js stream API incompatibility in the `v6.2.0` image. The endpoint always returns 500,
which fails the default curl-based healthcheck.

**Workaround (applied in this blueprint):**

The healthcheck uses wget with an HTTP status grep plus a TCP fallback:
```yaml
test: ["CMD-SHELL", "wget -qO/dev/null http://127.0.0.1:3000/api/health 2>&1 | grep -q '200\\|301\\|302' || nc -z 127.0.0.1 3000"]
```
This reports the container healthy as long as port 3000 accepts connections, which is the correct signal.

**Upstream status:** reported to [rubennati/cal.diy](https://github.com/rubennati/cal.diy).
