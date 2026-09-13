# Dependency Sweep — 2026-09-13

Repo-wide check of every pinned image tag against the upstream releases and the
published security advisories available on that date. Point-in-time record: the
versions below are what was current then, not what the tree pins now. Current
pins are in each stack's `.env.example`; the procedure is the Version Chain in
[`../maintenance.md`](../maintenance.md#chains).

**The findings below are the state before the sweep was applied.** What was done to
each of them is in [Outcome](#outcome) at the end. No stack was deployed: every
change is a pin and a document, and each one still needs a host before its
`Last verified` line may move.

## Method

- 61 stacks across `core/`, `apps/`, `business/`, `monitoring/`, `backup/`.
- Pinned `APP_TAG` / `*_IMAGE` read from each `.env.example`, compared against the
  upstream release list and against the registry that serves the image.
- Published GitHub security advisories fetched per upstream repository for
  2026-04-01 onward, and each advisory's affected and patched ranges compared
  against the pin rather than against the newest release. A stack behind the
  newest release is not the same as a stack inside an advisory's range.
- Running containers on the test host read for comparison. Declared and running
  are separate facts and this sweep records both.

## 1 · The reverse proxy is on an unsupported minor line

`core/traefik/.env.example` pins `TRAEFIK_IMAGE=traefik:v3.6`.

**Traefik 3.6 left security support on 2026-08-16.** Upstream's policy since 3.6
is six months of support from a minor's GA date. 3.6 went GA on 2025-11-07,
active support ended 2026-05-07, security support ended 2026-08-16. The last 3.6
release is `3.6.25` on 2026-07-31; there will be no 3.6.26. The supported lines
are 3.7 (current, `3.7.13`) and 2.11 (extended, security support to 2026-09-07,
now also ended).

Six advisories published 2026-09-07 and 2026-09-10 have **no fix on any 3.6
release**. The affected ranges below start at or below 3.6 and are patched only
in 3.7.12 or 3.7.13:

| CVE | Severity | Affected | Patched | Applies to this configuration |
|---|---|---|---|---|
| CVE-2026-88007 | critical | `>= 3.0.0` | 3.7.13 | HTTP/3 backend NTLM connection reuse. HTTP/3 is enabled — `http3.advertisedPort: 443` in `traefik.yml.tmpl`, `443/udp` published in `docker-compose.yml`. |
| CVE-2026-88008 | high | `>= 3.4.2` | 3.7.13 | Request smuggling and incorrect authorization. Applies to every router. |
| CVE-2026-88004 | high | `>= 3.2.0` | 3.7.13 | Entrypoint header-name sanitization bypassed via request trailers. Applies to both entrypoints. |
| CVE-2026-88009 | high | `>= 3.0.0` | 3.7.13 | Rootless HTTP/1 request-target routes as `/` but is forwarded verbatim — path-scoped routing, middleware guards and access logging are all bypassed. Four routers in this repository are path-scoped: `apps/paperless-ngx`, `business/opensign`, `monitoring/ntfy`, `core/authentik`. |
| CVE-2026-88011 | medium | `>= 3.0.0` | 3.7.12 | ForwardAuth identity spoofing via dot-form header alias. The ForwardAuth block ships commented out, so this lands on the first operator who enables Authentik in front of a route. |
| CVE-2026-88012 | medium | `>= 3.0.0` | 3.7.12 | `respondingTimeouts.readTimeout` not applied to HTTP/3, leaving slow-body uploads unbounded. HTTP/3 is enabled. |

The Kubernetes, Gateway API and CRD advisories in the same batches do not apply:
this blueprint runs the Docker and file providers only.

**The running container is further back than the pin.** `traefik-core` on the
test host runs **3.6.10**, built 2026-03-06. The `v3.6` tag it was pulled from
resolves to `3.6.25` today. Fifteen patch releases separate the two, and they
include `CVE-2026-65600` (critical, authentication bypass via path traversal in
`ReplacePathRegex`, patched 3.6.23), `CVE-2026-48020` (high, StripPrefix
route-level auth bypass via path normalization, patched 3.6.19),
`CVE-2026-71324` (high, cross-user response poisoning via proxied CONNECT,
patched 3.6.24) and `CVE-2026-53622` (high, HTTP/3 mTLS bypass, patched 3.6.18).
A minor-line tag does not update a container that is already running; `docker
compose pull` does. This is the same declared-versus-running gap that
[`../resource-measurement.md`](../resource-measurement.md) records for memory
limits, on a different axis.

### 3.6 → 3.7 is not the no-op the upgrade checklist describes

`core/traefik/UPSTREAM.md` says a minor bump expects no changes. Between 3.6 and
3.7.13 upstream changed request handling in ways that can drop traffic this
repository routes:

| Version | Change | Consequence here |
|---|---|---|
| 3.7.13 | `Upgrade: h2c` and `HTTP2-Settings` are no longer forwarded to backends; use the `h2c://` scheme | Any backend relying on cleartext HTTP/2 upgrade stops negotiating it |
| 3.7.13 | Rootless request targets rejected with 400 per RFC 9112 | Clients sending non-conforming targets now fail closed |
| 3.7.12 | `underscoreHeadersStrategy` deprecated, replaced by `aliasHeadersStrategy` (`keep` default, `delete`, `reject`) | Neither option is set in `traefik.yml.tmpl`; the default carries over |
| 3.7.9 | HTTP/1 `CONNECT` rejected with 501 | No router in this repository uses CONNECT |
| 3.7.7 | Bare `` Host(`*`) `` becomes a catch-all matching every request | No rule in this repository uses a bare `*`; all 59 router rules are `` Host(`…`) `` with an explicit host |
| 3.7.3 | `BasicAuth` with an empty user list returns 404 instead of 401; `StripPrefix`/`StripPrefixRegex` reject with 400 when stripping yields a non-normalized path | `apps/seafile` and `apps/seafile-pro` both define a `stripprefix` middleware for `/sdoc-server` |
| 3.6.14 | `trustForwardHeader` on ForwardAuth deprecated in favour of `forwardedHeaders.trustedIPs` at entrypoint level | The commented Authentik block in `integrations.yml.tmpl` sets `trustForwardHeader: true`. The entrypoint-level list is already present, so the block should drop the option when it is uncommented. |

`forwardedHeaders.trustedIPs` is set on both entrypoints, which is the
configuration the 3.6.14 deprecation points at and which mitigates the
`CVE-2026-54764` and `CVE-2026-35051` class of forwarded-header spoofing.

### What the pin should become

`traefik:v3.7`, re-pulled, plus the `UPSTREAM.md` checklist rewritten so that a
minor bump reads the migration guide instead of expecting no changes. Both are
changes to a live reverse proxy and neither is applied here.

## 2 · Core — everything else

| Stack | Pinned | Upstream | Finding |
|---|---|---|---|
| `portainer` + `portainer-agent` | 2.39.5 | 2.39.7 / 2.45.0 | **CVE-2026-72533 (critical)** — Docker API proxy authorization bypassed by a non-canonical Docker API version prefix, patched 2.39.7. 2.39.6 also closes a remaining gap in the CVE-2026-44849 fix and broadens bind-mount restrictions for non-admin users. 2.39.7 is a patch on the pinned line. |
| `dnsmasq` | `4km3/dnsmasq:2.90-r3` | image last published 2025-11-18 | Six dnsmasq CVEs were published in 2026: CVE-2026-2291 (heap overflow in `extract_name()`, cache poisoning), CVE-2026-4890 (DNSSEC infinite loop, DoS), CVE-2026-4892 (DHCPv6 heap out-of-bounds write, local root), CVE-2026-4893 (source-check bypass via RFC 7871 client-subnet), CVE-2026-5172 (out-of-bounds read in `extract_addresses()`). Alpine patched them in dnsmasq 2.91-r1 on 2026-05-14. This image still ships 2.90-r3 from 2025-11-18 and the upstream repository's last commit is from the same date. **The image is not receiving the fixes.** Either move to an image built on current Alpine or replace the stack. |
| `crowdsec` | v1.7.8 | 1.8.1 | Two medium advisories fixed in 1.8.0: unbounded body read in the HTTP acquisition datasource and in the kubernetes-audit webhook. Neither datasource is configured here — `acquis.yaml` uses `type: traefik` (file) and `appsec.yaml`. Not exposed. 1.8.0 adds WAF bot detection and a Kubernetes datasource; the upgrade is a feature decision, not a security one. |
| `authentik` | 2026.5.6 | 2026.5.7 / 2026.8.2 | Two **high** advisories published 2026-09-09, patched in 2026.5.7 alongside 2026.8.2 and 2026.2.7: denial of service via malformed SAML messages, and MFA bypass via recipient override in the email authenticator. 2026.5.7 is a patch on the pinned line. 2026.8 carries breaking changes — forwarded request headers are only honoured from a trusted proxy network, the WebAuthn "prevent duplicate devices" option is gone, `hash_password` no longer takes a positional password, and `AUTHENTIK_POSTGRESQL__CONN_OPTIONS` is deprecated. |
| `collabora` | 26.04.2.4.1 | 26.04.3.2.1 | CVE-2026-77276 (high, unauthenticated document conversion could run document macros) is patched in 26.04.2.2; the pin is later than that and is covered. Two minors behind. |
| `euro-office` | v9.3.2 | v9.3.4-hotfix.1 | v9.3.3 clears a picomatch ReDoS advisory in the web-apps build and adds a disclosure policy. |
| `keycloak` | 26.7.3 | 26.7.3 | Current. Carries CVE-2026-35563, CVE-2026-16093, CVE-2026-16072 and CVE-2026-16108. |
| `infisical` | v0.162.13 | v0.165.10 | No published advisory against the pin. v0.165.9 derives the cookie signing key from the KMS root key — security-relevant, not an advisory. Three minor lines behind. |
| `hawser` | 0.2.39 | v0.2.47 | v0.2.47 restricts `/etc/hawser/config` to 0600. **v0.2.46 changes default behaviour**: authentication is now required, and `ALLOW_INSECURE_NO_AUTH=true` restores the old default. This stack passes `HAWSER_TOKEN`, so a bump does not lock it out, but the change belongs in `UPSTREAM.md` before anyone bumps. |
| `dockhand` | v1.0.39 | v1.0.47 | Eight patches behind. `UPSTREAM.md` links `github.com/finsys/dockhand`; the repository resolves as `Finsys/dockhand`. |
| `traefik` socket-proxy | v0.4.2 | v0.5.0 | No advisory. v0.5.0 updates the HAProxy base and adds pause/resume endpoints — re-confirm the `ALLOW_*` surface before bumping, as `UPSTREAM.md` already instructs. |
| `whoami` | v1.11.0 | v1.12.0 | One minor behind. Test fixture. |
| `onlyoffice` | 9.4.0 | 9.4.0 | Current. |
| `acme-certs` | 0.2.1 | v0.2.1 | Current. `UPSTREAM.md` states "Based on version: 3.1.2", which matches no tag this image has ever published. The field is wrong. |
| `workbench` | nginx 1.29-alpine | 1.29.8 | Local playground, floating patch within 1.29. |

## 3 · Apps, business, monitoring, backup

Ordered by whether the pin sits inside a published advisory's affected range.

### Inside an advisory range

| Stack | Pinned | Fixed in | Advisories the pin is exposed to |
|---|---|---|---|
| `apps/ghost` | 6.54.0 | 6.63.0 | Suspended staff could reactivate accounts via password reset (**critical**), restricted-content bypass (high), unauthenticated Stripe checkout allowed member modification and HTML injection (high), plus two medium. Patched across v6.60.0, v6.62.0 and v6.63.0. |
| `apps/n8n` | 2.31.6 | ≥ 2.38.2 | Six advisories published 2026-09-02/03, including expression sandbox escape via shared builtin tampering (high), domain-restriction bypass in the OpenAI chat model node (high), disabled OIDC SSO endpoints still issuing valid sessions, Git node file sandbox escape, per-resource OAuth consent bypass, and improper authorization in source-control push. |
| `apps/lycheeorg` | v7.7.1 | > 7.8.2 | Six advisories between 2026-08-15 and 2026-09-03: multipart chunk replay bypasses upload quota (high), zip `file_name` escapes the extract destination (arbitrary file write), guest identity short-circuits basket ownership checks, unvalidated photo escapes upload moderation, registration exposes registered email addresses, PDF decoy forces expensive Ghostscript renders. |
| `apps/bookstack` | version-v26.05.2 | v26.05.4 | v26.05.3 and v26.05.4 are both security releases. |
| `apps/paperless-ngx` | 3.0.3 | 3.1.3 | GHSA-2jhj-xqrq-rmrq (3.1.2) and path traversal in filename generation with `FILENAME_FORMAT_REMOVE_NONE` (3.1.2); 3.1.3 validates the remote OCR endpoint. |
| `apps/adminer` | 5.5.0-standalone | 5.5.1 / 6.0.2 | X-Forwarded-Prefix backslash bypass (5.5.1). Four further advisories are fixed only in 6.0.2, a major: conditional RCE via CONNECTION_ID XSS with `INTO DUMPFILE`, pre-auth SSRF in the Elasticsearch plugin, ClickHouse driver reflecting arbitrary response bodies, privileged-port SSRF. |
| `apps/vaultwarden` | 1.37.0 | 1.37.3 | 1.37.3 (2026-09-13) revokes 2FA remember-tokens when credentials or 2FA change. |
| `apps/librephotos` | 2026w25 | 1.1.0 | Three advisories published 2026-08-31 with no patched version named — any authenticated user can trash, restore, unpublish or hide another user's public photos. 1.1.0 carries a security fix and moves upstream from weekly build tags to semver, so the pin scheme changes with the bump. |
| `apps/homepage` | v1.13.2 | 2.2.0 | Service proxy allows client-controlled methods and bodies to configured targets (medium, 2.2.0). The fix is across a major: v2.0.0 introduces homepage auth as a breaking change. |
| `apps/opnform` | 2.2.2 | v2.5.0 | v2.4.0 and v2.5.0 both carry security sections. |
| `business/kimai` | apache-2.61.0 | 2.66.0 | Six advisories across 2.62.0–2.65.0 (authorization gaps on team ACLs, project reporting export, admin-only work-contract fields, quick-entry timesheets). 2.66.0 states several security fixes and advises upgrading. |
| `business/vikunja` | 2.3.0 | 2.6.0 | 2.4.0 carries ten security fixes, 2.5.0 one (a share link could act as another user), 2.6.0 eighteen — six of them published 2026-08-31 covering unbounded filter recursion, CSV cardinality, image decode and unthrottled pre-auth endpoints. |
| `business/zammad` | 7.1.2-0013 | 7.1.3 | Four advisories published 2026-08-25: cross-tenant attachment disclosure via inline images (high), disclosure of external data-source credentials to non-admin users (high), group-restricted text modules, overview-object access control. Highest published build of 7.1.3 is `7.1.3-0012`. |

### Behind, not inside an advisory range

`apps/nextcloud` 34.0.2 → 34.0.4 · `apps/immich` v3.0.3 → v3.2.0 (the 2026-08-23
`/maintenance` continue-URL advisory names no patched version) ·
`apps/homarr` v1.72.0 → v1.77.1 · `apps/dashy` 4.5.0 → 4.6.0 ·
`apps/nocodb` 2026.07.0 → 2026.09.0 · `apps/wordpress` 7.0.2 → 7.0.4 (7.1.0 exists) ·
`apps/unifi` 10.4.57 → 10.6.101 · `apps/photoprism` 260601 → 260728 (adds a flag
to disable app passwords) · `apps/heimdall` 2.8.1 → 2.8.3 ·
`business/invoiceninja` 5.13.26 → 5.13.40 · `business/documenso` v2.15.0 → v2.18.0 ·
`business/matomo` 5.12.0 → 5.13.0 · `business/openproject` 17.6.0 → 17.8.0 (its
advisories are patched at 17.6.0) · `business/dolibarr` 23.0.3 → 24.0.1 ·
`monitoring/uptime-kuma` 2.5.3 → 2.5.4 (security fixes) ·
`monitoring/changedetection` 0.60.3 → 0.60.4 · `backup/urbackup` digest from
2026-04-23 while the `2.5.x` tag now resolves to a 2026-08-30 build.

### Current

`apps/mailpit` v1.31.1 · `apps/easyappointments` 1.6.0 · `apps/photoview` 2.4.0 ·
`apps/monicahq` 4.1.2-apache · `apps/it-tools` 2024.10.22 · `apps/caldiy` v6.2.0-6 ·
`apps/tymeslot` 1.15.1-slim · `business/listmonk` v6.2.0 · `monitoring/beszel` +
`beszel-agent` 0.19.0 · `monitoring/gatus` v5.36.0 ·
`monitoring/healthchecks` v4.4 · `monitoring/ntfy` v2.28.0.

The `monitoring/` tier is the only one where every stack is current or one patch
behind. It was verified on 2026-09-08.

### Unfixed upstream

`apps/easyappointments` is pinned at 1.6.0, which is the newest release and the
patch for CVE-2026-55651. Five further advisories published 2026-06-15 name no
patched version: unauthenticated customer PII disclosure on the booking
reschedule page (medium), CalDAV connection-test SSRF, cross-provider appointment
writes, Google OAuth provider rebinding, and `disable_booking_message` rendered
as raw HTML. There is no version to move to.

## 4 · Structural

- **No update mechanism is active.** [`../renovate-proposal.md`](../renovate-proposal.md)
  describes the configuration and stops before activating it. Dependabot cannot
  read `image: x:${APP_TAG}`, so the `.env.example` pins are outside its reach.
  Every bump in this repository is a manual sweep. The last one was 2026-07-26;
  the drift above is seven weeks of accumulation.
- **`Last verified` is missing from 27 `UPSTREAM.md` files** — `core/acme-certs`,
  `core/dnsmasq`, `core/dockhand`, `core/hawser`, `core/onlyoffice`,
  `core/portainer`, and 21 more across `apps/`, `business/` and `monitoring/`.
  `backup/urbackup` still carries `__REPLACE_ME__`.
  [`../standards/documentation-workflow.md`](../standards/documentation-workflow.md)
  requires the field on a version bump. Without it there is no way to tell a pin
  that was checked last week from one that has not been looked at since it was
  written.
- **Three `Based on version` fields disagree with the pin they describe.**
  `core/acme-certs` states 3.1.2 against `APP_TAG=0.2.1`; `apps/it-tools` states
  `2025.7.18-a0bc346`, a tag that does not exist on the registry, against
  `2024.10.22-7ca5933`; `apps/monicahq` states `5-apache` against
  `4.1.2-apache`. The field is the mirror the sweep reads first.
- **Minor-line tags hide drift in both directions.** `traefik:v3.6`, urbackup's
  `2.5.x` and workbench's `1.29-alpine` keep the same string while their content
  changes. A running container keeps the digest it started with, so the pin
  reports a version the host is not running, and a redeploy silently changes the
  version without a commit. The Traefik case above is a fifteen-release gap.
- **`business/opensign` is digest-pinned to `main`.** Upstream publishes no
  semver tags, so there is no release note to read and no advisory range to
  compare against. The pin is reproducible and unreviewable at the same time.
- **Database and runtime bases carried over from the 2026-08-16 registry check
  are unchanged**: PostgreSQL 16/17 against 18, MariaDB 11.4/11.8 against 12,
  Redis 7.4 against 8, Elasticsearch 8.17 against 9, and `business/opensign` on
  `mongo:6.0`, which reached end of life in July 2025. All except MongoDB 6.0 sit
  on supported branches. `apps/caldiy` pins `postgres:17.4` from 2025-02-27 while
  the rest of the tree is on 17.11.

## 5 · What this sweep did not check

- Site content under `site/` — no npm on this host, so the site build and its
  link checks did not run.
- `apps/seafile` and `apps/seafile-pro` — proprietary, operator-versioned.
- `business/vikunja`'s local build image and `core/acme-certs` beyond its tag —
  operator-owned per the 2026-07-26 sweep.
- Whether any bump above applies cleanly. Nothing here was deployed, and the
  advisory ranges come from upstream metadata rather than from testing the
  running versions.

## Outcome

Applied on 2026-09-13, on `dev`, without deploying anything.

### Core

| Stack | From | To | Reason |
|---|---|---|---|
| `traefik` | `traefik:v3.6` | `traefik:v3.7` | 3.6 left security support 2026-08-16; six advisories have no 3.6 fix |
| `traefik` socket-proxy | v0.4.2 | v0.5.0 | HAProxy base; the two new endpoints are revoked by default |
| `dnsmasq` | `4km3/dnsmasq:2.90-r3` | `dockurr/dnsmasq:2.93` | the old image stopped building in 2025-11 and never received the six 2026 dnsmasq CVEs |
| `portainer` | 2.39.5 | 2.39.7 | CVE-2026-72533 (critical) |
| `portainer` socket-proxy | 3.2.15 | 3.4.4 | two minor lines of drift on the Docker API filter |
| `portainer-agent` | 2.39.5 | 2.39.7 | same line |
| `authentik` | 2026.5.6 | 2026.5.7 | two high advisories, 2026-09-09 |
| `collabora` | 26.04.2.4.1 | 26.04.3.2.1 | two minors behind |
| `euro-office` | v9.3.2 | v9.3.4-hotfix.1 | picomatch ReDoS cleared in v9.3.3 |
| `hawser` | 0.2.39 | 0.2.47 | config mode 0600; the 0.2.46 auth-default change is recorded |
| `dockhand` | v1.0.39 | v1.0.47 | eight patches |
| `dockhand` socket-proxy | v0.4.2 | v0.5.0 | same as Traefik's |
| `workbench` socket-proxy | v0.4.2 | v0.5.0 | same |
| `infisical` | v0.162.13 | v0.165.10 | three minor lines behind |
| `whoami` | v1.11.0 | v1.12.0 | test fixture |

`crowdsec` stays at `v1.7.8`. The 1.8.0 advisories cover the HTTP and
kubernetes-audit acquisition datasources, and this deployment configures neither.
1.8.0 is a feature release whose WAF bot detection changes what the proxy serves
to clients, which is a decision rather than a patch.

### Apps, business, monitoring, backup

`adminer` 5.5.0 → 5.5.1-standalone · `bookstack` v26.05.2 → v26.05.4 ·
`dashy` 4.5.0 → 4.6.0 · `ghost` 6.54.0 → 6.63.0-alpine ·
`heimdall` 2.8.1 → 2.8.3 · `homarr` v1.72.0 → v1.77.1 ·
`homepage` v1.13.2 → v2.3.0 · `immich` v3.0.3 → v3.2.0 ·
`librephotos` 2026w25 → 1.1.0 · `lycheeorg` v7.7.1 → v7.8.3 ·
`n8n` 2.31.6 → 2.38.7 · `nextcloud` 34.0.2 → 34.0.4-fpm-alpine ·
`nocodb` 2026.07.0 → 2026.09.0 · `opnform` 2.2.2 → 2.5.0 ·
`paperless-ngx` 3.0.3 → 3.1.3 · `photoprism` 260601 → 260728 ·
`unifi` 10.4.57 → 10.6.101 · `vaultwarden` 1.37.0 → 1.37.3 ·
`wordpress` 7.0.2 → 7.0.4-php8.3-apache · `caldiy` `postgres:17.4` → `17.11` ·
`documenso` v2.15.0 → v2.18.0 · `dolibarr` 23.0.3 → 23.0.4 ·
`invoiceninja` 5.13.26 → 5.13.40 · `kimai` apache-2.61.0 → 2.66.0 ·
`matomo` 5.12.0 → 5.13.0-apache · `openproject` 17.6.0 → 17.8.0-slim ·
`vikunja` 2.3.0 → 2.6.0 · `zammad` 7.1.2-0013 → 7.1.3-0012 ·
`changedetection` 0.60.3 → 0.60.4 · `uptime-kuma` 2.5.3 → 2.5.4 ·
`urbackup` digest re-resolved to the 2026-08-30 build of `2.5.x`.

### Four of these are not a plain version bump

- **`core/dnsmasq` changed image.** `dockurr/dnsmasq` reads the same two paths the
  stack already mounts, so the compose surface is unchanged, but it is a different
  publisher and it has not run here.
- **`business/kimai` was pinned to a tag that no longer resolves.** `apache-2.61.0`
  answers 404 on Docker Hub — upstream dropped the `apache-` prefix after
  `apache-2.57.0`, so `docker compose pull` on that stack was already failing. The
  bare `2.66.0` tag carries the Apache variant, confirmed by digest.
- **`apps/homepage` crosses a major.** v2.0.0 introduces homepage's own
  authentication as a breaking change.
- **`apps/librephotos` changes tag scheme**, from dated weekly builds to semver.

### Where a fix was available and was not taken

- **`apps/adminer` stays on the 5.5.x line.** The four advisories published
  2026-09-07 are fixed in Adminer 6.0.2, and no 6.0.2 image exists — Docker Hub's
  newest 6.x tag is `6.0.1-standalone`, which predates them. One of the four is a
  regression introduced in 5.5.1, so 6.0.x is the affected line. `5.5.1` closes the
  advisory that applies to 5.5.x.
- **`business/dolibarr` stays on 23.x**, at `23.0.4`. Dolibarr 24 is a database
  migration.
- **`apps/easyappointments` has nowhere to go.** Five advisories from 2026-06-15
  name no patched version and 1.6.0 is the newest release.

### Documentation corrected alongside

- `core/acme-certs/UPSTREAM.md` described acme.sh, including its version and
  registry, while the stack runs `ghcr.io/rubennati/cert-ops-tool`. The Source
  block now names the image the compose file pulls and keeps acme.sh as the
  bundled tool.
- `core/dockhand/UPSTREAM.md` pointed at a repository path that does not resolve.
- `business/kimai/README.md` and its upgrade checklist documented the retired
  `apache-X.Y.Z` tag format.
- Four stacks gained the `Based on version` field they never had
  (`core/portainer-agent`, `business/openproject`, `business/vikunja`), and eight
  more had `latest`, `v3` or `v7` in it where an exact pin belonged.

### Still open after this sweep

`Last verified` is missing from 27 `UPSTREAM.md` files and 26 stacks carry the
pre-v0.5.1 `Last checked` stamp. Neither was touched here: both record that a
stack ran, and nothing in this sweep ran. They are in
[`../../.ai/tasks.md`](../../.ai/tasks.md).

### Later the same day

Seven of the bumped stacks ran on a host and carry `Last verified: 2026-09-13`:
`core/traefik` (3.7.13, socket-proxy v0.5.0), `core/whoami`,
`monitoring/uptime-kuma`, `monitoring/changedetection`, `apps/nextcloud`,
`business/invoiceninja`, and `apps/caldiy`'s database. Released as v0.8.2. The
render switch for the CrowdSec integration (`CROWDSEC_BOUNCER_ENABLED`) landed
afterwards, and `.github/dependabot.yml` now targets `dev` with an npm entry for
`site/` — the "no update mechanism" finding above is narrower than it was: image
pins are still manual, the site's dependencies and the workflow actions are not.
