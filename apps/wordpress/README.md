# WordPress

WordPress CMS with MariaDB database, PHP security hardening, and Apache .htaccess protection.

## Setup

```bash
# 1. Create .env
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, TZ

# 2. Generate secrets
mkdir -p .secrets
openssl rand -base64 32 | tr -d '\n' > .secrets/db_pwd.txt
openssl rand -base64 32 | tr -d '\n' > .secrets/db_root_pwd.txt

# 3. Start
docker compose up -d

# 4. Open https://your-domain.com and run the WordPress installer

# 5. Apply .htaccess hardening (after WordPress installer finishes)
docker compose exec app bash -c 'cat /config/.htaccess-security >> /var/www/html/.htaccess'
```

## Plugin Recommendations

Minimal plugin approach — only what's needed, everything else removed. Every plugin is attack surface.

### Core — Always Install

| Plugin | Purpose | Notes |
|--------|---------|-------|
| **FluentSMTP** | Email delivery | Brevo, Amazon SES, or any SMTP relay |
| **Two Factor** | Login 2FA (TOTP) | Not negotiable. FIDO2/YubiKey preferred |
| **Real Cookie Banner** | DSGVO/GDPR compliance | Pro recommended for tracking pixels |
| **WPvivid Backup** | Automated backups | Target: Hetzner Storage Box (SFTP) or S3 |
| **SEO Plugin** | Sitemap, robots.txt, meta tags | Rank Math or Yoast SEO — pick one |

### wp-admin Protection — Pick One Tier

| Tier | Who accesses wp-admin | Plugins needed | Infra |
|------|----------------------|----------------|-------|
| **Public + Plugins** | Mitarbeiter, Kunden, von überall | WPS Hide Login + WPS Limit Login + Cloudflare Turnstile + Two Factor | Standard Traefik sec-2 |
| **Public + Authentik** | Mitarbeiter mit SSO | Two Factor (Authentik handles the rest) | Authentik Forward Auth auf `/wp-admin` |
| **Tailscale-only** | Nur du, internes Tool | Two Factor (Plugins entfernbar) | `acc-tailscale` Router auf `/wp-admin` |

**Tier 1 is the default** for the Blueprint — most WordPress sites have external users accessing wp-admin.

When using Tier 2 or 3, these plugins become redundant and should be removed:
- WPS Hide Login (login URL already hidden behind auth/VPN)
- WPS Limit Login (rate limiting at Traefik/CrowdSec level)
- Cloudflare Turnstile (no bots reach wp-admin)

### Optional — Evaluate Per Site

| Plugin | Purpose | When to use |
|--------|---------|-------------|
| Simple Cloudflare Turnstile | CAPTCHA for forms/comments | Public sites with comment forms |
| WPS Hide Login | Obscure `/wp-login.php` URL | Tier 1 only (not needed with Authentik/Tailscale) |
| WPS Limit Login | Brute-force protection | Tier 1 only (Traefik + CrowdSec handle this otherwise) |
| Matomo | Privacy-friendly analytics | Self-hosted alternative to Google Analytics |

### Avoid

| Plugin | Why |
|--------|-----|
| Jetpack Protect | External Automattic connection, increases attack surface |
| WP Super Cache | CVE history; caching should be at proxy level |
| Wordfence | Heavy, duplicates what Traefik + CrowdSec already do |

## security.txt

Every public website should have a `/.well-known/security.txt` file ([RFC 9116](https://www.rfc-editor.org/rfc/rfc9116)). It tells security researchers how to report vulnerabilities.

Create `volumes/wordpress/.well-known/security.txt` after first start:

```bash
docker compose exec app mkdir -p /var/www/html/.well-known
docker compose exec app tee /var/www/html/.well-known/security.txt > /dev/null << 'EOF'
Contact: mailto:security@example.com
Expires: 2027-04-15T00:00:00.000Z
Preferred-Languages: en, de
Canonical: https://example.com/.well-known/security.txt
EOF
```

Adjust `Contact`, `Expires` (max 1 year), and `Canonical` URL. The file is served by Apache directly — no plugin needed.

Some SEO plugins (Rank Math) can also generate and manage security.txt through the dashboard.

## wp-config.php Hardening

After the WordPress installer finishes, add these constants. Either via wp-cli or by editing the file:

```bash
# Via wp-cli (recommended)
docker compose exec app wp config set DISALLOW_FILE_EDIT true --raw --allow-root
docker compose exec app wp config set WP_AUTO_UPDATE_CORE minor --allow-root
```

| Constant | Value | What it does |
|----------|-------|-------------|
| `DISALLOW_FILE_EDIT` | `true` | Disables Theme/Plugin Editor in dashboard (code editing) |
| `DISALLOW_FILE_MODS` | `true` | Disables ALL file changes via dashboard (use only with MainWP) |
| `WP_AUTO_UPDATE_CORE` | `minor` | Auto-update security patches only |

**Note:** `DISALLOW_FILE_MODS` blocks plugin uploads via dashboard. Only enable this when using MainWP or wp-cli for all plugin management.

## .htaccess Hardening

A security template is provided in `config/apache/.htaccess-security`. It blocks:
- PHP execution in `/wp-content/uploads/` (prevents uploaded shells)
- Direct access to `wp-config.php`, `.htaccess`, `readme.html`
- Directory listing
- XML-RPC (`xmlrpc.php` — used for brute-force and DDoS amplification)
- Author enumeration (`?author=1` scans)

Apply after WordPress installer finishes:

```bash
docker compose exec app bash -c 'cat /config/.htaccess-security >> /var/www/html/.htaccess'
```

**Important:** Append to the END of `.htaccess` — never edit the `# BEGIN WordPress` / `# END WordPress` block.

## PHP Security

`config/php/uploads.ini` sets:

| Setting | Value | Why |
|---------|-------|-----|
| `upload_max_filesize` | 64M | Allow plugin/theme uploads |
| `post_max_size` | 64M | Match upload limit |
| `memory_limit` | 256M | Prevent out-of-memory on large pages |
| `expose_php` | Off | Hides PHP version from HTTP headers |
| `disable_functions` | exec, shell_exec, system, ... | Prevents PHP shells from running system commands |

If a plugin breaks due to `disable_functions`, check which function it needs and selectively re-enable only that one.

## File Access

WordPress files live in `./volumes/wordpress/`. They are owned by `www-data` (UID 33):

```bash
# Shell into the container
docker compose exec app bash

# wp-cli
docker compose exec app wp plugin list --allow-root

# From host (needs sudo)
sudo nano ./volumes/wordpress/wp-config.php
```

## Verify

```bash
docker compose ps                    # Both services healthy
docker compose logs app              # No PHP errors
docker compose exec app wp --info --allow-root   # PHP + wp-cli version
```

## Details

- [UPSTREAM.md](UPSTREAM.md) — Upstream reference, upgrade checklist
