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

### 1. Render and install

The shipped stanza carries the placeholder `/path/to/secure-docker-blueprint`;
rendering replaces it with the checkout's path, and the printed command installs
the result ([`host-files.md`](host-files.md)):

```bash
# from the repository root
scripts/host-files.sh render core/traefik
scripts/host-files.sh install-commands core/traefik   # prints the sudo install line; run it
```

A copy made by hand without the substitution names a path that matches no file,
and logrotate says nothing about it (`missingok`): the logs keep growing. After a
blueprint update, `./scripts/overview.sh --host` reports whether the installed
stanza still matches the shipped one.

### 2. Verify the path

The path inside the installed stanza must be the **host-side** of the volume
mount in `docker-compose.yml`:

```yaml
volumes:
  - ./volumes/logs:/var/log/traefik
```

If your deploy path is `/srv/docker/core/traefik`, the two stanzas name:

```text
/srv/docker/core/traefik/volumes/logs/access.log
/srv/docker/core/traefik/volumes/logs/traefik.log
```

A path that matches nothing fails silently — the logs simply keep growing.
The dry run says which files it found:

```bash
sudo logrotate -d /etc/logrotate.d/traefik
```

Expect each log listed under `considering log …`, and the size threshold echoed
back as `log files >= 104857600 are rotated earlier`. `Handling 0 logs` means the
path is wrong.

### 3. Know when it actually runs

`daily` and `maxsize` describe *conditions*, not a schedule. Nothing rotates
until logrotate itself runs, which on Debian is a systemd timer:

```bash
systemctl list-timers logrotate.timer
```

Daily by default. `maxsize` therefore bounds a file at one day's traffic rather
than at the size given. That matters because the scenario it exists for is a
request flood that fills a disk in minutes. Where
that matters:

```bash
sudo systemctl edit logrotate.timer
# [Timer]
# OnCalendar=
# OnCalendar=hourly
```

From `man logrotate`: *"Log files are rotated when they grow bigger than size
bytes even before the additionally specified time interval"* — early, yes; but
only ever at a run.

### 4. Force a rotation (optional, to verify)

```bash
sudo logrotate -f /etc/logrotate.d/traefik
```

### 5. Check status

```bash
sudo cat /var/lib/logrotate/status | grep traefik
```

## How it works

The shipped file carries one stanza per log — `access.log` and `traefik.log` — with
the same options in each; the reasons for each choice are comments in the file:

```text
/path/to/secure-docker-blueprint/core/traefik/volumes/logs/access.log {
    daily              # Rotate once per day
    rotate 7           # Keep 7 rotated files (1 week)
    compress           # gzip old logs
    delaycompress      # Don't compress yesterday's log (still being read)
    missingok          # Don't error if log file doesn't exist
    notifempty         # Don't rotate empty files
    maxsize 100M       # Rotate early on size, at the next run
    copytruncate       # Copy out, truncate in place — no signal to the container
}
```

### Why no signal

Renaming a log and then signalling the process to reopen it is the classic
rotation. It does not fit here, for two reasons:

- **A signal through Docker switches off the restart policy.** Docker treats any
  `docker kill`, whatever the signal, as a stop by hand and cancels the
  container's restart policy until the next start (the daemon logs
  `stopping restart-manager`). With `docker kill --signal=USR1` in `postrotate`,
  every crash after the first nightly rotation left Traefik down — measured on
  2026-09-22 with an OOM kill.
- **Traefik 3 reopens only its access log on `USR1`.** Its main log stays on the
  renamed file (measured on v3.7.13, 2026-09-14).

`copytruncate` needs neither. Traefik opens both logs `O_APPEND` and keeps
writing at the new end; the lines written between the copy and the truncate are
lost. Use the same pattern for any container: never `docker kill --signal` from a
cron job or a logrotate hook.

**`systemctl reload traefik` does NOT work** because Traefik runs inside Docker,
not as a systemd service.

## When does logrotate run?

On Debian/Ubuntu, logrotate runs daily via systemd timer or cron:

```bash
# Check timer
systemctl status logrotate.timer

# Or check cron
ls -la /etc/cron.daily/logrotate
```

No additional cron job needed — installing the config file in `/etc/logrotate.d/` is enough.
