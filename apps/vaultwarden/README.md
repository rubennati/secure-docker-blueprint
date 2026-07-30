# Vaultwarden

Self-hosted Bitwarden-compatible password manager.

## Services

| Service | Image | Purpose |
|---|---|---|
| app | vaultwarden/server | Password manager |
| db | mariadb | Database |

## Security Features

- TLS 1.3 only (`tls-modern`)
- Admin token as Argon2 hash (never plain text)
- Rate limiting on login (10/min) + admin panel (3/5min)
- `read_only` container + `no-new-privileges`
- Signups disabled after initial account creation
- Password hints disabled
- Block non-global IPs (SSRF protection)
- Email verification required for signups

## First-Time Setup

### Step 1: Configure

```bash
cp .env.example .env
nano .env
```

Set these values:

- `APP_TRAEFIK_HOST` — your domain (e.g. `vault.example.com`)
- `VW_SIGNUPS_ALLOWED=true` — temporarily for first user creation

### Step 2: Configure SMTP (REQUIRED before first user!)

**IMPORTANT:** Without SMTP, user registration will fail because email
verification is enabled. Set these in `.env`:

```env
VW_SMTP_HOST=smtp-relay.brevo.com     # SMTP provider host
VW_SMTP_FROM=vault@example.com        # plain email only — no display name, no angle brackets
VW_SMTP_FROM_NAME=Vaultwarden         # display name shown to recipients
VW_SMTP_PORT=587
VW_SMTP_SECURITY=starttls
VW_SMTP_USERNAME=                     # Brevo: SMTP login (not your account email)
VW_SMTP_PASSWORD=                     # Brevo: SMTP key (not API key, not account password)
```

> **Brevo note:** the SMTP password is the SMTP key found under SMTP & API → SMTP. Use port 587 + starttls. If the invite lands in Junk, check SPF/DKIM/DMARC records and sender domain reputation for your sending domain.

### Step 3: Generate Passwords

```bash
# DB passwords (hex — no special chars that break DATABASE_URL)
sed -i "s|^DB_PASSWORD=.*|DB_PASSWORD=$(openssl rand -hex 32)|" .env
sed -i "s|^DB_ROOT_PASSWORD=.*|DB_ROOT_PASSWORD=$(openssl rand -hex 32)|" .env
```

### Step 4: Generate Admin Token (Argon2 Hash)

```bash
docker run --rm -it vaultwarden/server:1.37.0 /vaultwarden hash
```

Enter a strong password when prompted. Copy the `$argon2id$...` output.

**In .env:** Replace every `$` with `$$` (Docker Compose escaping), then paste:

```env
VW_ADMIN_TOKEN=$$argon2id$$v=19$$m=65540,t=3,p=4$$...your-hash...
```

### Step 5: Start

```bash
docker compose up -d
docker compose logs -f   # Wait for "Starting Vaultwarden" + no errors
```

### Step 6: Create Your Account

1. Open `https://vault.yourdomain.com` in browser
2. Click "Create Account"
3. Register with your email + strong master password
4. Check email for verification link (SMTP must work!)
5. Verify email and login

### Step 7: Harden

After creating your account(s), disable signups:

```bash
# In .env set VW_SIGNUPS_ALLOWED=false, then:
docker compose restart app
```

### Step 8: Configure Admin Panel

Visit `https://vault.yourdomain.com/admin` and enter your admin password.

**Recommended settings:**

| Setting | Value | Why |
|---|---|---|
| Allow new signups | false | Lock down after accounts created |
| Allow password hints | false | Prevent hint-based guessing |
| Block non global IPs | true | Prevent SSRF attacks |
| Disable Two-Factor remember | true | Force 2FA every login |
| Password iterations | 600000 | Strong PBKDF2 (default) |
| Admin session lifetime | 20 | Short admin sessions |

### Step 9: Push Notifications (Optional)

Push improves real-time sync on mobile and browser extensions. It is **not required** for login, SMTP, invites, 2FA, or manual sync.

1. Register free at https://bitwarden.com/host/ — choose **Global** or **EU** host
2. Get `INSTALLATION_ID` and `INSTALLATION_KEY`
3. Set in `.env`:

   **Global host** (default — leave relay URIs empty):

   ```env
   VW_PUSH_ENABLED=true
   VW_PUSH_INSTALLATION_ID=your-id
   VW_PUSH_INSTALLATION_KEY=your-key
   ```

   **EU host** (must set relay URIs — EU credentials without EU URIs cause token errors):

   ```env
   VW_PUSH_ENABLED=true
   VW_PUSH_INSTALLATION_ID=your-eu-id
   VW_PUSH_INSTALLATION_KEY=your-eu-key
   VW_PUSH_RELAY_URI=https://api.bitwarden.eu
   VW_PUSH_IDENTITY_URI=https://identity.bitwarden.eu
   ```

4. `docker compose up -d --force-recreate app`

Only works with official Bitwarden apps (App Store / Google Play, not F-Droid).

### Step 10: Enable 2FA

1. Login to your vault
2. Go to Settings → Security → Two-step login
3. Enable TOTP authenticator (recommended) or YubiKey

## Verify

```bash
docker compose ps                         # All healthy
curl -sI https://your-domain/alive        # 200 OK
curl -sI https://your-domain/admin        # Admin panel loads
```

## TODOs After Initial Setup

- [ ] Signups disabled (`VW_SIGNUPS_ALLOWED=false`)
- [ ] Admin token is Argon2 hash
- [ ] SMTP configured and tested (send test email from admin panel)
- [ ] 2FA enabled on all accounts
- [ ] Push notifications configured (for mobile sync)
- [ ] Backup strategy in place (see UPSTREAM.md)
- [ ] `/admin` restricted to Tailscale only (separate Traefik router — future)
- [ ] Docker Secrets migration (Phase 2 — future)
- [ ] Backup cronjob for MariaDB + data directory

## Diagnostics

### Version check

Visit `/admin` → **Diagnostics** to see installed vs. latest server and web-vault versions. Use it to identify when `APP_TAG` should be reviewed.

### SMTP troubleshooting

After changing SMTP env vars, recreate the app container:

```bash
docker compose up -d --force-recreate app
```

Verify env vars were picked up:

```bash
docker compose exec app sh -c 'env | grep -E "^SMTP_HOST=|^SMTP_FROM=|^SMTP_FROM_NAME=|^SMTP_PORT=|^SMTP_SECURITY=|^SMTP_USERNAME="'
```

Check logs after sending an invite:

```bash
docker compose logs app --tail=200 | grep -iE "smtp|mail|invite|address|error|lettre"
```

End-to-end test: invite a user from **Admin → Users → Invite User**. Verify the email arrives. If it lands in Junk, check SPF/DKIM/DMARC records and sender domain reputation.

### Push notification troubleshooting

Check active push variables (key value hidden):

```bash
docker compose exec app sh -c 'env | grep -E "^PUSH_ENABLED=|^PUSH_RELAY_URI=|^PUSH_IDENTITY_URI=|^PUSH_INSTALLATION_ID="'
docker compose exec app sh -c 'env | grep -q "^PUSH_INSTALLATION_KEY=." && echo "KEY is set" || echo "KEY is empty"'
```

Follow push-related log lines:

```bash
docker compose logs app --follow | grep -iE "push|relay|identity|token"
```

If you see `Unexpected push token received from bitwarden server: error decoding response body`: you are using EU credentials (`bitwarden.eu` registration) without setting the EU relay URIs. Add both `VW_PUSH_RELAY_URI` and `VW_PUSH_IDENTITY_URI` to `.env` and recreate the container.

End-to-end test: change an item in the Web Vault and verify the mobile app or browser extension syncs automatically without a manual refresh.

### Admin panel in browser

If `/admin` returns an error in the normal browser but works in Incognito, clear site data and check browser extensions. Do not treat this as a server-side failure without `curl` or log evidence.

### X-Frame-Options diagnostic

If **Admin → Diagnostics** shows:

```text
2FA Connector calls: Header 'x-frame-options' is present while it should not
```

This means a proxy (Traefik) is injecting `X-Frame-Options`. Vaultwarden must control this header per-route. The `strip-xfo` middleware in `docker-compose.yml` removes it — verify it is present in the Traefik labels.

### HTTP Response validation error

If **Admin → Diagnostics** shows `HTTP Response validation: Error`, check that the domain in `VW_DOMAIN` (derived from `APP_TRAEFIK_HOST`) matches the actual URL used to access the vault, and that HTTPS is enforced end-to-end.

## Backup

| | |
|---|---|
| **Database** | MariaDB · container `vaultwarden-db` · database `vaultwarden` · user `vw_user` |
| **Password** | `DB_PASSWORD` in `.env` — see the note below |
| **State** | `./volumes/mysql` (database) · **`./volumes/data`** — `rsa_key.*`, `attachments/`, `sends/` |
| **Reproducible** | the icon cache inside `./volumes/data` |
| **Quiescing** | Not needed. The dump is consistent on its own. |

```yaml
mariadb_databases:
    - name: vaultwarden
      container: vaultwarden-db
      username: vw_user
      password: "{credential file /srv/docker/apps/vaultwarden/.secrets/db_pwd.txt}"
```

**The credential file does not exist yet.** This stack holds `DB_PASSWORD` in
`.env`. Vaultwarden does support `_FILE`, so this is not an upstream dead end —
the obstacle is that the password sits inside `DATABASE_URL`, a connection
string, so the secret would have to carry the whole URL or an entrypoint would
have to assemble it. Until that happens, supply the value to borgmatic another
way rather than letting two systems read the same password from `.env`.

**`volumes/data/rsa_key.*` signs the authentication tokens.** A database restored
without those files leaves every client unable to log in, with vaults that are
present and inaccessible. They are a handful of small files next to a database
that is useless without them — and the single most common way a Vaultwarden
restore fails.

`attachments/` and `sends/` are referenced from the database and stored as files.
Restore both halves from the same archive.

Manual dump, when borgmatic is not in the picture:

```bash
docker exec -e MYSQL_PWD="$(grep DB_ROOT_PASSWORD .env | cut -d= -f2)" \
  vaultwarden-db mariadb-dump -u root vaultwarden > backup-$(date +%Y%m%d).sql
```

This archive holds everybody's passwords in encrypted form. Encryption at rest in
the borg repository is not optional here, and neither is keeping the repository
somewhere this host cannot delete from.

**Restore order:** database first, then the app.

## Details

- [UPSTREAM.md](UPSTREAM.md) — Security checklist, backup, troubleshooting, upgrade
