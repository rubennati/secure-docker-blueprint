# Upstream Reference

## Source

- **Image:** https://github.com/docker-mailserver/docker-mailserver/pkgs/container/docker-mailserver
- **GitHub:** https://github.com/docker-mailserver/docker-mailserver
- **Docs:** https://docker-mailserver.github.io/docker-mailserver/latest/
- **License:** MIT
- **Use restrictions:** none — https://github.com/docker-mailserver/docker-mailserver/blob/master/LICENSE · checked 2026-10-03
- **Edition gating:** none — one implementation, no paid tier — https://github.com/docker-mailserver/docker-mailserver · checked 2026-10-03
- **Commercial model:** no paid edition — https://github.com/docker-mailserver/docker-mailserver · checked 2026-10-03
- **Decision facts checked:** 2026-10-03
- **Origin:** Community · docker-mailserver organisation · no single jurisdiction
- **Domain:** Files, wiki and collaboration
- **Role:** Mail server — Postfix, Dovecot and Rspamd in one container, configured by files, without a database or a web interface
- **Based on version:** `16.0.1`

`tvial/docker-mailserver` on Docker Hub is this project's former image name; its
newest tag is from 2021-01-16.

## Project maturity

18 887 stars, pushed 2026-09-30, release 16.0.1 on 2026-09-04; six releases
between 2025-03-01 and 2026-09-04. No advisory is published in the repository.

## What we use

- `ghcr.io/docker-mailserver/docker-mailserver:16.0.1`, one container.
- `mail.yml`, an opt-in overlay that publishes 25, 465 and 993.
- `ops/setup.sh`, which creates the postmaster mailbox and the DKIM key.

## What we changed and why

| Change | Reason |
|--------|--------|
| `ENABLE_FAIL2BAN=1` with `cap_add: NET_ADMIN` | Upstream ships it off. Traefik's middlewares do not reach the mail ports, so this is their brute-force protection. Measured: with the capability a client is banned after repeated failed IMAP logins and its connections are dropped; without it the ban fails with `Operation not permitted` and Fail2ban stays `RUNNING` |
| `ENABLE_RSPAMD=1`, and OpenDKIM, OpenDMARC, policyd-spf, Amavis and SpamAssassin off | Upstream's default starts the four older services and no spam filter. Its documentation names Rspamd as the intended default and advises running it with the older services disabled |
| `SPOOF_PROTECTION=1` | Upstream's default lets a logged-in account send with any sender address |
| `ENABLE_UPDATE_CHECK=0` | Upstream's default asks `github.com/docker-mailserver/docker-mailserver/releases/latest` at start and once a day |
| `ENABLE_MTA_STS=1` | Outgoing mail honours the recipient domain's MTA-STS policy; off in upstream's default |
| `SSL_TYPE=manual` with files in `volumes/certs` | Upstream's default is no TLS. Traefik's `acme.json` is not mounted, because it carries every certificate the proxy has obtained |
| `cap_drop: ALL` with `CHOWN`, `DAC_OVERRIDE`, `FOWNER`, `SETGID`, `SETUID`, `NET_BIND_SERVICE` and `NET_ADMIN` | Upstream's compose file drops nothing. Measured: start, the mail checks below, a service restart and a container stop all work with this set; `KILL` and `SYS_CHROOT` were tried and are not needed |
| `no-new-privileges` | Measured with the checks below |
| No `user:`, no `read_only` | supervisord starts as root, and the start script writes the services' configuration under `/etc` |
| Three ports, in an overlay | Upstream's compose file publishes five; 143 and 587 are the unencrypted-start variants of 993 and 465 |
| `ENABLE_CLAMAV=0`, a variable | It holds about 850 MB of signatures in memory |

## Verified on the image (2026-10-03)

Not a host verification: no other mail system, a self-signed certificate.

- `ops/init.sh --local` and `ops/setup.sh --local` run through on a Linux
  filesystem: the container is healthy, the postmaster mailbox exists, the DKIM
  key and its DNS record are written.
- Running: Postfix, Dovecot, Rspamd with its Redis, Fail2ban, the MTA-STS
  daemon, cron, rsyslog and the change detector.
- Port 25: STARTTLS offered and no AUTH; a recipient at a foreign domain is
  answered `554 5.7.1 Relay access denied`; a sender domain that does not accept
  mail is answered `550 5.7.27`.
- Port 465: a recipient without authentication is answered `554 5.7.1 Access
  denied`; a sender address the account does not own `553 5.7.1 not owned by
  user`.
- A message submitted on 465 arrived over IMAP on 993 with a DKIM signature,
  selector `mail`.
- Fail2ban: after repeated failed IMAP logins the log reads `[dovecot] Ban`, the
  nftables set holds the address, and a new connection from it times out. The
  shipped jail defaults are `bantime = 1w`, `findtime = 1w`, `maxretry = 6`.
- `setup email add` reads the password from standard input, so `ops/setup.sh`
  passes none on a command line.
- 308 MiB at idle with Rspamd and two mailboxes, 57 pids.
- **A bind mount without Unix ownership does not work.** On macOS with Colima
  Postfix stops with `chmod socket private/smtpd: Invalid argument` and Rspamd
  exits; on a Linux filesystem and with Docker volumes it starts clean.

What a host run still has to establish: delivery to and from another mail
system, a certificate from a public authority, and the client address the
container sees on a published port — locally every client arrived as the Docker
gateway, and one ban blocked them all.

## What reaches the network on its own

- **Rspamd's maps**, from `maps.rspamd.com`, read from its log.
- **DNS**, for MX, SPF, DKIM and DMARC lookups, and the MTA-STS policy of a
  recipient domain over HTTPS.
- **Virus signatures**, when ClamAV is on.

The update check is off.

## Upgrade checklist

1. Read the release notes — https://github.com/docker-mailserver/docker-mailserver/releases —
   a major release changes defaults
2. Raise `APP_TAG` in `.env` and in `.env.local.example`
3. `docker compose pull && docker compose up -d`
4. `docker compose exec app supervisorctl status` — the services above `RUNNING`
5. Send a message between two accounts and read `setup fail2ban`
6. Record the result in `Last verified` once it ran on a host
