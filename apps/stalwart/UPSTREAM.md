# Upstream Reference

## Source

- **Image:** https://hub.docker.com/r/stalwartlabs/stalwart
- **GitHub:** https://github.com/stalwartlabs/stalwart
- **Docs:** https://stalw.art/docs/
- **License:** AGPL-3.0 (core; files marked SEL are under the Stalwart Enterprise License v2, and the published image is built with them)
- **Use restrictions:** none for the AGPL-3.0 code — https://github.com/stalwartlabs/stalwart#license · checked 2026-10-03
- **Edition gating:** multi-tenancy, branding, account archiving and un-deletion, live telemetry and alerts, AI models, masked addresses, SCIM, read replicas and sharded stores are listed as Enterprise — https://stalw.art/enterprise/ · checked 2026-10-03
- **Commercial model:** paid self-hosted edition; unlocked by a licence key — https://stalw.art/enterprise/ · checked 2026-10-03
- **Decision facts checked:** 2026-10-03
- **Origin:** United States and United Kingdom · Stalwart Labs LLC · non-EU
- **Domain:** Files, wiki and collaboration
- **Role:** Mail and collaboration server — SMTP, IMAP, JMAP, calendars, contacts and files in one binary
- **Based on version:** `v0.16.24`

Part of the development was funded through NLnet's NGI0 funds.

## Project maturity

14 927 stars, pushed 2026-10-03, release v0.16.24 on 2026-09-27; six patch
releases between 2026-08-24 and 2026-09-27. Still 0.x: upstream's upgrade page
states that upgrades are manual and that a minor release can need a migration.
Five advisories are published, each with a fixed release; the newest fix is
0.15.5.

## What we use

- `stalwartlabs/stalwart:v0.16.24`, one container, RocksDB in `volumes/data`.
- `mail.yml`, an opt-in overlay that publishes 25, 465 and 993.
- `ops/setup.sh`, which completes setup over the management API.

## What we changed and why

| Change | Reason |
|--------|--------|
| Setup over the API instead of the web wizard | The wizard runs on plain HTTP behind a password printed once to the log. `ops/setup.sh` pins a one-time administrator for a single start, completes setup and starts the container again without it |
| `cap_add: NET_BIND_SERVICE` beside `cap_drop: ALL` | The binary carries the file capability `cap_net_bind_service`; without it in the bounding set the exec is refused with `operation not permitted` |
| `read_only: true` with a tmpfs on `/tmp` | The web interface bundle is unpacked into `/tmp`; everything else Stalwart writes is in the two volumes |
| Logs to standard output | Upstream's setup default is a log directory under `/var/log/stalwart`, which a read-only root filesystem does not have |
| `useXForwarded: true` | Behind Traefik every HTTP request arrives from the proxy's address. Measured: 110 failed logins from one address banned that address for the whole listener. With the setting on, the ban landed on the address in `X-Forwarded-For` and a second client behind the same proxy kept working |
| Ban periods of 24 hours | Upstream's default leaves `authBanPeriod`, `abuseBanPeriod`, `loiterBanPeriod` and `scanBanPeriod` unset, which keeps a ban until it is removed by hand |
| No certificate requested during setup | The default requests one from Let's Encrypt with the TLS-ALPN challenge on port 443, which Traefik holds. README, "Certificate" |
| Mail ports in an overlay, three of them | Upstream's command publishes ten ports. 587, 143 and 110 are not listened on after setup; 995 and 4190 stay unpublished |
| `APP_TRAEFIK_ACCESS=acc-tailscale` | A blueprint ships closed |

Upstream's image is used as published. One built here without the `enterprise`
cargo feature would be AGPL-3.0 in full; that route is
[`docs/standards/custom-application.md`](../../docs/standards/custom-application.md)
and has not been taken.

## Verified on the image (2026-10-03)

Not a host verification: no Traefik router, no certificate, no other mail
system.

- Starts healthy as uid 2000 under `read_only`, `cap_drop: ALL` with
  `NET_BIND_SERVICE`, and `no-new-privileges`; without the capability the exec
  is refused.
- `ops/setup.sh` runs through in both variants: setup accepted, the
  administrator's password written to `.secrets/admin_pwd.txt`, the ban periods
  and `useXForwarded` read back from the API as set.
- Listeners after setup: 25, 465, 993, 995, 4190, 443 and 8080.
- Port 25: STARTTLS offered and no AUTH; a recipient at a foreign domain is
  answered `550 5.1.2 Relay not allowed`, an unknown local mailbox `550`.
- Port 465: `MAIL FROM` before authentication is answered `503`, a sender
  address the account does not own `501`.
- A message submitted on 465 arrived in the recipient's inbox over IMAP on 993;
  a wrong IMAP password is refused.
- Sign-in to the web interface over `http://localhost:8080`: 55 requests for
  the sign-in and the first page.
- 115 MiB at idle with one mailbox, 23 pids.

What a host run still has to establish: the route through `core/traefik`, a
certificate on the mail ports, delivery to and from another mail system, the
client address Stalwart sees on a published port, and a restore.

## What reaches the network on its own

Read from the start log of v0.16.24:

- **The web interface.** Downloaded at start from
  `github.com/stalwartlabs/webui/releases/latest/download/webui.zip`. The image
  tag does not pin it; the address is the `resourceUrl` of the application
  record and can name an internal server.
- **Address data.** Four files from
  `github.com/sapics/ip-location-db/releases/download/latest/`, for country and
  network lookups.
- **Spam filter rules.** The log reports them updated at start and does not
  name a source.
- **DNS block lists.** 18 are configured; a lookup sends the connecting address
  to the list's operator.
- **DNS**, for MX, SPF, DKIM and DMARC lookups.

## Upgrade checklist

1. Read the release notes — https://github.com/stalwartlabs/stalwart/releases —
   and upstream's `UPGRADING` notes for the target version. At 0.x a minor
   release can need a migration
2. Copy `volumes/data` and `volumes/etc` with the container stopped
3. Raise `APP_TAG` in `.env` and in `.env.local.example`
4. `docker compose pull && docker compose up -d`
5. Sign in, send a message between two accounts, and read *Blocked IPs* and the
   queue
6. Record the result in `Last verified` once it ran behind `core/traefik`
