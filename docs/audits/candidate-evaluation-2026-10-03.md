# Candidate evaluation — 2026-10-03

Seven mail servers proposed on 2026-10-03, checked against what the repository
requires of a stack before one is written: Stalwart, docker-mailserver,
jeboehm/docker-mailserver, Mailu, mailcow: dockerized, poste.io and Axigen.

The repository ships no mail server. `apps/greenmail` and `apps/mailpit` receive
mail for tests, and `business/listmonk` sends newsletters through an SMTP relay.
Twenty stacks carry SMTP settings in their `.env.example`, for a relay the operator
provides (`grep -li smtp` over the stacks' `.env.example` files, without
`apps/_reference`).

Every line below was read from the project's own repository, its documentation, or
its registry's metadata, read without pulling the image. Nothing was started. What
is said about an image under the baseline — its user, the capabilities it needs —
comes from the image configuration and the source, and the stack's first run has to
confirm it. Method and verdicts follow
[the 2026-09-22 evaluation](candidate-evaluation-2026-09-22.md).

What followed from it is in [Decided on 2026-10-03](#decided-on-2026-10-03): three
are added, one is held until a release carries a published fix, and three are not
added. The reasoning is in [`.ai/decisions.md`](../../.ai/decisions.md).

## What decides the verdict

| Requirement | Where it comes from |
|---|---|
| A published image with a version tag | `docs/standards/env-structure.md` — a bare major or `latest` fails `check-structure.py` |
| An independently operated service | The product criterion: a CLI or per-job container gets no entry |
| A deployment the project itself supports | Upstream's own compose or install documentation |
| Runs inside the security baseline | `check-baseline.py` fails `privileged: true`; host networking and the host PID namespace need a documented exception |
| Licence and origin stated | `scripts/ci/sovereignty-report.py --check` |

Three verdicts follow from it:

- **Stack** — every requirement is met.
- **Stack, after a decision** — it can be written, but one point needs deciding
  first: a baseline exception, a port outside Traefik's HTTP routing, or a licence
  or edition limit.
- **Held** — no pinnable image, a published advisory with no fixed release, or no
  release for years.

Every product here serves SMTP and IMAP, which Traefik's HTTP routing does not
carry. How those ports are exposed is decided before the first stack, so none has
the verdict *Stack*; the options are in [Across the list](#across-the-list).

Maturity is recorded, not scored: stars, the last push and the newest release are
facts a reader can weigh. Nothing here ranks one product against another.

## Result

Stars and last push as of 2026-10-03.

| Product | Stars | Last push | Licence | Image, pinnable tag | Verdict |
|---|---|---|---|---|---|
| [Stalwart](https://github.com/stalwartlabs/stalwart) | 14 927 | 2026-10-03 | AGPL-3.0; enterprise files under SELv2 | `stalwartlabs/stalwart:v0.16.24` | Stack, after a decision |
| [docker-mailserver](https://github.com/docker-mailserver/docker-mailserver) | 18 887 | 2026-09-30 | MIT | `ghcr.io/docker-mailserver/docker-mailserver:16.0.1` | Stack, after a decision |
| [jeboehm/docker-mailserver](https://github.com/jeboehm/docker-mailserver) | 472 | 2026-10-03 | MIT | `ghcr.io/jeboehm/mailserver-{mta,mda,web,filter,ssl,unbound}:8.0.8` | Stack, after a decision |
| [Mailu](https://github.com/Mailu/Mailu) | 7 533 | 2026-10-03 | MIT | `ghcr.io/mailu/{nginx,admin,dovecot,postfix,rspamd,unbound,webmail}:2024.06.61` | Held |
| [mailcow: dockerized](https://github.com/mailcow/mailcow-dockerized) | 13 557 | 2026-10-01 | GPL-3.0 | one image per service, each version-tagged — `ghcr.io/mailcow/netfilter:1.64` | Stack, after a decision |
| [poste.io](https://poste.io/) | source not published | — | Proprietary | `analogic/poste.io:2.5.17`, from 2026-09-18 | Stack, after a decision |
| [Axigen](https://www.axigen.com/docker-mail-server/) | source not published | — | Proprietary | `axigen/axigen:10.7.1`, from 2026-09-15 | Stack, after a decision |

`tvial/docker-mailserver` on Docker Hub is docker-mailserver's former image name;
its newest tag is from 2021-01-16. Mailu's documentation under `/2.0/` describes
the previous release line; `2024.06` is the current one.

## Stack shape, from each project's own compose

| Product | Services upstream ships | Datastores | Secrets from files | Runs as |
|---|---|---|---|---|
| Stalwart | 1 | RocksDB in the data volume, or PostgreSQL, MySQL, SQLite, S3 and Redis — the published build includes each | secret-typed fields take a value, an environment variable or a file; the bootstrap administrator comes from the environment only | uid 2000 |
| docker-mailserver | 1 | none — accounts and aliases in configuration files, mail as Maildir | every variable, through `<VAR>__FILE` | root; supervisord starts the daemons |
| jeboehm/docker-mailserver | 9: `ssl`, `mta`, `mda`, `web`, `filter`, `fetchmail`, `unbound`, `db`, `redis` | MySQL or PostgreSQL; Redis | the relay credentials only, `RELAY_PASSWD_FILE` | `mda`, `web`, `filter` and `unbound` under their own users; `mta` and `ssl` set none |
| Mailu | 6 always, up to 13 with resolver, webmail, antivirus, WebDAV, fetchmail, oletools and Tika | SQLite by default, PostgreSQL or MySQL; Redis | none documented | root, every image |
| mailcow: dockerized | 18 | MariaDB, Redis, Memcached | not established | not established |

poste.io and Axigen each ship one container. Their source is not published, so
nothing further was read from them.

## What needs attention, per product

These are facts to carry into each stack's `UPSTREAM.md`, `README.md` and, where a
call leaves the machine, [`docs/sovereignty/data-egress.md`](../sovereignty/data-egress.md).

**Stalwart.** One binary serves SMTP, IMAP, POP3, ManageSieve, JMAP, CalDAV,
CardDAV and WebDAV, with spam filtering and a web interface for administration and
for each account's own settings. The version is 0.16.24. Upstream's upgrade page
states that upgrades are manual, that a minor release can need a migration and that
patch releases are compatible; six patch releases were published between 2026-08-24
and 2026-09-27.

The repository is dual-licensed, AGPL-3.0 and the Stalwart Enterprise License v2,
with a notice per file. The published image is built with the `enterprise` cargo
feature, so the SELv2 code is in the image. Its features — multi-tenancy, branding,
account archiving and un-deletion, live telemetry and metric alerts, AI models in
the spam filter and in Sieve, masked addresses, SCIM provisioning, read replicas and
sharded stores — are unlocked by a licence key, which the server validates offline.
Upstream's comparison page states that both editions share one code base and
implement the same protocols and core features. Upstream publishes no image built
without the feature; one built here without it, under
[`custom-application.md`](../standards/custom-application.md), would be AGPL-3.0 in
full. `business/twenty` is the shipped precedent for an image that carries
separately licensed files, and the sovereignty report classes it `mixed`.

The image runs as uid 2000 and carries a healthcheck. Its binary has the file
capability `cap_net_bind_service`. `business/plane` measured that arrangement on
its Caddy: under `cap_drop: ALL` the exec itself is refused, so the stack adds
`NET_BIND_SERVICE`, which `CAP_BASELINE` allows.

Started without a `config.json`, the server is in bootstrap mode: no mail service
runs, and port 8080 serves the web interface and the management API over plain
HTTP. The temporary administrator's password is printed to the log once;
`STALWART_RECOVERY_ADMIN=admin:<password>` pins it instead, and the documentation
names no file form for that variable. The setup wizard writes `config.json`,
creates the permanent administrator and shows that password once. A path without
the wizard exists: a `config.json` that names the data store, then
`stalwart-cli apply` with a plan against the recovery listener. After setup the
interface answers at `https://<hostname>/admin`, and behind a proxy
`STALWART_PUBLIC_URL` sets the base URL published in the OAuth, OIDC and JMAP
discovery documents.

At its first start the server downloads its web interface as a bundle from
`github.com/stalwartlabs/webui/releases/latest/`; until that succeeds, `/admin` and
`/account` answer 404. The bundle is cached for 30 days and fetched again at the
next start after that, so the image tag does not pin the web interface. The
address is a setting, `resourceUrl`, and can name an internal server. The wizard's
certificate option is on by default and requests one from Let's Encrypt.

The image exposes 25, 465, 587, 143, 993, 110, 995 and 4190 for mail, and 443 and
8080 for HTTP. Five advisories are published, each with a fixed release; the newest
fix is 0.15.5. The README names Stalwart Labs LLC; the company page states
incorporation in the United States and the United Kingdom, with a London address,
and part of the development was funded through NLnet's NGI0 funds. Upstream gives
about 100 MB of memory at idle and 1 GB for five to ten users.

**docker-mailserver.** Postfix, Dovecot, Amavis, OpenDKIM, OpenDMARC and policyd-spf
run in one container under supervisord; Rspamd, ClamAV, SpamAssassin, Fail2ban,
Fetchmail and DNS block lists are off until enabled. Configuration is files and
environment variables: there is no database and no web interface, and accounts are
managed with the `setup` command inside the container. The image is published on
GHCR and on Docker Hub as `mailserver/docker-mailserver`. Six releases appeared
between 2025-03-01 and 2026-09-04, from 15.0.0 to 16.0.1.

The image sets no user and starts supervisord as root, so the baseline's rule
against `user:` on supervisord images applies. Which capabilities it needs under
`cap_drop: ALL` is established with the baseline's `docker run --cap-drop ALL`
procedure, and one outside `CAP_BASELINE` takes a `CAP_ADD_EXCEPTIONS` entry.
Fail2ban needs `NET_ADMIN`, which is outside it.

On its first start the container needs at least one account within two minutes;
without one it shuts down and restarts. Any variable can be read from a file through
`<VAR>__FILE`. `ENABLE_UPDATE_CHECK` is on by default: at start and once a day the
container asks GitHub for the newest release and mails the postmaster address when
there is one. The stack sets it to `0`.

With `SSL_TYPE=letsencrypt` the container reads Traefik's `acme.json` when it is
mounted at `/etc/letsencrypt/acme.json`, selects the certificate for its hostname
or for the domain one level up, wildcards included, and reloads Postfix and Dovecot
when the file changes. Traefik requests a certificate only for a hostname a router
names, and docker-mailserver has no HTTP service to carry one; the wildcard strategy
in `core/traefik` covers a mail hostname under `ACME_WILDCARD_DOMAIN` without it.
`acme.json` holds the ACME account key and every certificate Traefik has obtained,
each with its private key, and all of them are readable in a container that mounts
the file.

Upstream recommends 2 GB of memory with swap and gives 512 MB as the minimum without
ClamAV. ClamAV holds about 850 MB of signatures in memory, and upstream's figure for
a host without swap is 3 GB; this repository's default is no swap. No advisory is
published in the repository. The organisation states its location as worldwide.

**jeboehm/docker-mailserver.** Nine services: Postfix (`mta`), Dovecot (`mda`),
Rspamd (`filter`), a `web` container with an administration interface and
Roundcube, Unbound, a fetchmail manager, a certificate generator (`ssl`), MySQL and
Redis. PostgreSQL is supported in place of MySQL, and Kubernetes manifests ship
beside the compose files.

Upstream's compose names `latest` for its own images and `mysql:lts` for the
database; `8.0.8` exists for the six images in the table, and Redis and the
fetchmail manager are pinned. Upstream sets `read_only` and `no-new-privileges` on
`mda`, `web`, `filter` and `unbound`; those four images run under their own users,
and Dovecot listens on ports above 1024.

The first account and the administrator are created by a command-line wizard,
`web setup.sh`. The database, Redis, Rspamd controller and Dovecot API credentials
are plain variables, with `changeme` in `.env.dist`, so a wrapper provides them
from files. The administration interface, the webmail and Rspamd's interface share
one plain-HTTP port under `/`, `/webmail/` and `/rspamd/` — one backend with two
audiences, so the paths take separate routers. The mail ports are 25, 587, 143,
993, 110 and 995; the ports reference lists no 465. The `ssl` container writes a
self-signed certificate into a shared volume, and a real one is mounted as files
into `mta` and `mda`. `MTA_UPSTREAM_PROXY` and `MDA_UPSTREAM_PROXY` switch the mail
ports to PROXY protocol, and the documentation carries a Traefik example for
compose.

Four releases appeared between 2026-09-26 and 2026-10-03. One maintainer has 437
commits, Renovate's bot account 425 and the next human contributor four. No
advisory is published in the repository. The maintainer's profile gives Düsseldorf,
Germany.

**Mailu.** One image per function — `front` (nginx), `admin`, `imap` (Dovecot),
`smtp` (Postfix), `antispam` (Rspamd) and Redis always, and a resolver, webmail,
antivirus, WebDAV, fetchmail, oletools and Tika by choice. A setup utility renders
the compose file and `mailu.env` from a template, and that template leaves
`redis:alpine`, `apache/tika:latest-full` and `clamav/clamav-debian:stable` without
a version. The seven images in the table set no user and carry a healthcheck. The
first administrator comes from the `INITIAL_ADMIN_*` variables, and the
configuration reference names no file form for `SECRET_KEY` or the administrator
password. `DISABLE_STATISTICS` switches off a statistics report. Upstream's stated
minimum is 1 GB of memory and 1 GB of swap, and 3 GB of memory with ClamAV.

Mailu's reverse-proxy page recommends Traefik and keeps certificate requests in
Mailu: Traefik forwards `/.well-known/acme-challenge/` on port 80 to Mailu and
passes TLS through on 443 for Mailu's hostnames, so the HTTP-01 challenge is not
available to Traefik for any other service.

Ten advisories are published. Five are dated 2026-09-23; three of those are fixed
in 2024.06.59. The other two name `master` as the patched version:
CVE-2026-86008, rated high — an account with the domain-manager role can take over
administrator accounts and other domain managers — and CVE-2026-86009, rated low —
a domain manager can allow itself to send as a hosted domain it does not manage.
Neither fix commit is contained in the tag `2024.06.61`, the newest release, and
none of the pull requests merged into the `2024.06` branch since June carries
them. On the pull request for the first fix, the maintainers discussed a backport
and preferred releasing the next version. Both advisories need an account with the
domain-manager role, which exists only where an administrator assigns it.

**mailcow: dockerized.** Eighteen services with SOGo groupware, an administration
interface and its own nginx, ACME client and resolver; the release is `2026-09`.
The project is managed by The Infrastructure Company GmbH, Willich, Germany.
`netfilter-mailcow` runs `privileged: true` with host networking and `/lib/modules`
mounted, and `dockerapi-mailcow` and `ofelia-mailcow` mount the Docker socket
read-only. `generate_config.sh` offers switches that leave out ClamAV, full-text
search, SOGo, Olefy and Let's Encrypt; none leaves out `netfilter-mailcow`.
Updates run through `update.sh` in upstream's git checkout, which merges upstream's
changes to the compose file. The stated minimum is 6 GiB of memory and 1 GiB of
swap. The documentation lists its Traefik v3 guide as community supported. All 22
published advisories name a fixed release.

**poste.io.** A free edition, `analogic/poste.io`, and two paid ones pulled from
the vendor's registry after a login; the source is not published. The vendor is
Analogic s.r.o., Czech Republic. Upstream's start command uses host networking and
marks it as recommended; published ports are documented beside it.

**Axigen.** Proprietary. After installation the product offers a free licence for
ten users or a 60-day trial, and the vendor describes the free version as for
personal and lab use.

## Across the list

Facts that recur, so each stack handles them the same way.

- **Mail ports are outside Traefik's HTTP routing.** `core/traefik` defines the
  entrypoints `web` and `websecure` and no TCP router. Two shapes exist.
  *The stack publishes its mail ports* through an opt-in overlay, as
  `monitoring/zabbix` does with `trapper.yml` and `core/headscale` with `derp.yml`:
  `core/traefik` stays as it is, and the access policies, security chains and the
  CrowdSec bouncer plugin do not apply to those ports — what limits them is the
  mail server's own rate limits and bans and the host's firewall.
  *Traefik routes them* through one TCP entrypoint per mail port with PROXY
  protocol towards the mail server, which Stalwart, docker-mailserver,
  jeboehm/docker-mailserver and Mailu each document: `core/traefik` then publishes
  the mail ports, and the HTTP middlewares do not attach to a TCP router either.
  Plain SMTP on port 25 carries no server name, so port 25 on a host belongs to
  one mail stack in both shapes.
- **Who may send a PROXY header.** A mail server that accepts PROXY protocol takes
  the client address from the header, and SPF checks, block lists, rate limits and
  bans act on it. The header is trusted by source address. `proxy-public` holds the
  web-facing container of every routed stack, so trusting that network's range
  extends the trust to all of them; trusting Traefik alone needs a fixed address
  for it, which Stalwart's and docker-mailserver's examples assign.
- **The client address behind a published port.** What address the mail server sees
  for a connection through a published port is established on a host. CrowdSec's
  host remediation acts on the forward path, which traffic to a published port
  takes ([`networking.md`](../standards/networking.md#a-host-firewall-and-docker-share-the-forward-path));
  its enforcement against real traffic is open
  ([`firewall-bouncer.md`](../../core/crowdsec/docs/firewall-bouncer.md#verification-status)).
- **The certificate sits in the mail server.** In each upstream's Traefik example
  the proxy forwards the mail ports without terminating TLS, and STARTTLS is
  negotiated inside the mail protocol, so the mail server holds the certificate in
  both shapes. Three sources: the server's own ACME client — Stalwart has one, and
  with Traefik on ports 80 and 443 only its DNS challenges work without routing a
  challenge through the proxy; Traefik's `acme.json`, which docker-mailserver reads directly
  and upstream's Stalwart example converts to files with a third-party container;
  or files issued outside the proxy, mounted into the container.
  `core/acme-certs` names mail servers among its targets, and
  [`ROADMAP.md`](../../ROADMAP.md#out-of-scope-here) lists it as being extracted to
  its own repository.
- **What a run on the image can show.** A start under the baseline,
  authentication, delivery between local accounts and the interface behind Traefik.
  Delivery to and from other mail systems needs a public address with port 25 open
  in both directions, MX, SPF, DKIM and DMARC records and reverse DNS for the
  sending address. Those belong to the operator, and each stack's README states
  them.
- **First start.** Stalwart serves setup over plain HTTP behind a password from
  its log, docker-mailserver needs an account within two minutes, and
  jeboehm/docker-mailserver creates its administrator from the command line. None
  hands the instance to the first visitor.
- **Outbound calls on by default.** Stalwart's download of its web interface and
  docker-mailserver's update check; signature downloads wherever ClamAV is enabled.
  A DNS block list sends each connecting address to the list's operator; it is off
  by default in docker-mailserver.
- **Memory with ClamAV.** docker-mailserver's figure is about 850 MB for the
  signatures alone and 3 GB without swap; the repository's default swap policy is
  none.
- **A CDN proxy does not cover the mail ports.** Cloudflare proxies HTTP and
  HTTPS and states that it does not proxy mail traffic on port 25; mail records
  stay DNS-only. Arbitrary TCP ports go through Spectrum, which Cloudflare
  offers for custom ports on the Enterprise plan only. Its Email Routing, on the
  free plan, receives mail and forwards it to another address, which is a
  different arrangement from a proxy in front of this server. A stack's web
  interface can sit behind the proxy; the host's address is public for mail
  either way.
- **A relay for the other stacks is not part of these batches.** The stacks that
  send mail reach their relay over the internet. Submitting to a mail stack on the
  same host needs a network both are on, and stacks share none except
  `proxy-public`.

## Decided on 2026-10-03

Open source is the entry condition for this list, as it was on 2026-09-22.

**Added — three, in the batch order below.** Stalwart, docker-mailserver and
jeboehm/docker-mailserver. They differ in shape: one binary with its own web
interface, one container configured by files, and one container per function with
an administration interface and webmail.

**Held until a release carries the fix.** Mailu: CVE-2026-86008 has no fixed
release. It is revisited when a release contains the fix — a new release line, or
a backport into `2024.06`.

**Not added:**

| Product | Reason |
|---|---|
| mailcow: dockerized | `netfilter-mailcow` runs `privileged: true`, which the baseline refuses without an exception path, and upstream's configuration has no switch that leaves the service out |
| poste.io | proprietary; the source is not published |
| Axigen | proprietary; the free licence covers ten users |

## Batch order

Each batch is its own pull request under the existing rules, and every stack lands
`scaffolded`. The letters continue from the 2026-09-22 batches.

| Batch | Products | Note |
|---|---|---|
| W | Stalwart | One container; bootstrap administrator pinned before the first start; the web interface bundle comes from GitHub |
| X | docker-mailserver | One container, no web interface; an account within two minutes of the first start; update check off |
| Y | jeboehm/docker-mailserver | Nine services; a wrapper for five credentials; separate routers for administration and webmail |

Decisions the batches depend on:

| Decision | Batch |
|---|---|
| How the mail ports are exposed — published by the stack through an opt-in overlay, or routed by Traefik through TCP entrypoints with PROXY protocol | W, X, Y |
| Where each server's certificate comes from — its own ACME client, Traefik's `acme.json`, or files issued outside the proxy | W, X, Y |
| Which image Stalwart runs — upstream's, with the SELv2 code in it, or one built here without the `enterprise` feature | W |
| Whether a mail server sits in `apps/`, which the category test gives for a stack that serves its own users, and what the two docker-mailserver directories are called | W, X, Y |

**Decided on 2026-10-03, with batch W:** the stack publishes its mail ports
through an opt-in overlay, and `core/traefik` stays as it is; each stack states
where its certificate comes from; Stalwart runs upstream's image; mail servers
sit in `apps/`. The reasoning is in [`.ai/decisions.md`](../../.ai/decisions.md).

## Findings from implementation

What building the stacks turned up, recorded here so the tables above are not
mistaken for the end state.

**Batch W — Stalwart.** Shipped as `apps/stalwart`, verified on the image.

- **A ban lands on the proxy unless the forwarded address is read.** 110 failed
  logins from one address banned that address for the whole HTTP listener. Behind
  Traefik that address is the proxy's, so the web interface would stop answering
  for everyone. With `useXForwarded` on, the ban landed on the address in
  `X-Forwarded-For` and a second client behind the same address was still
  answered. The stack sets it.
- **A ban has no expiry by default.** All four ban periods are unset, which keeps
  a ban until it is removed by hand. The stack sets 24 hours.
- **Setup runs over the API.** `x:Bootstrap/set` on the bootstrap listener takes
  the wizard's fields and returns the permanent administrator; the stack's
  script uses it, with a one-time administrator that exists for a single start.
- **The listeners after setup are 25, 465, 993, 995, 4190, 443 and 8080.** 587,
  143 and 110 are in the image's `EXPOSE` list and are not listened on. The
  overlay publishes 25, 465 and 993.
- **Upstream's protections as they ship:** port 25 refuses to relay and offers
  no AUTH, submission on 465 requires a login and refuses a sender address the
  account does not own. The zone file it generates carries SPF with `-all` and
  DMARC with `p=reject`.
- **More leaves the machine than the web interface bundle.** The start log also
  shows four address-data files fetched from GitHub, and 18 DNS block lists are
  configured.
- **DANE is off behind Docker's resolver**, which cannot validate DNSSEC;
  Stalwart says so at start.

## Repository findings from this evaluation

Facts about files that already exist, found while checking the candidates. Each
belongs to the file named.

- [`docs/standards/networking.md`](../standards/networking.md#exposing-ports) lists
  dnsmasq and Hawser as the services that publish a port because Traefik cannot
  route them. `monitoring/zabbix`'s `trapper.yml` and `core/headscale`'s `derp.yml`
  publish one as well and are not on the list.
