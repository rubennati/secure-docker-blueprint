# Scrutiny

S.M.A.R.T. disk health: it collects the counters a drive keeps about itself,
holds their history, and warns when the numbers start moving the wrong way.
Upstream: [AnalogJ/scrutiny](https://github.com/AnalogJ/scrutiny).

It is the one axis in [`monitoring/`](../README.md) nothing else here covers.
A disk that is about to fail answers pings, serves HTTP and reports a healthy
container — right up until it does not.

## Architecture

```text
Traefik ──http──→ scrutiny-web :8080      interface and API
                       │
                       └──→ scrutiny-influxdb :8086   the history

collector (collector.yml) ──→ the disks ──→ POST to the API on a cron
```

The two halves are separate on purpose: the interface reads no disk, and the
collector is the only part that needs anything from the host.

## The interface has no password

Scrutiny ships no authentication of any kind, and two of its open endpoints are
destructive: `POST /api/settings` changes the instance's configuration and
`DELETE /api/device/:uuid` removes a disk together with its history. Measured:
`/api/health` and `/api/summary` answer without credentials.

So the proxy carries a password — a Traefik basic-auth middleware, the same
shape [`apps/paperless-gpt`](../../apps/paperless-gpt/) uses:

```bash
htpasswd -nbB ops 'the-password' | sed -e 's/\$/\$\$/g'
```

and paste the result into `APP_BASIC_AUTH_USERS` in `.env`. **Double every
`$`** — Compose expands `$apr1` and the rest as variable names, and the hash
that reaches the label is not the one you generated. Check what arrived with
`docker inspect`, not `docker compose config`: the latter re-escapes its own
output.

`acc-tailscale` is the other gate. Neither replaces the other.

## Setup

```bash
cp .env.example .env            # host name, and the hash above
ops/init.sh                     # the InfluxDB password and token
sudo chown -R 1000:1000 volumes/
docker compose up -d
```

Nothing appears in the interface yet: nothing is reading the disks.

## Reading the disks

```bash
docker compose -f docker-compose.yml -f collector.yml up -d
```

**Edit `devices:` in `collector.yml` first.** It lists `/dev/sda` as an
example, not as a default that fits your machine — run `lsblk` and name the
disks you want read. There is no wildcard: nothing outside that list is
reachable.

What the collector asks for, in upstream's own words:

| Capability | Upstream's description | Here |
|---|---|---|
| `SYS_RAWIO` | "allows for data exfiltration/modification from SATA drives" | granted — there is no reading S.M.A.R.T. without it |
| `SYS_ADMIN` | "would theoretically allow for significant system compromise" | **not granted.** Only NVMe needs it; uncomment if your disks are NVMe and you accept that sentence |

It also needs `SETGID` and `SETUID`, which is less alarming than it sounds: the
entrypoint uses `su` to drop privileges, and without them the container
restart-loops on `su: cannot set groups: Operation not permitted`.

**`privileged` is not needed.** Upstream's examples reach for it; this runs
without. Verified: a collection scanned a real disk, ran `smartctl --xall` and
published the result.

### The better answer, where you control the host

Every Scrutiny release publishes the collector as a **Linux binary**. Run it
from cron or a systemd timer on the host, pointed at the interface's URL, and
no container needs `SYS_RAWIO` at all — on the host it is simply a program that
can read `/dev`. That is the same split [`backup/`](../../backup/README.md)
uses for its agent, and it is what this stack would recommend if it could only
recommend one thing.

The overlay exists because the host is not always yours to install on.

## Security model

- **Two gates in front of an application with none.** See above.
- **The collector is an opt-in overlay**, and names each disk individually.
- **`SYS_ADMIN` is left out**, `privileged` is never used.
- **The InfluxDB token is a Docker Secret**, exported by a wrapper because
  Scrutiny has no `_FILE` variant — left to itself it uses the token compiled
  into the binary.
- **InfluxDB is not routed** and publishes no port.
- **`read_only`, `cap_drop: ALL`, `no-new-privileges`, non-root** on the
  interface and the database. The collector keeps `cap_drop: ALL` and adds back
  the three capabilities above.

## Known limits

- **Nothing has run on its cron.** The collection above was forced by hand; a
  scheduled run, and a warning raised by a disk that is actually failing, are
  host questions.
- **This disk reported a checksum error.** `smartctl` returned code 4 on the
  test machine's virtual disk, and Scrutiny published the reading anyway. On
  real hardware that code means something; in a VM it usually means the
  hypervisor's emulation is thin.
- **NVMe is untested here**, and needs the capability this stack leaves out.
- **Notifications are not configured.** Scrutiny supports many channels through
  Shoutrrr; none is set up and none has been delivered.
- **`sec-2` is not measured** against the interface.
- **Nothing here has run behind this repository's Traefik yet.** The stack is
  `scaffolded`, and the basic-auth middleware in particular has not been seen
  in a real chain.

## Backup

| | |
|---|---|
| **The history** | `./volumes/influxdb` — every reading ever collected. The part that makes a trend visible; losing it costs the trend, not the current state |
| **Settings** | `./volumes/scrutiny-config` — the interface's own configuration |
| **The keys** | `.secrets/influxdb_token.txt` is a bearer credential for the bucket; `.secrets/influxdb_password.txt` is the InfluxDB admin login. Restoring the volume without them leaves a database nothing can read |
| **In `.env`** | `APP_BASIC_AUTH_USERS` — the hash is not in `.secrets/`, because a Traefik middleware reads its users from the label |
| **Quiescing** | Stop InfluxDB before copying its directory |

```yaml
# /etc/borgmatic/config.yaml
source_directories:
  - /srv/secure-docker-blueprint/monitoring/scrutiny/volumes/influxdb
  - /srv/secure-docker-blueprint/monitoring/scrutiny/volumes/scrutiny-config
```

Restore: put the volumes back owned by `1000:1000`, restore the secrets and
`.env`, start the stack. Disks re-register themselves on the next collection.
