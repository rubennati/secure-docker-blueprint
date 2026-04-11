# docker-compose.yml Standard

Verbindliche Konventionen für alle `docker-compose.yml` Dateien in diesem Blueprint.

## Block-Reihenfolge pro Service

Jeder Service folgt dieser Reihenfolge. Optionale Blöcke werden weggelassen, nicht leer gelassen.

```yaml
services:
  service-name:

    # --- Identity ---
    image:                    # Immer via ${VAR} aus .env
    container_name:           # Immer via ${VAR} aus .env
    restart:                  # unless-stopped (Standard)
    depends_on:               # Abhängigkeiten zu anderen Services

    # --- Security ---
    security_opt:             # no-new-privileges:true
    read_only:                # true wenn das Image es unterstützt
    tmpfs:                    # /tmp, /run etc. wenn read_only: true
    user:                     # Non-root User wenn Image es unterstützt

    # --- Configuration ---
    environment:              # Nicht-sensible Konfiguration
    secrets:                  # Sensible Werte (Passwörter, Tokens)

    # --- Storage ---
    volumes:                  # Persistente Daten + Config-Mounts (:ro wo möglich)

    # --- Networking ---
    networks:                 # Netzwerk-Zugehörigkeit
    ports:                    # Host-Ports (nur wenn zwingend nötig)

    # --- Traefik ---
    labels:                   # Traefik-Labels für Routing

    # --- Health & Observability ---
    healthcheck:              # Container-Healthcheck
    logging:                  # Log-Driver/Optionen (optional)
```

## Warum diese Reihenfolge?

| Position | Blöcke | Grund |
|----------|--------|-------|
| 1. Identity | image, container_name, restart, depends_on | Sofort erkennen **was** der Service ist und **wovon** er abhängt |
| 2. Security | security_opt, read_only, tmpfs, user | Security-Härtung vor Konfiguration → wird nicht vergessen |
| 3. Configuration | environment, secrets | **Was** der Service wissen muss, getrennt in normal vs. sensibel |
| 4. Storage | volumes | **Wo** Daten liegen, :ro bei Config-Mounts |
| 5. Networking | networks, ports | **Wie** der Service erreichbar ist |
| 6. Traefik | labels | Routing-Konfiguration für den Reverse Proxy |
| 7. Health | healthcheck, logging | Nachprüfung: **Läuft** der Service korrekt? |

## Block-Details

### Identity

```yaml
image: ${APP_IMAGE}                       # Immer aus .env, nie hardcoded
container_name: ${CONTAINER_NAME_APP}     # Immer aus .env
restart: unless-stopped                   # Standard für alle Services
depends_on:                               # Nur bei echten Abhängigkeiten
  database:
    condition: service_healthy            # Bevorzugt mit Health-Condition
```

- `restart: unless-stopped` ist der Standard. `always` nur für Core-Infra (Traefik).
- `depends_on` mit `condition: service_healthy` wenn der abhängige Service einen Healthcheck hat.

### Security

```yaml
security_opt:
  - no-new-privileges:true    # Verhindert Privilege Escalation
read_only: true               # Root-Filesystem read-only
tmpfs:                        # Nötig wenn read_only: true
  - /tmp
  - /run
user: "1000:1000"             # Non-root wenn das Image es unterstützt
```

- `no-new-privileges:true` ist **Pflicht** für jeden Service.
- `read_only: true` ist Standard. Weglassen nur wenn das Image es nicht unterstützt (dokumentieren warum).
- `user:` nur setzen wenn das Image einen Non-root User unterstützt. Nicht raten.

### Configuration

```yaml
environment:
  - TZ=${TIMEZONE}
  - DB_HOST=database                      # Service-Name als Hostname
  - DB_NAME=${DB_MYSQL_DATABASE}

secrets:
  - DB_PASSWORD
```

- Nicht-sensible Werte → `environment:`
- Passwörter, Tokens, API Keys → `secrets:` (mit `_FILE` Pattern wenn das Image es unterstützt)
- Keine Secrets direkt in `environment:` – auch nicht via `${VAR}`

### Storage

```yaml
volumes:
  - ./config/app.conf:/etc/app/app.conf:ro    # Config-Mounts immer :ro
  - ./volumes/data:/var/lib/app/data          # Persistente Daten
```

- Config-Mounts: immer `:ro`
- Persistente Daten: `./volumes/{purpose}/`
- Keine Host-Pfade außerhalb des App-Verzeichnisses

### Networking

```yaml
networks:
  - proxy-public        # Nur wenn Traefik den Service sehen muss
  - app-internal        # Isoliertes Netz für App ↔ DB Kommunikation

ports:                  # NUR wenn der Service direkt erreichbar sein muss
  - "${APP_PORT}:8080"  # Immer via ${VAR}, nie hardcoded
```

- Services die nur über Traefik erreichbar sind: **kein** `ports:` Block
- Datenbanken: **nie** Ports exposen, nur über internes Netzwerk
- `proxy-public` nur für Services die Traefik-Routing brauchen

### Traefik Labels

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.${COMPOSE_PROJECT_NAME}.rule=Host(`${APP_TRAEFIK_HOST}`)"
  - "traefik.http.routers.${COMPOSE_PROJECT_NAME}.entrypoints=websecure"
  - "traefik.http.routers.${COMPOSE_PROJECT_NAME}.tls=true"
  - "traefik.http.routers.${COMPOSE_PROJECT_NAME}.tls.certresolver=${APP_TRAEFIK_CERT_RESOLVER}"
  - "traefik.http.routers.${COMPOSE_PROJECT_NAME}.tls.options=${APP_TRAEFIK_TLS_OPTION}"
  - "traefik.http.routers.${COMPOSE_PROJECT_NAME}.middlewares=${APP_TRAEFIK_ACCESS}@file,${APP_TRAEFIK_SECURITY}@file"
  - "traefik.http.services.${COMPOSE_PROJECT_NAME}.loadbalancer.server.port=${APP_INTERNAL_PORT}"
```

- Router-Name: `${COMPOSE_PROJECT_NAME}` (eindeutig pro App)
- Access + Security Middleware immer aus den zentralen Traefik-Policies
- Cert-Resolver und TLS-Option immer via `.env`

### Health & Observability

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
  interval: 30s
  timeout: 10s
  retries: 5
  start_period: 30s
```

- Jeder Service **soll** einen Healthcheck haben
- `start_period` anpassen an die Startzeit der App
- Für Datenbanken: das mitgelieferte Healthcheck-Script nutzen (z.B. `healthcheck.sh`)

## Top-Level Blöcke

Am Ende der Datei, nach allen Services:

```yaml
networks:
  proxy-public:
    external: true            # Das von Traefik erstellte Netzwerk

  app-internal:
    name: ${COMPOSE_PROJECT_NAME}-internal
    internal: true            # Kein Internet-Zugang

secrets:
  DB_PASSWORD:
    file: ./secrets/db_password.txt
```

- `proxy-public` ist immer `external: true` (wird von core/traefik erstellt)
- Interne Netze: `internal: true` + Name via `${COMPOSE_PROJECT_NAME}`
- Secrets: File-basiert, im `./secrets/` Verzeichnis (gitignored)

---

## Naming Conventions

### Container-Namen

Pattern: `{app}-{role}`

| Beispiel | Erklärung |
|----------|-----------|
| `wordpress-app` | WordPress Application |
| `wordpress-db` | WordPress Database |
| `gitea-app` | Gitea Application |
| `gitea-db` | Gitea Database |
| `vaultwarden-app` | Vaultwarden (kein DB-Service) |

### Netzwerke

| Name | Typ | Verwendung |
|------|-----|------------|
| `proxy-public` | external, bridge | Traefik ↔ App (von core/traefik erstellt) |
| `{app}-internal` | internal | App ↔ DB (isoliert, kein Internet) |

### Volumes

Pattern: `./volumes/{purpose}/`

| Pfad | Verwendung |
|------|------------|
| `./volumes/data/` | App-Daten |
| `./volumes/mysql/` | Datenbank-Daten |
| `./volumes/config/` | Generierte Konfiguration |

### Secrets

Pattern: `./secrets/{name}.txt`

| Pfad | Verwendung |
|------|------------|
| `./secrets/db_password.txt` | Datenbank-Passwort |
| `./secrets/admin_password.txt` | Admin-Passwort |

---

## Checkliste

- [ ] Block-Reihenfolge eingehalten (Identity → Security → Config → Storage → Net → Traefik → Health)
- [ ] Alle Images und Container-Namen via `.env`
- [ ] `no-new-privileges:true` auf jedem Service
- [ ] `read_only: true` wo möglich (dokumentieren wenn nicht)
- [ ] Secrets via `secrets:` Block, nicht in `environment:`
- [ ] Config-Mounts mit `:ro`
- [ ] Datenbank-Ports nicht exposed
- [ ] Internes Netzwerk ist `internal: true`
- [ ] Healthcheck auf jedem Service
- [ ] `./secrets/` und `./volumes/` in `.gitignore`
