# Upstream Reference

## Source

- **Image:** https://github.com/AnalogJ/scrutiny/pkgs/container/scrutiny
- **GitHub:** https://github.com/AnalogJ/scrutiny
- **Docs:** https://github.com/AnalogJ/scrutiny/tree/master/docs
- **License:** MIT
- **Use restrictions:** none — https://github.com/AnalogJ/scrutiny/blob/master/LICENSE · checked 2026-09-24
- **Edition gating:** none — one build, no paid tier — https://github.com/AnalogJ/scrutiny · checked 2026-09-24
- **Commercial model:** no paid edition — https://github.com/AnalogJ/scrutiny · checked 2026-09-24
- **Decision facts checked:** 2026-09-24
- **Origin:** Community · Jason Kulatunga (AnalogJ) · no single jurisdiction
- **Domain:** Monitoring
- **Role:** S.M.A.R.T. disk health — collects the counters, keeps their history and warns before a drive fails
- **Based on version:** `v0.9.4`

## Project maturity

8 243 stars, pushed 2026-09-13, v0.9.4 the same day. Releases paused for 22
months after v0.8.1 and resumed in February 2026; v0.9.0 migrated drive
identities and the data stored against them, so that upgrade is not a pin
change.

## What we use

- `ghcr.io/analogj/scrutiny:v0.9.4-web` — the interface and API.
- `influxdb:2.8`, **pinned by digest as well as by tag**: the `influxdb` tags
  are rebuilt in place, so a tag alone does not identify an image.
- `ghcr.io/analogj/scrutiny:v0.9.4-collector` as an opt-in overlay.

Upstream's own examples use `nightly-*` tags; its README says to pin a version,
and these do.

The omnibus image, which bundles InfluxDB under s6-overlay, is not used: it
carries an InfluxDB this stack cannot pin or update on its own.

## What we changed and why

| Change | Reason |
|--------|--------|
| A password at Traefik | Scrutiny has no authentication. `POST /api/settings` and `DELETE /api/device/:uuid` are open — configuration and disk history, both destructive |
| `config/entrypoint.sh` exports the InfluxDB token | Scrutiny reads settings through viper with a `SCRUTINY` prefix and has **no `_FILE` variant** — measured below |
| The collector is an opt-in overlay | It needs `SYS_RAWIO` and a `devices:` entry per disk. Upstream's own words for what that allows are in the overlay |
| `SYS_ADMIN` left out | Only NVMe needs it, and upstream says it "would theoretically allow for significant system compromise" |
| `user:` on web and InfluxDB | Both images declare root; neither half needs it |
| InfluxDB is not routed | It holds the history and authenticates with a bearer token; nothing outside this stack needs it |
| Version tags rather than `nightly-*` | Upstream's examples use the moving tag; its README says not to |

## Verified on the images (2026-09-24)

A throwaway network, no Traefik router — but the collector did read a real disk
on this host.

- InfluxDB, the interface and the collector all healthy; the interface as
  uid 1000 under `read_only`, `cap_drop: ALL` and `no-new-privileges`.
- **Scrutiny has no `_FILE` support, and fails in a way that does not say so.**
  `SCRUTINY_WEB_INFLUXDB_TOKEN_FILE` is simply ignored — `config.go` calls
  `SetEnvPrefix("SCRUTINY")` with `AutomaticEnv()`, so only
  `SCRUTINY_WEB_INFLUXDB_TOKEN` is read. Left unset it falls back to the token
  compiled into the binary and the container restart-loops on
  `panic: unauthorized: unauthorized access`, which names neither the variable
  nor the token. The wrapper exports it from the Docker Secret.
- **The collector needs `SETGID` and `SETUID` beside `SYS_RAWIO`.** Its
  entrypoint drops privileges with `su`; with `cap_drop: ALL` and `SYS_RAWIO`
  alone it restart-loops on `su: cannot set groups: Operation not permitted`.
- **The collector works without `privileged`.** A forced run scanned the disk,
  ran `smartctl --info --json` and `smartctl --xall --json` against it, and
  published the result: the API then listed one device, `sda`, with its model
  and capacity. `SYS_RAWIO`, `SETGID`, `SETUID`, one `devices:` entry and
  `/run/udev` read-only were enough.
- **The interface image carries curl and no wget**, and no busybox to provide
  one — the first healthcheck failed with `wget: not found`.
- `/api/health` and `/api/summary` answer without credentials. That is what
  the password in front is for.
- Idle: InfluxDB 50 MiB anonymous, the interface 5 MiB, the collector
  single-digit MB between runs.

What a host run still has to establish: the route through `core/traefik` with
the basic-auth middleware in the chain, a collection on its cron rather than
forced by hand, a failing disk actually raising a warning, and a restore from
the volumes.

## What reaches the network on its own

Nothing. Scrutiny talks to its own InfluxDB and to whatever notification
endpoint you configure. Upstream's device-failure prediction runs on data
already collected; it sends nothing away.

## Upgrade checklist

1. Read the release notes — https://github.com/AnalogJ/scrutiny/releases.
   v0.9.0 migrated stored drive identities; treat a major move as a migration
2. Raise `APP_TAG` and `COLLECTOR_TAG` in `.env` and in `.env.local.example`
3. For InfluxDB, resolve the new digest first:
   `docker pull influxdb:<tag> && docker inspect influxdb:<tag> --format '{{index .RepoDigests 0}}'`
4. `docker compose pull && docker compose up -d`
5. Force one collection and confirm the disks still appear:
   `docker compose exec scrutiny-collector /opt/scrutiny/bin/scrutiny-collector-metrics run --api-endpoint http://scrutiny-web:8080`
6. Record the result in `Last verified` once it ran behind `core/traefik`

## Diff against upstream

```bash
# Upstream's hub-and-spoke example — nightly tags, no password, omnibus variant
curl -s https://raw.githubusercontent.com/AnalogJ/scrutiny/master/example.hubspoke.docker-compose.yml

# What the collector asks the kernel for
curl -s https://raw.githubusercontent.com/AnalogJ/scrutiny/master/README.md | grep -A8 'SYS_RAWIO'
```
