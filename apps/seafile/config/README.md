# Seafile Config Directory

Custom configuration files mounted into Seafile containers.

## Files

| File | Mounted in | Purpose |
|------|-----------|---------|
| `entrypoint.sh` | All services | Reads Docker Secrets, exports as env vars, then starts the original service |
| `seahub_custom.py` | seafile (main) | Custom Python settings injected into `seahub_settings.py` on every container start |

---

## How `seahub_custom.py` injection works

Seafile auto-generates `seahub_settings.py` on first boot (DB settings, secret
key, timezone, etc.). We **don't replace** this file — we **append** our custom
settings to it.

### The mechanism

On every container start, `entrypoint.sh` replaces the blueprint block in
`seahub_settings.py`:

1. **`seahub_settings.py` exists** → remove any existing blueprint block (marker line to end-of-file), then append the current `seahub_custom.py`
2. **`seahub_settings.py` absent** → skip — Seafile will generate it during first-boot init

> **First-boot timing:** on a fresh installation `seahub_settings.py` does not
> exist when `entrypoint.sh` runs. Seafile creates the file only after
> `exec "$@"` starts the init system and DB migrations complete. The custom
> block is therefore absent after the very first start. Recreate the container
> once first boot is complete and the block will be injected on the second
> start.

### When to re-inject settings

The block is replaced on every container start — no manual sed step needed.
To apply changes to `seahub_custom.py` or SMTP env vars:

```bash
docker compose up -d --force-recreate seafile
```

### Alternative: manual edit

You can also edit `seahub_settings.py` directly inside the volume:

```bash
nano volumes/seafile-data/seafile/conf/seahub_settings.py
```

Manual edits below the marker line are overwritten on the next container start.
Edit `seahub_custom.py` instead to keep changes under version control.

---

## How `entrypoint.sh` secret injection works

Seafile services (Python, Go, bash-based) don't consistently support Docker's
`_FILE` convention for reading secrets. Our shared entrypoint solves this:

```text
┌─────────────────────────────────────────────────┐
│ Docker starts container                          │
│                                                  │
│ entrypoint.sh                                    │
│  ├─ Read /run/secrets/SEAFILE_DB_PWD             │
│  │  └─ export SEAFILE_MYSQL_DB_PASSWORD=...      │
│  │  └─ export DB_PASSWORD=...                    │
│  ├─ Read /run/secrets/JWT_KEY                    │
│  │  └─ export JWT_PRIVATE_KEY=...                │
│  ├─ Read /run/secrets/REDIS_PWD                  │
│  │  └─ export REDIS_PASSWORD=...                 │
│  ├─ Read /run/secrets/ONLYOFFICE_JWT_SECRET      │
│  │  └─ export ONLYOFFICE_JWT_SECRET=...          │
│  ├─ Read /run/secrets/SEAFILE_SMTP_PWD (opt.)    │
│  │  └─ export SEAFILE_SMTP_PASSWORD=...          │
│  ├─ Replace seahub_custom.py block               │
│  │  (skipped on first boot if file absent)       │
│  └─ exec "$@"  →  starts original service        │
└─────────────────────────────────────────────────┘
```

The same `entrypoint.sh` is used by **all** Seafile services:

| Service | Original command passed to `exec "$@"` |
|---------|---------------------------------------|
| seafile (main) | `/sbin/my_init -- /scripts/enterpoint.sh` |
| seafile-seadoc | `/sbin/my_init -- /scripts/enterpoint.sh` |
| seafile-notification | `/opt/seafile/notification-server -c /opt/seafile -l ...` |
| md-server | `bash -c /opt/scripts/entrypoint.sh` |

Each secret export is conditional (`[ -f ... ] &&`), so it only runs if the
secret file is actually mounted. Services that don't need a specific secret
simply don't mount it.

### SMTP secret

The SMTP secret is mounted unconditionally into the `seafile` container, so `.secrets/smtp_pwd.txt` must always exist — even when SMTP is disabled (`SEAFILE_SMTP_HOST` empty). Create an empty placeholder if not using SMTP.

| Property | Value |
|----------|-------|
| Source file | `.secrets/smtp_pwd.txt` |
| Docker secret name | `SEAFILE_SMTP_PWD` |
| Container path | `/run/secrets/SEAFILE_SMTP_PWD` |
| Exported as | `SEAFILE_SMTP_PASSWORD` |
| Consumed by | `seahub_custom.py` → `EMAIL_HOST_PASSWORD` |
| Purpose | SMTP authentication password or API key |
