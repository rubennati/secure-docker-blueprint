# Upstream Reference

## Source

- **Image:** https://hub.docker.com/r/calcom/cal.com
- **GitHub:** https://github.com/calcom/cal.com
- **Docs:** https://cal.com/docs/self-hosting
- **Release notes:** https://github.com/calcom/cal.com/releases
- **License (AGPL + Commercial):** https://github.com/calcom/cal.com/blob/main/LICENSE
- **License:** AGPL-3.0 + commercial tier
- **Origin:** US · Cal.com Inc · non-EU
- **Note:** Some features require the commercial plan — verify the feature set you need is covered by the AGPL tier before deploying.
- **Based on version:** `v6.2.0`
- **Last checked:** 2026-04-16

## What we use

- Official `calcom/cal.com` image, pinned tag
- `postgres:17` as primary backend
- Docker Secrets for DB password, NextAuth signing key, encryption key, SMTP password

## What we changed and why

| Change | Reason |
|--------|--------|
| Two-service layout (app + db) instead of upstream's all-in-one | Keeps database state independent from the app container, straightforward to back up and upgrade |
| Docker Secrets via `_FILE` for everything Cal.com supports | `NEXTAUTH_SECRET_FILE`, `CALENDSO_ENCRYPTION_KEY_FILE`, `EMAIL_SERVER_PASSWORD_FILE` — all natively honoured |
| `DB_PWD_INLINE` in `.env` | Prisma reads one single `DATABASE_URL` with no `_FILE` support; the password has to be inline. Documented as a Known Issue in README. |
| `CALCOM_TELEMETRY_DISABLED=1` | Default off — no phoning home |
| `NEXT_PUBLIC_LICENSE_CONSENT=agree` + empty `LICENSE` | Self-hosted use permitted under the project's license; no commercial license key required for standard deployments |
| `app-internal` network with `internal: true` | DB cannot reach the outside network |
| `no-new-privileges:true` on both services | Blueprint baseline |
| Encryption key generated with `openssl rand -hex 16` | Cal.com requires a 32-char hex string; `-base64` output breaks because of `+/=` chars in the ciphertext decoder |

## License

Cal.com is AGPL-3.0 with commercial options. For standard self-hosted use on your own infrastructure, `CALCOM_LICENSE_CONSENT=agree` with an empty `LICENSE` key is the correct setting. If you plan to offer Cal.com as a service to third parties, check the commercial license terms.

## 2026 heads-up — Cal.com goes partially closed, Cal.diy is the community edition

In 2026 Cal.com, Inc. announced that their production codebase (rewritten authentication, data handling, commercial systems) moves behind a closed-source licence, while a stripped-down **Cal.diy** remains available under MIT as the community edition. Cal.diy is explicitly positioned as "strictly for personal, non-production use" — no security guarantees from Cal.com, Inc.

**What this means for your deployment:**

- If you are **already running this compose** (`calcom/cal.com:${APP_TAG}`) on a pinned version: you keep working. Pinned tags under AGPL remain accessible indefinitely.
- If you want to **track the open-source community edition** going forward: see the sibling app [`apps/caldiy/`](../caldiy/). Same tech stack, different image + licence, different support expectations.
- If you want a **fully open PHP-stack alternative**: see [`apps/easyappointments/`](../easyappointments/). Simpler feature set, established since 2013.
- If you want **group scheduling polls** ("when does everyone have time?") rather than 1:1 booking: Rallly is planned as a complementary app (see root `README.md`).

The three 1:1-booking apps (Cal.com, Cal.diy, Easy!Appointments) are a choice-matrix — pick one; don't run parallel instances of the same use case.

## Upgrade checklist

Cal.com moves fast — read the release notes for every minor bump.

1. Release notes: https://github.com/calcom/cal.com/releases (look for "Breaking changes" sections)
2. Back up:
   ```bash
   # DB
   docker compose exec db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' \
     > calcom-$(date +%Y%m%d).sql
   # App data volume (uploaded images, etc.)
   tar czf calcom-data-$(date +%Y%m%d).tgz ./volumes/data
   ```
3. Bump `APP_TAG` in `.env`
4. `docker compose pull && docker compose up -d`
5. Watch the first boot; Prisma migrations run on startup:
   ```bash
   docker compose logs app --follow
   ```
6. Verify:
   - `curl -fsSI https://<APP_TRAEFIK_HOST>/api/health` returns 200
   - Log in, open an existing event type, make a test booking
   - Check connected calendars are still functional (they should be — the encryption key hasn't changed)

### Rollback

Prisma migrations are forward-only. Rollback = restore the SQL dump and revert `APP_TAG`.

## Related images to keep in sync

- `postgres:17` — safe to update within 17.x. Jumping to 18 (when released) requires the standard Postgres major upgrade procedure.

## Useful commands

```bash
# Shell into the app
docker compose exec app sh

# Run Prisma manually (e.g. to generate client after a schema change)
docker compose exec app npx prisma migrate status
docker compose exec app npx prisma migrate deploy

# Connect to the database directly
docker compose exec db psql -U $(grep ^DB_USER .env | cut -d= -f2) \
                            -d $(grep ^DB_NAME .env | cut -d= -f2)

# Test SMTP from inside the app container (uses the mounted secret)
docker compose exec app node -e \
  'require("nodemailer").createTransport({
     host: process.env.EMAIL_SERVER_HOST,
     port: +process.env.EMAIL_SERVER_PORT,
     auth: { user: process.env.EMAIL_SERVER_USER,
             pass: require("fs").readFileSync(process.env.EMAIL_SERVER_PASSWORD_FILE,"utf8") }
   }).verify().then(console.log, console.error)'

# Full DB backup
docker compose exec db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > dump.sql

# Restore into a fresh DB (after wiping the volume)
cat dump.sql | docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```
