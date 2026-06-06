---
title: Vaultwarden
description: Self-hosted Bitwarden-compatible password manager on Docker Compose. Setup, hardening, backup, and update guidance.
---

Vaultwarden is a self-hosted password manager compatible with Bitwarden clients — browser extensions, mobile apps, and the desktop client all work with it. It can hold access credentials to everything else you run. Treat the setup, the backup, and the signing keys accordingly.

## Before you start

These must be in place before deploying:

- **Traefik is running** and the `proxy-public` Docker network exists. Vaultwarden connects to Traefik through it.
- **A domain with DNS pointing to your server.** The vault is only accessible over HTTPS.
- **SMTP credentials ready.** Email verification is enabled by default. Without SMTP, account creation fails at the verification step.
- **Access policy decided.** The default configuration (`APP_TRAEFIK_ACCESS=acc-tailscale`) restricts the vault to Tailscale / VPN access only. If you need the vault reachable from the public internet, set `APP_TRAEFIK_ACCESS=acc-public` in `.env` before starting — that is a deliberate architectural choice with implications for your attack surface, not a default.

## Configure

From the `apps/vaultwarden/` directory:

**1. Copy the example configuration:**

```bash
cp .env.example .env
```

**2. Set your domain:**

Open `.env` and set `APP_TRAEFIK_HOST` to your domain (e.g. `vault.example.com`).
Confirm `APP_TRAEFIK_ACCESS` reflects the access policy you decided above.

**3. Configure SMTP — required before the first account:**

```ini
VW_SMTP_HOST=smtp.example.com
VW_SMTP_FROM=vault@yourdomain.com
VW_SMTP_PORT=587
VW_SMTP_SECURITY=starttls
VW_SMTP_USERNAME=your-smtp-user
VW_SMTP_PASSWORD=your-smtp-password
```

**4. Generate database passwords:**

The database connection string requires hex-only passwords (special characters break `DATABASE_URL`).

```bash
sed -i "s|^DB_PASSWORD=.*|DB_PASSWORD=$(openssl rand -hex 32)|" .env
sed -i "s|^DB_ROOT_PASSWORD=.*|DB_ROOT_PASSWORD=$(openssl rand -hex 32)|" .env
```

**5. Generate the admin token (Argon2 hash):**

The admin token must be an Argon2 hash — never plain text. Use the same image version as `APP_TAG` in your `.env`:

```bash
docker run --rm -it vaultwarden/server:${APP_TAG} /vaultwarden hash
```

Enter a strong password when prompted. Copy the full `$argon2id$...` output.

Before pasting into `.env`, replace every `$` with `$$` (Docker Compose escaping):

```ini
VW_ADMIN_TOKEN=$$argon2id$$v=19$$m=65540,t=3,p=4$$...your-hash...
```

**6. Enable signups temporarily:**

`VW_SIGNUPS_ALLOWED` defaults to `false`. Set it to `true` now — you will disable it again after creating your account.

## Start

```bash
docker compose up -d
docker compose logs -f
```

MariaDB starts first and runs a health check. Vaultwarden waits for the database to be healthy before starting. Wait until you see `Starting Vaultwarden` in the logs with no errors.

## First checks

```bash
docker compose ps                      # Both containers should show healthy
curl -sI https://your-domain/alive     # Expect 200 OK
curl -sI https://your-domain/admin     # Admin panel should respond
```

Open `https://your-domain` in a browser. The login page should load over TLS 1.3.

## First account and signup hardening

1. Click **Create Account** on the login page.
2. Register with your email and a strong master password.
3. Check your email for the verification link — this requires working SMTP.
4. Verify your email and log in.

**Disable signups immediately after creating your account(s).**

In `.env`, set:

```ini
VW_SIGNUPS_ALLOWED=false
```

Then restart the app:

```bash
docker compose restart app
```

Confirm it is locked: the "Create Account" option should no longer appear on the login page.

**Admin panel settings:**

Visit `https://your-domain/admin` and enter your admin password. Verify these settings:

| Setting | Recommended | Why |
|---|---|---|
| Allow new signups | false | Closed after accounts are created |
| Allow password hints | false | Prevent hint-based credential guessing |
| Block non-global IPs | true | SSRF protection |
| Disable 2FA remember | true | Force 2FA re-entry on every login |

For the full settings table, see [`apps/vaultwarden/README.md`](https://github.com/rubennati/secure-docker-blueprint/blob/main/apps/vaultwarden/README.md).

**Enable 2FA on your account:**

Go to Settings → Security → Two-step login and enable TOTP or YubiKey.

## Backup before real use

Do not add real credentials to the vault before a working backup is in place.

**What must be backed up:**

- `volumes/mysql/` — the MariaDB data directory
- `volumes/data/attachments/` — vault file attachments
- `volumes/data/rsa_key.*` — signing keys; without these, existing sessions and tokens break after restore even if the database is intact
- `volumes/data/sends/` — Send feature data

**Manual MariaDB backup:**

```bash
docker exec -e MYSQL_PWD="$(grep DB_ROOT_PASSWORD .env | cut -d= -f2)" \
  vaultwarden-db mariadb-dump -u root vaultwarden > backup-$(date +%Y%m%d).sql
```

No automated backup integration is included in this Blueprint yet. Set up a scheduled job for the dump command and the data directories before relying on this deployment.

## Restore

Restoring Vaultwarden is not the same as reinstalling Vaultwarden.

A reinstall gives you an empty database. A restore requires the MariaDB dump, the RSA signing keys (`rsa_key.*`), and any attachments — in a consistent state from the same point in time. Missing the signing keys means existing sessions will not work even with a correct database.

No complete tested restore procedure is documented for this Blueprint yet. Do not treat a backup as a recovery plan until you have verified that restore works end-to-end on a test instance.

## Updates

1. Check the [Vaultwarden releases page](https://github.com/dani-garcia/vaultwarden/releases) for breaking changes.
2. Read the release notes.
3. Back up the database before upgrading (see Backup section above).
4. Update `APP_TAG` in `.env` to the new version.
5. Pull and restart:
   ```bash
   docker compose pull
   docker compose up -d
   ```
6. Verify: check `/alive` and log in to the vault.

## Troubleshooting

**Container not starting:**

```bash
docker compose logs app
docker compose logs db
```

Common causes: SMTP variables empty (not required to start, but check for misconfiguration errors), MariaDB not yet healthy — the app waits for it, incorrect `$$` escaping in `VW_ADMIN_TOKEN`.

**Login page not loading:**

```bash
curl -sI https://your-domain/alive
docker compose ps
```

If the app container shows healthy but the page does not load, check Traefik logs and confirm `APP_TRAEFIK_HOST` matches your DNS record exactly.

**Email verification not arriving:**

Test SMTP from the admin panel — open `/admin`, go to Settings, and send a test email. Check your SMTP provider's outbound send log if the test fails.

## Repository files

- [`apps/vaultwarden/README.md`](https://github.com/rubennati/secure-docker-blueprint/blob/main/apps/vaultwarden/README.md) — full setup steps and admin panel settings table
- [`apps/vaultwarden/.env.example`](https://github.com/rubennati/secure-docker-blueprint/blob/main/apps/vaultwarden/.env.example) — all configurable variables
- [`apps/vaultwarden/docker-compose.yml`](https://github.com/rubennati/secure-docker-blueprint/blob/main/apps/vaultwarden/docker-compose.yml) — compose stack
- [`apps/vaultwarden/UPSTREAM.md`](https://github.com/rubennati/secure-docker-blueprint/blob/main/apps/vaultwarden/UPSTREAM.md) — upstream notes, security checklist, backup, and upgrade steps
