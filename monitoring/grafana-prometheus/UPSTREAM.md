# Upstream Reference

## Source

- **Image:** https://hub.docker.com/r/grafana/grafana · https://hub.docker.com/r/prom/prometheus
- **GitHub:** https://github.com/grafana/grafana · https://github.com/prometheus/prometheus
- **Docs:** https://grafana.com/docs/grafana/latest/ · https://prometheus.io/docs/
- **License:** AGPL-3.0 (Grafana) / Apache-2.0 (Prometheus, node_exporter, cAdvisor)
- **Use restrictions:** none — https://github.com/grafana/grafana/blob/main/LICENSE · checked 2026-09-23
- **Edition gating:** Grafana keeps SAML authentication, team sync, enhanced LDAP and protected roles in the paid Enterprise edition; generic OAuth and LDAP are in the AGPL build — https://github.com/grafana/grafana/blob/main/docs/sources/introduction/grafana-enterprise.md · checked 2026-09-23
- **Commercial model:** paid self-hosted edition — https://grafana.com/pricing/ · checked 2026-09-23
- **Decision facts checked:** 2026-09-23
- **Origin:** US · Grafana Labs (Raintank, Inc.) · non-EU (Prometheus: CNCF, no single jurisdiction)
- **Domain:** Monitoring
- **Role:** Metrics collection and dashboards — a time series database, its scraper, and the interface that queries it
- **Based on version:** `13.3.0` (Grafana), `v3.15.1` (Prometheus)

## Project maturity

Grafana 76 870 stars, Prometheus 66 196, node_exporter 13 805, cAdvisor 19 440.
All four are long past 1.0 and on regular releases; Prometheus is a graduated
CNCF project.

## What we use

- `grafana/grafana:13.3.0` — the only routed service.
- `prom/prometheus:v3.15.1` — internal network only, no router, no host port.
- Two opt-in overlays: `prom/node-exporter:v1.12.1` for host metrics and
  `ghcr.io/google/cadvisor:v0.60.6` for per-container metrics.

`ghcr.io/google/cadvisor` rather than `gcr.io/cadvisor/cadvisor`: the gcr
repository serves `latest` but not the versioned tag, and a pin is not optional
here.

## What we changed and why

| Change | Reason |
|--------|--------|
| **Prometheus is not routed and publishes no port** | It has no authentication of any kind. Anything that reaches it can read every metric, run any query and read the scrape configuration. Most tutorials publish 9090 |
| `--no-web.enable-lifecycle`, `--no-web.enable-admin-api` | Both are off upstream; named so they stay off. `/-/reload`, `/-/quit` and an API that can delete series |
| Grafana's password from a Docker Secret | Without it Grafana creates `admin`/`admin` |
| `GF_ANALYTICS_REPORTING_ENABLED`, `CHECK_FOR_UPDATES`, `CHECK_FOR_PLUGIN_UPDATES`, `GF_NEWS_NEWS_FEED_ENABLED` all false | All four are **on** by default and reach grafana.com |
| `GF_USERS_ALLOW_SIGN_UP=false`, `GF_AUTH_ANONYMOUS_ENABLED=false` | Sign-up is off upstream too; both are set so a changed default cannot open the instance |
| A provisioned Prometheus data source | Otherwise the first thing anyone does is type the URL into a form |
| tmpfs on `/usr/share/grafana/data` | Required under `read_only` — see below |
| The host collectors are overlays | They read the host. That is a deliberate step, not something a first start brings up |
| cAdvisor without `--privileged` | Upstream's documented command uses it. Verified unnecessary |
| `PROMETHEUS_RETENTION=30d` | Upstream keeps 15 days; this is the only thing between a long uptime and a full disk, so it is a named variable rather than a default |

## Verified on the images (2026-09-23)

Not a host verification in the sense of running behind `core/traefik` — but the
two overlays did read this host.

- Both base services healthy, `read_only`, `cap_drop: ALL`,
  `no-new-privileges`, non-root.
- **Grafana 13 needs `/usr/share/grafana/data` writable, or its core data
  source plugins are never registered.** Under `read_only: true` with only
  `/tmp` as tmpfs, the container starts, the log shows nothing unusual, the
  data source is provisioned and listed — and every query fails with
  `{"statusCode":404,"messageId":"plugin.notRegistered"}`. Isolated by testing
  each tmpfs path against a clean volume: `/tmp` alone fails, `/tmp` plus
  `/usr/share/grafana/data` works.
- **Prometheus rejects `--web.enable-lifecycle=false`.** It uses kingpin flags,
  where the negative form is `--no-<flag>`; `=false` exits with
  `unexpected false` before anything starts.
- Grafana reads any `GF_*` variable ending in `__FILE` from the file it names,
  so the admin password needs no wrapper.
- Anonymous requests to `/api/datasources` and `/api/search` answer `401`, and
  so does a wrong password.
- **Prometheus is unreachable from the proxy network** — measured from a
  container there — and reachable from Grafana.
- **The overlays work, and cAdvisor needs no `--privileged`.** With both
  applied, Prometheus scraped three targets: `count(up==1)` = 3,
  `count(node_cpu_seconds_total)` = 64, `count by (name)(container_last_seen)`
  = 15 containers, and `node_memory_MemTotal_bytes` returned this host's real
  memory size.
- Grafana logs an error for every provisioning subdirectory that does not
  exist, so `dashboards/`, `plugins/`, `alerting/` and `notifiers/` are present
  and empty.
- Idle: Grafana 269 MiB anonymous, Prometheus 41 MiB with three targets,
  node_exporter 9 MiB, cAdvisor 16 MiB.

What a host run still has to establish: the route through `core/traefik`, a
dashboard that someone actually reads, alerting with a delivery path, and what
the series count does to Prometheus' memory over weeks rather than minutes.

## What reaches the network on its own

Grafana's four outbound behaviours are off: usage reporting, update checks,
plugin update checks and the news feed. Installing a plugin from the catalogue
still reaches grafana.com, which is what a plugin catalogue is.

Prometheus, node_exporter and cAdvisor make no outbound call of their own.
Prometheus reaches exactly the targets in `config/prometheus.yml`.

## Version notes

- Grafana moved to `13.3.0` on 2026-11-05, not run on a host at this tag; the
  findings above were measured on `13.2.2`. The one breaking change listed is
  the `config.ini` section `marketplace`, renamed `plugins_marketplace`; this
  stack does not set it. The Alpine image drops `bash`; BusyBox `sh` and
  `wget`, which the healthcheck uses, stay, and the entrypoint's `__FILE`
  handling is rewritten for `sh`. 13.2.5 fixes plugins reported as "not
  registered" when a request times out. Advisories fixed: CVE-2026-13719,
  CVE-2026-13720, CVE-2026-15577, CVE-2026-17183, CVE-2026-33374,
  CVE-2026-81841, CVE-2026-88858, CVE-2026-88967, CVE-2026-93294,
  CVE-2026-95502, CVE-2026-100105 (13.3.0), and CVE-2026-103506 in the 13.2.5
  patch line.
- Moved `prom/prometheus` to `v3.15.1` on 2026-11-05 (released 2026-10-21), not
  run on a host at this tag; the `v3.16.0-rc` tags are pre-releases. 3.15.1 is a
  security release: the container image's CA certificates distrust "emSign ECC
  Root CA - G3" and "Comodo AAA Services root" after the compromise of eMudhra
  intermediate CA keys, the build moves to Go 1.27.3 (`net/http`,
  `net/textproto`, `crypto/tls`, `html/template`), and `golang.org/x/net` to
  v0.60.0 for HTTP/2 vulnerabilities. 3.15.0 deprecates `--log.level` in favour
  of `runtime.log_level` in the configuration file (this stack sets neither),
  stabilises the XOR2 chunk encoding (opt-in, off by default) and fixes subquery
  evaluation past the last step of unaligned range queries. The flags this stack
  passes, the distroless image and `promtool check healthy` are unchanged, so the
  compose files keep their configuration. Sources:
  https://github.com/prometheus/prometheus/releases/tag/v3.15.1,
  https://github.com/prometheus/prometheus/releases/tag/v3.15.0

## Upgrade checklist

1. Read the release notes — https://github.com/grafana/grafana/releases and
   https://github.com/prometheus/prometheus/releases
2. Raise the tags in `.env` and in `.env.local.example`
3. `docker compose pull && docker compose up -d`
4. **Open a dashboard and run one query.** A Grafana that starts is not a
   Grafana that can query — see the plugin registration finding above
5. `docker compose logs prometheus` — no flag rejected, targets still up
6. Record the result in `Last verified` once it ran behind `core/traefik`

## Diff against upstream

```bash
# Every Grafana setting and its default
docker run --rm --entrypoint sh grafana/grafana:13.3.0 -c 'cat /usr/share/grafana/conf/defaults.ini' | head -80

# Prometheus' flags, including the negative forms
docker run --rm prom/prometheus:v3.15.1 --help
```
