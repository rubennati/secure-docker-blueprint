# Host Watchdog (optional)

Two independent, host-installed scripts that watch one critical service each —
the Docker daemon and the Traefik container — and take exactly one recovery
action after a confirmed, sustained failure. Neither is installed by default,
neither is required by any other stack in this repository, and either can be
enabled without the other.

This exists because most container-level supervision already works —
`restart: unless-stopped` relaunches a crashed process, and every stack's own
healthcheck reports whether it is up. What that does not cover is a service
that is running but not answering (Traefik unhealthy while the process stays
alive) or the Docker daemon itself hanging. Nothing in this repository acts on
either today; `docker inspect --format '{{.State.OOMKilled}} {{.RestartCount}}'`
from [`docs/resource-measurement.md`](../../docs/resource-measurement.md) is a
manual command, not an automated response.

## What this is not

- **Not a general auto-heal mechanism.** `business/openproject` already
  documents why `willfarrell/autoheal` was left out: it needs a direct
  `docker.sock` mount, which this repository does not grant to containers. A
  host-installed script, run by systemd as root, is a different trust
  boundary — it has the access a system administrator has, not a container.
- **Not for stateful services.** Restarting Traefik on repeated unhealthy
  status is judged acceptable specifically because Traefik holds no data of
  its own — a wrong restart costs a few seconds of routing. Do not point
  `traefik-watchdog.sh` at a database or any other stateful container; an
  unhealthy stateful service should alert a person, not restart itself.
- **Not endless retries.** Each script tries exactly one recovery action per
  confirmed failure episode. If that attempt does not fix it, the script stops
  trying and reports failure on every subsequent run until the service
  recovers on its own or a person intervenes. It will not restart the same
  thing every two minutes forever.
- **Not verified on a live host.** Both scripts are new and documented, not
  rehearsed. Prove each one on a host you can afford to break before trusting
  it in production — stop the watched service, or block its healthcheck, and
  confirm the ping sequence, the one restart, and the escalation all behave as
  documented below.

## The model, both scripts

```text
repeated confirmed failure  (N consecutive checks, not one blip)
        |
        v
one controlled recovery attempt
        |
        v
verification
        |
   +----+----+
   |         |
 fixed    still broken
   |         |
 report    report failure, stop retrying
 success   until a human clears it or it
           recovers on its own
```

Both scripts report every run to a [Healthchecks](../../monitoring/healthchecks/)
check — the same dead-man's-switch pattern `backup/borgmatic` already uses.
This means the watchdog dying silently is itself caught: if it stops pinging
at all, Healthchecks' own grace-time alarm fires, independent of whatever the
watchdog was watching. No new alerting channel is needed — Healthchecks
already reaches ntfy, email or a webhook per
[`monitoring/README.md`](../../monitoring/README.md#alerting).

## Docker daemon watchdog

Checks the daemon's own API — `GET /_ping` over the raw Unix socket, the same
call `docker version` makes — not whether the `dockerd` process exists.
Process-level recovery (the daemon crashing outright) is already handled by
the systemd unit Docker's own package installs; this script exists for the
case where the process is alive but the API stops answering.

Runs as root on the host, because a containerised watcher cannot restart the
daemon it depends on — the same reasoning [`backup/README.md`](../../backup/README.md#where-the-backup-agent-belongs)
already gives for why Borgmatic runs on the host rather than in a container.

**Install:**

```bash
sudo cp docker-daemon-watchdog.env.example /etc/docker-daemon-watchdog.env
sudo nano /etc/docker-daemon-watchdog.env
# Set HEALTHCHECKS_PING_URL to a check created for this purpose in
# monitoring/healthchecks — do not reuse a check another job already pings.

sudo cp docker-daemon-watchdog.sh /usr/local/bin/docker-daemon-watchdog.sh
sudo chmod 755 /usr/local/bin/docker-daemon-watchdog.sh

sudo cp docker-daemon-watchdog.service.example /etc/systemd/system/docker-daemon-watchdog.service
sudo cp docker-daemon-watchdog.timer.example /etc/systemd/system/docker-daemon-watchdog.timer
sudo systemctl daemon-reload
sudo systemctl enable --now docker-daemon-watchdog.timer

# Prove it once before trusting the timer:
sudo systemctl start docker-daemon-watchdog.service
journalctl -u docker-daemon-watchdog.service -n 20
```

**Configuration** (`docker-daemon-watchdog.env.example`): `HEALTHCHECKS_PING_URL`
(required), `CONFIRM_AFTER` (consecutive failed checks before acting, default
3), `SETTLE_SECONDS` (wait after `systemctl restart docker` before
re-checking, default 10).

## Traefik watchdog

Checks `docker inspect --format '{{.State.Health.Status}}'` on the Traefik
container — the same status Traefik's own container healthcheck already
computes (`core/traefik/docker-compose.yml`'s `healthcheck: test: ["CMD",
"traefik", "healthcheck"]`). This script adds the missing step: something
acting on three consecutive `unhealthy` reports, which Docker itself never
does outside Swarm mode.

Lives beside Traefik's other operational scripts in
[`core/traefik/ops/scripts/`](../traefik/ops/scripts/) rather than here,
because it is specific to that one container. See
[`core/traefik/README.md`](../traefik/README.md) for install steps.

## Uninstalling

```bash
sudo systemctl disable --now <name>-watchdog.timer
sudo rm /etc/systemd/system/<name>-watchdog.{service,timer} /etc/<name>-watchdog.env
sudo rm -rf /var/lib/<name>-watchdog
sudo systemctl daemon-reload
```

Delete the corresponding check in Healthchecks separately if it is no longer
needed.
