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
VW_SMTP_HOST=smtp-relay.brevo.com    # or your SMTP provider
VW_SMTP_FROM=vault@yourdomain.com
VW_SMTP_PORT=587
VW_SMTP_SECURITY=starttls
VW_SMTP_USERNAME=your-smtp-user
VW_SMTP_PASSWORD=your-smtp-password
```

### Step 3: Generate Passwords

```bash
# DB passwords (hex — no special chars that break DATABASE_URL)
sed -i "s|^DB_PASSWORD=.*|DB_PASSWORD=$(openssl rand -hex 32)|" .env
sed -i "s|^DB_ROOT_PASSWORD=.*|DB_ROOT_PASSWORD=$(openssl rand -hex 32)|" .env
```

### Step 4: Generate Admin Token (Argon2 Hash)

```bash
docker run --rm -it vaultwarden/server:1.35.7 /vaultwarden hash
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

For real-time mobile sync:

1. Register free at https://bitwarden.com/host/
2. Get `INSTALLATION_ID` and `INSTALLATION_KEY`
3. Set in `.env`:
   ```env
   VW_PUSH_ENABLED=true
   VW_PUSH_INSTALLATION_ID=your-id
   VW_PUSH_INSTALLATION_KEY=your-key
   ```
4. `docker compose restart app`

Only works with official Bitwarden apps (App Store / Google Play).

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

## Details

- [UPSTREAM.md](UPSTREAM.md) — Security checklist, backup, troubleshooting, upgrade
