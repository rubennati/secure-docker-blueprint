# Candidate evaluation — 2026-09-22

The products the blueprint held until this evaluation — the *Planned* lists in
[`apps/`](../../apps/README.md), [`business/`](../../business/README.md),
[`monitoring/`](../../monitoring/README.md) and [`backup/`](../../backup/README.md),
and Suricata and Coraza under *On hold* in [`ROADMAP.md`](../../ROADMAP.md) —
checked against what the repository requires of a stack before one is written.
That is twenty-three products, counting Grafana and Prometheus as one as the planned
list does, three more that other sections of `apps/README.md` planned — Rallly,
Headscale and SnapPass — and two proposed the same day: paperless-gpt and
paperless-ai.

Every line below was read from the project's own repository, its documentation, or
its registry's metadata, read without pulling the image. Nothing was started. What
is said about an image under the baseline — its user, the capabilities it needs,
whether its root filesystem can be read-only — comes from the image configuration
and the source, and the stack's first run has to confirm it. Method and verdicts
follow [the 2026-09-21 evaluation](candidate-evaluation-2026-09-21.md).

What followed from it is in [Decided on 2026-09-22](#decided-on-2026-09-22):
eighteen are added in batches, three wait for an image built here, one waits for
its upstream to decide, and the rest are not added. The reasoning is in
[`.ai/decisions.md`](../../.ai/decisions.md).

## What decides the verdict

| Requirement | Where it comes from |
|---|---|
| A published image with a version tag | `docs/standards/env-structure.md` — a bare major or `latest` fails `check-structure.py` |
| An independently operated service | The product criterion: a CLI or per-job container gets no entry |
| A deployment the project itself supports | Upstream's own compose or install documentation |
| Runs inside the security baseline | `check-baseline.py` fails `privileged: true`; host networking and the host PID namespace need a documented exception |
| Licence and origin stated | `scripts/ci/sovereignty-report.py --check` |

Four verdicts follow from it:

- **Stack** — every requirement is met. What remains is ordinary stack work:
  secrets, a healthcheck, limits, and a first-run window closed before the router
  opens.
- **Stack, after a decision** — it can be written, but one point needs the
  maintainer first: a baseline exception, a path that must be public, a licence or
  edition limit, or a component upstream leaves open.
- **Held** — no pinnable image, a published advisory with no fixed release, or no
  release for years.
- **Capability** — Suricata and Coraza are evaluation entries for two capabilities
  in [`docs/architecture.md`](../architecture.md#capabilities-and-reference-implementations),
  not applications. The open question is the capability's design, not a stack.

Maturity is recorded, not scored: stars, the last push and the newest release are
facts a reader can weigh. Nothing here ranks one product against another, and none
is held because a similar product already ships.

## Result

Stars and last push as of 2026-09-22.

| Product | Stars | Last push | Licence | Image, pinnable tag | Verdict |
|---|---|---|---|---|---|
| **apps/** | | | | | |
| [Wiki.js](https://github.com/requarks/wiki) | 28 949 | 2026-09-21 | AGPL-3.0 | `ghcr.io/requarks/wiki:2.5.315` | Stack |
| [Outline](https://github.com/outline/outline) | 40 659 | 2026-09-22 | BSL 1.1 | `outlinewiki/outline:1.10.1` | Stack |
| [Formbricks](https://github.com/formbricks/formbricks) | 12 996 | 2026-09-22 | AGPL-3.0, enterprise directory separate | `ghcr.io/formbricks/formbricks:6.0.0` | Stack, after a decision |
| [HeyForm](https://github.com/heyform/heyform) | 8 986 | 2026-09-09 | AGPL-3.0 | `heyform/community-edition:v3.0.3` | Stack, after a decision |
| [Shlink](https://github.com/shlinkio/shlink) | 5 300 | 2026-09-21 | MIT | `ghcr.io/shlinkio/shlink:5.1.7`, web client `4.8.1` | Stack |
| [Rallly](https://github.com/lukevella/rallly) | 5 266 | 2026-09-22 | AGPL-3.0 | `lukevella/rallly:4.15.2` | Stack, after a decision |
| [Headscale](https://github.com/juanfont/headscale) | 44 041 | 2026-09-17 | BSD-3-Clause | `ghcr.io/juanfont/headscale:0.29.3` | Stack, after a decision |
| [SnapPass](https://github.com/pinterest/snappass) | 904 | 2026-06-29 | MIT | none — upstream's compose builds from source | Held |
| [paperless-gpt](https://github.com/icereed/paperless-gpt) | 2 709 | 2026-09-19 | MIT | `ghcr.io/icereed/paperless-gpt:v0.28.0` | Stack, after a decision |
| [paperless-ai](https://github.com/clusterzx/paperless-ai) | 5 951 | 2026-09-19 | MIT | `clusterzx/paperless-ai:3.0.9`, from 2025-11-04 | Held |
| **business/** | | | | | |
| [Plane](https://github.com/makeplane/plane) | 59 742 | 2026-09-22 | AGPL-3.0 | `makeplane/plane-{backend,frontend,space,admin,live,proxy}:v1.4.2` | Stack, after a decision |
| [Leantime](https://github.com/Leantime/leantime) | 11 630 | 2026-09-07 | AGPL-3.0 | `leantime/leantime:3.9.8` | Stack |
| [AppFlowy](https://github.com/AppFlowy-IO/AppFlowy) | 76 885 | 2026-09-22 | Server: commercial; clients AGPL-3.0 | `appflowyinc/appflowy_cloud:0.18.11` and six more | Stack, after a decision |
| [Ackee](https://github.com/electerious/Ackee) | 4 709 | 2026-09-19 | MIT | `electerious/ackee:3.6.1` | Stack, after a decision |
| [Plausible CE](https://github.com/plausible/analytics) | 29 179 | 2026-09-22 | AGPL-3.0-or-later | `ghcr.io/plausible/community-edition:v3.2.1` | Stack, after a decision |
| [Live Helper Chat](https://github.com/LiveHelperChat/livehelperchat) | 2 246 | 2026-09-22 | Apache-2.0 | none — `remdex/livehelperchat-*` carries only `latest` | Held |
| [Eramba Community](https://github.com/eramba/docker) | 79, deployment repository; source private | 2026-08-19 | Proprietary | `ghcr.io/eramba/eramba:3.31.0-29` | Stack, after a decision |
| **monitoring/** | | | | | |
| [Statping](https://github.com/statping/statping) | 7 292 | 2024-07-05 | GPL-3.0 | `statping/statping:v0.90.74`, from 2020-12-18 | Held |
| [Statping-ng](https://github.com/statping-ng/statping-ng), a fork | 1 992 | 2025-06-04 | GPL-3.0 | `ghcr.io/statping-ng/statping-ng:0.93.0` | Held |
| [ciao](https://github.com/brotandgames/ciao) | 1 981 | 2026-07-16 | MIT | `brotandgames/ciao:1.10.1` | Stack |
| [Checkmate](https://github.com/bluewave-labs/Checkmate) | 10 875 | 2026-09-22 | AGPL-3.0 | `ghcr.io/bluewave-labs/checkmate:3.12.0` | Stack, after a decision |
| [Zabbix](https://github.com/zabbix/zabbix) | 6 395 | 2026-09-22 | AGPL-3.0 since 7.0 | `zabbix/zabbix-server-pgsql:alpine-7.0.30`, matching web image | Stack, after a decision |
| [Grafana](https://github.com/grafana/grafana) + [Prometheus](https://github.com/prometheus/prometheus) | 76 851 / 66 175 | 2026-09-22 | AGPL-3.0 / Apache-2.0 | `grafana/grafana:13.2.2`, `quay.io/prometheus/prometheus:v3.13.3`, `quay.io/prometheus/node-exporter:v1.12.1` | Stack, after a decision |
| [Scrutiny](https://github.com/AnalogJ/scrutiny) | 8 240 | 2026-09-13 | MIT | `ghcr.io/analogj/scrutiny:v0.9.4-web`, `-collector` | Stack, after a decision |
| [Gotify](https://github.com/gotify/server) | 15 946 | 2026-09-20 | MIT, logo CC BY 4.0 | `ghcr.io/gotify/server:3.1.1` | Stack |
| **backup/** | | | | | |
| [Kopia](https://github.com/kopia/kopia) | 14 174 | 2026-09-20 | Apache-2.0 | `kopia/kopia:0.23.1` | Stack |
| [Bareos](https://github.com/bareos/bareos) | 1 254 | 2026-09-22 | AGPL-3.0 with exceptions | none from upstream | Held |
| **Capabilities** | | | | | |
| [Suricata](https://github.com/OISF/suricata) | 6 659 | 2026-09-22 | GPL-2.0 | `jasonish/suricata:8.0.7`, not published by OISF | Capability |
| [Coraza](https://github.com/corazawaf/coraza) | 3 832 | 2026-09-16 | Apache-2.0 | Traefik plugin v0.3.0 from 2024-10-29 | Capability |

In the previous evaluation's terms, Live Helper Chat, Bareos and SnapPass are
Tier 3 — no published, pinnable image — and every other product is Tier 1.

## Stack shape, from each project's own compose

| Product | Services upstream ships | Datastores | Secrets from files | Runs as |
|---|---|---|---|---|
| Wiki.js | 2 | PostgreSQL | `DB_PASS_FILE` only | uid 1000 |
| Outline | 3, plus a TLS proxy Traefik replaces | PostgreSQL, Redis; files local or S3 | every variable | uid 1001 |
| Formbricks | 6 long-running, 5 one-shot jobs, 3 optional profiles | PostgreSQL with pgvector, Valkey, SpiceDB; S3 for uploads | none | uid 1001 |
| HeyForm | 3 | Percona MongoDB 4.4, KeyDB 6.3.3 | none | root |
| Shlink | 1, and an optional web client | PostgreSQL, MariaDB, MySQL or MSSQL | every variable | uid 1001; client uid 101 |
| Rallly | 2 | PostgreSQL | not established | `nextjs` |
| Headscale | 1 | SQLite by default | the OIDC client secret, `client_secret_path` | uid 0 |
| paperless-gpt | 1, beside Paperless-ngx and a model endpoint | files under `/app/db` and `/app/config` | none | root, dropping to uid 10001; `user:` supported |
| paperless-ai | 1, a Node server and a Python retrieval service together | files under `/app/data` | none | root |
| Plane | 13 | PostgreSQL, Valkey, RabbitMQ, MinIO | none | root, all six images |
| Leantime | 2 | MySQL 8.4 | nine variables | uid 1000 |
| AppFlowy | 11 | PostgreSQL with pgvector, Redis, MinIO | none | root, except the auth service |
| Ackee | 2 | MongoDB 7 or newer | none | non-root |
| Plausible CE | 3 | PostgreSQL, ClickHouse | every variable, from `/run/secrets` | uid 999 |
| Live Helper Chat | 7, or 8 with the Node.js helper | MariaDB, Redis | none | root |
| Eramba Community | 7 | MySQL 8.4, Redis | none | root |
| Statping-ng | 1 | SQLite, PostgreSQL or MySQL | none | root |
| ciao | 1 | SQLite | none | uid 1000 |
| Checkmate | 2 | MongoDB | none | uid 1000 |
| Zabbix | 4 in the default profile, of 17 | PostgreSQL | `POSTGRES_USER_FILE`, `POSTGRES_PASSWORD_FILE` | uid 1997 |
| Grafana + Prometheus | no combined compose upstream; 3 or 4 assembled here | SQLite for Grafana; Prometheus's own store | Grafana `__FILE`; Prometheus `*_file` fields | uid 472; `nobody` |
| Scrutiny | 1 (omnibus) or 3 (web, collector, InfluxDB) | InfluxDB 2 | none | root |
| Gotify | 1 | SQLite | every variable | root; `user:` documented upstream |
| Kopia | 1 | its repository, on a volume or remote storage | none for the repository password | root |
| Bareos | 5, no upstream compose | PostgreSQL | — | file daemon as root |

## What needs attention, per product

These are facts to carry into each stack's `UPSTREAM.md`, `README.md` and, where a
call leaves the machine, [`docs/sovereignty/data-egress.md`](../sovereignty/data-egress.md).

### apps/

**Wiki.js.** The 2.5 line receives security fixes; 3.0 is in beta and its release
notes say "Not for production use", and upstream's documentation lists the 2.x
upgrade path as coming soon. 3.0 accepts PostgreSQL 16–18 only, so the stack starts
on PostgreSQL although 2.5 takes others. The first run is a web wizard that makes
whoever completes it the administrator, with a telemetry box ticked by default;
update and locale checks go to `graph.requarks.io` daily. The image has `curl` and
`/healthz` but no healthcheck. OIDC, SAML and LDAP are in the free code.

**Outline.** BSL 1.1: production use is allowed except as a "Document Service"
offered to third parties, and the code becomes Apache-2.0 on 2030-09-09.
`SOURCE_AVAILABLE` already matches the spelling; `core/dockhand` and
`business/akaunting` are precedents. Until a workspace exists,
`/api/installation.create` answers without authentication and makes the caller the
administrator, so the router stays restricted until setup. Sign-in without an
external identity provider is an e-mail link, which needs SMTP, or a passkey; there
is no password login, and `core/authentik` or `core/keycloak` can be the OIDC
provider. `FILE_STORAGE` defaults to `s3`; the stack sets `local`. A daily report
with usage counts goes to `updates.getoutline.com` unless `ENABLE_UPDATES=false`.
The separate enterprise image adds SAML, an audit log and the Confluence importer.

**Formbricks.** 6.0.0 was released on 2026-09-21 and makes AuthZed SpiceDB a
required service. Upstream's compose runs six long-running services and five
one-shot jobs, and pins the application and its Hub service to `latest`; both
publish version tags. File uploads need S3-compatible storage the browser reaches
directly, on its own subdomain; without it, uploads are off. The network model
keeps datastores off `proxy-public`, so the stack either routes uploads through an
internal hop, as Plane's bundled proxy does, or leaves them off — whether uploads
are in scope decides the stack's shape. No variable is read from a file, so a
wrapper covers about ten secrets across four images. The enterprise code ships in
the image behind a licence key: SSO, two-factor authentication, roles and audit logs
are enterprise features. The first visitor becomes the owner, and a daily usage
report goes to `ee.formbricks.com` unless `TELEMETRY_DISABLED=1`.

**HeyForm.** Upstream's compose pins Percona MongoDB 4.4, whose newest image is from
2024-04, and KeyDB 6.3.3, whose last release is from 2023-10, run with protected mode
off and no password. Whether HeyForm 3.0 runs on a current MongoDB and on Valkey is
not established, and that is the decision before a stack: establish it by a run, or
hold. The image runs as root, reads no secret from a file and has no healthcheck;
`/health` and busybox `wget` exist. Registration is open by default
(`APP_DISABLE_REGISTRATION=false`), and `TRUST_PROXY` must be set behind Traefik. The
`latest` tag also moves on release candidates. The repository published 42 security
advisories in 2026, three critical and sixteen high. Most record no patched version;
the vulnerable ranges of every critical and high one end at 3.0.0 or earlier, or at
a commit 3.0.3 contains. One low-severity advisory's range is open-ended from a
commit 3.0.3 contains. Nearly all commits come from one maintainer.

**Shlink.** Short links have to be reachable by whoever follows them, so the stack
needs two routers: redirects on a public one, `/rest` on a restricted one. There are
no user accounts; the API takes keys, created from the CLI or `INITIAL_API_KEY`. The
web client runs in the browser and keeps the keys there — upstream warns that
pre-configured servers "could cause your API keys to be exposed" — so the client
sits behind a restricted router or is left out. GeoLite lookups need a free MaxMind
licence key and are otherwise skipped. `AUTO_RESOLVE_TITLES` makes the server fetch
every long URL it shortens. `curl` and `/rest/health` are in the image.

**Rallly.** The code is AGPL-3.0, and the build enforces a licence of its own:
without a purchased key an instance has one registered user
(`DEFAULT_SEAT_LIMIT = 1`), and upstream's licensing page asks for a key for any
multi-user setup; activation calls `licensing.rallly.co`. Guests who only vote do
not count. Google, Microsoft and OIDC sign-in are documented without a licence
condition. The image runs as `nextjs` on port 3000 with a `curl` healthcheck on
`/api/status`; upstream's compose adds PostgreSQL 18.

**Headscale.** A self-hosted control server for Tailscale clients; its README states
that the project is not associated with Tailscale Inc. OIDC sign-in with PKCE and
group filters is built in, and the client secret can be read from a file. The image
runs as uid 0 with no healthcheck, and the example configuration listens on
`127.0.0.1:8080`, so the stack sets the address. Every client has to reach the
control server, and the optional embedded DERP relay needs STUN on 3478/udp, outside
Traefik's HTTP routing. It serves the installation's network rather than users of
its own — the `core/` question in the category test — while the planned list has it
in `apps/`.

**SnapPass.** No published image: upstream's compose builds from the repository,
and the package is distributed through PyPI. The newest release, v1.6.2, is from
2024-01-03.

**paperless-gpt.** Titles, tags, correspondents and OCR for Paperless-ngx through a
language model; four releases since July, v0.28.0 on 2026-09-18. It has no
authentication, and its README says so plainly: "paperless-gpt has no built-in
authentication. Its web UI and `/api/*` endpoints are open to anyone who can reach
the port." Whoever reaches it can rewrite documents in the connected Paperless-ngx,
run model and OCR jobs on the configured keys, and change its settings — so the
router needs a gate in front, basic auth at Traefik or Authentik's forward auth,
which exists here only as a commented-out block. It holds a Paperless-ngx API token
and, for a hosted model, a provider key; no variable is read from a file. The
entrypoint starts as root and drops to uid 10001 (`PUID`/`PGID`), or runs directly
under `user:`. OCR goes to a vision model, Google Document AI, Azure or a Docling
server — `apps/docling-serve` is one — and the model to Ollama or any
OpenAI-compatible endpoint. No telemetry was found.

**paperless-ai.** Its README opens with a notice dated 2026-03-31: "This repo is
currently not maintained." Its author is rewriting it and is not sure the rewrite
will be finished, citing the AI integration Paperless-ngx now ships itself. The
newest release, 3.0.9, is from 2025-11-04; the one before fixed an API token leak.
The image runs as root and starts a Node server and a Python retrieval service in
one container, with its state in `/app/data`; setup happens in its web interface.
A `nightly` tag is still built.

Both work beside a feature Paperless-ngx added in 3.0 — `PAPERLESS_AI_ENABLED`, with
an `ollama` or `openai-like` backend — which the pinned 3.1.3 carries, off unless
enabled.

### business/

**Plane.** Thirteen services from six application images, all running as root and
none reading secrets from files; the backend image makes `/code` world-writable.
Upstream's documentation leads with the commercial installer; the Community Edition
path is `setup.sh`, which downloads the release's compose file. That file names
`minio/minio:latest`, and `minio/minio` no longer exists on Docker Hub —
`monitoring/langfuse` already pins `quay.io/minio/minio:RELEASE.2025-09-07T16-13-09Z`,
the newest server release there. It also pins `postgres:15.7-alpine` and
`rabbitmq:3.13.6-management-alpine`, both built in 2024. Uploads go through the
bundled Caddy proxy at `/<bucket>/`; keeping that proxy as an internal hop behind
Traefik keeps MinIO off `proxy-public`. `/god-mode` makes its first visitor the
instance administrator, and sign-up is open by default. Every six hours a report
with the instance domain and every workspace slug goes to `telemetry.plane.so`. OIDC
and SAML are in the paid editions, and the commercial edition is a separate
codebase. Six critical advisories were published on 2026-08-03, all fixed in 1.4.0.

**Leantime.** Two services, a non-root image with a healthcheck, and `_FILE` support
for nine variables — not for the OIDC client secret or the S3 key. OIDC and LDAP are
in the free code. `/install` is an open web installer until installation completes;
the command-line installer avoids exposing it. A daily report goes to
`telemetry.leantime.io`, and a news feed is fetched unless `LEAN_NEWS_ENABLED=false`.
The plugin marketplace downloads plugin code with TLS verification switched off; the
stack leaves it unused. The 3.9.8 image was built before two Dockerfile changes on
the main branch, the PostgreSQL driver and support for an arbitrary uid, so MySQL is
the database. CVE-2026-85990 let any signed-in user make themselves administrator up
to 3.9.5.

**AppFlowy.** The self-hosted server is no longer open source: `AppFlowy-Cloud` is
archived and says its images come from "a closed-source fork", and deployment moved
to `AppFlowy-SelfHost-Commercial` under a commercial licence. The free tier is "One
User Seat (per instance)" plus up to three guest editors; OIDC, SAML and SCIM are
paid. The Docker deployment is the whole product — eleven services, including a
browser client and an admin console — mostly as root, with no secret files, an
administrator `admin@example.com` with a published password in the template, and
open sign-up with automatic confirmation. There were 22 server versions in the two
months to 2026-09-22. A user limit is not new here — `business/akaunting` allows two
users and `apps/seafile-pro` runs three without a licence file — but this one is a
single person, in a category of team tools.

**Ackee.** One administrator from the environment, compared in plain text; no rate
limit, no second factor, no SSO. The tracker and the login share `/api`, which must
be public for visitors' browsers, so the login is on the public path whatever the
router does, and a rate limit at Traefik is the only brake. The start command
rebuilds `dist/` on every start, so a read-only root filesystem needs a writable
volume there. No secret is read from a file, and MongoDB in upstream's compose runs
without authentication. There was no release between v3.4.2 (2022-12-17) and v3.5.0
(2025-11-13); the images are built outside the repository's CI.

**Plausible CE.** v3.2.1 is the minimum: CVE-2026-8467, unauthenticated remote code
execution through `/storybook`, affects every 3.x before it. Secrets are read
natively from `/run/secrets`. The tracker needs `/js/*` and `POST /api/event` public,
and everything else can stay restricted — a public router for those paths and a
restricted one for the rest. `/api/system` answers without authentication and is
refused at the router. Plausible takes the client address from headers such as
`X-Plausible-IP` and `CF-Connecting-IP`, and the same address drives its login rate
limit, so Traefik strips them. Upstream pins ClickHouse 24.12 with
`CLICKHOUSE_SKIP_USER_SETUP=1`, which leaves the `default` user without a password;
ClickHouse's security policy supports 26.9, 26.8, 26.7 and 26.3, and whether
Plausible runs on 26.x is not established. The first visitor registers as owner;
after that registration is invite-only. TOTP and a login rate limit are built in;
SSO is not in the Community Edition. Releases come twice a year and fixes are not
backported.

**Live Helper Chat.** No pinnable image. The deployment upstream points to,
`LiveHelperChat/docker-standalone`, uses `remdex/livehelperchat-*` images tagged only
`latest`, amd64 only, and they carry no application code: the install script clones
the `master` branch and installs PHP dependencies inside the running container. That
repository has no licence file. Releases come several times a month and often need a
manual SQL migration. A stack would build its own image from the release archive
under [`custom-application.md`](../standards/custom-application.md).

**Eramba Community.** Proprietary: the Community Terms & Conditions grant use "for
its normal internal business purposes" and forbid modifying, distributing or making
derivative works; there is no user or time limit, and the application source is
private. Activation is mandatory — the first administrator receives a token by
e-mail — and upstream states that "eramba cannot operate fully offline":
registration, updates and error logs go to the vendor. The code lives in a writable
volume and is updated from the interface one version at a time, so the pinned tag
sets the first install, as with `business/facturascripts`. Upstream's compose uses
`latest`, runs the application, cron, triggers and MCP containers as root, gives the
triggers container `NET_ADMIN`, and the image sets `LDAPTLS_REQCERT=never`. The
deployment repository has no licence file, so a stack is written without copying
it. Automations and MCP are listed as not included in Community, which may make
those two containers unnecessary. Upstream's stated minimum is 4 GB of memory and
10 GB of swap; the repository's default is no swap. GRC already has
`apps/ciso-assistant`, in `apps/`, while the planned list puts Eramba in
`business/` and the category test names compliance as a `business/` example — the
placement needs deciding before a second GRC stack lands.

### monitoring/

**Statping.** The newest release is v0.90.74 from 2020-12-18, built with Go 1.14 and
Node 12, and the last push was 2024-07-05 — the case Cabot was held for. The fork's
README says development stopped on the original.

**Statping-ng.** The fork's newest release, 0.93.0, is from 2025-06-04, with no
commit since. GHSA-5442-mh7f-72px (CVE-2026-50884, high), escalation to
administrator, affects every version up to 0.93.0 and has no fixed release. Every
successful OAuth sign-in is made an administrator (issue #357, acknowledged
2026-05-28, open), and the default login is `admin`/`admin`.

**ciao.** One container, SQLite, HTTP checks only, so no capability is needed. The
interface and the REST API are open unless `BASIC_AUTH_USERNAME` is set, and
`/metrics` has its own basic-auth settings. When `SECRET_KEY_BASE` is unset, a new
one is generated on every start, which ends every session; no variable is read from
a file, so a wrapper provides it. The image has no `curl` or `wget` and no
unauthenticated health route, so the healthcheck needs Ruby or a TCP check. Nearly
all commits come from one maintainer.

**Checkmate.** Since 3.10 one image runs the API, the interface and the worker;
MongoDB is the only database, and upstream's compose runs it without
authentication. Ping monitors call `/usr/bin/ping`, which carries the `cap_net_raw`
file capability; under `cap_drop: ALL` the kernel refuses to execute it, so ping
monitors need `cap_add: NET_RAW`. Docker monitoring, new in 3.12, uses the Unix
socket or TCP 2376 with mutual TLS, and upstream states that plain TCP on 2375 is
not supported — the repository's socket proxy speaks plain TCP, so Docker monitors
stay off. `NODE_ENV` must be `production`, or the general API rate limiter is off,
and the server does not trust forwarded addresses, so its login limiter would count
every client as Traefik — to be measured. The first registrant becomes the
superadmin; later accounts need an invitation. No SSO; upstream states it sends no
telemetry. A ReDoS advisory records "not yet patched" for 3.5.1–3.8.1, and whether
3.12.0 carries the fix is not established. `package.json` says ISC; the `LICENSE`
file and the image label say AGPL-3.0.

**Zabbix.** 7.0 is the current long-term-support line, fully supported to 2027-06-30
and in limited support to 2029-06-30; 8.0 is in beta. 7.0.31 was tagged on
2026-09-22 before its images were published, so the pin is `alpine-7.0.30`. Server,
web interface and PostgreSQL fit the baseline except `read_only`: both entrypoints
rewrite configuration under `/etc` on every start, and the database password ends up
in the server's configuration file inside the container. Upstream runs the agent
`privileged: true` with `pid: host`, and the agent2 README says it "must be
privileged or you may mount some system-wide volumes". `privileged` has no exception
path here, so the agent is either installed on the host — as `backup/` places its
agent — or replaced: Zabbix reads Prometheus endpoints, so node-exporter can be its
source. Active agents and `zabbix_sender` need 10051/tcp, SNMP traps 162/udp; those
ports are outside Traefik's HTTP routing, which makes them a host-firewall question
([Exposure decides which controls apply](../architecture.md#exposure-decides-which-controls-apply)).
The default login `Admin`/`zabbix` is changed by hand at first sign-in. LDAP, SAML
and MFA are built in; OIDC is not. `AllowSoftwareUpdateCheck` contacts zabbix.com by
default.

**Grafana + Prometheus.** No upstream publishes a combined compose, so the stack is
this repository's own composition of individually documented components.
`grafana/grafana` is the open-source image — `grafana/grafana-oss` stopped at 13.0.2
on 2026-06-02 — and `grafana/grafana-enterprise` the commercial one. Prometheus 3.13
is the long-term-support line until 2027-07-31. Grafana's defaults change before the
first start: `admin`/`admin`, a `secret_key` fixed in its default configuration,
usage statistics to `stats.grafana.org`, update and plugin checks, the news feed and
external snapshots. The admin password and the secret key are read from files with
`__FILE`, which the distroless variant does not support. OIDC is in the open-source
edition; SAML and team sync are Enterprise. node-exporter runs with the host's
network, PID namespace and root filesystem (`/:/host:ro,rslave`), so it needs an
entry in `HOST_MODE_EXCEPTIONS`, as the Beszel agent has, and then listens on every
host interface unless its address is bound. cAdvisor's quick start is `privileged`
and mounts `/var/run`, which holds the Docker socket; its `docs/running.md` documents
running without `privileged`, and pointing it at the socket proxy is untested. Beszel
already reports per-container figures, so the stack can start without cAdvisor.
Prometheus, node-exporter and cAdvisor have no authentication and stay on the
internal network.

**Scrutiny.** The collector reads disks directly: the README requires `SYS_RAWIO`,
`SYS_ADMIN` for NVMe, one `devices:` entry per disk and `/run/udev`. Upstream's own
note: `SYS_RAWIO` "allows for data exfiltration/modification from SATA drives", and
`SYS_ADMIN` "would theoretically allow for significant system compromise". Each
release also publishes the collector as a Linux binary, so it can run on the host —
as `backup/` runs its agent — with only the web interface and InfluxDB in Docker.
Scrutiny has no authentication: `POST /api/settings` and `DELETE /api/device/:uuid`
are open, so the router needs a gate. The omnibus image bundles InfluxDB 2.2.0 under
s6-overlay; the hub-and-spoke shape uses the official `influxdb:2.8`, whose tags are
rebuilt and are therefore pinned by digest. Releases paused for 22 months after
v0.8.1 and resumed in February 2026; v0.9.0 migrated drive identities and their
stored data. Upstream's examples use `nightly-*` tags; its README says to pin a
version.

**Gotify.** Fits the baseline as upstream documents it: every variable is read from
a file (`GOTIFY_DEFAULTUSER_PASS_FILE` among them), `user:` works with a data
directory the user owns, and `curl` and `/health` are in the image. 3.1.1 is the
minimum: GHSA-phfm-q6fr-wv34 (high) is fixed there. The initial login is
`admin`/`admin` unless the password file is set before the first start. Tokens are
accepted in the query string, so they can reach Traefik's access log. OIDC arrived
in 3.0, and by default any user of the identity provider is let in. The base image
is Debian `sid-slim`. Clients hold a connection open to the server;
[Where the receiver runs](../../monitoring/README.md#where-the-receiver-runs) already
covers where it belongs.

### backup/

**Kopia.** The repository-server mode is the shape
[`backup/README.md`](../../backup/README.md#where-the-backup-agent-belongs) already
allows: the server in Docker holds the repository, each machine's Kopia client stays
installed on that machine, and the container needs no host mount — the same split as
`backup/urbackup`. Upstream's compose examples use `privileged: true` and mount `/`;
the stack does neither. The repository password comes only from `--password` or
`KOPIA_PASSWORD`, so a wrapper provides it; the interface login can come from an
htpasswd file. Clients speak gRPC, which Kopia serves only over HTTP/2 with TLS:
behind Traefik that means an HTTPS backend and a `serversTransport`, which upstream
documents only for nginx and which the first run has to establish. `/metrics`
answers on the main port without authentication and is refused at the router. The
default access rule gives each client full rights on its own snapshots, delete
included; an `APPEND` rule keeps a compromised client from removing them. The
version is still 0.x.

**Bareos.** No image from upstream: the Docker Hub `bareos` namespace is empty, and
the organisation's one container repository is a 2022 example "by no means ready to
be used in production". The `barcus/bareos-*` images are a third party's, last pushed
2025-01-12, at Bareos 22. The community package repositories carry "only the latest
build", so a stack built from packages cannot pin a version; the subscription
repositories keep three majors and need a subscription. Tape ties the storage daemon
to the host's devices, and the daemons talk on 9101–9103, outside Traefik's HTTP
routing.

## Suricata and Coraza

Neither is an application: each is the candidate for a capability. Both are added
in the last batch, once the design questions below have answers.

**Suricata — Network Security / IDS.**

- The image, `jasonish/suricata:8.0.7`, is maintained by a Suricata core developer
  and is not published by OISF. Tags are rebuilt in place and pushed by hand, so a
  stack pins by digest; the public build repository still describes 8.0.6. 7.0
  reached end of life on 2026-07-07.
- Suricata's documentation gives containers `NET_ADMIN`, `NET_RAW` and `SYS_NICE`
  with host networking; passive AF_PACKET capture does not need `privileged`. Under
  `cap_drop: ALL`, the entrypoint's `chown` and Suricata's own privilege drop likely
  need `CHOWN`, `SETUID`, `SETGID` and `SETPCAP` too — to be established with the
  baseline's `docker run --cap-drop ALL` procedure.
- On one Docker host the physical interface carries TLS to Traefik, so payloads are
  opaque there. A Docker bridge, captured promiscuously, carries the plaintext HTTP
  between Traefik and each application, cookies and form data included: inspecting
  payloads on one host means inspecting decrypted user traffic. Bridge names are
  generated unless `com.docker.network.bridge.name` is set, so the name of
  `proxy-public`'s bridge changes when the network is recreated.
- The `crowdsecurity/suricata` collection exists, and its severity-1 scenario
  carries `remediation: true`: one alert bans the source. Fed into CrowdSec as it
  ships, a passive IDS becomes an enforcing one — the failure mode the ROADMAP entry
  rules out.
- ET Open rules are licensed GPLv2 or BSD by rule-ID range; ET Pro is commercial.

Of the ROADMAP's four questions, two now have partial answers: usefulness on one
host depends on accepting bridge capture of plaintext traffic, and CrowdSec can read
the alerts only without the auto-ban scenario. Cost under inspection and the
false-positive load need a disposable host. A stack would sit in `core/` and need a
`HOST_MODE_EXCEPTIONS` entry.

**Coraza — Web Application Security, the documented alternative.**

- The ROADMAP's condition is a maintained Traefik integration. Coraza's own README
  lists the Traefik plugin as "experimental, needs a maintainer"; its newest release,
  v0.3.0 from 2024-10-29, bundles CRS 4.0.0. Traefik's native Coraza integration is
  part of Traefik Hub, a commercial product. The condition is not met.
- Coraza with the OWASP Core Rule Set is already reachable through the reference
  implementation: CrowdSec's AppSec engine is built on Coraza, and the hub offers
  `appsec-crs`, which evaluates out of band, and `appsec-crs-inband`, which blocks.
  The rule files those collections download identify themselves as
  `OWASP_CRS/4.0.0-rc1`, a 2022 pre-release; the current CRS release is v4.29.0
  from 2026-08-17. `core/crowdsec` installs `appsec-generic-rules` and
  `appsec-virtual-patching`, not the CRS collections.
- `coraza-caddy` is "stable, needs a maintainer" and publishes no image, so a Caddy
  in front of an application would be an image built here.

## Across the list

Facts that recur, so each stack handles them the same way.

- **First-run windows.** Wiki.js, Outline, Formbricks, Plane, Leantime, Plausible CE,
  Checkmate and Live Helper Chat hand the instance to whoever completes setup first;
  AppFlowy's template carries an administrator with a published password; Grafana,
  Gotify, Zabbix and Statping-ng ship a known login. Where a password is read from a
  file, the stack sets it before the first start. Elsewhere the router ships
  `acc-deny` or a restricted policy until setup is done — `apps/windmill` and
  `apps/dify` are the precedents.
- **Paths that must be public.** Plausible CE's and Ackee's trackers, Shlink's
  redirects, and — depending on where the clients sit — Gotify's and Kopia's
  clients. Each gets a router for exactly those paths and a restricted one for the
  rest, and the shipped defaults stay restricted. Ackee cannot be split: its login
  shares the public `/api`.
- **Outbound calls on by default.** Wiki.js, Outline, Formbricks, Plane, Leantime,
  Grafana and Zabbix each have a switch; the stack sets it and `data-egress.md`
  records the call. Plane's report carries the instance domain and every workspace
  slug.
- **Secrets without file support.** Formbricks, HeyForm, Plane, AppFlowy, Ackee,
  ciao, Checkmate, Scrutiny, Kopia and Statping-ng need the entrypoint wrapper.
  Outline, Shlink, Plausible CE, Gotify and Grafana read every value from a file;
  Wiki.js, Leantime and Zabbix cover the database password.
- **Docker Hub.** Plane's six images, Zabbix, Outline, Leantime, Ackee, HeyForm,
  ciao and Kopia come from Docker Hub; the image scan already records images it
  could not pull under Docker Hub's anonymous limit. Wiki.js, Shlink and Gotify
  publish the same images on GHCR and Prometheus on quay.io, and the stacks pull
  from there.
- **Two datastores shared with an existing stack.** MinIO: `minio/minio` no longer
  exists on Docker Hub, and the newest server release on quay.io is
  `RELEASE.2025-09-07T16-13-09Z`; Plane and AppFlowy need it, and
  `monitoring/langfuse` runs it. ClickHouse: Plausible CE's upstream pins 24.12 and
  `monitoring/langfuse` pins 25.12, and ClickHouse's security policy supports
  neither line.
- **Capabilities and devices are not checked.** `check-baseline.py` fails
  `privileged` and warns on host networking and the host PID namespace; it reads
  neither `cap_add` nor `devices`. Checkmate's `NET_RAW`, Scrutiny's `SYS_RAWIO` and
  `SYS_ADMIN`, and Suricata's `NET_ADMIN` would pass CI with nothing recorded but
  the stack's README. Its socket check matches the literal `/var/run/docker.sock`,
  so cAdvisor's documented `/var/run` mount would pass as well; no stack mounts a
  parent directory today.
- **Every new image enters the Trivy baseline.** The image scan runs on pull
  requests into `main`, not into `dev`. Each new image's CRITICAL findings belong in
  `.trivy-baseline.json` before `dev` reaches `main`; otherwise the scan fails on the
  release pull request. It is not a required check, so the failure blocks nothing,
  but it names every unrecorded finding.

## Decided on 2026-09-22

**Added — eighteen, in the batch order below.** Wiki.js, Shlink, paperless-gpt,
HeyForm, obot and Headscale; Plane, Leantime and Plausible CE; Gotify, ciao,
Checkmate, Zabbix, Grafana + Prometheus and Scrutiny; Kopia; Suricata and Coraza.
obot was held on 2026-09-21 and is added with its Docker API access documented as a
deviation. HeyForm is added on a condition: if it does not run on a current MongoDB
and Valkey, it is dropped.

**Build candidates — wanted, but no image to pin.** Live Helper Chat, DayOtter and
Bareos. Upstream is asked to publish an image first; one built here from a fork,
under [`custom-application.md`](../standards/custom-application.md), is the
fallback — the route `apps/caldiy` took.

**Held until its upstream decides.** paperless-ai: its README states that the
repository is not maintained. It is revisited once the announced rewrite is
released or maintenance resumes.

**Not added:**

| Product | Reason |
|---|---|
| Outline | BSL 1.1, which its licence text calls "not an Open Source license" |
| AppFlowy | the self-hosted server comes from a closed-source commercial codebase; its free tier is one user |
| Eramba Community | proprietary Community terms; activation with the vendor is required |
| Formbricks | enterprise code in the image; SSO and two-factor authentication need a licence; the community edition has one workspace |
| Rallly | one registered user without a purchased licence key |
| Ackee | its administrator login shares the public tracker path, with no second factor and no rate limit |
| Statping | no release since 2020-12-18 |
| Statping-ng | a high advisory with no fixed release; no commit since 2025-06-04 |
| Cabot | newest image from January 2019 — [evaluated 2026-09-21](candidate-evaluation-2026-09-21.md) |
| SnapPass | no image; newest release 2024-01-03 |
| Dapta Calendars, MAILFLOW-AI, Crater | no image — [evaluated 2026-09-21](candidate-evaluation-2026-09-21.md); at v0.1.0, with no release at all, and with no release since 2022-03 respectively |
| Tika, Gotenberg, ClamAV as standalone stacks | not needed on their own; they stay inside Paperless-ngx and Seafile Pro |

## Batch order

Batches share a category and a review, each is its own pull request under the
existing rules, and every stack lands `scaffolded`. The letters continue from the
2026-09-21 batches.

| Batch | Products | Note |
|---|---|---|
| H | Gotify, ciao | One container each |
| I | Wiki.js, Shlink | PostgreSQL; Wiki.js restricted until setup; Shlink's redirects public, its API and web client restricted |
| J | paperless-gpt | No authentication of its own — a gate in front; Paperless-ngx, a model and optionally Docling Serve behind it |
| K | Kopia | Its first run establishes gRPC through Traefik |
| L | Leantime | Command-line install |
| M | Plausible CE | Public tracker paths; the ClickHouse line |
| N | Checkmate | `NET_RAW`; MongoDB with authentication |
| O | obot | A read-only socket proxy first, the documented deviation otherwise |
| P | Headscale | Its category; a control server every client reaches |
| Q | Grafana + Prometheus | node-exporter in host mode; cAdvisor only if it runs without `privileged` |
| R | Zabbix | The agent on the host, or node-exporter as its source; 10051/tcp and 162/udp |
| S | Scrutiny | The collector on the host, or in a container with `SYS_RAWIO`; a gate in front of the interface |
| T | Plane | Thirteen services, all root, MinIO |
| U | HeyForm | A current MongoDB and Valkey first |
| V | Suricata, Coraza | Capture interfaces, the CrowdSec scenario, the WAF route |

Decisions each batch depends on:

| Decision | Batch |
|---|---|
| How paperless-gpt's interface is gated — basic auth at Traefik, or Authentik's forward auth | J |
| Which ClickHouse line Plausible CE runs on | M |
| Where monitoring collectors get host access — node-exporter's host mode, the Zabbix agent, Scrutiny's collector — and whether `cap_add` and `devices` get an exception table beside `HOST_MODE_EXCEPTIONS` | N, Q, R, S |
| How obot reaches the Docker API | O |
| Whether Headscale belongs in `core/`, and how its control server is exposed | P |
| Which interfaces Suricata captures, whether its alerts reach CrowdSec without the ban scenario, and which route Coraza takes | V |

## Repository findings from this evaluation

Facts about files that already exist, found while checking the candidates. Each
belongs to the file named.

- [`monitoring/README.md`](../../monitoring/README.md) names disk health among the
  axes it covers. No stack covers it; Scrutiny is the planned one.
- [`scripts/ci/check-baseline.py`](../../scripts/ci/check-baseline.py) matches the
  socket path literally and does not read `cap_add` or `devices` — see
  [Across the list](#across-the-list).
- [`monitoring/langfuse`](../../monitoring/langfuse/) pins ClickHouse 25.12, a line
  outside ClickHouse's security support, and MinIO
  `RELEASE.2025-09-07T16-13-09Z`, the newest server image on quay.io.
- [`docs/sovereignty/provenance.md`](../sovereignty/provenance.md) counts licence
  classes as of 2026-09-19 — 84 stacks, five of them source-available.
  `sovereignty-report.py` now classes 101 stacks, nine of them source-available.
