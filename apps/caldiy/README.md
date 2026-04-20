# Cal.diy

> **Status: Draft — not yet live-tested.**
>
> **Read first:** Cal.diy is the MIT-licensed community edition of Cal.com, spun out in 2026 when Cal.com moved its production codebase behind a closed-source licence. Upstream explicitly labels Cal.diy as "strictly for personal, non-production use" with no security guarantees. **Do not use for business-critical scheduling** without understanding that trade-off.

Sibling app to [`apps/calcom/`](../calcom/). Same tech stack (Next.js + Postgres + Prisma), different licence and support model.

## When to pick Cal.diy over Cal.com

| Pick Cal.diy if… | Pick Cal.com if… |
|---|---|
| You want pure MIT, no commercial licence ambiguity | You need commercial / enterprise support path |
| Personal / hobby / homelab use | Customer-facing production booking |
| You're OK patching your own security issues | You want Cal.com, Inc. security updates |
| You want to diverge / customise the codebase | You want feature-parity with the hosted SaaS |

If you are unsure → use `apps/calcom/` on a pinned AGPL tag. The v6.x pinned images remain downloadable indefinitely.

## Architecture

| Service | Image | Purpose |
|---------|-------|---------|
| `app` | `${APP_IMAGE}:${APP_TAG}` (see `.env.example` caveat) | Next.js web app + scheduling engine |
| `db` | `postgres:17` | Users, event types, bookings, team memberships |

## Setup

```bash
cp .env.example .env

# 1. Verify the upstream image path at https://cal.diy/docs/docker
#    Update APP_IMAGE in .env to match.

# 2. Generate secrets
mkdir -p .secrets volumes/postgres volumes/data
openssl rand -hex 32 > .secrets/db_pwd.txt
openssl rand -hex 32 > .secrets/nextauth_secret.txt
openssl rand -hex 16 > .secrets/encryption_key.txt
touch .secrets/smtp_password.txt  # write your SMTP password here

# 3. Sync DB_PWD_INLINE (Prisma URL has no _FILE support)
sed -i "s|^DB_PWD_INLINE=.*|DB_PWD_INLINE=$(cat .secrets/db_pwd.txt)|" .env

docker compose up -d
docker compose logs app --follow
# Watch for: "ready on port 3000"

# https://<APP_TRAEFIK_HOST>
# First user to sign up becomes the owner.
```

## Security Model

- **Community-maintained security fixes only** — no Cal.com, Inc. incident response. Follow upstream releases manually.
- **`DB_PWD_INLINE` duplicates DB password** — same Prisma limitation as Cal.com.
- **`NEXTAUTH_SECRET_FILE` + `CALENDSO_ENCRYPTION_KEY_FILE`** — Docker Secrets, `_FILE` natively.
- **`EMAIL_SERVER_PASSWORD_FILE`** — Docker Secret for SMTP.
- **Postgres on `app-internal` (`internal: true`)** — DB not reachable from host.
- **`no-new-privileges:true`** on both services.
- **Default access `acc-public` + `sec-2`** — booking URLs must be reachable by external visitors.

## Known Issues

- **Live-tested: no.**
- **`APP_IMAGE` is a placeholder** — the exact upstream registry path is pending verification against `cal.diy/docs/docker`. Adjust before first boot.
- **`APP_TAG=latest` is not reproducible** — pin to a specific release once the upstream tagging convention is known.
- **Feature parity with Cal.com is partial** — commercial / enterprise modules (routing forms, advanced team workflows, etc.) may be stripped out of the community build. Read the upstream docs before relying on a specific feature.

## Details

- [UPSTREAM.md](UPSTREAM.md)
- Sibling: [`apps/calcom/`](../calcom/) — commercial pathway
- Sibling: [`apps/easyappointments/`](../easyappointments/) — PHP-stack alternative
