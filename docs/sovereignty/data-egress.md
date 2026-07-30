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
that reading the file answers the question. `checkNewVersion` is the one that
actually changes behaviour.

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
absent from CT is unlisted, not protected. Anything reachable needs to survive
being found.

### Container registries

Every `docker compose pull` tells the registry which images this host runs, from
which IP. Docker Hub, GHCR and Quay all see it. There is no configuration that
avoids this short of running a pull-through cache or a private registry, which
is out of scope here — but it means "which software does this organisation run"
is not a secret from the registries involved.

### Monitoring — gone through, stack by stack

Monitoring was the category most likely to phone home, on the reasoning that a
tool whose job is watching things tends to want to report. It is better than
expected: two of seven make an unrequested outbound call, and only one of those
sends anything about the installation.

None of these stacks has been run on a host yet, so every line below is read from
upstream's source, not observed on the wire.

| Stack | Unrequested outbound call | Off by |
|---|---|---|
| **changedetection** | daily POST to `changedetection.io/check-ver.php` — version, **persistent install GUID**, watch count | `DISABLE_VERSION_CHECK=yes`, now set in compose |
| **uptime-kuma** | GET `uptime.kuma.pet/version` every 48 h — no payload | Settings → About, post-install only |
| **ntfy** | none unless you enable iOS push | already commented out |
| beszel · beszel-agent | none — the agent dials the hub, nothing else | — |
| gatus | none | — |
| healthchecks | none | — |

**changedetection is the one worth naming.** The GUID is persistent, so the daily
request is a per-installation beacon rather than a version lookup, and the watch
count is usage data. Neither is hidden — the environment variable to stop it is
documented — but nothing in a compose file would have told you.

**Uptime Kuma's is milder and cannot be pre-set.** It sends no data about the
instance; the vendor learns that an installation exists at your address. The
setting lives in the database, so it is a post-install step alongside creating
the owner account. Upstream defaults it on.

**ntfy is the interesting case, because it is not really telemetry.** A
self-hosted server cannot deliver instant iOS notifications by itself — Apple
does not permit it. Setting `upstream-base-url` sends a poll request to ntfy.sh
carrying the message ID and a SHA256 of the topic URL, never the content; the
device then fetches the real message from your server. Same shape as Nextcloud's
push path: self-hosting the server does not self-host the push, because Apple and
Google own that leg.

It is commented out in `server.example.yml`, which is the right default —
Android and desktop work without it, and only an iOS receiver needs the trade.

**What all three probing tools do by design** is worth stating once: gatus,
Uptime Kuma and changedetection all reach out to whatever you point them at, so
those targets see this server's address and its polling pattern. That is the
function. changedetection's optional AI features additionally send page content
and diffs to whichever AI provider you configure.

## What to do with this

There is no setting that makes a stack silent, and chasing one is the wrong
goal. The useful version is narrower:

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
