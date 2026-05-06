# Dolibarr

> **Status: 🚧 Draft** First-pass import from inbox material.

Open-source ERP / CRM — invoicing, bookkeeping, project management, HR, inventory. Two-service stack: tuxgasy/dolibarr app + MariaDB.

## Architecture

| Service | Image | Purpose |
|---------|-------|---------|
| `app` | `tuxgasy/dolibarr:latest` | PHP/Apache app with Dolibarr pre-installed |
| `db` | `mariadb:11.4` | Primary store (customers, invoices, products, accounting entries) |

## Setup

```bash
# 1. Create .env
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, TZ

# 2. Generate DB + admin secrets
mkdir -p .secrets
openssl rand -base64 32 | tr -d '\n' > .secrets/db_pwd.txt
openssl rand -base64 32 | tr -d '\n' > .secrets/db_root_pwd.txt
echo "admin" > .secrets/doli_admin.txt
openssl rand -base64 24 | tr -d '\n' > .secrets/doli_pass.txt
echo "Initial admin password: $(cat .secrets/doli_pass.txt)"

# 3. Create volumes
mkdir -p volumes/mysql volumes/documents volumes/custom

# 4. Start
docker compose up -d

# 5. Wait for first-run install (~90 seconds)
docker compose logs app --follow
# Watch for: "apache2 -D FOREGROUND"

# 6. Open UI and log in
# https://<APP_TRAEFIK_HOST>
# Username/password from .secrets/doli_admin.txt and .secrets/doli_pass.txt
```

## Verify

```bash
docker compose ps                              # both services healthy
curl -fsSI https://<APP_TRAEFIK_HOST>/         # 200 OK (or 302 to /install/ on first run)
```

## Security Model

- **`tuxgasy/dolibarr` supports `_FILE` on every secret env var** — DB password, admin login, and admin password are all Docker Secrets. No inline duplication anywhere.
- **Admin credentials created on first install** — the secret files `.secrets/doli_admin.txt` + `.secrets/doli_pass.txt` seed the initial super-user. Change the password in the UI afterwards; the secrets are only re-read if the DB is empty.
- **`cap_drop: ALL`** on MariaDB with minimal `cap_add`.
- **`no-new-privileges:true`** on both services.
- **MariaDB on `app-internal` (`internal: true`)** — not reachable from outside.
- **Default access `acc-tailscale` + `sec-3`** — ERPs hold all of your business data (invoices, customer details, financials). VPN-only is the right default; switch to `acc-public + sec-3` only with `sec-crowdsec` + 2FA.

## Known Issues

- **Live-tested: no.** Expect minor surprises, especially first-install behaviour if volumes aren't empty.
- **`APP_TAG=latest` is not reproducible** — pin to a specific Dolibarr version for stable deployments. tuxgasy publishes tags like `21.0.0` that follow Dolibarr's semver.
- **Custom modules** — stored in `volumes/custom/`. Install via the UI → the module tarball is unpacked here. Back up together with the documents volume.
- **Document attachments** — PDFs, scanned invoices, etc. go into `volumes/documents/`. Can grow large; plan backups and storage accordingly.
- **Upgrades run on first boot after a version bump** — Dolibarr detects the version difference and triggers a schema migration through a web wizard at `/install/`. Do not clear browser cookies during the migration.

## Details

- [UPSTREAM.md](UPSTREAM.md)
