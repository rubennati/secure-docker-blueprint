# Upstream Reference

## Source

- **Repo:** https://github.com/dani-garcia/vaultwarden
- **Wiki:** https://github.com/dani-garcia/vaultwarden/wiki
- **License:** GPL-3.0
- **Origin:** Community · unofficial Bitwarden reimplementation · no single company
- **Based on version:** 1.35.7
- **Last checked:** 2026-04-14

## What we changed and why

| Change | Reason |
|--------|--------|
| MariaDB instead of SQLite | More robust for concurrent access, better backup tooling |
| Passwords in .env (not Secrets) | Phase 1 — Vaultwarden has no _FILE support. Secrets planned for Phase 2 |
| ADMIN_TOKEN as Argon2 hash | Official recommendation — never store plain text |
| `read_only: true` + `no-new-privileges` | Security hardening |
| `tls-modern` (TLS 1.3 only) | Password manager deserves strictest TLS |
| `sec-4` security middleware | Rate limiting + strict headers |
| `PASSWORD_HINTS_ALLOWED=false` | Prevent hint-based guessing |
| `SIGNUPS_VERIFY=true` | Require email verification |
| Rate limiting configured | Login + Admin panel rate limiting |
| WebSocket via Traefik | Automatic since v1.29, Traefik passes upgrades natively |

## Security Checklist

After deployment, verify:

- [ ] `SIGNUPS_ALLOWED=false` (set after creating your accounts)
- [ ] `ADMIN_TOKEN` is Argon2 hash (not plain text)
- [ ] TLS 1.3 only (`tls-modern`)
- [ ] SMTP configured (needed for 2FA recovery)
- [ ] Admin panel accessible and rate-limited
- [ ] Push notifications working (if mobile sync needed)
- [ ] Backup strategy in place (see below)
- [ ] Domain is not obviously named (e.g., not `bitwarden.example.com`)

## Backup

**Critical files to back up:**
- `volumes/data/db.sqlite3` (if using SQLite)
- `volumes/mysql/` (if using MariaDB)
- `volumes/data/attachments/`
- `volumes/data/rsa_key.*` (signing keys — without these, tokens break)
- `volumes/data/sends/` (if using Send feature)

```bash
# MariaDB backup (password via env var, not visible in process list)
docker exec -e MYSQL_PWD="$(grep DB_ROOT_PASSWORD .env | cut -d= -f2)" \
  vaultwarden-db mariadb-dump -u root vaultwarden > backup-$(date +%Y%m%d).sql
```

## First-time setup

```bash
# 1. Copy and configure
cp .env.example .env
nano .env  # Set APP_TRAEFIK_HOST, SMTP settings

# 2. Generate DB passwords
# hex only — base64 chars +/= break DATABASE_URL
sed -i "s|^DB_PASSWORD=.*|DB_PASSWORD=$(openssl rand -hex 32)|" .env
sed -i "s|^DB_ROOT_PASSWORD=.*|DB_ROOT_PASSWORD=$(openssl rand -hex 32)|" .env

# 3. Generate Argon2 admin token
docker run --rm -it vaultwarden/server:1.35.7 /vaultwarden hash
# Enter a strong password, copy the $argon2id$... output
# In .env: replace every $ with $$ then paste as VW_ADMIN_TOKEN

# 4. Start
docker compose up -d

# 5. Create your account (SIGNUPS_ALLOWED must be true for this)
# Visit https://vault.example.com and register

# 6. Disable signups
# Set VW_SIGNUPS_ALLOWED=false in .env
docker compose restart app
```

## Verify

```bash
docker compose ps                                    # All healthy
curl -sI https://your-domain/alive                   # 200 OK
curl -sI https://your-domain/admin                   # Admin panel loads
docker exec vaultwarden-app curl -s http://127.0.0.1:80/alive  # Internal check
```

## Push Notifications

Free registration at https://bitwarden.com/host/:
1. Enter any email
2. Get `INSTALLATION_ID` and `INSTALLATION_KEY`
3. Set in .env:
   ```env
   VW_PUSH_ENABLED=true
   VW_PUSH_INSTALLATION_ID=your-id
   VW_PUSH_INSTALLATION_KEY=your-key
   ```
4. `docker compose restart app`

Only works with official Bitwarden apps (App Store / Google Play, not F-Droid).

## Upgrade checklist

1. Check [Vaultwarden releases](https://github.com/dani-garcia/vaultwarden/releases)
2. Read release notes for breaking changes
3. **Back up database before upgrading**
4. Bump `APP_TAG` in `.env`
5. `docker compose pull` → `docker compose up -d`
6. Check `/alive` and login
