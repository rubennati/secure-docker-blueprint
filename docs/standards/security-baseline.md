# Security Baseline

## Pflicht für jeden Service

```yaml
security_opt:
  - no-new-privileges:true
```

Keine Ausnahmen. Verhindert Privilege Escalation innerhalb des Containers.

## Empfohlen

### Read-only Root Filesystem

```yaml
read_only: true
tmpfs:
  - /tmp
  - /run
```

Verwenden wenn das Image es unterstützt. Beispiele: Redis, Whoami, Socket Proxy.
Weglassen bei Images die ins Root-FS schreiben müssen (Ghost, Paperless).

### Capability Drop

```yaml
cap_drop:
  - ALL
cap_add:
  - NET_BIND_SERVICE    # Nur wenn Port < 1024 nötig
```

Ideal für leichtgewichtige Services (Whoami, dnsmasq).

### Non-root User

```yaml
user: "${USERMAP_UID}:${USERMAP_GID}"
```

Nur setzen wenn das Image es unterstützt. Nicht raten — in der Image-Doku prüfen.

## Secrets

### Regel

Passwörter, Tokens und API Keys **nie** in `environment:` — immer via Docker Secrets.

### Pattern 1: Image unterstützt `_FILE`

```yaml
environment:
  POSTGRES_PASSWORD_FILE: /run/secrets/DB_PWD
secrets:
  - DB_PWD

secrets:
  DB_PWD:
    file: ./secrets/db_pwd.txt
```

Unterstützt von: PostgreSQL, MySQL/MariaDB, OnlyOffice.

### Pattern 2: Custom Entrypoint

Wenn das Image kein `_FILE` unterstützt (Vaultwarden, Dockhand, Hawser):

```sh
#!/bin/sh
set -e
export DATABASE_URL="postgres://${DB_USER}:$(cat /run/secrets/DB_PWD)@db:5432/${DB_NAME}"
exec "$@"
```

```yaml
entrypoint: ["/bin/sh", "/config/entrypoint.sh"]
volumes:
  - ./config/entrypoint.sh:/config/entrypoint.sh:ro
```

### Pattern 3: Kein Secret möglich

Wenn der Wert in einem JSON-String steckt (z.B. Paperless SSO `PAPERLESS_SOCIALACCOUNT_PROVIDERS`):
Env-Var in `.env` belassen — ist gitignored, also akzeptabel.

## Docker Socket

### Niemals direkt am App-Container

```yaml
# FALSCH
volumes:
  - /var/run/docker.sock:/var/run/docker.sock
```

### Immer über Socket Proxy

```yaml
# RICHTIG
socket-proxy:
  image: tecnativa/docker-socket-proxy:v0.4.2
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock:ro
  environment:
    CONTAINERS: "1"    # Nur was die App braucht
    POST: "0"          # Schreibzugriff nur wenn nötig

app:
  environment:
    DOCKER_HOST: tcp://socket-proxy:2375
```

Ausnahme: Hawser — braucht Socket-Zugriff als Kernfunktion, nutzt aber trotzdem einen Socket Proxy als Defence in Depth.

## Netzwerk-Isolation

- Datenbanken, Redis, interne Services: **nur** im `app-internal` Netzwerk
- Web-Apps: `proxy-public` + `app-internal`
- DB-Ports **nie** auf Host exposen

## Checkliste

- [ ] `no-new-privileges:true` auf jedem Service
- [ ] `read_only: true` wo möglich
- [ ] Secrets via `secrets:` Block, nie in `environment:`
- [ ] Docker Socket nur über Socket Proxy
- [ ] Config-Mounts mit `:ro`
- [ ] DB nur im internen Netzwerk
- [ ] Images gepinnt (nie `:latest`)
- [ ] `./secrets/` und `./volumes/` in `.gitignore`
