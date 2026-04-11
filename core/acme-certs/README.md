# acme-certs

Certificate issuing and renewal tool using [acme.sh](https://github.com/acmesh-official/acme.sh) with Cloudflare DNS-01 challenge.

Use this for devices and services that don't go through Traefik — NAS (Synology, TrueNAS), routers (OPNsense, pfSense), mail servers, or any internal service that needs a valid TLS certificate.

## How It Works

1. A lightweight container runs `crond` in the background for automatic renewal
2. You issue certificates via scripts that run inside the container (`docker compose exec`)
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

## Usage

### Interactive Wizard (recommended)

The wizard prompts for domain, SAN, key type, and ACME server — then issues the certificate:

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

### Issue a Single Domain Certificate

```bash
docker compose exec \
  -e CERT_DOMAIN=mynas.example.com \
  -e CERT_SAN= \
  acme-certs /scripts/issue.sh
```

### Issue a Wildcard Certificate

```bash
docker compose exec \
  -e CERT_DOMAIN=example.com \
  -e CERT_SAN='*.example.com' \
  acme-certs /scripts/issue.sh
```

### Issue a Certificate with Multiple SANs

```bash
docker compose exec \
  -e CERT_DOMAIN=example.com \
  -e CERT_SAN='*.example.com' \
  acme-certs /scripts/issue.sh
```

### Renew a Certificate

```bash
docker compose exec \
  -e CERT_DOMAIN=example.com \
  acme-certs /scripts/renew.sh
```

Renewal also happens automatically via `crond` inside the container.

### Convert to PFX (for Windows, Synology, etc.)

Some devices require PKCS#12 / PFX format instead of PEM:

```bash
docker compose exec acme-certs /scripts/convert-to-pfx.sh example.com MyPassword123
```

## Output

Certificates are exported to `./volumes/output/<domain>/`:

```
volumes/output/example.com/
├── cert.pem          # Server certificate
├── fullchain.pem     # Server cert + intermediate CA
├── privkey.pem       # Private key (chmod 600)
├── ca.pem            # CA certificate
└── example.com.pfx   # PFX format (only after convert-to-pfx.sh)
```

**Most devices need:** `fullchain.pem` + `privkey.pem`

| Device | Files to Upload |
|--------|----------------|
| Synology DSM | Certificate: `fullchain.pem`, Private Key: `privkey.pem` |
| OPNsense / pfSense | Certificate: `cert.pem`, CA: `ca.pem`, Key: `privkey.pem` |
| Windows / IIS | `example.com.pfx` (convert first) |
| Generic / Nginx | `fullchain.pem` + `privkey.pem` |

## Scripts Reference

| Script | Description | Runs on |
|--------|-------------|---------|
| `scripts/wizard.sh` | Interactive certificate wizard | Host |
| `scripts/issue.sh` | Issue a new certificate | Container |
| `scripts/renew.sh` | Renew an existing certificate | Container |
| `scripts/convert-to-pfx.sh` | Convert PEM to PFX format | Container |

**Host scripts** run directly: `./scripts/wizard.sh`
**Container scripts** run via exec: `docker compose exec acme-certs /scripts/...`

## Supported ACME Servers

| Server | Value | Notes |
|--------|-------|-------|
| Let's Encrypt | `letsencrypt` | Default, most common |
| ZeroSSL | `zerossl` | Alternative, needs email registration |
| Buypass | `buypass` | European CA |

## Key Types

| Type | Value | Notes |
|------|-------|-------|
| ECDSA P-256 | `ec-256` | Default, fast, small, recommended |
| ECDSA P-384 | `ec-384` | Stronger, slightly slower |
| RSA 2048 | `2048` | Legacy compatibility |
| RSA 4096 | `4096` | Legacy, large key |
