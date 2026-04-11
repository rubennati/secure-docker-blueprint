# App Template

Kopierbare Vorlage für neue Apps im Blueprint.

## Verwendung

```bash
# 1. Template kopieren
cp -r docs/templates apps/my-new-app
cd apps/my-new-app

# 2. .env erstellen und anpassen
cp .env.example .env
# Alle Werte in .env anpassen

# 3. Secrets erstellen
mkdir -p secrets
openssl rand -base64 32 > secrets/db_password.txt

# 4. Starten
docker compose up -d
```

## Anpassen

- **Ohne Datenbank:** `database` Service, `app-internal` Netzwerk und `secrets` Block entfernen
- **Ohne Traefik:** `labels` Block und `proxy-public` Netzwerk entfernen
- **read_only:** Auskommentierung bei `read_only`, `tmpfs` entfernen wenn das Image es unterstützt
- **Healthcheck:** An die App anpassen (Port, Pfad, Timing)

## Checkliste

Siehe die Standards-Dokumentation:
- [docker-compose.yml Standard](../standards/docker-compose.md)
- [.env File Standard](../standards/env-file.md)
