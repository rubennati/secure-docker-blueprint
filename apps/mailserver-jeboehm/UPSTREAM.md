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
- **Last verified:** not yet — needs a host with port 25 open and public DNS

## Project maturity

472 stars, pushed 2026-10-03, release v8.0.8 the same day; four releases between
2026-09-26 and 2026-10-03. One maintainer has 437 commits, Renovate's bot
account 425 and the next human contributor four. No advisory is published in
the repository.

## What we use

- `ghcr.io/jeboehm/mailserver-mta`, `-mda`, `-filter`, `-web` and `-unbound`, all
  at `8.0.8`; `mysql:9.7.4`; `redis:8.10.3-alpine`.
- `mail.yml`, an opt-in overlay that publishes 25, 587 and 993.
- `ops/setup.sh`, which creates the domain, the administrator and the DKIM key
  with the web image's console commands instead of its interactive wizard.

## What we changed and why

| Change | Reason |
|--------|--------|
| Version tags instead of `latest`, and `mysql:9.7.4` instead of `mysql:lts` | Upstream's compose names floating tags; its tutorial says not to use `latest` in production |
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
| `APP_TRAEFIK_ACCESS=access-vpn` | A blueprint ships closed |
| `MCP_ENABLED=false` on `web` | Upstream turns the MCP endpoint (`/mcp`) on by default from 8.1.0: an agent holding a user's API token can manage domains, accounts and DKIM and read and send that user's mail. That is a new way into every mailbox, and upstream's own guide warns that mail can carry instructions aimed at the agent reading it. Off until an operator decides to offer it; then also set `MCP_ALLOWED_HOSTS` to the host name |

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

## Version notes

- Moved to `8.0.18` on 2026-10-31 (released the same day), all five images
  together, not run at this tag. 8.0.9 to 8.0.18 are dependency and bug-fix
  releases with no breaking change, variable change or migration; 8.0.15
  (2026-10-21) fixes CVE-2026-109618 and CVE-2026-109619 in the web image.
- Moved `mysql` from `8.4.11` to `9.7.4` (the newest LTS line) on 2026-11-05,
  not run on a host at this tag. Upstream's own compose defaults to
  `DB_IMAGE=mysql:lts` and its CI image list uses the same tag, which is 9.7
  today (https://github.com/jeboehm/docker-mailserver,
  `deploy/compose/db.yaml`). `DB_SERVER_VERSION` stays `"8.4"`, upstream's
  default: Doctrine uses it to pick its SQL dialect, and the 8.4 dialect is
  valid on 9.7. MySQL upgrades in place from one LTS line to the next: the 9.7
  server upgrades the data dictionary and system tables in `./volumes/db` at its
  first start. 9.x no longer has `mysql_native_password`; the accounts the 8.4
  image created use `caching_sha2_password`, which `SELECT user, plugin FROM
  mysql.user;` confirms before the move. Take the `mysqldump` before the tag
  changes: going back to 8.4 is only a restore of that dump.
- Moved to `8.1.0` on 2026-11-05 (released 2026-11-04), all five images
  together, not run on a host at this tag. No breaking change, removed variable
  or database migration in the release
  (https://github.com/jeboehm/docker-mailserver/releases/tag/v8.1.0) or in the
  upgrade changelog (`docs/reference/upgrade-changelog.md`, "v8.0.x to later").
  New: the `web` image ships an MCP server, on by default with mail reading
  and sending, answering only for API tokens a user creates and only for the
  host names in `MCP_ALLOWED_HOSTS`
  (`docs/how-to/configure-mcp-server.md`); this stack sets
  `MCP_ENABLED: "false"` in both compose files, which also hides the API-token
  pages — see the table above. The bundled mailserver-admin moves to 5.20.0,
  which keeps admin logins in Redis whatever `PHP_SESSION_*` says (not set
  here, so existing logins stay valid). The MDA accepts
  short-lived mailbox credentials issued by mailserver-admin. No advisory in
  the release. The other upgrade-changelog entry concerns Kubernetes only.
- Moved `redis` from `8.2.10-alpine` to `8.10.3-alpine` on 2026-11-05, not run on a
  host at this tag; across 8.4, 8.6, 8.8 and 8.10, minor releases of the same major
  with no breaking change listed (they add commands, compact hashes and performance
  work). Redis does not load data files written by a newer version, so a rollback
  needs the backup of the Redis data. Security fixes in the 8.10 line:
  CVE-2026-62356 (8.10.1, heap write when loading a Count-min sketch from an RDB
  file), queued `MULTI` commands keeping access to keys whose ACL permission was
  revoked (8.10.2), and a cluster-bus overflow that needs cluster mode (8.10.3).
  Rspamd, the Redis client here, names no Redis version. This service starts as UID
  999 through its own `config/redis-entrypoint.sh`, which execs `redis-server`
  directly, so the image entrypoint's privilege handling and module loading do not
  apply; no compose change. Sources:
  https://github.com/redis/redis/releases/tag/8.10.0,
  https://github.com/redis/redis/releases/tag/8.10.3, https://docs.rspamd.com/

## Upgrade checklist

1. Read the upgrade changelog —
   https://github.com/jeboehm/docker-mailserver/blob/main/docs/reference/upgrade-changelog.md
2. Compare `config/entrypoint-web.sh` with the web image's `/entrypoint.sh` of
   the new version
3. Raise `APP_TAG` in `.env` and in `.env.local.example`
4. `docker compose pull && docker compose up -d --wait`
5. Sign in, send a message between two accounts
6. Record the result in `Last verified` once it ran behind `core/traefik`
