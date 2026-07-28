# Seafile CE — MariaDB Aborted Connection Warnings

**Date observed:** 2026-06-15
**Status:** Noisy but acceptable — monitor, do not blindly tune

---

## Scope

- **Blueprint:** `apps/seafile/` (Seafile Community Edition 13)
- **MariaDB:** `mariadb:10.11`
- **Containers generating warnings:** `seafile-app` (Seahub/Django), `seafile-thumbnail`
- **Not related to:** the `/thumbnail/...` 403 fix in commit `63caff6` — thumbnails work correctly after that fix

---

## Symptoms

MariaDB logs repeated warnings during normal operation (browsing, uploads, deletions, thumbnail
generation):

```text
[Warning] Aborted connection ... to db: 'seafile_db' user: 'sefiuser' host: '172.23.0.9' (Got an error reading communication packets)
[Warning] Aborted connection ... to db: 'seahub_db' user: 'sefiuser' host: '172.23.0.6' (Got an error reading communication packets)
```

Container IP mapping at time of observation:

```text
172.23.0.9  →  seafile-thumbnail
172.23.0.6  →  seafile-app
```

---

## Observed Facts

At time of investigation the deployment was fully functional:

- File uploads (~300 files) succeeded without errors
- Folder browsing worked normally
- Thumbnail generation worked (after the `63caff6` fix)
- No user-visible browser errors
- No 5xx responses
- No `Aborted_connects` (= 0) — zero authentication failures
- No connection exhaustion — `Max_used_connections = 35` against `max_connections = 151`
- Resource usage was low across all containers

### MariaDB status snapshot

```text
Aborted_clients      40
Aborted_connects      0
Connections          924
Max_used_connections  35
Threads_connected     33
max_connections      151
max_allowed_packet   16777216 (16 MiB)
wait_timeout         28800    (8 h)
interactive_timeout  28800    (8 h)
net_read_timeout       30
net_write_timeout      60
```

### Resource snapshot

```text
seafile-app         0.80% CPU   800 MiB / 7.6 GiB
seafile-thumbnail   0.34% CPU   171 MiB / 7.6 GiB
seafile-db          0.03% CPU   136 MiB / 7.6 GiB
seafile-redis       1.38% CPU     9 MiB / 7.6 GiB
seafile-md-server   0.00% CPU    93 MiB / 7.6 GiB
```

---

## Interpretation

### `Aborted_clients` vs `Aborted_connects`

These are distinct counters tracking different failure modes:

| Counter | Meaning | Value |
|---|---|---|
| `Aborted_connects` | Connection **attempts that failed** (wrong password, no privilege, network rejection before auth) | **0** |
| `Aborted_clients` | Connections that **established successfully** but were later closed without a clean MySQL-protocol shutdown (`COM_QUIT`) | **40** |

**`Aborted_connects = 0` is the critical data point.** It confirms there are zero authentication failures. The DB credentials are correct, the JWT fix is working, and there are no unknown clients probing the database.

`Aborted_clients = 40` means 40 connections over the deployment's uptime were successfully opened, used, and then closed in a way MariaDB considers unclean — typically the application exited or the OS closed the socket without sending the MySQL-level close command. This is a warning, not a data-loss or outage condition.

### Why these warnings appear more visibly in MariaDB 10.11

MariaDB changed the default `log_warnings` value from `1` to `2` in version 10.2.4. At `log_warnings = 1`, aborted connection messages were not written to the error log. At `log_warnings = 2` (the current default) they are. MariaDB 10.11 LTS inherits this default. Equivalent behavior on MariaDB 10.1 or earlier would have been completely silent.

This means many users running the same Seafile workload on older MariaDB versions never saw these warnings — not because the connections were cleaner, but because they were silenced by default.

---

## Likely Root Cause

Two independent connection streams contribute:

### Stream 1 — `seafile-app` (Seahub / Django)

Seahub is a Django application. Django's default `CONN_MAX_AGE = 0` opens a new database connection for every HTTP request and closes it when the request ends. Under normal operation Django closes connections cleanly. However, in WSGI forked-worker deployments (gunicorn, uWSGI), if a **worker process is killed mid-request** — due to timeout, graceful restart, or an unhandled exception — any open connection is abandoned at OS level without a MySQL-protocol close. Each such event increments `Aborted_clients`.

### Stream 2 — `seafile-thumbnail`

The thumbnail-server is a Go/Python service that connects to the database for thumbnail task metadata. Before commit `63caff6`, it could not authenticate to the database at all (`JWT_PRIVATE_KEY` and `SEAFILE_MYSQL_DB_PASSWORD` were absent). After the fix it connects successfully — and now appears in the `Aborted_clients` log like the main app does.

The thumbnail-server has no documented connection pool configuration. If it opens short-lived connections per thumbnail task and relies on Go garbage collection or process exit rather than an explicit `db.Close()` call, MariaDB will log each such close as an aborted connection.

---

## What Is Ruled Out

| Hypothesis | Evidence against |
|---|---|
| Wrong DB password / auth failure | `Aborted_connects = 0` — zero authentication failures |
| Connection exhaustion | `Max_used_connections = 35`, `max_connections = 151` — 77% headroom |
| CPU or RAM overload | All containers idle or very low utilization |
| Broken thumbnail fix | Thumbnails load correctly; `Aborted_connects = 0` |
| MariaDB healthcheck probes as primary source | Healthcheck probes originate from the MariaDB container itself (`127.0.0.1` or the `db` container IP); observed warnings came from `seafile-app` and `seafile-thumbnail` IPs |
| `wait_timeout` killing idle connections | Warnings appeared during active operations (uploads, deletes, browsing); `wait_timeout = 28800 s` cannot fire during seconds-long requests |
| `max_allowed_packet` packet overflow | No evidence of large queries; `16 MiB` is well above typical Seafile metadata operations |

---

## Community Reports

This pattern is a known, reported, unresolved issue across Seafile versions:

- **[GitHub haiwen/seafile #2508](https://github.com/haiwen/seafile/issues/2508)** — same warning, MariaDB 10.5, closed without fix
- **[GitHub haiwen/seafile #2996](https://github.com/haiwen/seafile/issues/2996)** — same warning, MariaDB 10.11 + Seafile Pro 13.0, closed without fix
- **[Seafile Forum — MariaDB log warnings in Docker](https://forum.seafile.com/t/mariadb-log-and-why-in-docker-there-are-always-such-errors-in-mariadb/18808)** — multiple users, multiple versions, unresolved, described as not affecting functionality

Seafile has not published a configuration-level fix or official statement on this behavior.

---

## Recommended Handling

1. **Monitor first.** Run the status snapshot commands below twice, 10–15 minutes apart. Calculate how fast `Aborted_clients` grows. If it grows by a handful per hour proportional to traffic with no functional impact, accept it as known noise.

2. **Establish a rate baseline.** If `Aborted_clients` grows by dozens per minute during idle periods or coincides with user-visible errors (502s, "page unavailable", slowness), that signals a real problem worth investigating.

3. **Do not blindly tune DB settings.** The observed values (`wait_timeout = 28800`, `max_connections = 151`) are appropriate for this workload. Changing them without evidence risks introducing new problems.

4. **Do not suppress logs first.** Reducing `log_warnings` hides the signal before you understand whether the rate is stable or growing. Only reduce verbosity after confirming the behavior is stable.

5. **If the rate is low and functionality is unaffected:** accept as known background noise from the Seafile container ecosystem and document it (this file).

6. **If the rate grows heavily or correlates with errors:** proceed with deeper diagnostics (see below) before any tuning.

---

## Safe Diagnostic Commands

All commands are read-only and use the Docker Secret password. Run from the `apps/seafile/` directory.

### MariaDB connection counters

```bash
docker compose exec db sh -lc '
mariadb -uroot -p"$(cat /run/secrets/DB_ROOT_PWD)" -e "
SHOW GLOBAL STATUS WHERE Variable_name IN (
  '\''Aborted_clients'\'',
  '\''Aborted_connects'\'',
  '\''Connections'\'',
  '\''Threads_connected'\'',
  '\''Max_used_connections'\''
);
"
'
```

Run twice (10 minutes apart) and compare `Aborted_clients` to measure growth rate.

### MariaDB timeout and limit variables

```bash
docker compose exec db sh -lc '
mariadb -uroot -p"$(cat /run/secrets/DB_ROOT_PWD)" -e "
SHOW GLOBAL VARIABLES WHERE Variable_name IN (
  '\''max_connections'\'',
  '\''max_allowed_packet'\'',
  '\''wait_timeout'\'',
  '\''interactive_timeout'\'',
  '\''net_read_timeout'\'',
  '\''net_write_timeout'\'',
  '\''log_warnings'\''
);
"
'
```

### Map container IPs to names

```bash
docker inspect seafile-app seafile-thumbnail seafile-md-server seafile-notification seafile-seadoc \
  --format '{{.Name}} {{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}'
```

Use this to correlate warning IP addresses in future MariaDB log entries to specific containers.

### Live log correlation

```bash
docker compose logs -f --tail=0 db seafile thumbnail-server \
  | grep -iE "aborted connection|too many connections|packet|timeout|error|exception|traceback"
```

### Resource snapshot

```bash
docker stats --no-stream seafile-app seafile-thumbnail seafile-db seafile-redis seafile-md-server
```

### Current process list

```bash
docker compose exec db sh -lc '
mariadb -uroot -p"$(cat /run/secrets/DB_ROOT_PWD)" -e "
SELECT user, host, db, command, time, state
FROM information_schema.processlist
ORDER BY time DESC;
"
'
```

Look for many `Sleep` connections from `seafile-app` or `seafile-thumbnail` — that would indicate held-idle-open connections rather than abrupt closes.

---

## Possible Future Diagnostic (Not a Production Default)

If the growth rate turns out to be significant and the basic diagnostics above are insufficient, temporarily increase MariaDB verbosity to get errno details on each aborted connection:

```bash
# One-time live change — reverts on DB container restart
docker compose exec db sh -lc '
mariadb -uroot -p"$(cat /run/secrets/DB_ROOT_PWD)" -e "
SET GLOBAL log_warnings = 4;
"
'
```

At `log_warnings = 4`, each aborted connection entry includes a system errno. Errno `104` (`ECONNRESET` — "Connection reset by peer") means the application socket was closed by the process side. Errno `110` (`ETIMEDOUT`) means a genuine network timeout. This distinction identifies whether the source is application process recycling or a real network-level problem.

**Do not set `log_warnings = 4` permanently in production** — it generates high-volume diagnostic output under normal load.

---

## What Not to Change Yet

- **`max_connections`** — not exhausted; 35 peak against 151 limit
- **`wait_timeout` / `interactive_timeout`** — the aborts are from improper socket close, not idle timeout; reducing these would produce more warnings, not fewer
- **`net_read_timeout` / `net_write_timeout`** — no evidence these are involved
- **`max_allowed_packet`** — no evidence of oversized packets
- **`log_warnings = 1`** — do not suppress logs before understanding the growth rate
- **Volumes** — do not delete
- **All services** — do not restart without a specific reason; the stack is functional

---

## Final Classification

```text
Current classification: noisy but acceptable / known MariaDB-Seafile logging behavior.
Action: monitor and document. No immediate tuning required.
```

Root cause is the combination of:

1. Seafile's Go/Python sidecar services and Django workers not always issuing an explicit MySQL-protocol close before releasing connections
2. MariaDB 10.11 logging this more visibly than earlier versions due to the `log_warnings = 2` default (changed from `1` in MariaDB 10.2.4)

Neither root cause represents a data-loss risk or an outage condition given the observed metrics.
