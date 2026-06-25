# Cal.diy — Operations Runbook

Operational checklists for deploying, hardening, maintaining, and recovering Cal.diy on the
secure-docker-blueprint.

Steps marked **Phase 2** require CrowdSec Phase 2 (Traefik bouncer) to be configured and
verified on a test app first. Do not attempt them until the prerequisites are met.

---

## 1. Clean deployment checklist

Before `docker compose up`:

- [ ] `.env` created from `.env.example`; all placeholder values replaced
- [ ] `APP_TRAEFIK_HOST` set to the deployment hostname
- [ ] SMTP variables set (`EMAIL_FROM`, `EMAIL_SERVER_HOST`, `EMAIL_SERVER_PORT`, `EMAIL_SERVER_USER`)
- [ ] VAPID keypair generated:
  ```bash
  docker run --rm node:lts-alpine npx --yes web-push generate-vapid-keys
  ```
  - Public key → `VAPID_PUBLIC_KEY` in `.env`
  - Private key → `.secrets/vapid_private_key.txt`
- [ ] All `.secrets/*.txt` generated fresh (never copied from a previous instance):
  ```bash
  mkdir -p .secrets volumes/postgres volumes/redis
  openssl rand -hex 32 > .secrets/db_pwd.txt
  openssl rand -base64 32 | tr -d '\n' > .secrets/nextauth_secret.txt
  openssl rand -base64 24 | tr -d '\n' > .secrets/encryption_key.txt
  openssl rand -hex 16 | tr -d '\n' > .secrets/cron_api_key.txt
  touch .secrets/smtp_password.txt          # write SMTP password here
  touch .secrets/vapid_private_key.txt      # write VAPID private key here
  ```
- [ ] SMTP password written to `.secrets/smtp_password.txt` (use a dedicated credential — see §4)
- [ ] `docker compose config` shows no undefined variables and no warnings
- [ ] `docker compose up -d`
- [ ] `docker compose logs app --follow` — wait for `ready on port 3000`
- [ ] Setup wizard completes at `https://<APP_TRAEFIK_HOST>` — first user becomes the owner
- [ ] Send a test booking confirmation email and confirm delivery

---

## 2. Post-bootstrap hardening checklist

After the first successful deployment:

- [ ] Confirm no secret values appear in `docker inspect`:
  ```bash
  docker inspect caldiy-app | grep -E 'VAPID_PRIVATE|SMTP|NEXTAUTH_SECRET|ENCRYPTION_KEY|CRON_API'
  # Expected: empty output
  ```
- [ ] Confirm `cap_drop: ALL` is enforced on all three containers:
  ```bash
  docker inspect caldiy-app | grep -A2 CapDrop
  docker inspect caldiy-db  | grep -A2 CapDrop
  docker inspect caldiy-redis | grep -A2 CapDrop
  # Expected: "CapDrop": ["ALL"] on all three
  ```
- [ ] Confirm Redis filesystem is read-only:
  ```bash
  docker exec caldiy-redis touch /test-write
  # Expected: touch: /test-write: Read-only file system
  ```
- [ ] Confirm DB and Redis are not reachable from outside the internal network:
  ```bash
  docker inspect caldiy-db | grep -A5 '"Ports"'
  # Expected: no port mappings (empty Ports object)
  ```
- [ ] Disable public self-registration if Cal.diy supports it (check `NEXT_PUBLIC_DISABLE_SIGNUP`
  or admin settings panel — pending source-code review of the fork)
- [ ] Set `deploy.resources` memory limits after 24–48 hours of normal usage (measure with
  `docker stats caldiy-app caldiy-db caldiy-redis` — add limits at 2× peak memory)
- [ ] **Phase 2** — Expand Traefik access log filter to `200-599` (see `core/traefik/`)
- [ ] **Phase 2** — Attach CrowdSec bouncer to the Cal.diy router (see §6)

---

## 3. Secret rotation checklist

Rotate one secret at a time. Verify the app is healthy after each rotation before continuing.

### DB password

```bash
# 1. Generate new password
openssl rand -hex 32 > .secrets/db_pwd.txt.new

# 2. Update the PostgreSQL user while the container is running
docker compose exec db psql -U caldiy -c \
  "ALTER USER caldiy WITH PASSWORD '$(cat .secrets/db_pwd.txt.new)';"

# 3. Replace the secret file
mv .secrets/db_pwd.txt.new .secrets/db_pwd.txt

# 4. Restart app to pick up the new DATABASE_URL
docker compose restart app

# 5. Confirm app connects without errors
docker compose logs app --tail 30 | grep -iE 'error|fail|connect'
```

### NEXTAUTH_SECRET

> ⚠️ **All active sessions are immediately invalidated.** Every logged-in user is signed out.

```bash
openssl rand -base64 32 | tr -d '\n' > .secrets/nextauth_secret.txt
docker compose restart app
```

Verify: log in to Cal.diy and confirm authentication works.

### CALENDSO_ENCRYPTION_KEY

> ⚠️ **All stored calendar OAuth tokens become unreadable.** Every user who connected Google or
> Outlook must re-authorise their calendar integration after restart.

Inform users before rotating.

```bash
openssl rand -base64 24 | tr -d '\n' > .secrets/encryption_key.txt
docker compose restart app
```

### CRON_API_KEY

If an external scheduler calls `/api/cron/*`, update its key before rotating here.

```bash
openssl rand -hex 16 | tr -d '\n' > .secrets/cron_api_key.txt
docker compose restart app
```

### SMTP password

See §4 (SMTP emergency rotation) for the full procedure.

### VAPID keypair

> ⚠️ **Existing push notification subscriptions are invalidated.** Users who enabled push
> notifications must re-subscribe.

```bash
# Generate a new keypair
docker run --rm node:lts-alpine npx --yes web-push generate-vapid-keys

# Write the new private key
printf '%s' 'NEW_VAPID_PRIVATE_KEY_HERE' > .secrets/vapid_private_key.txt

# Update the public key in .env (VAPID_PUBLIC_KEY=<new public key>)
# Then restart
docker compose restart app
```

---

## 4. SMTP emergency rotation

Use this procedure when the SMTP credential may have been compromised, or during planned rotation.

```
Step 1 — Revoke at the provider immediately.
  Do not wait until after deployment. Log in to the SMTP provider and revoke the
  current credential now. Any email sent with the old credential after this point
  will fail — that is the correct behaviour.

Step 2 — Provision a new dedicated credential.
  Label it: caldiy-<hostname>-<YYYY-MM-DD>
  Enable provider-side controls on the new credential:
    - Daily sending cap (example: 200 emails/day)
    - Alert when 50% of daily cap is consumed
    - Alert recipient on a separate notification channel

Step 3 — Write the new password to the secret file.
  printf '%s' 'NEW_SMTP_PASSWORD_HERE' > .secrets/smtp_password.txt

Step 4 — Restart the app.
  docker compose restart app

Step 5 — Send a test booking email and confirm delivery.

Step 6 — Confirm the old credential is rejected.
  At the provider, verify the revoked credential returns an authentication failure.
```

**Monitoring after rotation:**
- Check the provider dashboard daily for send volume
- Expected baseline: roughly `N bookings × 2 emails` per day
- Investigate immediately if volume is unexpectedly higher

---

## 5. Backup and restore

### Manual DB dump

```bash
docker compose exec db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' \
  > caldiy-$(date +%Y%m%d).sql
```

### Restore DB

```bash
cat caldiy-YYYYMMDD.sql | docker compose exec -T db \
  sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

Always back up before upgrading. See [UPSTREAM.md](../UPSTREAM.md) → "Upgrade checklist" for the
full upgrade and rollback procedure.

---

## 6. CrowdSec verification — Phase 2

> **Phase 2 prerequisites — do not attempt until all of the following are true:**
> - `core/crowdsec/` engine healthy: `docker exec crowdsec cscli lapi status`
> - Traefik access log filter expanded to `200-599` in `core/traefik/ops/templates/traefik.yml.tmpl`
>   (re-render required: `./ops/scripts/render.sh && docker compose restart traefik`)
> - Phase 2 bouncer plugin verified on `core/whoami` per `core/crowdsec/README.md` Phase 2 guide
> - `sec-crowdsec@file` added as the first middleware on the Cal.diy Traefik router

**Phase 2 verification checklist:**

- [ ] Bouncer is actively pulling decisions:
  ```bash
  docker exec crowdsec cscli bouncers list
  # Expected: traefik-bouncer with a recent "Last API pull" timestamp (within 60 s)
  ```
- [ ] Access log is capturing Cal.diy requests:
  ```bash
  docker exec crowdsec cscli metrics show acquisition
  # Expected: lines_parsed increases when Cal.diy is browsed
  ```
- [ ] End-to-end ban test:
  ```bash
  docker exec crowdsec cscli decisions add \
    --ip <your-ip> --duration 3m --reason phase2-verify
  # Wait 65 seconds for the plugin to pull the decision
  # Access Cal.diy from that IP — must return HTTP 403
  docker exec crowdsec cscli decisions delete --ip <your-ip>
  # Confirm access is restored
  ```
- [ ] Weekly: review active decisions
  ```bash
  docker exec crowdsec cscli decisions list
  ```
- [ ] Weekly: review detected threats
  ```bash
  docker exec crowdsec cscli alerts list
  ```
- [ ] Monthly: update hub parsers and scenarios
  ```bash
  docker exec crowdsec cscli hub update && docker exec crowdsec cscli hub upgrade
  ```

---

## 7. Emergency kill-switch

Blocks all Cal.diy traffic immediately without restarting any container. Traefik hot-reloads the
change within seconds.

### Step 1 — Block all traffic

In `apps/caldiy/.env`, change:
```
APP_TRAEFIK_ACCESS=acc-public
```
to:
```
APP_TRAEFIK_ACCESS=acc-deny
```

Then force Traefik to read the updated container labels:
```bash
docker compose up -d --force-recreate app
```

All requests to `APP_TRAEFIK_HOST` now return HTTP 403. No container restart needed for Traefik.

### Step 2 — Revoke SMTP credential

Log in to the SMTP provider and revoke the credential immediately. Do not wait for investigation.

### Step 3 — Preserve evidence before rotating anything

```bash
docker compose logs app --tail 500 > incident-app-$(date +%Y%m%d%H%M).log
docker compose logs db  --tail 100 > incident-db-$(date +%Y%m%d%H%M).log
```

If CrowdSec is running:
```bash
docker exec crowdsec cscli alerts list    > incident-cs-alerts-$(date +%Y%m%d%H%M).txt
docker exec crowdsec cscli decisions list > incident-cs-decisions-$(date +%Y%m%d%H%M).txt
```

### Step 4 — Rotate secrets

Follow §3 for each secret. Order: SMTP (step 2 above) → `NEXTAUTH_SECRET` → DB password →
remaining secrets as root-cause analysis warrants.

### Step 5 — Restore access

After root-cause is understood and all affected secrets rotated:
```bash
# Revert .env
APP_TRAEFIK_ACCESS=acc-public
docker compose up -d --force-recreate app
```

---

## 8. Update and rollback

See [UPSTREAM.md](../UPSTREAM.md) → "Upgrade checklist" and "Rollback" for the full procedure.

Key points:
- Back up the database before every upgrade (§5)
- Prisma migrations are forward-only — rollback requires restoring the DB dump
- Watch `docker compose logs app --follow` after every upgrade for migration errors
- If the image at a new tag introduces incompatible env vars, check
  [Cal.diy releases](https://github.com/calcom/cal.diy/releases) for breaking changes before
  bumping `APP_TAG`
