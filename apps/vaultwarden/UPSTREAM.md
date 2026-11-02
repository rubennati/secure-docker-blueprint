# Upstream Reference

## Source

- **Repo:** https://github.com/dani-garcia/vaultwarden
- **Wiki:** https://github.com/dani-garcia/vaultwarden/wiki
- **License:** AGPL-3.0 — `LICENSE.txt` upstream is the GNU **Affero** GPL v3, not the plain GPL recorded here; §13 obliges an operator to offer source to users reaching it over a network
- **Decision facts checked:** not yet
- **Origin:** Community · unofficial Bitwarden reimplementation · no single jurisdiction
- **Domain:** Identity, access and secrets
- **Role:** Password manager: logins, TOTP and shared collections
- **Based on version:** `1.37.4`
- **Last verified:** 2026-11-02 (1.37.4) — step 8 lab host behind Traefik 3.7.17 with MariaDB 11.4: registration through the e-mail token flow with `apps/mailpit` as the SMTP sink, password-grant login, sync and a created item through the client API (a lab script; no official client run), WebSocket notifications (101 with a token, 401 without), the admin panel's Argon2 token (401 wrong, session on right), signups off refusing a new registration, Vaultwarden's own `X-Frame-Options` passed through; restored from a borgmatic archive into a throwaway instance (docs/labs/ingress/2026-11-01-results.md)

## What we changed and why

| Change | Reason |
|--------|--------|
| MariaDB instead of SQLite | More robust for concurrent access, better backup tooling |
| Passwords in .env (not Secrets) | Phase 2 open. **Vaultwarden does support `_FILE`** — confirmed against the upstream configuration wiki on 2026-07-27; this entry previously claimed it does not, and whether that was wrong when written or went stale could not be established from the release notes. The genuine obstacle is narrower: the password sits inside `DATABASE_URL`, a connection string, so the secret has to carry the whole URL (`DATABASE_URL_FILE`) or an entrypoint has to assemble it — the pattern this repository already uses elsewhere. A real option, not a blocked path |
| ADMIN_TOKEN as Argon2 hash | Official recommendation — never store plain text |
| `read_only: true` + `no-new-privileges` | Security hardening |
| `tls-strict` (TLS 1.3 only) | Password manager deserves strictest TLS — named by the router's `tls.options` label as a documented exception |
| `headers-application-owned` + `limit-standard` | Vaultwarden sends its own headers (`nosniff`, a frame header per route, a referrer policy, a Permissions-Policy, an enforcing CSP — measured 2026-10-18); the proxy sets only the HSTS base, so Vaultwarden controls `X-Frame-Options` per-route (required by admin diagnostics) |
| `PASSWORD_HINTS_ALLOWED=false` | Prevent hint-based guessing |
| `SIGNUPS_VERIFY=true` | Require email verification |
| Rate limiting configured | Login + Admin panel rate limiting |
| WebSocket via Traefik | Automatic since v1.29, Traefik passes upgrades natively |

## Security Checklist

After deployment, verify:

- [ ] `SIGNUPS_ALLOWED=false` (set after creating your accounts)
- [ ] `ADMIN_TOKEN` is Argon2 hash (not plain text)
- [ ] TLS 1.3 only (`tls-strict`)
- [ ] SMTP configured (needed for 2FA recovery)
- [ ] Admin panel accessible and rate-limited
- [ ] Push notifications working (if mobile sync needed)
- [ ] Backup strategy in place (see below)
- [ ] Domain is not obviously named (e.g., not `bitwarden.example.com`)

## Backup

Owned by [`README.md`](README.md#backup) — engine, container, which volumes
hold state, and the borgmatic block. Kept there because that is where the
per-app backup pattern lives and what `lifecycle-report.py` reads.

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
docker run --rm -it vaultwarden/server:1.37.0 /vaultwarden hash
# Enter a strong password, copy the $argon2id$... output
# In .env: replace every $ with $$ then paste as VW_ADMIN_TOKEN

# 4. Start
docker compose up -d

# 5. Create your account (SIGNUPS_ALLOWED must be true for this)
# Visit https://vault.example.com and register

# 6. Disable signups
# Set VW_SIGNUPS_ALLOWED=false in .env, then recreate — restart alone does not
# pick up an .env change
docker compose up -d --force-recreate vaultwarden-app
```

## Verify

```bash
docker compose ps                                    # All healthy
curl -sI https://your-domain/alive                   # 200 OK
curl -sI https://your-domain/admin                   # Admin panel loads
docker exec vaultwarden-app curl -s http://127.0.0.1:80/alive  # Internal check
```

## Push Notifications

Push does not send the vault to Bitwarden — it only notifies a client that
something changed, so the client then syncs against this instance. Free
registration at https://bitwarden.com/host/:

1. Choose **Global** or **EU** host, and use a real, monitored email address —
   Bitwarden uses it to notify about out-of-date server versions
2. Get `INSTALLATION_ID` and `INSTALLATION_KEY`
3. Set in .env:

   **Global host** (default — leave relay URIs empty):

   ```env
   VW_PUSH_ENABLED=true
   VW_PUSH_INSTALLATION_ID=your-id
   VW_PUSH_INSTALLATION_KEY=your-key
   ```

   **EU host** (must set relay URIs — EU credentials without EU URIs cause
   token errors):

   ```env
   VW_PUSH_ENABLED=true
   VW_PUSH_INSTALLATION_ID=your-eu-id
   VW_PUSH_INSTALLATION_KEY=your-eu-key
   VW_PUSH_RELAY_URI=https://api.bitwarden.eu
   VW_PUSH_IDENTITY_URI=https://identity.bitwarden.eu
   ```

4. `docker compose up -d --force-recreate vaultwarden-app`

Only works with official Bitwarden apps (App Store / Google Play, not F-Droid).
Upstream reference:
[Enabling Mobile Client Push Notification](https://github.com/dani-garcia/vaultwarden/wiki/Enabling-Mobile-Client-push-notification).

## Version notes

- Moved to `1.37.4` on 2026-10-31 (released 2026-10-05), not run at this tag. A
  security release: GHSA-69q9-v8p6-xvx3 (high, 8.1), GHSA-7jg8-8m5x-6j9r,
  GHSA-v576-3wvq-xh3c, GHSA-q5x6-grh5-fqgc, GHSA-64mc-4p6f-r7x9,
  GHSA-7ccc-c43j-4p36 and GHSA-qwx4-wcv4-mpcv; upstream advises rotating an
  organisation's API key. Behaviour changes: with `IP_HEADER=X-Forwarded-For` the
  client address is the rightmost one outside `IP_HEADER_TRUSTED_PROXIES` — this
  stack sets `IP_HEADER: X-Real-IP`, which Traefik writes, so the change does not
  reach it; the legacy `POST /identity/accounts/register` and
  `POST /api/accounts/prelogin` are removed; the feature flags are removed and
  `EXPERIMENTAL_CLIENT_FEATURE_FLAGS` only warns (not set here); `DUO_USE_IFRAME`
  is ignored (not set here); `MARIADB_TLS_DISABLE_PEER_VERIFICATION` is new.

## Upgrade checklist

1. Check [Vaultwarden releases](https://github.com/dani-garcia/vaultwarden/releases)
2. Read release notes for breaking changes
3. **Back up database before upgrading**
4. Bump `APP_TAG` in `.env`
5. `docker compose pull` → `docker compose up -d`
6. Check `/alive` and login
