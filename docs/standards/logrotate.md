# Logrotate for Docker Services

## Why

Some services write logs directly to bind-mounted volumes (e.g. Traefik access logs).
Docker's built-in log rotation (`json-file` driver with `max-size`/`max-file`) does **not**
manage these files — they grow indefinitely without logrotate.

## Which services need logrotate?

| Service | Log path on host | Reason |
|---------|-----------------|--------|
| Traefik | `core/traefik/volumes/logs/*.log` | Access + error logs written to file via `accessLog.filePath` |

Services that log only to stdout/stderr (most apps) are managed by Docker's log driver
and do **not** need logrotate.

## Setup

### 1. Copy config to host

```bash
sudo cp /path/to/docker-ops-blueprint/core/traefik/config/logrotate/traefik /etc/logrotate.d/traefik
```

### 2. Verify the path

The path inside the logrotate config must match the **host-side** of the volume mount.
Check `docker-compose.yml`:

```yaml
volumes:
  - ./volumes/logs:/var/log/traefik
```

If your deploy path is `/path/to/docker-ops-blueprint/core/traefik`, the host path is:
```
/path/to/docker-ops-blueprint/core/traefik/volumes/logs/*.log
```

### 3. Test (dry run)

```bash
sudo logrotate -d /etc/logrotate.d/traefik
```

This shows what **would** happen without actually rotating. Check for errors.

### 4. Force a rotation (optional, to verify)

```bash
sudo logrotate -f /etc/logrotate.d/traefik
```

### 5. Check status

```bash
sudo cat /var/lib/logrotate/status | grep traefik
```

## How it works

```
/path/to/docker-ops-blueprint/core/traefik/volumes/logs/*.log {
    daily              # Rotate once per day
    rotate 7           # Keep 7 rotated files (1 week)
    compress           # gzip old logs
    delaycompress      # Don't compress yesterday's log (still being read)
    missingok          # Don't error if log file doesn't exist
    notifempty         # Don't rotate empty files
    create 0640 root adm
    postrotate
        docker kill --signal=USR1 traefik-core >/dev/null 2>&1 || true
    endscript
}
```

### Why USR1?

After logrotate renames `access.log` → `access.log.1`, Traefik still writes to the
old file descriptor. `USR1` tells Traefik to close and reopen its log files — same
mechanism as nginx.

**`systemctl reload traefik` does NOT work** because Traefik runs inside Docker,
not as a systemd service.

### Container name

The `docker kill --signal=USR1 traefik-core` command uses the container name from `.env`:

```env
TRAEFIK_CONTAINER_NAME=traefik-core
```

If you change the container name, update the logrotate config too.

## When does logrotate run?

On Debian/Ubuntu, logrotate runs daily via systemd timer or cron:

```bash
# Check timer
systemctl status logrotate.timer

# Or check cron
ls -la /etc/cron.daily/logrotate
```

No additional cron job needed — installing the config file in `/etc/logrotate.d/` is enough.
