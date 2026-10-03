# mailserver (jeboehm)

A mail server built from one container per function: Postfix, Dovecot and
Rspamd, with an administration interface and Roundcube webmail. Upstream:
[jeboehm/docker-mailserver](https://github.com/jeboehm/docker-mailserver). The
directory is named after its maintainer because
[`apps/docker-mailserver`](../docker-mailserver/) is a different product.

## Architecture

```text
Traefik ──http──→ web :8080      administration /, webmail /webmail/, Rspamd /rspamd/
Internet ───────→ mta :25        mail from other servers          (mail.yml)
Mail clients ───→ mta :587       submission, STARTTLS             (mail.yml)
Mail clients ───→ mda :993       IMAP, TLS                        (mail.yml)

mta (Postfix) ── filter (Rspamd) ── unbound (resolver)
      │                │
mda (Dovecot)        redis          db (MySQL): domains, accounts, aliases
```

`db`, `redis` and `mda` sit on a network with no route out. `mta`, `filter` and
`unbound` also join one that has it, for delivery, Rspamd's maps and DNS.

## Requirements

- **Outbound port 25.** Mail leaves the host on port 25. Many providers block it
  until asked; without it nothing is delivered.
- **Inbound 25, 587 and 993** open in the host's firewall, once `mail.yml` is in
  use.
- **A DNS zone you can edit**, and reverse DNS for the host's address pointing
  at `APP_TRAEFIK_HOST`.
- **A certificate for `APP_TRAEFIK_HOST`** before the first start — see
  [Certificate](#certificate).

## Setup

```bash
cp .env.example .env            # host name, mail domain
ops/init.sh                     # directories and secret files
# put tls.crt and tls.key into volumes/certs
sudo chown -R 1000:1000 volumes/mail
sudo chown -R root:1000 volumes/certs && sudo chmod 640 volumes/certs/tls.key
sudo chown root:root volumes/spool && sudo chmod 755 volumes/spool
sudo chown -R 11333:11333 volumes/filter
sudo chown -R 999:999 volumes/redis
ops/setup.sh                    # first start, domain, administrator, DKIM key
```

`ops/setup.sh` creates the mail domain and the account `postmaster@<domain>`
with access to the administration interface, writes its password to
`.secrets/admin_pwd.txt` and the DKIM record to `volumes/dkim-<domain>.txt`.

Then, in this order:

1. **DNS** — see [DNS](#dns).
2. **Mail ports** — `docker compose -f docker-compose.yml -f mail.yml up -d`.
3. **Mailboxes** — in the administration interface.

## Try it locally

```bash
cp .env.local.example .env.local
ops/init.sh --local             # fills .env.local, creates a self-signed certificate
# the chown lines init.sh prints
ops/setup.sh --local
```

`http://localhost:8080` — the user is printed by `setup.sh`, the password is in
`.secrets/admin_pwd.txt`. SMTP answers on `localhost:1025`, submission on
`localhost:1587`, IMAP on `localhost:1993`. Mail between local accounts works;
nothing leaves the machine. The ownership steps need a Linux filesystem under
`volumes/`.

```bash
docker compose -f docker-compose.local.yml --env-file .env.local down
```

## DNS

For `example.com` served by `mail.example.com`:

```text
example.com.                  MX   10 mail.example.com.
example.com.                  TXT  "v=spf1 mx -all"
dkim._domainkey.example.com.  TXT  <the record in volumes/dkim-example.com.txt>
_dmarc.example.com.           TXT  "v=DMARC1; p=quarantine; rua=mailto:postmaster@example.com"
```

Outgoing mail is signed once the DKIM record is published: Rspamd looks the
key up in DNS first and skips the signature while it is missing. The
administration interface checks the published records for each domain.

## Certificate

SMTP and IMAP are encrypted by Postfix and Dovecot. Both read
`volumes/certs/tls.crt` and `volumes/certs/tls.key`, and neither starts without
them. Dovecot runs as uid 1000 and Postfix checks that the files belong to
root, so the directory is `root:1000` with the key at mode `640`. Restart `mta`
and `mda` after replacing the files.

The source is an ACME client on the host, or any other place the certificate
for `APP_TRAEFIK_HOST` is issued. Only a self-signed one has been run here.

## Mail ports (`mail.yml`)

| Port | For | Who connects |
|---|---|---|
| 25 | SMTP | other mail servers — has to be reachable from the internet |
| 587 | Submission, STARTTLS | mail clients sending |
| 993 | IMAP, TLS | mail clients reading |

Upstream offers submission on 587 only; there is no port 465.
`APP_MAIL_BIND` sets the host address the ports are published on. `0.0.0.0` is
every interface. A VPN address there keeps the client ports off the public
interface; port 25 then no longer receives mail from outside.

## Security model

Measured on the images on 2026-10-03:

- **No open relay.** Port 25 offers no login and answers a recipient outside the
  hosted domains with `454 Relay access denied`.
- **Sending needs TLS, a login, and your own address.** Port 587 answers
  `530 Must issue a STARTTLS command first` before TLS, `553 not logged in`
  without a login, and `553 not owned by user` for a sender address the account
  does not own.
- **Five of seven services run with no capability at all.** `mda`, `filter`, the
  web container, `unbound` and `redis` run as their own users, read-only, under
  `cap_drop: ALL`; `mta` and `db` start as root and keep the routine set.
- **The datastores have no route out.** `db`, `redis` and `mda` are on an
  internal network only — measured from `mda`.
- **Every credential comes from a file** in `.secrets/`, generated by
  `ops/init.sh`. Upstream's template ships `changeme`.
- **The web interface ships closed**, `acc-tailscale`. Administration, webmail
  and Rspamd's interface share one port, so one access policy covers all three;
  open it only as far as the webmail's users need.

There is no automatic ban: nothing here blocks an address after failed logins.
Postfix limits one client to 20 connections a minute. A ban needs a tool on the
host that reads the containers' logs.

## Monitoring (optional)

- **The ports.** A TCP check on 25, 587 and 993 from outside the host —
  [`monitoring/uptime-kuma`](../../monitoring/uptime-kuma/) has a TCP port
  monitor — and the expiry date of the certificate in `volumes/certs`.
- **Rspamd's interface**, at `/rspamd/`, shows what was scored and rejected. Its
  password is `.secrets/controller_pwd.txt`.
- **The queue.** `docker compose exec mta postqueue -p`. A growing queue shows a
  DNS or reputation problem before a block list does.

None of the three has been set up here.

## Cloudflare in front

The web interface can sit behind Cloudflare's proxy like any other stack. The
mail ports cannot on the free plan: Cloudflare proxies HTTP and HTTPS, requires
mail records to be DNS-only, and offers arbitrary TCP ports only through
Spectrum on the Enterprise plan. The host's address is public for mail.

## Known limits

- **Nothing has been delivered to or from another mail system**, and no DKIM
  signature has been produced: the test domain has no DNS.
- **Not run behind this repository's Traefik.** The stack is `scaffolded`.
- **No automatic ban** — see above.
- **Upstream's fetchmail service is not included.** It collects mail from
  mailboxes elsewhere.
- **One maintainer.** Upstream's releases come several times a week.

## Backup

| | |
|---|---|
| **Mailboxes** | `./volumes/mail` |
| **Database** | MySQL in `mailserver-jeboehm-db`, database `mailserver`, user `mailserver` — domains, accounts, aliases, DKIM keys. Password in `.secrets/db_pwd.txt` |
| **Rspamd** | `./volumes/filter` — statistics; reproducible over time |
| **Queue** | `./volumes/spool` — stop `mta` before copying |
| **Credentials** | `.secrets/` — the services cannot reach the database without them |
| **Reproducible** | `./volumes/redis` holds sessions and Rspamd's short-lived state |

```yaml
# /etc/borgmatic/config.yaml
source_directories:
  - /srv/secure-docker-blueprint/apps/mailserver-jeboehm/volumes/mail
  - /srv/secure-docker-blueprint/apps/mailserver-jeboehm/.secrets
mysql_databases:
  - name: mailserver
    container: mailserver-jeboehm-db
    username: mailserver
    password: "{credential file /srv/secure-docker-blueprint/apps/mailserver-jeboehm/.secrets/db_pwd.txt}"
```

Restore: the database first, then `volumes/mail` owned by `1000:1000`, then
start the stack.
