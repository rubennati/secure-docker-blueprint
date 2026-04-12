# Seafile Config Directory

Custom configuration files mounted into Seafile containers.

## Files

| File | Mounted in | Purpose |
|------|-----------|---------|
| `entrypoint.sh` | All services | Reads Docker Secrets, exports as env vars, then starts the original service |
| `seahub_custom.py` | seafile (main) | Custom Python settings appended to `seahub_settings.py` |

---

## How `seahub_custom.py` injection works

Seafile auto-generates `seahub_settings.py` on first boot (DB settings, secret
key, timezone, etc.). We **don't replace** this file — we **append** our custom
settings to it.

### The mechanism

1. On container start, `entrypoint.sh` runs before Seafile
2. It checks if `seahub_settings.py` already contains our marker line:
   ```
   # --- Blueprint custom settings ---
   ```
3. **Marker not found** → appends the marker + full content of `seahub_custom.py`
4. **Marker found** → skips (prevents duplicate entries on every restart)

### When to re-inject settings

The injection runs **only once** (marker-based). If you change
`seahub_custom.py`, the old version stays in `seahub_settings.py` because the
marker already exists.

**To apply changes to `seahub_custom.py`:**

```bash
# 1. Remove everything from the marker to end-of-file
docker exec seafile-app sed -i '/# --- Blueprint custom settings ---/,$d' \
  /shared/seafile/conf/seahub_settings.py

# 2. Restart — entrypoint.sh will re-inject the updated settings
docker compose down && docker compose up -d
```

**What this `sed` command does:**

- `/# --- Blueprint custom settings ---/` — find the line containing our marker
- `,$d` — delete from that line to the end of the file (`$` = last line, `d` = delete)
- `-i` — edit the file in-place

This safely removes only our appended block while keeping all of Seafile's
auto-generated settings above it intact.

### Alternative: manual edit

You can also edit `seahub_settings.py` directly inside the volume:

```bash
nano volumes/seafile-data/seafile/conf/seahub_settings.py
```

But changes made this way are not version-controlled and will diverge from
`seahub_custom.py`.

---

## How `entrypoint.sh` secret injection works

Seafile services (Python, Go, bash-based) don't consistently support Docker's
`_FILE` convention for reading secrets. Our shared entrypoint solves this:

```
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
│  ├─ (Optional) Append seahub_custom.py           │
│  └─ exec "$@"  →  starts original service        │
└─────────────────────────────────────────────────┘
```

The same `entrypoint.sh` is used by **all** Seafile services:

| Service | Original command passed to `exec "$@"` |
|---------|---------------------------------------|
| seafile (main) | `/sbin/my_init -- /scripts/enterpoint.sh` |
| seadoc | `/sbin/my_init -- /scripts/enterpoint.sh` |
| notification-server | `/opt/seafile/notification-server -c /opt/seafile -l ...` |
| md-server | `bash -c /opt/scripts/entrypoint.sh` |

Each secret export is conditional (`[ -f ... ] &&`), so it only runs if the
secret file is actually mounted. Services that don't need a specific secret
simply don't mount it.
