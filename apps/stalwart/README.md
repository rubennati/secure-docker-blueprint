# Stalwart

A mail and collaboration server in one binary: SMTP, IMAP, JMAP, CalDAV, CardDAV
and WebDAV, with spam filtering and a web interface for administration and for
each account's own settings. Upstream:
[stalwartlabs/stalwart](https://github.com/stalwartlabs/stalwart).

## Architecture

```text
Traefik ──http──→ app :8080      web interface, JMAP, CalDAV/CardDAV, autoconfig
Internet ───────→ app :25        mail from other servers          (mail.yml)
Mail clients ───→ app :465 :993  submission and IMAP, both TLS    (mail.yml)
                    │
                    ├── volumes/data   mail, accounts, settings, DKIM keys
                    └── volumes/etc    config.json — where the data store is
```

The web interface goes through Traefik like every other stack. SMTP and IMAP are
not HTTP, so the mail ports are published by the container itself, through the
opt-in file `mail.yml`. Without it no mail port is reachable from outside.

## Requirements

- **Outbound port 25.** Mail leaves the host on port 25. Many providers block it
  until asked; without it nothing is delivered.
- **Inbound 25, 465 and 993** open in the host's firewall, once `mail.yml` is in
  use.
- **A DNS zone you can edit**, and reverse DNS for the host's address pointing
  at `APP_TRAEFIK_HOST`.

## Setup

```bash
cp .env.example .env            # host name, mail domain
ops/init.sh                     # the data directories
sudo chown -R 2000:2000 volumes/etc volumes/data
ops/setup.sh                    # first start, setup and security settings
```

`ops/setup.sh` completes Stalwart's setup over its API instead of the web
wizard, writes the administrator's password to `.secrets/admin_pwd.txt` and
prints the user name. Sign in at `https://<APP_TRAEFIK_HOST>/admin`.

Then, in this order:

1. **DNS** — the records are listed in the web interface under the domain. See
   [DNS](#dns).
2. **Certificate** — see [Certificate](#certificate).
3. **Mail ports** — `docker compose -f docker-compose.yml -f mail.yml up -d`.
4. **Mailboxes** — create a user under *Directory › Accounts*. Do not use the
   administrator account for mail.

## Try it locally

```bash
cp .env.local.example .env.local
ops/init.sh --local
ops/setup.sh --local
```

`http://localhost:8080/admin` — the user is printed by `setup.sh`, the password
is in `.secrets/admin_pwd.txt`. SMTP answers on `localhost:1025`, submission on
`localhost:1465`, IMAP on `localhost:1993`, with a self-signed certificate. Mail
between local accounts works; nothing leaves the machine.

```bash
docker compose -f docker-compose.local.yml --env-file .env.local down
```

## DNS

The web interface lists the records for each domain as a zone file, ready to
copy: MX, SPF with `-all`, two DKIM keys, DMARC with `p=reject`, MTA-STS, TLS
reporting, and the SRV and autoconfig names mail clients look up. `ops/setup.sh`
generates the DKIM keys. Publish the records before sending the first mail: a
message without SPF and DKIM is what receiving servers score as spam, and
repeated spam scores are what puts an address on a block list.

The zone file names port 995 in an SRV record. `mail.yml` does not publish that
port; leave the record out or publish the port.

Stalwart can also write the records itself through a DNS provider's API
(*Settings › Network › DNS*). That is upstream's feature and has not been run
here.

## Certificate

SMTP and IMAP are encrypted by the mail server, not by Traefik, so it needs a
certificate for `APP_TRAEFIK_HOST` of its own. Until it has one it presents a
self-signed certificate, which mail clients refuse. Two ways, both upstream's:

| Way | How |
|---|---|
| Stalwart requests it | An ACME provider with the `Dns01` challenge and a DNS provider, under *Settings › TLS*. The HTTP and TLS-ALPN challenges need ports 80 and 443, which Traefik holds |
| You supply it | A certificate and key as PEM files, mounted into the container and referenced under *Settings › TLS › Certificates* |

Neither has been run here.

## Mail ports (`mail.yml`)

`mail.yml` publishes three ports and no more:

| Port | For | Who connects |
|---|---|---|
| 25 | SMTP | other mail servers — has to be reachable from the internet |
| 465 | Submission, TLS | mail clients sending |
| 993 | IMAP, TLS | mail clients reading |

`APP_MAIL_BIND` sets the host address they are published on. `0.0.0.0` is every
interface. A VPN address there keeps the client ports off the public interface;
port 25 then no longer receives mail from outside.

Stalwart also listens on 995 (POP3, TLS) and 4190 (ManageSieve) inside the
container. Add a line to `mail.yml` to publish one.

Traefik's access policies, rate limits and the CrowdSec bouncer do not apply to
these ports. What protects them is in the next section, and the host's firewall.

## Security model

Measured on the image on 2026-10-03:

- **No open relay.** Port 25 answers a recipient outside the hosted domains
  with `550 Relay not allowed`, and an unknown mailbox with `550`.
- **Sending needs a login, and only as yourself.** Port 465 refuses
  `MAIL FROM` before authentication, and refuses a sender address the account
  does not own.
- **Automatic bans, with an expiry.** Stalwart bans an address after 100 failed
  logins a day, 35 relay or recipient-probing attempts, 150 connections that
  send nothing, or 30 port scans. Upstream's default keeps a ban until someone removes it;
  `ops/setup.sh` sets 24 hours (`APP_BAN_HOURS`). Bans are listed under
  *Settings › Security › Blocked IPs*.
- **Bans land on the client, not on Traefik.** Behind a proxy Stalwart sees the
  proxy's address unless told to read `X-Forwarded-For`. Left at upstream's
  default, 100 failed logins through the web interface ban Traefik's address
  and the interface is gone for everyone. `ops/setup.sh` switches it on.
- **Non-root**, `read_only`, `cap_drop: ALL` with `NET_BIND_SERVICE`,
  `no-new-privileges`. The image runs as uid 2000.
- **The one-time setup administrator exists for one start.** `ops/setup.sh`
  generates it, uses it and starts the container again without it.
- **The web interface ships closed**, `acc-tailscale`. Autoconfig and MTA-STS
  are fetched by mail clients and other servers over HTTPS; they work once the
  interface is reachable for them.

Port 8080 inside the container trusts `X-Forwarded-For` from whoever connects.
It is not published; only containers on `proxy-public` reach it.

## Monitoring (optional)

- **The ports.** A TCP check on 25, 465 and 993 from outside the host —
  [`monitoring/uptime-kuma`](../../monitoring/uptime-kuma/) has a TCP port
  monitor — and the expiry date of the mail certificate.
- **Metrics.** Stalwart exposes a Prometheus endpoint, `/metrics/prometheus`,
  off by default (*Settings › Telemetry › Metrics*); set credentials when
  enabling it.
- **Delivery.** The queue and the DMARC and TLS reports other servers send are
  in the web interface. A growing queue or rejected reports show a DNS or
  reputation problem before a block list does.

None of the three has been set up here.

## Cloudflare in front

The web interface can sit behind Cloudflare's proxy like any other stack. The
mail ports cannot on the free plan: Cloudflare proxies HTTP and HTTPS, requires
mail records to be DNS-only, and offers arbitrary TCP ports only through
Spectrum on the Enterprise plan. The host's address is therefore public for
mail in any case. Cloudflare Email Routing is a different thing — Cloudflare
receives the mail and forwards it to another address — and does not put a proxy
in front of this server.

## Known limits

- **Nothing has been delivered to or from another mail system.** The checks
  above ran against the image with local accounts.
- **Not run behind this repository's Traefik.** The stack is `scaffolded`.
- **Which address Stalwart sees on a published port** is established on a host;
  the bans above depend on it.
- **DANE is off.** Stalwart reports that Docker's resolver cannot validate
  DNSSEC and disables DANE for outgoing mail.
- **0.x.** Upstream states that a minor release can need a migration and that
  upgrades are manual. `UPSTREAM.md` has the checklist.
- **The web interface is not pinned by the image tag.** It is downloaded at
  start — see `UPSTREAM.md`, "What reaches the network on its own".

## Backup

| | |
|---|---|
| **Everything** | `./volumes/data` — mail, accounts, settings and the DKIM keys, in one RocksDB store. Stop the container before copying |
| **Where the store is** | `./volumes/etc/config.json` |
| **The administrator password** | `.secrets/admin_pwd.txt` — also changeable in the web interface |

```yaml
# /etc/borgmatic/config.yaml
source_directories:
  - /srv/secure-docker-blueprint/apps/stalwart/volumes/data
  - /srv/secure-docker-blueprint/apps/stalwart/volumes/etc
```

Restore: put both directories back owned by `2000:2000` and start the
container. The DKIM keys come back with the store, so the published DNS records
stay valid.
