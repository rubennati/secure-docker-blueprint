# .env File Standard

Verbindliche Konventionen für alle `.env.example` und `.env` Dateien in diesem Blueprint.

## Sektionen-Reihenfolge

Jede `.env.example` folgt dieser Struktur:

```env
# =============================================
# {App Name} – Environment
# =============================================
# Copy this file to .env and adjust all values.
# NEVER commit the .env file.
# =============================================

# --- Images ---
APP_IMAGE=wordpress:6.7-php8.3-apache
DB_IMAGE=mariadb:11.4

# --- Container ---
CONTAINER_NAME_APP=wordpress-app
CONTAINER_NAME_DB=wordpress-db

# --- General ---
TIMEZONE=Europe/Vienna
COMPOSE_PROJECT_NAME=wordpress

# --- Network ---
# (nur wenn app-spezifische Netzwerk-Konfiguration nötig)

# --- Database ---
DB_MYSQL_DATABASE=wordpress
DB_MYSQL_USER=wp_user

# --- App Configuration ---
# (app-spezifische Werte)

# --- Traefik Routing ---
APP_TRAEFIK_HOST=wordpress.example.com
APP_TRAEFIK_CERT_RESOLVER=cloudflare-dns
APP_TRAEFIK_TLS_OPTION=tls-basic
APP_TRAEFIK_ACCESS=acc-public
APP_TRAEFIK_SECURITY=sec-2
APP_INTERNAL_PORT=80

# --- Secrets ---
# Secrets are stored in ./secrets/ (gitignored).
# See README.md for setup instructions.
```

## Warum diese Reihenfolge?

| Position | Sektion | Grund |
|----------|---------|-------|
| 1. Images | Image-Tags mit Version | Ganz oben → sofort sichtbar welche Versionen laufen |
| 2. Container | Container-Namen | Direkt nach Images → Identität |
| 3. General | Timezone, Project-Name | Globale Einstellungen |
| 4. Network | App-spezifische Netz-Config | Nur wenn nötig, sonst weglassen |
| 5. Database | DB-Name, User | Getrennt von App-Config |
| 6. App Configuration | Alles app-spezifische | Hauptteil, variiert pro App |
| 7. Traefik Routing | Host, Resolver, TLS, Middlewares | Routing-Entscheidungen an einem Ort |
| 8. Secrets | Hinweis auf Secret-Files | Am Ende als Referenz |

## Sektionen-Details

### Images

```env
# --- Images ---
APP_IMAGE=wordpress:6.7-php8.3-apache
DB_IMAGE=mariadb:11.4
```

- **Immer** mit expliziter Version, nie `:latest`
- Ermöglicht zentrale Image-Updates über die `.env` ohne Compose-Änderung

### Container

```env
# --- Container ---
CONTAINER_NAME_APP=wordpress-app
CONTAINER_NAME_DB=wordpress-db
```

- Pattern: `{app}-{role}` (siehe Naming Conventions unten)
- Eindeutig über den gesamten Docker-Host

### General

```env
# --- General ---
TIMEZONE=Europe/Vienna
COMPOSE_PROJECT_NAME=wordpress
```

- `COMPOSE_PROJECT_NAME` wird in Traefik-Labels als Router-Name verwendet → muss eindeutig sein
- `TIMEZONE` für konsistente Zeitstempel in Logs

### Database

```env
# --- Database ---
DB_MYSQL_DATABASE=wordpress
DB_MYSQL_USER=wp_user
```

- Nur nicht-sensible DB-Konfiguration
- Passwörter gehören in `./secrets/`, nicht hierher

### App Configuration

```env
# --- App Configuration ---
WORDPRESS_TABLE_PREFIX=wp_
WORDPRESS_DEBUG=false
```

- Alles was app-spezifisch ist und nicht in andere Sektionen passt
- Bei vielen Werten: mit Kommentaren gruppieren

### Traefik Routing

```env
# --- Traefik Routing ---
APP_TRAEFIK_HOST=wordpress.example.com
APP_TRAEFIK_CERT_RESOLVER=cloudflare-dns
APP_TRAEFIK_TLS_OPTION=tls-basic
APP_TRAEFIK_ACCESS=acc-public
APP_TRAEFIK_SECURITY=sec-2
APP_INTERNAL_PORT=80
```

| Variable | Mögliche Werte | Erklärung |
|----------|----------------|-----------|
| `APP_TRAEFIK_HOST` | `app.example.com` | FQDN unter dem die App erreichbar ist |
| `APP_TRAEFIK_CERT_RESOLVER` | `cloudflare-dns`, `httpResolver` | Welcher ACME-Resolver das Cert ausstellt |
| `APP_TRAEFIK_TLS_OPTION` | `tls-basic`, `tls-aplus`, `tls-modern` | TLS-Profil (siehe core/traefik) |
| `APP_TRAEFIK_ACCESS` | `acc-public`, `acc-tailscale` | Zugriffskontrolle |
| `APP_TRAEFIK_SECURITY` | `sec-0` bis `sec-4` | Security-Level |
| `APP_INTERNAL_PORT` | `80`, `8080`, `3000`, ... | Port auf dem die App im Container lauscht |

### Secrets

```env
# --- Secrets ---
# Secrets are stored in ./secrets/ (gitignored).
# Create them with:
#   mkdir -p secrets
#   openssl rand -base64 32 > secrets/db_password.txt
```

- Keine echten Werte in der `.env`
- Nur ein Hinweis wie und wo Secrets erstellt werden

## Regeln

### Header

Jede `.env.example` beginnt mit dem gleichen Header-Block:

```env
# =============================================
# {App Name} – Environment
# =============================================
# Copy this file to .env and adjust all values.
# NEVER commit the .env file.
# =============================================
```

### Sektions-Trenner

Sektionen werden mit diesem Pattern getrennt:

```env
# --- Sektionsname ---
```

### Werte

- `.env.example` enthält **Beispiel-Werte**, nie echte Credentials
- Domains immer `*.example.com`
- Passwörter/Tokens: weglassen oder `__REPLACE_ME__`
- Versions-Tags: aktuelle stabile Version angeben

---

## Naming Conventions

### Variablen-Prefixe

Pattern: `{SCOPE}_{PROPERTY}`

| Scope | Beispiel | Verwendung |
|-------|----------|------------|
| `APP_` | `APP_IMAGE`, `APP_TRAEFIK_HOST`, `APP_INTERNAL_PORT` | App-Container + Traefik-Routing |
| `DB_` | `DB_IMAGE`, `DB_MYSQL_USER`, `DB_MYSQL_DATABASE` | Datenbank-Container |
| `CONTAINER_NAME_` | `CONTAINER_NAME_APP`, `CONTAINER_NAME_DB` | Container-Namen |
| `COMPOSE_` | `COMPOSE_PROJECT_NAME` | Docker Compose Globals |

### Container-Namen

Pattern: `{app}-{role}`

| Beispiel | Erklärung |
|----------|-----------|
| `wordpress-app` | WordPress Application |
| `wordpress-db` | WordPress Database |
| `vaultwarden-app` | Vaultwarden (kein DB-Service) |

---

## Checkliste

- [ ] Header-Block vorhanden mit App-Name
- [ ] Sektionen-Reihenfolge eingehalten (Images → Container → General → DB → App → Traefik → Secrets)
- [ ] Sektions-Trenner mit `# --- Name ---` Pattern
- [ ] Alle Images mit expliziter Version (nie `:latest`)
- [ ] `COMPOSE_PROJECT_NAME` gesetzt und eindeutig
- [ ] Traefik-Block vollständig (Host, Resolver, TLS, Access, Security, Port)
- [ ] Keine echten Credentials oder Domains
- [ ] Secrets-Sektion mit Hinweis auf `./secrets/`
