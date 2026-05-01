# Monitoring

Self-hosted monitoring stack — covers five axes: **uptime**, **cron / scheduled-job monitoring**, **host & container metrics**, **content changes**, **disk health**. Each app in its own subdirectory, drafted and tested independently. Mix-and-match based on what you actually need — you do not need all of them.

## Status

✅ Ready · ⚠️ Draft · 📋 Planned

### Uptime & status pages

| App | Approach | Status | Notes |
|---|---|---|---|
| [Uptime Kuma](uptime-kuma/) | UI-driven, SQLite | ⚠️ | Community default. Click-config, 90+ notification integrations, public status pages. |
| [Gatus](gatus/) | YAML-as-code, SQLite/Postgres | ⚠️ | Config-as-code counterpart. Prometheus export built-in. |
| [Statping](#) | UI-driven | 📋 | Older alternative to Kuma. Less active, but richer plugin ecosystem. |
| [ciao](#) | Minimal HTTP checks | 📋 | Ruby, YAML-driven. Tiny — "Gatus without the UI." |
| [Checkmate](#) | Modern YAML uptime | 📋 | Newer alternative to Gatus, richer UI. |

### Cron & scheduled-job monitoring

| App | Approach | Status | Notes |
|---|---|---|---|
| [Healthchecks](healthchecks/) | Dead-man's switch for cron / backup / scheduled jobs | ⚠️ | Django + SQLite default. Migrated from `apps/healthchecks/` — structurally belongs in monitoring, not user-facing apps. |

### Host & container metrics

| App | Approach | Status | Notes |
|---|---|---|---|
| [Beszel](beszel/) | Hub + local agent | ⚠️ | Lightweight (~20 MB per agent), modern, per-container Docker stats. |
| [Beszel Agent](beszel-agent/) | Standalone agent for remote hosts | ⚠️ | Deploy on each additional host; same hub key, no hub needed on the remote. |
| [Zabbix](#) | Full NMS (Server + Frontend + Agent + DB) | 📋 | Enterprise-grade. Heavy — use only if you need SNMP, auto-discovery, or complex triggers. |
| [Grafana + Prometheus](#) | Scrape-and-visualize classic | 📋 | Industry standard. Prometheus stores + Grafana dashboards. Needs scrape targets (Beszel can export; cAdvisor / node-exporter are typical). |

### Content & web change detection

| App | Approach | Status | Notes |
|---|---|---|---|
| [changedetection.io](changedetection/) | Page diff + notification | ⚠️ | Restock / price / ToS / defacement watcher. |

### Disk health

| App | Approach | Status | Notes |
|---|---|---|---|
| [Scrutiny](#) | S.M.A.R.T. dashboard | 📋 | Hub + collector on each host with disks. Needs `/dev/sd*` passthrough. |

## Recommended starter combo

Pick one per axis you care about:

| Need | Recommendation |
|---|---|
| "Is my website / service up?" | **Uptime Kuma** (UI) OR **Gatus** (YAML) |
| "What is my server doing right now?" | **Beszel** |
| "Did this external page change?" | **changedetection.io** |
| "Is my disk about to fail?" | Scrutiny *(planned)* |
| "Long-term metric graphs / capacity planning?" | Grafana + Prometheus *(planned)* |

A realistic homelab stack: Kuma OR Gatus + Beszel + changedetection.io. Covers the 90% case. Add `beszel-agent/` on each additional host you want in the metrics view.

## Why four are drafted, six are planned

The four drafted apps cover **four distinct monitoring axes** with minimal overlap. The six planned apps are overlapping alternatives or specialized heavier tools — draft them on demand when the drafted options don't fit.

Rationale per planned:

- **Statping / ciao** — overlap with Uptime Kuma. Pick up only if Kuma turns out unsuitable.
- **Checkmate** — overlap with Gatus. Pick up if you want to compare YAML-config uptime tools.
- **Zabbix** — heavy enterprise NMS. Draft when you actually need SNMP / auto-discovery / multi-tenant.
- **Grafana + Prometheus** — bigger project. Needs Beszel / node-exporter / cAdvisor as exporters first. Draft when you've outgrown Beszel's built-in graphs.
- **Scrutiny** — requires physical-disk passthrough (`/dev/sda` etc.) — host-specific. Draft when deploying on hardware with spinning rust or NVMe where SMART data matters.

## Layout

Each app subdirectory follows the blueprint structure:

```
monitoring/<app>/
├── docker-compose.yml
├── .env.example
├── .gitignore
├── README.md
└── volumes/            # gitignored, created at setup
```
