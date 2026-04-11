# acme-certs

Certificate issuing and renewal tool using [acme.sh](https://github.com/acmesh-official/acme.sh) with Cloudflare DNS-01 challenge.

Use this for devices and services that don't go through Traefik — NAS (Synology, TrueNAS), routers (OPNsense, pfSense), mail servers, or any internal service that needs a valid TLS certificate.

## How It Works

1. A lightweight container runs `crond` in the background for automatic renewal
2. You issue certificates via the **wizard** or manual commands
3. Certificates are exported to `./volumes/output/<domain>/` as standard PEM files
4. The Cloudflare API token is stored as a Docker Secret, never in environment variables

## Setup

```bash
# 1. Create .env
cp .env.example .env
# Edit: ACME_EMAIL, CERT_DOMAIN

# 2. Create Cloudflare API token secret
#    Token needs: Zone > DNS > Edit on the target zone
#    Use a scoped API Token, NOT the Global API Key
mkdir -p secrets
echo 'your-cloudflare-api-token' > secrets/cf_token.txt

# 3. Start the container
docker compose up -d
```

## Issuing Certificates

### Using the Wizard (recommended)

The wizard walks you through everything interactively:

```bash
./scripts/wizard.sh
```

```
Certificate Wizard
==================

Domain [example.com]: mynas.example.com
Wildcard / SAN (leave empty for none) [*.example.com]:
Key type [ec-256|ec-384|2048|3072|4096] [ec-256]:
ACME server [letsencrypt|zerossl|buypass] [letsencrypt]:

Configuration:
  Domain:     mynas.example.com
  SAN:        <none>
  Key type:   ec-256
  ACME:       letsencrypt

Issue certificate now? [y/N]: y
```

That's it — the certificate files appear in `./volumes/output/mynas.example.com/`.

### Using Manual Commands (for scripting/automation)

If you want to skip the wizard and issue certificates directly:

```bash
# Single domain
docker compose exec \
  -e CERT_DOMAIN=mynas.example.com \
  -e CERT_SAN= \
  acme-certs /scripts/issue.sh

# Domain + wildcard
docker compose exec \
  -e CERT_DOMAIN=example.com \
  -e CERT_SAN='*.example.com' \
  acme-certs /scripts/issue.sh
```

## Renewal

Certificates are **renewed automatically** by crond inside the container.

To trigger a manual renewal:

```bash
docker compose exec \
  -e CERT_DOMAIN=example.com \
  acme-certs /scripts/renew.sh
```

## Output

Certificates are exported to `./volumes/output/<domain>/`:

```
volumes/output/example.com/
├── cert.pem          # Server certificate
├── fullchain.pem     # Server cert + intermediate CA
├── privkey.pem       # Private key (chmod 600)
└── ca.pem            # CA certificate
```

**Most devices need:** `fullchain.pem` + `privkey.pem`

## Importing Certificates

| Device | What to Upload |
|--------|---------------|
| **Synology DSM** | Certificate: `fullchain.pem`, Private Key: `privkey.pem` |
| **OPNsense / pfSense** | Certificate: `cert.pem`, CA: `ca.pem`, Key: `privkey.pem` |
| **Generic / Nginx** | `fullchain.pem` + `privkey.pem` |
| **Windows / IIS** | Needs PFX format — see below |

### PFX Conversion (Windows, IIS, .NET)

Some devices don't accept PEM files. They need PFX (PKCS#12) — a single file that bundles the certificate and private key, protected by a password you choose:

```bash
docker compose exec acme-certs \
  /scripts/convert-to-pfx.sh example.com your-chosen-password
```

This creates `./volumes/output/example.com/example.com.pfx`. When importing the PFX on the device, enter the same password you chose above.

## Scripts Reference

| Script | Run with | Description |
|--------|----------|-------------|
| `scripts/wizard.sh` | `./scripts/wizard.sh` | Interactive wizard (runs on host) |
| `scripts/issue.sh` | `docker compose exec ...` | Issue new certificate |
| `scripts/renew.sh` | `docker compose exec ...` | Renew existing certificate |
| `scripts/convert-to-pfx.sh` | `docker compose exec ...` | Convert PEM → PFX |

## Configuration Reference

### ACME Servers

| Server | Value | Notes |
|--------|-------|-------|
| Let's Encrypt | `letsencrypt` | Default, most common |
| ZeroSSL | `zerossl` | Alternative, needs email registration |
| Buypass | `buypass` | European CA |

### Key Types

| Type | Value | Notes |
|------|-------|-------|
| ECDSA P-256 | `ec-256` | Default — fast, small, recommended |
| ECDSA P-384 | `ec-384` | Stronger, slightly slower |
| RSA 2048 | `2048` | Legacy compatibility |
| RSA 4096 | `4096` | Legacy, large key |
