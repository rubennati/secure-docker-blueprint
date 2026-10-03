# docker-mailserver

Postfix, Dovecot and Rspamd in one container, configured by files and
environment variables: no database, no web interface. Upstream:
[docker-mailserver/docker-mailserver](https://github.com/docker-mailserver/docker-mailserver).

## Architecture

```text
Internet ───────→ app :25        mail from other servers          (mail.yml)
Mail clients ───→ app :465 :993  submission and IMAP, both TLS    (mail.yml)
                    │
                    ├── volumes/mail-data    the mailboxes
                    ├── volumes/mail-state   queue, Rspamd and Fail2ban state
                    ├── volumes/config       accounts, aliases, DKIM keys
                    ├── volumes/mail-logs    mail.log, fail2ban.log
                    └── volumes/certs        fullchain.pem, privkey.pem
```

Nothing here is HTTP, so nothing goes through Traefik. The mail ports are
published by the container itself, through the opt-in file `mail.yml`. Without
it no port is reachable from outside.

## Requirements

- **Outbound port 25.** Mail leaves the host on port 25. Many providers block it
  until asked; without it nothing is delivered.
- **Inbound 25, 465 and 993** open in the host's firewall, once `mail.yml` is in
  use.
- **A DNS zone you can edit**, and reverse DNS for the host's address pointing
  at `APP_MAIL_HOST`.
- **A certificate for `APP_MAIL_HOST`** before the first start — see
  [Certificate](#certificate).

## Setup

```bash
cp .env.example .env            # host name, mail domain
ops/init.sh                     # the data directories
# put fullchain.pem and privkey.pem into volumes/certs
ops/setup.sh                    # first start, postmaster mailbox, DKIM key
```

`ops/setup.sh` writes the postmaster's password to `.secrets/postmaster_pwd.txt`
and prints where the DKIM record is.

Then, in this order:

1. **DNS** — see [DNS](#dns).
2. **Mail ports** — `docker compose -f docker-compose.yml -f mail.yml up -d`.
3. **The client address** — see [Before relying on the bans](#before-relying-on-the-bans).
4. **Mailboxes** — `docker compose exec app setup email add name@example.com`
   asks for the password.

## Try it locally

```bash
cp .env.local.example .env.local
ops/init.sh --local             # also creates a self-signed certificate
ops/setup.sh --local
```

SMTP answers on `localhost:1025`, submission on `localhost:1465`, IMAP on
`localhost:1993`. Mail between local accounts works; nothing leaves the machine.

This needs a Linux filesystem under `volumes/`. On Docker Desktop or Colima on
macOS the bind mount carries no Unix ownership and Postfix stops with
`chmod socket private/smtpd: Invalid argument`.

```bash
docker compose -f docker-compose.local.yml --env-file .env.local down
```

## DNS

docker-mailserver does not write a zone file. For `example.com` served by
`mail.example.com`:

```text
example.com.                  MX   10 mail.example.com.
example.com.                  TXT  "v=spf1 mx -all"
mail._domainkey.example.com.  TXT  <the content of volumes/config/rspamd/dkim/rsa-2048-mail-example.com.public.dns.txt>
_dmarc.example.com.           TXT  "v=DMARC1; p=quarantine; rua=mailto:postmaster@example.com"
```

Publish them before sending the first mail: a message without SPF and DKIM is
what receiving servers score as spam, and repeated spam scores are what puts an
address on a block list.

## Certificate

SMTP and IMAP are encrypted by the mail server. The stack reads
`volumes/certs/fullchain.pem` and `volumes/certs/privkey.pem`
(`SSL_TYPE=manual`); `ops/setup.sh` stops until both files exist. Restart the
container after replacing them.

| Source | How |
|---|---|
| An ACME client on the host | Copy or link its certificate for `APP_MAIL_HOST` into `volumes/certs` |
| Traefik's `acme.json` | Upstream reads it directly: `SSL_TYPE=letsencrypt` and the file mounted at `/etc/letsencrypt/acme.json`. The file holds every certificate Traefik has obtained, each with its private key, and all of them are then readable in this container |

Only the first has been run here, with a self-signed certificate.

## Mail ports (`mail.yml`)

| Port | For | Who connects |
|---|---|---|
| 25 | SMTP | other mail servers — has to be reachable from the internet |
| 465 | Submission, TLS | mail clients sending |
| 993 | IMAP, TLS | mail clients reading |

`APP_MAIL_BIND` sets the host address they are published on. `0.0.0.0` is every
interface. A VPN address there keeps the client ports off the public interface;
port 25 then no longer receives mail from outside.

## Security model

Measured on the image on 2026-10-03:

- **No open relay.** Port 25 offers no login and answers a recipient outside the
  hosted domains with `554 Relay access denied`.
- **Sending needs a login, and only as yourself.** Port 465 answers an
  unauthenticated recipient with `554 Access denied`, and a sender address the
  account does not own with `553 not owned by user` (`SPOOF_PROTECTION`, off in
  upstream's default).
- **Fail2ban is on**, off in upstream's default. After repeated failed logins
  the address is banned for a week and its connections are dropped — measured
  on port 993. It needs `NET_ADMIN`; without the capability Fail2ban keeps
  running and bans nothing.
- **Rspamd filters and signs.** Spam scoring, SPF, DKIM and DMARC checks on
  incoming mail and a DKIM signature on outgoing mail, in place of the four
  older services upstream still starts by default.
- **`cap_drop: ALL`** with the six routine capabilities and `NET_ADMIN`, and
  `no-new-privileges`. The container starts as root and is not read-only:
  supervisord and the start script need both.
- **The update check is off.** Upstream's default asks GitHub for the newest
  release once a day.

### Before relying on the bans

Fail2ban bans the address the container sees. Check that it is the client's and
not Docker's:

```bash
docker compose exec app grep 'connect from' /var/log/mail/mail.log | tail
```

If every line shows the same private address, every client arrives from it, and
the first ban blocks all of them. That is a property of how the host publishes
ports and has to be solved there.

```bash
docker compose exec app setup fail2ban              # what is banned
docker compose exec app setup fail2ban unban <ip>
```

## Monitoring (optional)

- **The ports.** A TCP check on 25, 465 and 993 from outside the host —
  [`monitoring/uptime-kuma`](../../monitoring/uptime-kuma/) has a TCP port
  monitor — and the expiry date of the certificate in `volumes/certs`.
- **The logs.** `volumes/mail-logs/mail.log` shows rejected and deferred mail,
  `fail2ban.log` every ban.
- **The queue.** `docker compose exec app postqueue -p`. A growing queue shows
  a DNS or reputation problem before a block list does.

None of the three has been set up here.

## Cloudflare in front

Not for these ports on the free plan: Cloudflare proxies HTTP and HTTPS,
requires mail records to be DNS-only, and offers arbitrary TCP ports only
through Spectrum on the Enterprise plan. The host's address is public for mail.

## Known limits

- **Nothing has been delivered to or from another mail system.** The checks
  above ran against the image with local accounts.
- **The virus scanner is off.** `APP_CLAMAV=1` switches it on; it holds about
  850 MB of signatures in memory, and upstream's figure without swap is 3 GB.
- **No web interface.** Accounts, aliases and quotas are managed with
  `docker compose exec app setup help`.
- **Rspamd's own interface is not published** and has no password by default.
- **The stack is `scaffolded`.**

## Backup

| | |
|---|---|
| **Mailboxes** | `./volumes/mail-data` |
| **Accounts and DKIM keys** | `./volumes/config` — without the DKIM key the published DNS record no longer matches |
| **State** | `./volumes/mail-state` — the queue, Rspamd's statistics, Fail2ban's bans |
| **Certificate** | `./volumes/certs`, unless it is renewed from elsewhere |
| **Reproducible** | `./volumes/mail-logs` |

```yaml
# /etc/borgmatic/config.yaml
source_directories:
  - /srv/secure-docker-blueprint/apps/docker-mailserver/volumes/mail-data
  - /srv/secure-docker-blueprint/apps/docker-mailserver/volumes/config
  - /srv/secure-docker-blueprint/apps/docker-mailserver/volumes/mail-state
```

Restore: put the directories back and start the container. Stop it before
copying `mail-state`, or the queue is copied mid-write.
