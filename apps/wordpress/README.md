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

### wp-admin Protection

Three realistic scenarios. Pick the one that fits the site:

| Scenario | Frontend | wp-admin | Security Plugins | Infra |
|----------|----------|----------|-----------------|-------|
| **A: Public site, public admin** | Public | Public (employees, clients) | WPS Hide Login, WPS Limit Login, Turnstile, Two Factor | sec-2, acc-public |
| **B: Public site, admin VPN-only** | Public | Tailscale only (single admin) | Two Factor only (rest redundant) | Two Traefik routers: public + acc-tailscale on `/wp-admin` |
| **C: Fully internal** | Tailscale | Tailscale (e.g. MainWP Dashboard) | Two Factor only | acc-tailscale on entire site |

**Scenario A is the most common** — use this when multiple people need wp-admin access from different locations.

**Scenario B** is ideal for personal/company sites where only the owner manages content. The public frontend works normally, but wp-admin is only reachable via VPN. This eliminates the need for Hide Login, Limit Login, and CAPTCHA plugins.

**Scenario C** is for management tools like MainWP that should never be public.

When wp-admin is behind Tailscale or Authentik (Scenario B/C), these plugins are redundant:
- WPS Hide Login — login URL is already unreachable
- WPS Limit Login — no brute-force possible, Traefik + CrowdSec handle rate limiting
- Cloudflare Turnstile — no bots reach the login page

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

## Security Hardening (mu-plugin)

A must-use plugin is mounted from `config/mu-plugins/security-hardening.php`. It is loaded automatically and cannot be deactivated via the dashboard.

What it does:

| Protection | What it prevents |
|------------|-----------------|
| REST API blocked for anonymous | User enumeration via `/wp-json/wp/v2/users` |
| Generator meta tag removed | WordPress version leak in HTML source |
| RSS generator removed | WordPress version leak in RSS feeds |
| Version query strings removed | Version leak from `?ver=` on CSS/JS files |
| Generic login errors | Username/password guessing ("Invalid credentials" for both) |
| XML-RPC disabled | Brute-force and DDoS amplification via `xmlrpc.php` |

This makes it significantly harder for scanners and bots to detect WordPress or enumerate users. Combined with WPS Hide Login (Tier A), the login page URL is also obscured.

**What still reveals WordPress:** The `/wp-content/` and `/wp-includes/` paths are visible in the HTML source. Fully hiding WordPress would require rewriting all URLs — this is not recommended as it breaks plugins and updates.

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
