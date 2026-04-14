# Vaultwarden

Self-hosted Bitwarden-compatible password manager.

## Services

| Service | Image | Purpose |
|---|---|---|
| app | vaultwarden/server | Password manager |
| db | mariadb | Database |

## Security

- TLS 1.3 only (`tls-modern`)
- Rate limiting on login + admin panel
- Signups disabled after initial account creation
- Admin token as Argon2 hash (never plain text)
- `read_only` container + `no-new-privileges`
- Password hints disabled

## Quick Start

```bash
# 1. Copy and configure
cp .env.example .env
nano .env  # Set domain, SMTP

# 2. Generate passwords
sed -i "s|^DB_PASSWORD=.*|DB_PASSWORD=$(openssl rand -base64 32 | tr -d '\n')|" .env
sed -i "s|^DB_ROOT_PASSWORD=.*|DB_ROOT_PASSWORD=$(openssl rand -base64 32 | tr -d '\n')|" .env

# 3. Generate admin token (Argon2 hash)
docker run --rm -it vaultwarden/server:1.35.7 /vaultwarden hash
# Copy output, replace $ with $$ in .env

# 4. Start with signups enabled
# Set VW_SIGNUPS_ALLOWED=true in .env
docker compose up -d

# 5. Register your account at https://vault.example.com

# 6. Disable signups
# Set VW_SIGNUPS_ALLOWED=false in .env
docker compose restart app
```

## Verify

```bash
docker compose ps
curl -sI https://your-domain/alive    # 200 OK
```

## Details

- [UPSTREAM.md](UPSTREAM.md) — Security checklist, backup, push notifications, upgrade
