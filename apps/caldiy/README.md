# Cal.diy

> **Status: ✅ Ready** — v6.2.0-4 · 2026-07-26

> **Note:** Cal.diy is the MIT-licensed community edition of Cal.com, spun out in 2026 when Cal.com moved its production codebase behind a closed-source licence. Upstream explicitly labels Cal.diy as "strictly for personal, non-production use" with no security guarantees. **Do not use for business-critical scheduling** without understanding that trade-off.

> **⚠️ Cloudflare (proxied) is a required layer for this deployment.** Because Cal.diy is community-maintained and not confirmed secure — and because a live instance was compromised once (SMTP credential exfiltrated) — this blueprint runs Cal.diy **behind Cloudflare as a proxy (orange cloud), not DNS-only**, as a mandatory extra layer: WAF, geo allowlist on the human-facing surface, rate limiting, and origin hiding. Exact settings: **[docs/cloudflare.md](docs/cloudflare.md)**. The full post-incident hardening roadmap: **[docs/hardening-plan.md](docs/hardening-plan.md)**.

For an alternative with an established track record and no build dependency, see [`apps/easyappointments/`](../easyappointments/) (PHP + MariaDB, GPL-3.0).

## Architecture

| Service | Image | Purpose |
|---------|-------|---------|
| `app` | `ghcr.io/rubennati/cal.diy:v6.2.0-4` | Next.js web app + scheduling engine |
| `db` | `postgres:17.4` | Users, event types, bookings, team memberships |
| `redis` | `redis:7.4-alpine` | Session cache + job queue |

The image is built from [`rubennati/cal.diy`](https://github.com/rubennati/cal.diy) — the security-first, review-gated **cal.forte** fork that publishes reviewed, versioned images to GHCR (never `latest`). Upstream does not publish a reliable pre-built image. See [UPSTREAM.md](UPSTREAM.md).

## Setup

```bash
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, APP_TAG, TZ, EMAIL_*, branding vars

# 1. Generate secrets
mkdir -p .secrets volumes/postgres volumes/redis
openssl rand -hex 32 > .secrets/db_pwd.txt
openssl rand -base64 32 | tr -d '\n' > .secrets/nextauth_secret.txt
openssl rand -base64 24 | tr -d '\n' > .secrets/encryption_key.txt
openssl rand -hex 16 | tr -d '\n' > .secrets/cron_api_key.txt
touch .secrets/smtp_password.txt          # write SMTP password here (dedicated credential)
touch .secrets/vapid_private_key.txt      # write VAPID private key here (see step 2)

# 2. Generate VAPID keys (required — app errors on boot without them)
# No Node.js on the server? Use a temporary container:
docker run --rm node:lts-alpine npx --yes web-push generate-vapid-keys
# Public key  → VAPID_PUBLIC_KEY in .env
# Private key → .secrets/vapid_private_key.txt  (Docker Secret — never in .env)

# 3. Update ALLOWED_HOSTNAMES in .env to match APP_TRAEFIK_HOST:
#    ALLOWED_HOSTNAMES='"cal.yourdomain.com"'

# 4. Start
docker compose up -d
docker compose logs app --follow
# Watch for: "ready on port 3000"

# https://<APP_TRAEFIK_HOST>
# Setup wizard runs on first visit — first user becomes the owner.
```

> **Before exposing publicly:** put the host behind Cloudflare (proxied) and apply
> [docs/cloudflare.md](docs/cloudflare.md) — WAF, geo allowlist, and origin hiding are part of
> this deployment's security model, not optional extras.

## Local testing (no Traefik)

Run the app standalone on `http://localhost:3000` — no Traefik, Cloudflare, or Docker Secrets:

```bash
cp .env.local.example .env.local   # fill values (openssl one-liners inside)
docker compose -f docker-compose.local.yml --env-file .env.local up -d
# http://localhost:3000 — signup is ON so you can create the first user
```

Secrets are plain env in `.env.local` (gitignored) — **local only**, never production.

## Security Model

| Concern | How handled |
|---------|-------------|
| Edge protection (Cloudflare) | **Required** proxied layer — WAF, geo allowlist on the human surface, rate limiting, origin hiding. See [docs/cloudflare.md](docs/cloudflare.md) |
| DB password | Docker Secret (`db_pwd.txt`) — never in `.env` |
| `NEXTAUTH_SECRET` | Docker Secret (`nextauth_secret.txt`) — never in `.env` |
| `CALENDSO_ENCRYPTION_KEY` | Docker Secret (`encryption_key.txt`) — never in `.env` |
| `CRON_API_KEY` | Docker Secret (`cron_api_key.txt`) — protects `/api/cron/*` |
| SMTP password | Docker Secret (`smtp_password.txt`) — never in `.env` |
| VAPID private key | Docker Secret (`vapid_private_key.txt`) — never in `.env` |
| Secret injection | Custom entrypoint (`config/entrypoint.sh`) reads all secrets at runtime |
| Postgres | `app-internal` network (`internal: true`) — not reachable from host |
| Redis | `app-internal` (`internal: true`), `read_only: true`, `cap_drop: ALL`, `pids_limit: 50` |
| Host header injection | `ALLOWED_HOSTNAMES` set to deployment hostname |
| Public self-registration | Disabled — `NEXT_PUBLIC_DISABLE_SIGNUP=true` (no open account creation) |
| HTTP security headers | Traefik `sec-3` chain (`APP_TRAEFIK_SECURITY`) — strict HSTS, Referrer-Policy, Permissions-Policy, CSP report-only. See [Security chain (sec-3)](#security-chain-sec-3) below. |
| Privilege escalation | `no-new-privileges:true` on all services |
| Capability restriction | `cap_drop: ALL` on all services |
| Process count | `pids_limit` on all services (app: 200, db: 100, redis: 50) |
| Resource limits | Interim caps set — `deploy.resources` (memory/cpus/pids) on all three services; retune after measuring under load |
| CrowdSec enforcement | Not yet attached — roadmap in [docs/hardening-plan.md](docs/hardening-plan.md) Phase 2; steps in [ops-runbook.md](docs/ops-runbook.md) §6 |
| Community-maintained security | No Cal.com, Inc. incident response — watch upstream releases manually |

### Security chain (sec-3)

Cal.diy defaults to the **`sec-3`** Traefik middleware chain (`APP_TRAEFIK_SECURITY=sec-3`), one level stricter than the blueprint's standard `sec-2`. The difference is **header hardening only — no request is blocked at the proxy, and the rate limit is unchanged** (100 req/s average, 50 burst, same as sec-2):

| Header | sec-2 | sec-3 |
|--------|-------|-------|
| `Strict-Transport-Security` | `max-age=63072000` | `max-age=63072000; includeSubDomains; preload` |
| `Referrer-Policy` | — | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | — | camera / microphone / geolocation / payment / usb / … all denied |
| `Content-Security-Policy` | — | `…-Report-Only` (reports violations, does **not** block) |
| `X-Content-Type-Options` / `X-Frame-Options: DENY` | yes | yes (unchanged) |

`sec-3` is the right default for a **public-facing scheduling app that stores PII** (names, emails, meeting topics): it tells browsers to enforce HTTPS, limit referrer leakage, and disable device APIs the app never uses. The CSP ships **report-only**, so it surfaces violations without breaking the page — a later phase can promote it to enforcing once the report stream is clean.

> **⚠️ HSTS `includeSubDomains` + `preload` is browser-sticky.** The header applies to **the exact host that served it** (`APP_TRAEFIK_HOST`) and, with `includeSubDomains`, to **any subdomain below that host** — it does **not** affect sibling hosts or the parent domain unless those serve the header themselves. Scope examples: `calendar.example.com` covers `*.calendar.example.com` but **not** `www.example.com` or `example.com`; an apex host `example.com` covers `*.example.com` (the whole zone). Rolling back to `sec-2` stops *sending* the header, but browsers that already received `max-age=63072000` keep enforcing HTTPS for the in-scope hosts until it expires (~2 years) or the user clears HSTS state. **Before enabling in production, confirm every subdomain *below the Cal.diy hostname* is HTTPS-capable**, and treat `preload` as a deliberate, hard-to-reverse choice. A dedicated leaf host with no child subdomains carries much lower practical scope; an apex host carries the most.

**Rollback:** set `APP_TRAEFIK_SECURITY=sec-2` in `.env` and recreate the app container — `docker compose up -d --force-recreate app`. Traefik hot-reloads the middleware reference; no Traefik restart needed. See [docs/ops-runbook.md](docs/ops-runbook.md) → "Traefik security chain rollout" for the full procedure and the HSTS caveat.

## Post-incident redeployment

> **If the previous instance was compromised, treat every secret as burned. None of the values below can be reused.**

Revoke the SMTP credential at the provider **before** running `docker compose up`. Do not deploy first.

| Secret | Burn status | Action |
|--------|-------------|--------|
| SMTP password | **Burned** | Revoke at provider UI now. Provision a new dedicated credential. |
| DB password | **Burned** | `openssl rand -hex 32 > .secrets/db_pwd.txt` |
| `NEXTAUTH_SECRET` | **Burned** | `openssl rand -base64 32 \| tr -d '\n' > .secrets/nextauth_secret.txt` |
| `CALENDSO_ENCRYPTION_KEY` | **Burned** ⚠️ | `openssl rand -base64 24 \| tr -d '\n' > .secrets/encryption_key.txt` |
| `CRON_API_KEY` | **Burned** | `openssl rand -hex 16 \| tr -d '\n' > .secrets/cron_api_key.txt` |
| VAPID private key | Rotate | Re-run `web-push generate-vapid-keys`. Write private key to `.secrets/vapid_private_key.txt`. |
| Google OAuth client secret | Rotate if enabled | Revoke in Google Cloud Console, provision a new client. |

**⚠️ `CALENDSO_ENCRYPTION_KEY` impact:** rotating this key invalidates all stored calendar OAuth tokens (Google, Outlook). Every connected user must re-authorise their calendar integrations after the new instance starts.

**⚠️ `NEXTAUTH_SECRET` impact:** rotating this key immediately invalidates all active sessions. All logged-in users are signed out.

Never copy `.secrets/` from the compromised instance. Generate every file fresh on the new host.

For the full rotation procedure including per-secret steps and SMTP emergency rotation, see [docs/ops-runbook.md](docs/ops-runbook.md).

## SMTP containment

Cal.diy sends emails for booking confirmations, reminders, and account events. A compromised SMTP credential causes reputational damage and potential account suspension.

| Control | Description |
|---------|-------------|
| Dedicated credential | One credential for this deployment only — never shared with other applications |
| Provider sending cap | Set a daily limit at the provider (example: 200 emails/day) |
| Provider alert | Alert at 50% of daily cap; receive it on a channel separate from the Cal.diy mailbox |
| Sender identity | Use a dedicated address or subdomain (`noreply@cal.yourdomain.com`), not a personal address |
| Storage | SMTP password is a Docker Secret (`smtp_password.txt`) — never written to `.env` |

For the emergency rotation procedure and ongoing monitoring, see [docs/ops-runbook.md](docs/ops-runbook.md).

## Known Issues

- **VAPID keys are mandatory** — skip step 2 and the app logs `Error: No key set vapidDetails.publicKey` on every request.
- **`CLIENT_FETCH_ERROR` if `NEXTAUTH_URL` is wrong** — must include `/api/auth` path. Already set correctly in `docker-compose.yml`.
- **`/api/health` returns 500** — Node.js stream API incompatibility in this image version causes a `TypeError` on the health endpoint. The healthcheck falls back to `nc -z 127.0.0.1 3000` (TCP) which works fine. The app itself runs normally.
- **Feature parity with Cal.com is partial** — Teams, Organisations, advanced Insights, SSO/SAML, and Workflows are removed from the community edition.
- **Google/Outlook integrations require OAuth app registration** — see [upstream docs](https://github.com/rubennati/cal.diy#obtaining-the-google-api-credentials).

## Details

- [docs/hardening-plan.md](docs/hardening-plan.md) — post-incident hardening roadmap (surface reduction, CrowdSec, geo)
- [docs/cloudflare.md](docs/cloudflare.md) — required Cloudflare settings (WAF, geo allowlist, rate limiting, origin hiding)
- [UPSTREAM.md](UPSTREAM.md) — fork (cal.forte) reference, upgrade checklist, gotchas
- [docs/ops-runbook.md](docs/ops-runbook.md) — deployment, secret rotation, SMTP, CrowdSec, emergency kill-switch
- Sibling: [`apps/easyappointments/`](../easyappointments/) — PHP-stack alternative, no build dependency
