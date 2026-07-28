# Monitoring

Self-hosted monitoring stack — covers five axes: **uptime**, **cron / scheduled-job monitoring**, **host & container metrics**, **content changes**, **disk health**. Each app in its own subdirectory, drafted and tested independently. Mix-and-match based on what you actually need — you do not need all of them.

## Status

🛡️ Ops-ready · ✅ Ready · 🚧 Preview · 📋 Planned

`🛡️ Ops-ready` means a restore has actually been performed — no service holds it yet. Full definitions: [`docs/standards/status-model.md`](../docs/standards/status-model.md).

### Uptime & status pages

| App | Approach | Status | Notes |
|---|---|---|---|
| [Uptime Kuma](uptime-kuma/) | UI-driven, SQLite | 🚧 | Community default. Click-config, 90+ notification integrations, public status pages. |
| [Gatus](gatus/) | YAML-as-code, SQLite/Postgres | 🚧 | Config-as-code counterpart. Prometheus export built-in. |
| [Statping](#) | UI-driven | 📋 | Older alternative to Kuma. Less active, but richer plugin ecosystem. |
| [ciao](#) | Minimal HTTP checks | 📋 | Ruby, YAML-driven. Tiny — "Gatus without the UI." |
| [Checkmate](#) | Modern YAML uptime | 📋 | Newer alternative to Gatus, richer UI. |

### Cron & scheduled-job monitoring

| App | Approach | Status | Notes |
|---|---|---|---|
| [Healthchecks](healthchecks/) | Dead-man's switch for cron / backup / scheduled jobs | 🚧 | Django + SQLite default. Migrated from `apps/healthchecks/` — structurally belongs in monitoring, not user-facing apps. |

### Host & container metrics

| App | Approach | Status | Notes |
|---|---|---|---|
| [Beszel](beszel/) | Hub + local agent | 🚧 | Lightweight (~20 MB per agent), modern, per-container Docker stats. |
| [Beszel Agent](beszel-agent/) | Standalone agent for remote hosts | 🚧 | Deploy on each additional host; same hub key, no hub needed on the remote. |
| [Zabbix](#) | Full NMS (Server + Frontend + Agent + DB) | 📋 | Enterprise-grade. Heavy — use only if you need SNMP, auto-discovery, or complex triggers. |
| [Grafana + Prometheus](#) | Scrape-and-visualize classic | 📋 | Industry standard. Prometheus stores + Grafana dashboards. Needs scrape targets (Beszel can export; cAdvisor / node-exporter are typical). |

### Content & web change detection

| App | Approach | Status | Notes |
|---|---|---|---|
| [changedetection.io](changedetection/) | Page diff + notification | 🚧 | Restock / price / ToS / defacement watcher. |

### Disk health

| App | Approach | Status | Notes |
|---|---|---|---|
| [Scrutiny](#) | S.M.A.R.T. dashboard | 📋 | Hub + collector on each host with disks. Needs `/dev/sd*` passthrough. |

### Notification receivers

Not a monitoring axis — the receiving end of one. Every service above can reach
these, which is what makes them usable as a single channel across all of them.
They belong on a different host than the services that publish to them; see
[Where the receiver runs](#where-the-receiver-runs).

| App | Approach | Status | Notes |
|---|---|---|---|
| [ntfy](ntfy/) | Topic-based push over HTTP | 🚧 | Self-hosted, no account. A free public instance exists, so an off-host path costs no second machine. iOS push needs `upstream-base-url`. |
| [Gotify](#) | Token-based push, own Android app | 📋 | Self-hosting only — no public instance, so it always needs a home. Healthchecks reaches it through Apprise rather than natively. |

## Recommended starter combo

Pick one per axis you care about:

| Need | Recommendation |
|---|---|
| "Is my website / service up?" | **Uptime Kuma** (UI) OR **Gatus** (YAML) |
| "What is my server doing right now?" | **Beszel** |
| "Did this external page change?" | **changedetection.io** |
| "Is my disk about to fail?" | Scrutiny *(planned)* |
| "Long-term metric graphs / capacity planning?" | Grafana + Prometheus *(planned)* |
| "How do the alerts reach me?" | **ntfy** — on a different host than the rest |

A realistic homelab stack: Kuma OR Gatus + Beszel + changedetection.io. Covers the 90% case. Add `beszel-agent/` on each additional host you want in the metrics view, and ntfy wherever it is not next to them.

## Alerting

Alerting is not a service in this category — it is delivered by the services above.
Each ships its own notification channels; none of them needs a separate tool.

| Service | Alerts on | Configured |
|---|---|---|
| Uptime Kuma | an endpoint stops responding | per monitor, in the UI — many channel integrations |
| Gatus | a condition in `config.yaml` fails | `alerting:` block plus `alerts:` per endpoint |
| Healthchecks | an expected ping **fails to arrive** | per check; email needs working SMTP, otherwise webhook or chat |
| Beszel | a threshold is crossed (CPU, memory, disk, temperature) | per system, in the hub |
| changedetection.io | a watched page changed | per watch |

### Which service can reach which channel

Pick the channel first, then check that every service in use can actually reach it.
Verified against upstream documentation, 2026-07-27:

| | ntfy | Gotify | Matrix | Webhook | Email (SMTP) |
|---|---|---|---|---|---|
| Uptime Kuma | ✅ | ✅ | ✅ | ✅ | ✅ |
| Gatus | ✅ | ✅ | ✅ | ✅ | ✅ |
| Healthchecks | ✅ | via Apprise | ✅ | ✅ | ✅ |
| changedetection.io | ✅ | ✅ | ✅ | ✅ | ✅ |
| Beszel | ✅ | ✅ | ✅ | ✅ | — |

Two entries decide setups:

- **Beszel sends only through Shoutrrr URLs, and email is not among them.** A single
  channel spanning all five services therefore cannot be SMTP.
- **Healthchecks reaches Gotify only through Apprise**, which needs `APPRISE_ENABLED`
  and the `apprise` package present in the image — not the stock configuration. Its
  ntfy, webhook, Matrix and email integrations are native.

Channels are not exclusive, and mixing them is the normal case: several services can
alert into the same ntfy topic while a webhook carries the same event into a chat
platform or an automation runner. Which one fits depends on the devices that have to
receive it.

### The closed-circuit principle

Safety engineering separates two ways to build an alarm. An open-circuit alarm fires
when a signal arrives. A **closed-circuit** alarm fires when an expected signal *stops*
arriving — cut the wire and it sounds. Only the second kind detects its own failure,
which is why emergency-stop chains are wired that way.

Monitoring splits the same way. Uptime Kuma, Gatus, Beszel and changedetection.io
alert when they *observe* something wrong — open circuit, and that works only while
they are running. Healthchecks alerts when an expected ping stops arriving — closed
circuit. It is the only pattern here that catches a monitor that died, a host that
went down, or a timer that was silently disabled weeks ago.

This is also why `backup/borgmatic` reports to Healthchecks or Uptime Kuma rather
than logging locally — a backup that stopped running looks exactly like a backup that
never had a problem.

### Where the receiver runs

The services above are the blueprint's part. The topology around them belongs to
whoever deploys it, and one consideration carries enough weight to state plainly:

**A notification receiver on the monitored host dies with it.** When the host stops,
the monitoring services stop — and a receiver sitting next to them stops too. The
outage that most needs an alert is then the one that produces none. The same applies
to email through an SMTP server on that host. A closed-circuit design only closes
this gap if something outside the host is watching.

The two self-hostable receivers leave different room for that:

| Receiver | Self-hosted | Operated by the project |
|---|---|---|
| [ntfy](ntfy/) | Docker — this repository | free public instance |
| Gotify | Docker — *planned* | — |

ntfy has an off-host path that costs no second machine. Gotify always needs a home,
so choosing that home is part of the design rather than an afterthought.

The [`ntfy/`](ntfy/) stack is built to stand alone — one Traefik, one compose file,
no dependency on the rest of this category. Deploying it on a second host is the
intended use, not a workaround.

For a receiver on a private address, note that Healthchecks refuses to deliver
webhooks into private IP ranges unless `INTEGRATIONS_ALLOW_PRIVATE_IPS` is enabled.

### Proving a channel works

A notification path that has never fired is worth as little as a backup that has
never been restored. Both fail the same way: silently, and only when it matters.

For each channel actually relied on:

1. Trigger it deliberately — stop a monitored container, let a check expire, cross a
   threshold on purpose.
2. Confirm the notification **arrives**, on the device that is supposed to receive it.
3. Write down which channel was proven, and when.

Whether it also arrives while the sending host itself is down is a property of the
topology, not of the channel — established where the deployment is, not here.

## Why these seven are in place and seven are planned

The services in place cover **four distinct monitoring axes** with minimal overlap — uptime (Kuma or Gatus), host and container metrics (Beszel + agent), scheduled-job liveness (Healthchecks), and content change (changedetection.io) — plus ntfy as the receiving end for all of them. The seven planned apps are overlapping alternatives or specialized heavier tools — add them on demand when the ones in place don't fit.

Rationale per planned:

- **Statping / ciao** — overlap with Uptime Kuma. Pick up only if Kuma turns out unsuitable.
- **Checkmate** — overlap with Gatus. Pick up if you want to compare YAML-config uptime tools.
- **Zabbix** — heavy enterprise NMS. Draft when you actually need SNMP / auto-discovery / multi-tenant.
- **Grafana + Prometheus** — bigger project. Needs Beszel / node-exporter / cAdvisor as exporters first. Draft when you've outgrown Beszel's built-in graphs.
- **Scrutiny** — requires physical-disk passthrough (`/dev/sda` etc.) — host-specific. Draft when deploying on hardware with spinning rust or NVMe where SMART data matters.
- **Gotify** — overlaps with ntfy. Pick up if the Android app or the token model fits better; note that Healthchecks reaches it only through Apprise.

## Layout

Each app subdirectory follows the blueprint structure:

```text
monitoring/<app>/
├── docker-compose.yml
├── .env.example
├── .gitignore
├── README.md
└── volumes/            # gitignored, created at setup
```
