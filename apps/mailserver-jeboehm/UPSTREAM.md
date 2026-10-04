# Upstream Reference

## Source

- **Image:** https://github.com/jeboehm?tab=packages&repo_name=docker-mailserver
- **GitHub:** https://github.com/jeboehm/docker-mailserver
- **Docs:** https://jeboehm.github.io/docker-mailserver/
- **License:** MIT
- **Use restrictions:** none — https://github.com/jeboehm/docker-mailserver/blob/main/LICENSE · checked 2026-10-03
- **Edition gating:** none — one implementation, no paid tier — https://github.com/jeboehm/docker-mailserver · checked 2026-10-03
- **Commercial model:** no paid edition — https://github.com/jeboehm/docker-mailserver · checked 2026-10-03
- **Decision facts checked:** 2026-10-03
- **Origin:** Germany · Jeffrey Boehm (individual maintainer) · EU
- **Domain:** Files, wiki and collaboration
- **Role:** Mail server — Postfix, Dovecot and Rspamd as separate containers, with an administration interface and webmail
- **Based on version:** `8.0.8`

## Project maturity

472 stars, pushed 2026-10-03, release v8.0.8 the same day; four releases between
2026-09-26 and 2026-10-03. One maintainer has 437 commits, Renovate's bot
account 425 and the next human contributor four. No advisory is published in
the repository.

## What we use

- `ghcr.io/jeboehm/mailserver-mta`, `-mda`, `-filter`, `-web` and `-unbound`, all
  at `8.0.8`; `mysql:8.4.11`; `redis:8.2.10-alpine`.
- `mail.yml`, an opt-in overlay that publishes 25, 587 and 993.
- `ops/setup.sh`, which creates the domain, the administrator and the DKIM key
  with the web image's console commands instead of its interactive wizard.

## What we changed and why

| Change | Reason |
|--------|--------|
| Version tags instead of `latest`, and `mysql:8.4.11` instead of `mysql:lts` | Upstream's compose names floating tags; its tutorial says not to use `latest` in production |
| Credentials from files in `.secrets/`, through `config/entrypoint.sh` | The images read `DB_PASSWORD`, `REDIS_PASSWORD`, `CONTROLLER_PASSWORD` and `DOVEADM_API_KEY` from the environment only, and upstream's template ships `changeme`. Each service gets only the secrets it uses |
| `config/entrypoint-web.sh` in place of the web image's entrypoint | The image's entrypoint generates `APP_SECRET` at every start and passes nothing else through; the stack supplies a 48-character one from a file. The script repeats the entrypoint's two remaining steps and has to be compared with it on an upgrade |
| Redis password in a tmpfs config file | Upstream passes it as a command-line argument |
| `cap_drop: ALL` on every service, the routine set on `mta` and `db` | Upstream drops nothing. Measured with the checks below |
| `read_only`, `no-new-privileges` on `redis` and `unbound` as well | Upstream sets both on four of its services |
| Two networks: one internal, one with a route out for `mta`, `filter` and `unbound` | Upstream uses one default network for everything |
| No `ssl` service; the certificate is two files in `volumes/certs` | Upstream's `ssl` container writes a self-signed certificate into a shared volume |
| No `fetchmail` service | It collects mail from mailboxes elsewhere and is not needed to run a mail server |
| Mail ports in an overlay: 25, 587 and 993 | Upstream's production file also publishes 110, 143 and 995 |
| `TRUSTED_PROXIES` set to the proxy network's range | The administration interface reads the client address Traefik forwards |
| `APP_TRAEFIK_ACCESS=acc-tailscale` | A blueprint ships closed |

## Verified on the images (2026-10-03)

Not a host verification: no Traefik router, a self-signed certificate, no other
mail system. Both compose files were run on a Linux filesystem.

- `ops/init.sh` and `ops/setup.sh` run through in both variants; all seven
  services report healthy.
- Port 25: STARTTLS offered and no AUTH; a recipient at a foreign domain is
  answered `454 4.7.1 Relay access denied`, an unknown local mailbox `550`.
- Port 587: `530 5.7.0 Must issue a STARTTLS command first` before TLS; `553
  5.7.1 not logged in` without a login; `553 5.7.1 not owned by user` for a
  sender address the account does not own.
- A message submitted on 587 arrived over IMAP on 993; a wrong IMAP password is
  refused.
- **No DKIM signature was produced.** Rspamd logs `public key for domain … is
  not found … skip signing` until the record is published, and the test domain
  has no DNS.
- The web container answers `/login`, `/webmail/` and `/rspamd/` on port 8080;
  `/` redirects to the login.
- `APP_SECRET` in the running web process is the 48-character value from the
  secret file.
- `mda` has no route out; `mta` reaches an external address.
- With `volumes/certs` owned by uid 1000 Postfix logs `not owned by root` for
  the certificate files; with `root:1000` and the key at mode `640` it logs
  nothing and Dovecot still reads the key.
- At idle: `db` 449 MiB, `filter` 153, `web` 67, `mda` 19, `mta` 17, `unbound`
  13, `redis` 5.

What a host run still has to establish: the route through `core/traefik`,
sign-in to the administration interface in a browser, a DKIM signature against a
published record, delivery to and from another mail system, and the client
address Postfix and Dovecot see on a published port.

## What reaches the network on its own

- **Rspamd's maps**, from `maps.rspamd.com`, read from its log.
- **DNS**, through the stack's own Unbound.

## Upgrade checklist

1. Read the upgrade changelog —
   https://github.com/jeboehm/docker-mailserver/blob/main/docs/reference/upgrade-changelog.md
2. Compare `config/entrypoint-web.sh` with the web image's `/entrypoint.sh` of
   the new version
3. Raise `APP_TAG` in `.env` and in `.env.local.example`
4. `docker compose pull && docker compose up -d --wait`
5. Sign in, send a message between two accounts
6. Record the result in `Last verified` once it ran behind `core/traefik`
