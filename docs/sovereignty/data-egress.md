# Data egress — what leaves the machine while it runs

Self-hosting moves the data onto your disk. It does not stop the software from
talking to its vendor. Several components in this repository make outbound calls
by design, and two of them are enabled by their own defaults.

None of this is hidden by the projects involved. It is simply not visible from
the compose file, which is where an operator looks.

## What this blueprint sends

### CrowdSec — bidirectional, on by default

The engine registers with CrowdSec's Central API on first start and both pulls
and pushes. Measured on a running host: **15,880 decisions arrive**, essentially
all from other installations. In return this host sends the address that
triggered, which scenario fired, and a timestamp.

Not the request. `context` forwarding is off by default, so URLs, headers and
bodies stay local. Verify with:

```bash
docker exec crowdsec cscli console status   # what is forwarded
docker exec crowdsec cscli capi status      # registration and sharing
```

Turning sharing off also ends the pull — it is one arrangement, not two
switches. CrowdSec SAS is French, so the data stays in the EU, but it is a data
flow and should be a decision. The full trade-off, including the diagnostic cost
of blocking addresses you did not choose, is in
[`core/crowdsec/README.md`](../../core/crowdsec/README.md).

### Traefik — turned off here, on by upstream's default

Traefik's `checkNewVersion` is **enabled by default upstream**. It contacts
`update.traefik.io` periodically with the running version and **the instance's
public IP address**. Traefik Labs states the purpose plainly: to detect
companies running Traefik and offer them support contracts and enterprise
features.

That is commercial lead generation, switched on unless you switch it off. This
blueprint switches it off, in `ops/templates/traefik.yml.tmpl`:

```yaml
global:
  checkNewVersion: false
  sendAnonymousUsage: false
```

`sendAnonymousUsage` is opt-in upstream and already off; it is set explicitly so
that reading the file answers the question. `checkNewVersion` is the setting that
changes behaviour.

Trade-off: you no longer get told about new releases. This repository tracks
versions in `UPSTREAM.md` and via Renovate instead, so nothing is lost that was
not already covered.

### Nextcloud — several, mostly optional

Mobile push notifications route through the project's own push service, because
Apple and Google will only accept push from a registered application. The
notification metadata therefore passes through Nextcloud GmbH's infrastructure —
the message content does not. Alongside that: the app store, update checks and
external storage all reach out.

`apps/nextcloud/README.md` documents which of these break if the server has no
outbound internet, which is the practical form of the question.

### Certificate Transparency — public, and easy to miss

Every certificate Let's Encrypt issues is submitted to public Certificate
Transparency logs. This is mandatory for public trust and not something the
issuer can opt out of. The consequence:

**Every hostname you request a certificate for becomes publicly searchable**,
within minutes, forever. `crt.sh` will list them. An internal-sounding
`backup-admin.example.com` is not internal once it has a certificate.

A wildcard certificate publishes only `*.example.com`, so individual hostnames
stay out of the log. That is the reason to prefer the DNS-01 wildcard path in
`ops/templates/dynamic/acme-wildcard.yml.tmpl` when hostnames are themselves
worth not advertising — not convenience.

It is not a reason to skip TLS, and not a reason to rely on it: a hostname
absent from CT is harder to find. It is not protected by that absence — anything
reachable needs to survive being found.

### Container registries

Every `docker compose pull` tells the registry which images this host runs, from
which IP. Docker Hub, GHCR and Quay all see it. There is no configuration that
avoids this short of running a pull-through cache or a private registry, which
is out of scope here — but it means "which software does this organisation run"
is not a secret from the registries involved.

### Monitoring — gone through, stack by stack

Each monitoring stack was read individually. Two of seven make an unrequested
outbound call, and only one of those sends anything about the installation.

None of these stacks has been run on a host yet, so every line below is read from
upstream's source, not observed on the wire.

| Stack | Unrequested outbound call | Off by | How well established |
|---|---|---|---|
| **changedetection** | daily POST to `changedetection.io/check-ver.php` — version, **persistent install GUID**, watch count | `DISABLE_VERSION_CHECK=yes`, now set in compose | the call is in `flask_app.py` |
| **uptime-kuma** | GET `uptime.kuma.pet/version` every 48 h — no payload | Settings → About, post-install only | URL and interval in `check-version.js`; default in `Settings.vue` |
| **ntfy** | none unless you enable iOS push | already commented out | documented upstream |
| beszel · beszel-agent | none automatically — but `beszel update` fetches from `api.github.com` (or `gh.beszel.dev` with the mirror flag) | it is a subcommand, not a timer | invocation traced to `case subcommand == "update"` |
| gatus | none found | — | **searched, nothing found** |
| healthchecks | none found | — | vendor documents its outbound integrations; search found nothing |

### The last two rows are a weaker claim than the first two

Finding a call establishes that it exists. Not finding one establishes only that
the searches ran. A source search covers the shapes somebody thought to search
for, and this repository has already been bitten four times by the same class of
error: a thing that was configured, looked correct, and silently did nothing
because it was never actually reached. "I looked and found nothing" becoming
"there is nothing" is the same mistake pointed the other way.

**The only thing that settles it is watching the wire**, and none of these
stacks has been run yet. When monitoring is deployed for v0.8.0, the test is
cheap: attach the stack to a network with a default-deny egress rule and read
what gets refused, over at least 48 hours — Uptime Kuma's interval is long
enough to be missed by a short observation.

Until then, treat the bottom two rows as *not currently known to*, not as
*does not*.

**changedetection sends a persistent GUID.** The GUID does not rotate, so the daily
request is a per-installation beacon rather than a version lookup, and the watch
count is usage data. Neither is hidden — the environment variable to stop it is
documented — but nothing in a compose file would have told you.

**Uptime Kuma's call carries no payload and cannot be pre-set.** It sends no data
about the instance; the vendor learns that an installation exists at your address. The
setting lives in the database, so it is a post-install step alongside creating
the owner account. Upstream defaults it on.

**ntfy's outbound call is not telemetry.** A
self-hosted server cannot deliver instant iOS notifications by itself — Apple
does not permit it. Setting `upstream-base-url` sends a poll request to ntfy.sh
carrying the message ID and a SHA256 of the topic URL, never the content; the
device then fetches the real message from your server. Same shape as Nextcloud's
push path: self-hosting the server does not self-host the push, because Apple and
Google own that leg.

It is commented out in `server.example.yml`, which is the right default —
Android and desktop work without it, and only an iOS receiver needs the trade.

**All three probing tools reach outward by design:** gatus,
Uptime Kuma and changedetection all contact whatever you point them at, so
those targets see this server's address and its polling pattern. That is the
function. changedetection's optional AI features additionally send page content
and diffs to whichever AI provider you configure.

### apps/ and business/ — gone through, 29 stacks

Read from each project's own documentation and source on 2026-07-31. Every
positive was then checked by a second pass whose job was to refute it; one
claim did not survive. The full record, per stack with citations, is in
[`docs/research/egress-apps-business-2026-07-31.json`](../research/egress-apps-business-2026-07-31.json).

None of this was observed on the wire. It establishes that a call exists, not
that no other one does.

**Six carry a persistent installation identifier.** That is what separates a
version lookup from a per-install beacon: the vendor can count installations and
follow each one over time.

| Stack | Sends | Off by |
|---|---|---|
| **apps/photoprism** | POST to `my.photoprism.app/v1/hello` on first run and on renewal — persistent `ClientSerial`, version, OS, architecture, CPU core count | **nothing.** `hub.Disable()` is reachable only from test configuration |
| **business/dolibarr** | POST to `ping.dolibarr.org` — `hash_unique_id`, the company's country code from the ERP's own record, version | install wizard checkbox, **ticked by default** |
| **business/documenso** | PostHog EU Cloud, `installationId` as the distinct ID; one startup event, then a heartbeat | `DOCUMENSO_DISABLE_TELEMETRY=true` |
| **apps/homarr** | PostHog at `hog.homarr.dev`; a cuid minted on first run and stored in the database | `NO_EXTERNAL_CONNECTION=true` |
| **apps/opnform** | OpenPanel at `telemetry.opnform.com`; a UUID in the settings table, cached forever | `OPNFORM_ANONYMOUS_TELEMETRY_DISABLED=true` |
| **business/openproject** | `releases.openproject.com/v1/check.svg` — uuid, installation type, version | admin setting, or `security_badge_display=false` |

**WordPress sends more than a version.** `api.wordpress.org/core/version-check/`
carries the PHP and MySQL versions, the locale, **the number of sites and the
number of users**, and whether multisite is enabled. There is no supported
environment variable in the official image.

**Seven check a version without identifying the installation.** These are
downloads rather than beacons — a plain GET, no payload, no identifier. The
receiving host learns the source IP and the timing.

| Stack | Endpoint | Off by |
|---|---|---|
| apps/lycheeorg | `lycheeorg.dev/update.json`, GitHub advisories | `VULNERABILITY_CHECK_ENABLED=false` works; `UPDATE_CHECK_ENABLED=false` **does not** — see below |
| apps/dashy | `raw.githubusercontent.com/.../package.json` | **nothing in 4.5.0**, despite what the setting suggests |
| business/invoiceninja | `pdf.invoicing.co/api/version` daily, hardcoded | no variable exists |
| apps/easyappointments | `easyappointments.org/feed/` | none found |
| apps/vaultwarden | GitHub releases | reachable only through the admin panel |
| business/listmonk | `update.listmonk.app` | `app.check_updates`, default on |
| apps/adminer | `adminer.org` — but from the **browser**, not the server, via an injected iframe | needs a custom build; the admin's own address is what is seen |

**Two documented switches do not work.** Both were found by reading the code
rather than the documentation, and neither project's own docs say so:

- **Lychee** — `UPDATE_CHECK_ENABLED=false` does not stop the fetch on the
  `/Admin/UpdateStatus` route. `CheckUpdate` is constructor-injected, and its
  constructor calls `hydrate()` unconditionally, so the request has already
  fired before the feature flag is evaluated. Capped at one call per three days
  by the response cache.
- **Dashy** — `appConfig.disableUpdateChecks` gates the browser-side check.
  The server-side one in 4.5.0 has no switch at all.

**Three send data about people rather than about the installation.** Different
in kind from telemetry, and easier to miss:

- **apps/bookstack** — an MD5 of each user's e-mail address goes to Automattic
  whenever an avatar is rendered. `DISABLE_EXTERNAL_SERVICES=true`
- **apps/librephotos** — the GPS coordinates of **every scanned photo** go to
  OpenStreetMap's Nominatim for reverse geocoding. `FEATURE_REVERSE_GEOCODING=false`
- **business/zammad** — `images.zammad.com` for avatar and organisation lookups,
  `geo.zammad.com` for location. Admin UI, Settings → System → Services

**Cal.diY carries a telemetry module that never runs.** `packages/lib/telemetry.ts`
holds a hardcoded Jitsu endpoint and a server-to-server write key inherited from
Cal.com, and `.env.example` ships `CALCOM_TELEMETRY_DISABLED` with an opt-out
comment. None of it executes: `next-collect` is not a dependency, the exported
configuration has no consumers, and `apps/web` has no `middleware.ts`. Recorded
because the code reads as active and is not.

**Twelve produced no finding.** Heimdall, Seafile, Seafile Pro, Vikunja,
OpenSign, IT-Tools, Paperless-ngx, Monica, Photoview, Kimai — each checked
against its own configuration reference. **UniFi is not in that list in the same
sense**: the controller is closed-source Java, so no source was readable and
Ubiquiti's documentation does not settle it. It is unestablished, not clean.

## What to do with this

There is no setting that makes a stack silent, and chasing one is the wrong
goal. The narrower question:

1. **Know which calls are on.** The ones above are the ones this repository
   ships. A new stack should have its outbound calls checked before it is marked
   ready, not after.
2. **Decide the ones that are decisions.** CrowdSec's exchange is a genuine
   trade with a genuine benefit. Traefik's version check is not — it serves the
   vendor's sales function, so it is off.
3. **Record it where the operator will look.** In the stack's README, not only
   here.

## Open

`core/`, `monitoring/` and the stacks named above have been gone through.
`apps/` and `business/` have not — only Nextcloud and Invoice Ninja were looked
at, because those are the two that have been run.

The pattern to check for, in order of how often it turns up:

1. **A version check with an installation identifier.** The check itself is
   harmless; a persistent GUID turns it into a beacon. changedetection was the
   one instance of this so far.
2. **A vendor-hosted push relay.** Anything delivering to iOS or Android phones
   has one, because Apple and Google require it. ntfy and Nextcloud both do.
3. **An app store or update feed** the application queries at runtime.
4. **Optional AI features**, which send content to a third-party provider by
   definition.
