# Upstream Reference

## Source

- **Image:** https://hub.docker.com/r/thinkst/opencanary
- **GitHub:** https://github.com/thinkst/opencanary
- **Docs:** https://github.com/thinkst/opencanary/wiki
- **License:** BSD 3-Clause
- **Decision facts checked:** not yet
- **Origin:** South Africa · Thinkst Applied Research · non-EU. OpenCanary is
- **Domain:** Security operations
- **Role:** Honeypot: fake network services that log every connection attempt
  the open-source counterpart to Thinkst's commercial Canary product —
  confirmed via upstream's own README; this stack uses only the
  open-source project
- **Based on version:** `0.9.9`
- **Verification snapshot:** 2026-09-19 — local Compose stack booted and
  every enabled fake service exercised against a live container; the
  production compose's sub-1024 port publishing not confirmed on this test
  host (see Known limitations)

## What we use

- `thinkst/opencanary:0.9.9` — the official image, confirmed present as a
  specific version tag on Docker Hub (not just `latest`)

## Why not `network_mode: host` (upstream's own default)

Upstream's own `docker-compose.yml` uses `network_mode: "host"` by default,
apparently for convenience — it avoids maintaining an explicit `ports:`
mapping per enabled module rather than being a hard functional requirement
of any individual fake-service module. This repository's own networking
standard (`docs/standards/networking.md`) restricts host networking to one
named exception, `core/dnsmasq`, for a DNS-specific reason that does not
apply here. This stack uses normal bridge networking with an explicit
`ports:` list instead — verified against a live container that every
enabled module (FTP, HTTP, MySQL, RDP, Telnet) works identically this way.

## What we changed vs. upstream's own compose

| Change | Reason |
|--------|--------|
| Bridge networking + explicit `ports:` instead of `network_mode: host` | See above |
| `cap_drop: ALL` + `cap_add: [NET_BIND_SERVICE, SETUID, SETGID]` | Verified against a live container: the image starts as root (no `USER` set) to bind sub-1024 ports, then drops to `nobody`/`nogroup` via its own `--uid`/`--gid` CLI flags — both binding and the drop itself need capabilities upstream's own compose file does not specify (it runs unhardened) |
| `read_only: true` + `tmpfs: [/tmp, /run]` | Verified against a live container: Twisted's daemon runner writes a PID file under `/run`; without it as tmpfs, startup fails with `Read-only file system: '/var/run/opencanaryd.pid'` |
| `portscan.enabled: false`, explicit and commented | Verified against upstream's own module source (`opencanary/modules/portscan.py`) and wiki: the module shells out to `iptables`, which does not work the same way inside a container's network namespace, and does not work at all against an nftables-backed host. Not worked around |
| `app-internal` network set `internal: true` | Nothing this stack does by default needs outbound access; documented as removable if webhook/Slack/Teams/hpfeeds alerting is enabled |
| SMB module left disabled | Needs a real host-side Samba audit-log file this stack does not assume exists — see README.md |

## What was actually verified, and how

- `docker inspect thinkst/opencanary:0.9.9` — confirmed `User: ""` (root by
  default), entrypoint `opencanaryd`, default `Cmd: ["--dev",
  "--uid=nobody", "--gid=nogroup"]`.
- Read `opencanary/logger.py` directly from inside the image to confirm the
  real alerting handler classes (`WebhookHandler`, `SlackHandler`,
  `TeamsHandler`, `HpfeedsHandler`) rather than assuming from documentation.
- Ran with `--cap-drop ALL` and only `NET_BIND_SERVICE`/`SETUID`/`SETGID`
  added: FTP, HTTP, MySQL, RDP and Telnet fake services all started, the
  log line `set uid/gid 65534/65534` confirmed the privilege drop actually
  happened, and a real connection to each (FTP banner, HTTP 302 to the fake
  login page) was logged with the correct source IP.
- Ran the same configuration additionally under `--read-only --tmpfs /tmp
  --tmpfs /run`: identical clean start.
- Ran the actual `docker-compose.local.yml` end to end on high, unprivileged
  ports (2121/2323/8080/3306/3389 → 21/23/80/3306/3389): all five services
  responded correctly and access was logged.
- Ran the actual production `docker-compose.yml` (sub-1024 host ports):
  the container itself started and logged all five services binding
  correctly *inside* the container, but this test host (Docker Desktop for
  macOS) did not expose the corresponding host-side port bindings the same
  way the local (high-port) stack did — `docker compose ps` showed no
  `0.0.0.0:80->80/tcp`-style mapping. The compose file differs from the
  already-verified local one only in port numbers, so this is recorded as
  a fact about this test host rather than resolved either way.
- **Not verified:** the production compose's sub-1024 bindings on a real
  Linux host, any webhook/Slack/Teams/hpfeeds handler actually delivering,
  and the SMB module.

## Upgrade checklist

1. Watch [OpenCanary releases](https://github.com/thinkst/opencanary/releases)
2. Read the changelog — new fake-service modules or config keys occasionally
   land
3. Nothing to back up beyond `config/opencanary.conf` — see README.md#backup
4. Bump `APP_TAG` in `.env`
5. `docker compose pull && docker compose up -d`
6. Confirm each enabled module still starts and logs a test connection

## Known limitations

- **Portscan module is not available** — see above, not worked around.
- **Production compose's sub-1024 port bindings not confirmed on this test
  host** — see above.
- **No alert handler configured by default** — logs reach `docker compose
  logs` only until you add one. See README.md#alerting.
- **SMB module not enabled or exercised.**
