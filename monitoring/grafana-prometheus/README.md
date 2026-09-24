# Grafana + Prometheus

Metrics and dashboards: Prometheus scrapes and stores time series, Grafana
queries and draws them. Two services in the base stack, and two opt-in overlays
that collect from the host.

This is the general-purpose end of [`monitoring/`](../README.md). Beszel gives
you host and container figures with no configuration; this gives you every
metric anything exposes, and asks you to say which.

## Architecture

```text
Traefik ──http──→ grafana :3000        the only routed service, the only login
                     │
                     └──→ prometheus :9090   internal network, no router, no port
                              │
                              ├── node-exporter :9100   (node-exporter.yml)
                              └── cadvisor :8080        (cadvisor.yml)
```

**Prometheus is deliberately unreachable.** It has no authentication of any
kind: anything that can reach it can read every metric, run any query and read
the scrape configuration. Grafana is what you open, and Grafana is what has a
password.

## Setup

```bash
cp .env.example .env            # host name
ops/init.sh                     # the admin password and the data directories
sudo chown -R 472:472 volumes/grafana
sudo chown -R 65534:65534 volumes/prometheus
docker compose up -d

cat .secrets/grafana_admin_password.txt
```

Sign in as the user in `.env`. The Prometheus data source is already there —
provisioned, and marked not editable so nobody points it somewhere else by
accident.

A fresh install scrapes only Prometheus itself, which is enough to prove the
path works and nothing else. What you add next is up to what you run.

## Adding a target

Every service that exposes `/metrics` is a job in
[`config/prometheus.yml`](config/prometheus.yml):

```yaml
  - job_name: traefik
    static_configs:
      - targets: ["traefik:8080"]
```

then `docker compose restart prometheus`. There is no reload endpoint —
`--no-web.enable-lifecycle` is set, because that endpoint has no authentication
either.

Prometheus has to be able to *reach* the target, which on this host means the
target joins this stack's internal network, or Prometheus joins a network the
target is on. It is on `app-internal` and nothing else by default.

## Collecting from the host

A container cannot see the machine it runs on. Two overlays change that, and
both are opt-in because both read the host:

```bash
docker compose -f docker-compose.yml -f node-exporter.yml up -d
docker compose -f docker-compose.yml -f cadvisor.yml up -d
docker compose -f docker-compose.yml -f node-exporter.yml -f cadvisor.yml up -d
```

| | What it adds | What it reads |
|---|---|---|
| `node-exporter.yml` | CPU, memory, disk, filesystem, network for the host | `/proc`, `/sys` and `/` mounted read-only, plus the host PID namespace — which includes process names and command lines |
| `cadvisor.yml` | CPU, memory, network, filesystem **per container** | the host's cgroups, `/var/lib/docker` and `/var/run` read-only, and `/dev/kmsg` |

Neither writes anything, neither publishes a port, and both listen only on this
stack's internal network. **cAdvisor runs without `--privileged`**, which
upstream's documented command uses — verified, with per-container metrics
arriving.

Both need their job added to `config/prometheus.yml`; the comment at the top of
each overlay gives the block to paste.

That is the whole trade: a read of everything the kernel says about the machine,
in exchange for knowing when it is about to run out of disk. Worth it on a host
you own, and a decision rather than a default.

## Security model

- **Prometheus is not routed and publishes no port.** Measured: unreachable
  from the proxy network, reachable from Grafana.
- **`--no-web.enable-lifecycle` and `--no-web.enable-admin-api`.** Both are off
  upstream; they are named so a changed default cannot turn them on. The admin
  API can delete series.
- **Grafana's password is a Docker Secret**, read natively through Grafana's
  `__FILE` convention. Without it Grafana creates `admin`/`admin`.
- **Sign-up and anonymous access are off**, and set explicitly rather than
  relied on.
- **Four outbound behaviours are off**: usage reporting, update checks, plugin
  update checks and the news feed — all on by default, all to grafana.com.
- **`read_only`, `cap_drop: ALL`, `no-new-privileges`, non-root** on both base
  services.
- **`acc-tailscale`.** A metrics dashboard describes the installation it
  watches: which hosts exist, what runs on them, when they are busy and when
  they fail.

## Known limits

- **Grafana under `read_only` needs `/usr/share/grafana/data` as tmpfs**, or its
  core data source plugins are never registered — the container starts, the log
  says nothing, and every query answers "Plugin not registered". The tmpfs is in
  the compose file; the trap is recorded because an upgrade could move it.
- **No dashboard ships with this stack.** Grafana's dashboard catalogue and
  the community dashboards for node_exporter and cAdvisor are a download from
  grafana.com, which is a decision rather than a default. Provisioning
  directories are present and empty.
- **Alerting is not configured.** Grafana can alert; nothing here sets up a
  contact point, and no delivery has been tested.
- **Retention is a guess, not a measurement.** `PROMETHEUS_RETENTION=30d`. What
  that costs in disk depends entirely on how many series you scrape.
- **SAML is Enterprise.** Generic OAuth and LDAP are in the AGPL build; SAML,
  team sync, enhanced LDAP and protected roles are not.
- **`sec-2` is not measured** against Grafana, which loads its interface in one
  burst and then polls.
- **Nothing here has run behind this repository's Traefik yet.** The stack is
  `scaffolded`.

## Backup

| | |
|---|---|
| **Dashboards and users** | `./volumes/grafana` — Grafana's SQLite: dashboards, users, API keys, alert rules. The part you would miss |
| **The metrics** | `./volumes/prometheus` — the time series. Large, and expiring by design; a gap here is history you cannot reconstruct, not a broken install |
| **The password** | `.secrets/grafana_admin_password.txt` — restoring `volumes/grafana` without it leaves you locked out of the admin account |
| **Reproducible** | `config/` is in git |
| **Quiescing** | Stop Grafana before copying its SQLite. Prometheus writes blocks continuously; stop it or accept that the newest block may be partial |

```yaml
# /etc/borgmatic/config.yaml
source_directories:
  - /srv/secure-docker-blueprint/monitoring/grafana-prometheus/volumes/grafana
```

`volumes/prometheus` is not in that list. It is large, it expires anyway, and
restoring last month's metrics into a running instance is rarely what anyone
wants. Add it if the history matters to you.

Restore: put the volumes back with `volumes/grafana` owned by `472:472` and
`volumes/prometheus` by `65534:65534`, restore the secret, start the stack.
