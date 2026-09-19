# OpenCanary

Lightweight deception: fake FTP, Telnet, HTTP, MySQL and RDP services that
do nothing except look real and log every connection attempt against them.

## What security problem this solves

Detection through a completely different signal than logs or metrics from
your real services: **a legitimate user or automated process has no reason
to ever touch these ports.** Where an IDS or a SIEM has to distinguish real
attack traffic from an ocean of legitimate traffic, a canary service starts
from zero legitimate traffic — any connection at all is already the
finding.

## When this is useful

- Placed on an internal network segment, to catch lateral movement after
  some other control has already been bypassed
- As an early-warning tripwire for credential-stuffing or scanning activity
  against services that look worth targeting (a fake MySQL, a fake RDP)
- Alongside real monitoring, not instead of it — see "What this does not
  replace" below

## When this is not useful, and what it does not replace

**Not an IDS, not an EDR, not a SIEM.** It detects exactly one thing:
someone or something interacting with a service that should never receive
real traffic. It has no visibility into your actual applications, no
correlation engine, and nothing resembling behavioral analysis. A
sophisticated attacker who never touches this container's ports generates
zero signal here — that is a property of deception tooling generally, not a
gap specific to this stack.

**Not a replacement for CrowdSec** (`core/crowdsec/`), which analyzes real
service logs and reputation data. The two are complementary: CrowdSec
watches traffic against services people actually use; OpenCanary watches
traffic against services nobody should be using at all.

## What is sensitive here

Nothing persistent — this stack holds no credentials, no user data, and no
state that survives a restart by design (see Backup below). What *is*
sensitive is what a hit represents: source IP, timestamp, and whatever
credentials an attacker tried against the fake login. Treat the log stream
itself as an incident signal, not routine noise.

## The portscan module does not work in Docker, and stays off

Upstream's portscan detection shells out to `iptables` to watch for SYN
scan patterns. A container's network namespace does not give it the host's
own `iptables` view, and — separately — a host running nftables (the
current default on most modern Linux distributions) does not expose the
`iptables` interface OpenCanary's portscan module expects at all. Verified
against upstream's own module source and the project's own documented
limitation, not assumed. `config/opencanary.conf` sets
`"portscan.enabled": false` explicitly, with the reason recorded in the
file. This is **not** worked around with `network_mode: host` or added
capabilities — see UPSTREAM.md for why that path was rejected.

## Enabled fake services

FTP (21), Telnet (23), HTTP (80, a fake NAS login page), MySQL (3306), RDP
(3389) — a representative, deliberately small default. Upstream ships
several more modules (git, https, httpproxy, mongodb, mssql, ntp, redis,
sip, snmp, ssh, tftp, vnc); enable more in `config/opencanary.conf` and
publish the matching port in `.env` and `docker-compose.yml`.

**SMB is not enabled by default.** Its module needs an extra host-side
Samba audit-log file mounted in — a real Samba installation on the host,
which this stack does not assume exists. Enabling it means adding that
bind mount and `smb.auditfile`'s path together; see upstream's own
[Dockerised OpenCanary wiki page](https://github.com/thinkst/opencanary/wiki/Using-Dockerised-OpenCanary)
for the exact mount.

## Security model

- **Starts privileged, drops immediately.** The upstream image has no
  `USER` — it starts as root to bind the (several sub-1024) fake-service
  ports, then drops to `nobody`/`nogroup` itself via its own `--uid`/`--gid`
  flags. `cap_drop: ALL` plus `NET_BIND_SERVICE` (to bind) and
  `SETUID`/`SETGID` (to actually drop) — verified against a live container;
  the log line `set uid/gid 65534/65534` confirms the drop happens.
- **`read_only: true`** — verified against a live container, with `/tmp`
  and `/run` on tmpfs (Twisted's daemon runner writes a PID file under
  `/run`).
- **No outbound internet access by default** (`app-internal` is
  `internal: true`) — nothing this stack does out of the box needs it.
  Removing that flag is required if you enable webhook/Slack/Teams/hpfeeds
  alerting (see below); inbound connections to the published fake-service
  ports are unaffected either way.
- **No secrets** — OpenCanary asks other people for credentials; it needs
  none of its own.

## Setup

```bash
cp .env.example .env
# Review: which ports you actually want reachable, and from where

docker compose up -d
docker compose logs -f    # every hit logs here as JSON, in real time
```

A hit looks like this in the logs — source IP, port, and (for FTP/Telnet/
HTTP/MySQL) whatever credential was attempted:

```json
{"src_host": "203.0.113.4", "dst_port": 21, "logdata": {"USERNAME": "admin", "PASSWORD": "..."}, ...}
```

## Alerting

No file handler and no webhook is configured by default — every hit
already reaches `docker compose logs`, and this stack runs fully
`read_only` with no writable log path. To get a real-time alert elsewhere,
add a handler to `config/opencanary.conf`'s `logger.kwargs.handlers` block
— OpenCanary ships `WebhookHandler`, `SlackHandler`, `TeamsHandler` and an
`HpfeedsHandler` (confirmed by reading `opencanary/logger.py` directly).
A generic webhook pointed at this repository's own
[`monitoring/ntfy`](../../monitoring/ntfy/) is a reasonable, already-present
target — not wired up here, since which alert channel you want is a
deployment decision this stack does not make for you.

## Backup

| | |
|---|---|
| **Config** | `config/opencanary.conf` — which fake services are enabled and how they're configured. Not sensitive |
| **State** | None. No volume, no database — every hit is a log line, and this stack does not decide where your logs are retained |

No backup entry beyond the config file: a restored OpenCanary with the same
config is functionally identical to the one that existed before, because
it holds no state of its own. If you route hits to a log aggregator,
retention of that history is that system's concern, not this stack's.

## Local testing (no Traefik)

```bash
cp .env.local.example .env.local
docker compose -f docker-compose.local.yml --env-file .env.local up -d
curl -I http://localhost:8080/          # fake login page
nc localhost 2121                       # fake FTP banner
docker compose -f docker-compose.local.yml --env-file .env.local logs -f
docker compose -f docker-compose.local.yml --env-file .env.local down
```

## Verify on first deploy (Preview → Ready gate)

- [x] `docker compose config` clean; local stack `up -d` — running, privileges dropped to `nobody`/`nogroup` — **verified locally, 2026-09-19**
- [x] FTP, HTTP, MySQL, RDP and Telnet fake services all confirmed responding, with real access logged — **verified locally, 2026-09-19**
- [ ] The production compose's own sub-1024 port bindings on a real Linux host — this test host's Docker Desktop did not bind them the same way the local (high-port) stack did; see UPSTREAM.md
- [ ] A webhook/Slack/Teams alert handler actually delivering a notification
- [ ] SMB module enabled against a real Samba audit log

## Details

- [UPSTREAM.md](UPSTREAM.md) — source, upgrade checklist, deviations
