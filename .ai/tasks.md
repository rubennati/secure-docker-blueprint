# Tasks

Current work items. Larger direction lives in [`../ROADMAP.md`](../ROADMAP.md);
this file is the short list.

## Open after v0.9.1

State at the v0.9.1 tag (2026-09-20): `dev` and `main` level, no open pull requests,
no open Dependabot alerts, CI green. Everything below is what is not done.

### 1. Image findings as facts — closes audit finding C1

Decision and reasoning: [`decisions.md`](decisions.md#2026-09-20--image-findings-are-recorded-as-facts-and-the-shipped-access-default-follows-them).
Input data: the last full Trivy scan on `main` (2026-09-17, `trivy-image-scan-results`
artifact; a new run started after the v0.9.1 merge and includes the 26 new images).
Snapshot of the 2026-09-17 scan: 99 images, 59 with at least one CRITICAL finding, 1003
CRITICAL in total, every one with a published fix, plus 11 466 HIGH; n8n could not be
scanned (registry rate limit). Largest: `opensign/opensign` 196, `opensign/opensignserver`
206, `louislam/uptime-kuma` 127, `cal.diy` 45, `lycheeorg/lychee` 25, `sdoc-server` 24,
Paperless-ngx 23, OpenProject 22, Seafile 20.

- [ ] Generate a per-image facts file from the scan: CRITICAL and HIGH counts, how many
      have a fix, image age, scan date. Checked in CI for staleness like the other
      generated files.
- [ ] Add an `Exposure` field to `UPSTREAM.md` with a reason, first for the five images
      above; the rest get the rule-derived value.
- [ ] Checker: a stack whose findings mark it private-only or lab-only cannot ship
      `APP_TRAEFIK_ACCESS=access-public`.
- [x] Trivy gate: block only on CRITICAL findings absent from the recorded facts.
      Done — `scripts/ci/trivy-gate.py` against `.trivy-baseline.json`, which records
      513 findings across 76 image repositories as of the 2026-09-21 scan of `dev`.
      Closes audit C1. The bullets around it — the per-image facts file, the
      `Exposure` field and the access checker — are the *decision-data* half and
      remain open; the gate does not depend on them.
- [ ] Catalogue page: show the facts (counts, fix available, age, licence limits) in
      neutral wording; no judgement of the project.
- [ ] For OpenSign and Uptime Kuma: check whether upstream has published a newer image;
      if so bump the pin (normal upgrade), if not record the facts.

### 2. Host verification of the scaffolded stacks (audit S1)

[`../docs/host-session-priority-1.md`](../docs/host-session-priority-1.md) is the ordered
run: Traefik with TLS, a refused client, restart, restore, and each stack's own open
items. Needs a host; nothing in the 26 new stacks has one. Until then they stay
`scaffolded`.

- [ ] `apps/litellm`, `apps/ciso-assistant` and `monitoring/langfuse` were verified on a
      host at the previous pin and moved on 2026-10-04 (`v1.101.4`, `v4.0.9`, `4.50.0`).
      They are `scaffolded` until the run is repeated at the new pin.

### 3. Personal data on the public site (audit W7 / D3)

A decision, with a possible v1.0 impact — see [`decisions.md`](decisions.md) and
`../ROADMAP.md`. Not decided.

### 4. Operator site

- [ ] The catalogue is live and lists every stack; only stacks with a guide appear in
      the Applications sidebar. Guides for the newer stacks (AI, PAM, secret sharing,
      security tooling) do not exist; the audit does not require them.
- [ ] The start page has no link to the catalogue; it is reachable from the sidebar of
      the other pages and from the search.
- [ ] The FAQ names "around thirty" application guides (correct) without pointing to
      the catalogue.
- [ ] The catalogue's "Files" links point at `tree/main`; correct now that v0.9.1 is on
      `main`, but each new stack needs a repository check once.
- [ ] The catalogue page was verified through its built HTML and a public fetch, not in
      a browser.

### 5. Cal.diY hardening

Phased plan in [`../apps/caldiy/docs/hardening-plan.md`](../apps/caldiy/docs/hardening-plan.md).
The stack builds from a reviewed fork; the hardening phases are not finished.

- [ ] The fork image `v6.2.0-6` is built on Next.js 16.2.3. GHSA-vcvr-r3jv-pc5j (remote code
      execution in `next/og`) is fixed in 16.3.6 and recorded in `.trivy-baseline.json` since
      2026-10-04; a fork build on a fixed Next.js removes it.

### 6. Fifteen proposed products — evaluated 2026-09-21

Full evidence per product in
[`../docs/audits/candidate-evaluation-2026-09-21.md`](../docs/audits/candidate-evaluation-2026-09-21.md):
what each publishes, where its compose actually lives, the licence splits, and what
was verified by running it. Three of the fifteen already ship.

- [x] Eleven products have a version-tagged image and can be written as stacks, in
      six batches (A calrs+Calnode · B SolidInvoice+FacturaScripts+Akaunting ·
      C Twenty+Chatwoot · D CISO Assistant+DefectDojo · E obot · F ERPNext).
      Batch A shipped (#140). Batch B: Akaunting and SolidInvoice shipped,
      FacturaScripts held (#145), then shipped on upstream's update model — the
      in-app updater owns the webroot. Batch C: Twenty and Chatwoot shipped (#146).
      Batch D: CISO Assistant and DefectDojo shipped (#150). Batch E: obot held —
      it does not start without the Docker API. Batch F: ERPNext shipped. See the
      evaluation's *Findings from implementation*.
- [x] Batch G, proposed later: rclone-web (`backup/`) and httpbin (`apps/`)
      shipped; Cabot held — no image since January 2019.
- [x] Four publish no image (DayOtter, Dapta Calendars, MAILFLOW-AI, Crater).
      Decided 2026-09-22: DayOtter is a build candidate — §7; the other three are
      not added, with the reason in the 2026-09-22 evaluation.
- [x] Upstream requests, filed by the maintainer and linked where the rule says
      — the stack's `UPSTREAM.md` where one exists, the candidate evaluation
      otherwise: the FacturaScripts installer fix NeoRazorX/facturascripts#2041, merged
      2026-09-25 ·
      rclone/rclone#9957 (`rclone gui` logs a supplied RC password) and
      rclone/rclone-web#139 (its sign-in discards the address) in
      `../backup/rclone-web/UPSTREAM.md` · obot-platform/obot#7978 (start without a
      runtime backend) in the 2026-09-22 evaluation · Dayotter/dayotter#291 and
      Dapta-Tech/dapta-calendars-slate#173 (publish an image) and
      NeoNexAI/MAILFLOW-AI_MAILING#20 and #21 (a patched Next.js, secure defaults)
      in the 2026-09-21 evaluation. All open. None filed for Crater, where images
      have been asked for since 2021 in crater-invoice/crater#659 without a reply,
      or for httpbin, where the failing image is psf/httpbin#69 with a fix proposed
      in #70. When the next one is posted, its link goes the same way.
- [x] Adding these while `../ROADMAP.md` holds applications is a deliberate
      exception — recorded in `../ROADMAP.md` and `decisions.md` (2026-09-21).
- [x] Host verification, 2026-09-22: all twelve behind Traefik with TLS, with the
      refused client, a smoke test, a restart and the README's restore — each
      stack's `UPSTREAM.md`. `Last verified` for nine that day; Twenty and ERPNext
      followed on 2026-09-23 once their causes were fixed. rclone-web is still
      recorded without it — its sign-in takes the password only from a URL. Fixed
      on the way: calrs, Akaunting, SolidInvoice, CISO Assistant.
- [x] Closed on 2026-09-23: Twenty's and Windmill's interfaces — `sec-2-spa-xl`
      (`limit-extra-large` since the middleware model) holds one whole first load
      and both ship it, measured without a `429` ·
      ERPNext's realtime service — a second nginx listener for `/socket.io` gives
      its session check an address it can reach from `app-internal` · Akaunting —
      the stack stays, and the runtime gate is a decision fact in its
      `../business/akaunting/UPSTREAM.md`: every `…/create` page asks
      `api.akaunting.com` for the plan limits with an akaunting.com account's API
      key, and the code has no switch to skip it.
- [ ] Still open from the host verification of 2026-09-22: rclone-web's sign-in — `/login?url=…` applies
      the address and then discards it again, so once the first attempt fails
      against an RC that wants credentials, there is no field left to type them
      into; read in the current source and reproduced on rclone 1.75.1 with the
      GUI version it serves. Filed as rclone/rclone-web#139 (2026-09-23), separate
      from rclone/rclone#9957 on the logged password; the link is in the stack's
      `../backup/rclone-web/UPSTREAM.md` · calnode sets `Secure` on its
      session cookie only with Google or Microsoft sign-in configured (upstream) ·
      the candidate stacks write their secrets with mode `644` inside a `700`
      directory, a third variant beside `600` and `640` in
      `../docs/standards/secrets.md` — recorded, not changed.

### 7. The held candidates — decided 2026-09-22

No application is added while the v1.0 items are open — S1 (verification), C1
(above) and D3. The candidates `../ROADMAP.md` held were narrowed to open-source
products and are added as a second deliberate exception (`decisions.md`,
2026-09-22). Evidence, what was not added and why, and the batch order:
[`../docs/audits/candidate-evaluation-2026-09-22.md`](../docs/audits/candidate-evaluation-2026-09-22.md).

- [x] Batches H–V, each its own pull request, in this order:
      H Gotify+ciao · I Wiki.js+Shlink · J paperless-gpt · K Kopia ·
      L Leantime · M Plausible CE · N Checkmate · O obot · P Headscale ·
      Q Grafana+Prometheus · R Zabbix · S Scrutiny · T Plane ·
      U HeyForm, dropped if it does not run on a current MongoDB and Valkey ·
      V Suricata+Coraza.
      Batch P put Headscale in `core/`, not the `apps/` this list had: the
      category test asks about capability for the installation.
      Batch U's condition was tested and not met, so HeyForm was built: v3.0.3
      runs on `mongo:8.0.32` and `valkey/valkey:8.1.4-alpine` under the full
      baseline — sign-in, a published form, an anonymous submission stored with
      its answer, and an upload under `read_only` as uid 1000. Recorded in
      `../apps/heyform/UPSTREAM.md`.
      Batch V added no stack. Coraza's condition — a maintained Traefik
      integration — is not met, and the capability is already here, because
      CrowdSec's AppSec engine is Coraza; what was missing was documentation,
      now in `../core/crowdsec/docs/appsec.md`. Suricata's two remaining
      questions need a host that can be flooded without consequence, so it
      waits. Both in `decisions.md`, 2026-09-24.
      Which of them landed is in [`../CHANGELOG.md`](../CHANGELOG.md).
      Each stack ships `scaffolded` — verified on its image, not yet behind
      Traefik. Moving them to `baseline-aligned` is S1, above.
- [ ] Replace MinIO in `business/plane` and `monitoring/langfuse`. Both stacks
      stop at it: MinIO withdrew every public image on 2026-09-24 and archived
      its source repository, so the pinned tag cannot be pulled and the services
      that depend on it never start. Each README says so. `cgr.dev/chainguard/minio`
      is public and is what Langfuse's own compose uses, but it ships `latest`
      only, so it runs an installation without being pinnable. A versioned
      S3-compatible store — SeaweedFS or Garage — is the fix, and it needs a run
      against each stack rather than a tag change.
- [ ] Build candidates — Live Helper Chat, DayOtter, Bareos: ask upstream to
      publish an image first; otherwise a fork and an image built here under
      `../docs/standards/custom-application.md`.
- [ ] paperless-ai: revisit once upstream's announced rewrite is released or the
      repository is maintained again — its README says it is not.
- [x] `backup/borgmatic/README.md` counted database engines as "24 · 16 · 13"
      for PostgreSQL · MySQL · MariaDB. The rule is now stated beside the table —
      stacks whose compose files name that database image, MariaDB and MySQL
      apart because borgmatic has a hook for each — with the command to
      re-measure. On 2026-09-24 that gives 31 · 3 · 17. Three more rows were
      stale in the same table: Zabbix stood as planned, and ntfy and rclone as
      absent, though all three now have stacks; MongoDB listed two of its four.
      Both hook names given there were wrong and are checked against upstream's
      schema now — Zabbix reaches the web interface's `/api_jsonrpc.php`, not
      the trapper port, and ntfy's key is `topic`, not `topic_url`.

### 8. Mail servers — decided 2026-10-03

Three mail servers are added as a third deliberate exception (`decisions.md`,
2026-10-03). Evidence, what was held or not added and why, and the batch order:
[`../docs/audits/candidate-evaluation-2026-10-03.md`](../docs/audits/candidate-evaluation-2026-10-03.md).

- [x] Decided 2026-10-03 (`decisions.md`): the stack publishes its mail ports
      through an opt-in overlay, each stack states where its certificate comes
      from, Stalwart runs upstream's image, mail servers sit in `apps/`.
- [x] Batch W, Stalwart — `../apps/stalwart`, `scaffolded`, verified on the
      image. What a host still has to establish is in its `UPSTREAM.md`.
- [x] Batch X, docker-mailserver — `../apps/docker-mailserver`, `scaffolded`,
      verified on the image. Fail2ban is on and needs `NET_ADMIN`, recorded in
      `CAP_ADD_EXCEPTIONS`.
- [x] Batch Y, jeboehm/docker-mailserver — `../apps/mailserver-jeboehm`,
      `scaffolded`, verified on the images. It has no automatic ban; its README
      says so.
- [ ] `apps/mailserver-jeboehm` on a host: sign-in to the administration
      interface behind Traefik, a DKIM signature against a published record,
      and delivery to and from another mail system.
- [ ] `apps/docker-mailserver` on a host: which client address the container
      sees on a published port — Fail2ban bans that address — and delivery to
      and from another mail system.
- [ ] `apps/stalwart` on a host: a certificate on the mail ports, delivery to and
      from another mail system, and the client address Stalwart sees on a
      published port — its bans depend on it.
- [ ] Mailu: revisit when a release contains the fix for CVE-2026-86008 — a new
      release line, or a backport into `2024.06`.

### 9. Milestone v0.10.0 — measured resource limits

Every `✅` stack's limits from a measurement on a real install
([`../docs/resource-measurement.md`](../docs/resource-measurement.md)). Needs a host.
Whether it stays a release is D4 of the stabilization audit; `state.md` carries the
milestone.

### 10. Small items

- Vikunja's `.env.example` carried `smtp-relay.brevo.com` as the mailer host with the
  mailer disabled — a vendor value where the convention is `example.com` or empty.
  Done: `VIKUNJA_MAILER_HOST` is empty, and the Brevo host stands only in a comment
  as an example.
- The five AI stacks and Dify/Langfuse have no restore procedure performed; the READMEs
  document one. The Restore docs column in `LIFECYCLE.md` records what each README
  has; `ops-proven` records a rehearsal.
- The Trivy scan does not cover images built locally (Cal.diY, the vikunja layer);
  recorded in `decisions.md`, 2026-09-18, the custom-application path.
- `core/traefik/ops/scripts/validate.sh` searched the whole of `config/` for
  unresolved `${…}`, `config/host/` included; the watchdog files
  `scripts/host-files.sh render` writes there carry shell variables on purpose, so
  validate failed on a host that rendered them (found 2026-10-23 in a scratch run
  of the middleware-model migration). Done 2026-10-25: the search covers the files
  `render.sh` writes — `config/traefik.yml`, `config/haproxy.cfg.template`,
  `config/dynamic/*.yml`, `config/host/cloudflare-ranges.nft` — with five tests.

---

The three sections below were dropped by the merge `9b7a171` on 2026-09-23 and
restored on 2026-10-15 from its first parent, with their original reasons and notes.
Every box was checked against the tree and git on 2026-10-16: a closed item names its
evidence, an open item its owner. An item whose state could not be established would
be marked *for review*; none needed it.

### 11. Upstream versions — the programme of 2026-10-31

Inventory and batches:
[`../docs/audits/upstream-version-inventory-2026-10-31.md`](../docs/audits/upstream-version-inventory-2026-10-31.md).
One pull request per batch, one commit per stack, the move recorded in the
stack's `UPSTREAM.md`; the scan of the pull request from `dev` to `main`
measures it.

- [x] Batch 1 — seven patch releases with the most recorded CRITICAL pairs (#292, 2026-10-31; none run on a host)
- [ ] Batch 2 — the remaining 28 patch releases; `apps/defectdojo`, `apps/dify`, `apps/greenmail` and `business/chatwoot` are `baseline-aligned` and fall to `scaffolded` without a host run
- [ ] Batch 3 — 60 minor releases of applications, release notes per stack
- [ ] Batch 4 — 9 minor releases of database and infrastructure images, one pull request per family
- [ ] Batch 5 — 20 major releases of applications, a decision per stack
- [ ] Batch 6 — 23 major releases of databases: PostgreSQL 18 across 12 stacks with one procedure, then Valkey 9, MariaDB 11.8, nginx 1.31
- [ ] Batch 7 — floating, release-candidate, date and distribution tags, and the six registries the inventory could not reach
- [ ] The inventory is retaken before each batch until the Renovate decision (`docs/renovate-proposal.md`) is made

### 12. The ingress programme — decided 2026-10-31

DEC-075 to DEC-078 ([`decisions.md`](decisions.md)); the audit is
[`../docs/audits/ingress-architecture-2026-10-31.md`](../docs/audits/ingress-architecture-2026-10-31.md).
One pull request per step, each without a behaviour change for an installation that
declares nothing — the render-identity test holds that.

- [x] 1. The guards: `missing-network-label`, `port-no-host-address`, the subnet check,
      the render-identity test; the records and the register.
- [x] 2. The published ports on one named network: `gw_priority` on `proxy-public`;
      `check-published-family.py` reads the gateway endpoint of the container rather
      than assuming `public`; the Compose minimum for `gw_priority` written down (2.33.1). Changes
      the hairpin source address on the next `up -d` — CHANGELOG Migration. Done on
      `feature/ingress-step-2-gateway`; the IPv6 endpoint stays a host proof.
- [x] 3. `access-trusted*` from `TRUSTED_RANGES`, the overlap check, `access-lan*`
      retired, `migrate-traefik-env.sh` renames and adds the line (DEC-076, amended:
      breaking with a migration, no gate). Done on `feature/ingress-step-3-trusted`.
      Integrations call back over a Docker network with the application's setting;
      Seafile's two OnlyOffice paths have opt-in routes (`onlyoffice-callback.yml`).
- [x] 4. The auth posture in every `.env.example` (`# auth posture:` above the auth
      variable), the `auth-posture` rule, the stacks without a login decided one by
      one (DEC-077): basicAuth for Ollama, Homepage, Dashy, Heimdall; Mailpit's own
      htpasswd; `none` with a reason for whoami, httpbin, it-tools, GreenMail, Gatus.
      Done on `feature/ingress-step-4-posture`.
- [ ] 5. Edge networks: `render.sh` derives them from the installed stacks — a stack
      counts as installed by a signal more reliable than the presence of `.env`, to be
      chosen in the step (a running project, or an explicit list) — the stack template
      carries `name: ${TRAEFIK_NETWORK}`, the migration guide shared → isolated.
- [ ] 6. Exposure shown: the derived profile and the layer list in `validate.sh`, the
      external test script and its marker, the rendered `ingress.nft`, the management
      requirement (DEC-078).
- [ ] 7. IPv6 as bind overlays per family; `TRAEFIK_BIND_V6` without a default; the
      nine known unbound ports bound; the operator site corrected.
- [ ] 8. Host evidence and release; `ipv6-only` stays "not verified" until its own run.

## Blocked on a host

v0.8.0 closed on 2026-09-08 — the record is
[`../docs/host-session-v0.8.0.md`](../docs/host-session-v0.8.0.md); what v0.7.0's
session left open is in
[`../docs/host-session-v0.7.0.md`](../docs/host-session-v0.7.0.md)

- Verify the Priority 1 stacks behind Traefik with TLS and restore each —
      [`../docs/host-session-priority-1.md`](../docs/host-session-priority-1.md).
      Until then they stay `scaffolded`. Not done; the same item is §2 above, which
      carries it, so it has no box here.

- [x] Borgmatic: install, initialise repository, first backup, export the key off-host
      — evidence: `../backup/borgmatic/RESTORE.md` records the rehearsal of 2026-07-29
- [x] **Restore rehearsal — closed v0.7.0** and produced the first `ops-proven` stack
      — evidence: `../LIFECYCLE.md` lists one `ops-proven` stack
- [ ] Exercise append-only over a remote repository — the one Borgmatic mechanism
      a local rehearsal cannot establish. Not about owning an off-site target;
      about whether the documented protection behaves as written
- [ ] UrBackup: verify against the gate list in `backup/urbackup/README.md`
- [ ] Verify the nine pending major versions — the list is `../ROADMAP.md` →
      *Verified before the standards moved*; `LIFECYCLE.md` carries each pin beside
      the version last verified
- [ ] Decide the legacy verification stamps, per app — `LIFECYCLE.md` marks them ⚠️
- [x] Verify `monitoring/healthchecks` and `monitoring/uptime-kuma` — done 2026-09-08,
      closed circuit and down/up both on a phone. Evidence: `Last verified` 2026-09-08
      (v4.4) in `../monitoring/healthchecks/UPSTREAM.md`; Uptime Kuma re-verified
      2026-09-13 (2.5.4)
- [ ] Point borgmatic's run monitoring at a real Healthchecks check — the receiver
      exists now; this is what turns the backup timer's silence into an alert.
      `state.md` → *Immediate next steps* lists it first
- [x] Point `monitoring/beszel` and `monitoring/beszel-agent` at a socket proxy —
      done 2026-09-16: `tecnativa/docker-socket-proxy` with `CONTAINERS=1` only
      (`POST=0`, everything else 0), matching what the agent's Docker client
      actually calls (`agent/docker.go` upstream: list, inspect, stats, logs).
      The agent's `network_mode: host` has no Docker network to resolve a
      service name on, so the proxy publishes `127.0.0.1:2375` and the agent's
      `DOCKER_HOST` points there. `docker compose config` validated on both
      stacks. Per-container metrics through the proxy are unverified on a real
      daemon — issue #36 holds that acceptance test open. Evidence: the
      `docker-socket-proxy` service in `../monitoring/beszel/docker-compose.yml`;
      `Last verified` 2026-09-08 in its `UPSTREAM.md`.
- [x] Verify `monitoring/ntfy` — done 2026-09-08: `read_only` holds, a message
      arrived on an iPhone through the public read-only router; a publish burst
      against the rate limit is still unmeasured. Evidence: `Last verified`
      2026-09-08 (v2.28.0) in `../monitoring/ntfy/UPSTREAM.md`
- [ ] Non-root for the monitoring stacks that run as root — Uptime Kuma, the
      Beszel hub, changedetection.io. Each needs a `user:` line and a data
      directory owned by that user; the READMEs now say who runs as what
- [ ] Validate `apps/caldiy` on `v6.2.0-6` — the pin and the documentation moved,
      the verification did not. `UPSTREAM.md` still reads `Last verified: 2026-07-26
      (v6.2.0-3)`, so the stamp is now three fork releases behind the pin. Issue #30
      lists what has to pass: entrypoint against the non-root `node` user, every
      mounted secret readable without widening permissions, database migration,
      `/api/health` and the container healthcheck, login plus one booking, SMTP and
      cron, and a log read for permission or migration errors. Rollback pin is in
      `.env.example`. Still open on 2026-10-15: `UPSTREAM.md` carries the same line;
      the database image moved to 17.11 on a host on 2026-09-13, the application pin
      was not re-verified
- [ ] Finish CrowdSec host-firewall remediation acceptance. Lifecycle, readiness,
      fail-open, restart ordering and the shape of the scoped rules are verified;
      enforcement against real traffic is not. Blocked on one prerequisite: a second
      machine whose traffic the operator controls, reachable both over the management
      network and from the public internet. It gates five tests — the peer-initiated
      management-path adverse test, controlled public IPv4 and IPv6 drops, the
      inbound/mid-session `ct original` case, and the guarded reboot acceptance.
      Sequence and evidence: `core/crowdsec/docs/firewall-bouncer.md` → "Verification
      status"
- [ ] Rehearse the host reserve on a disposable host before it becomes a default.
      The invariant is approved and documented (`docs/architecture.md` → "Workload
      pressure must not consume what recovery needs"); the mechanism is not. The
      rehearsal has to show container workloads in the intended hierarchy with
      management services outside it, controlled container memory pressure reaching
      the container boundary, and the trusted management path, the container runtime,
      logs and the ability to stop the workload all surviving it — plus what happens
      when the reserve is absent. Needs a host that may be lost.
- [ ] Monitoring follow-up for the resilience model: alert on `OOMKilled`, on a
      climbing restart count, on host swap usage and on memory PSI. None of the four
      is covered by the thresholds v0.8.0 verified, and recovery should not depend on
      someone watching a terminal.
- [ ] Boot `apps/_reference/` once to confirm the template actually runs
- [ ] Count the first-load requests for the four photo galleries —
      `apps/photoprism`, `apps/librephotos`, `apps/lycheeorg`, `apps/photoview` —
      and for `apps/it-tools`, a Vue single-page app. All five sit behind
      `limit-standard`, whose burst is 500 per client address since the middleware
      model (200 before it, 50 when this was written), and a thumbnail grid is the
      shape that exceeds it; `apps/immich` needed the bucket of 500 before it became
      the standard. Method in `docs/standards/traefik-security.md` under Rate
      Limits. `core/portainer` was measured on 2026-09-20 and fits `limit-strict`
      (issue #37)
- [x] Seafile's four path-scoped routers — closed 2026-10-22 with the middleware
      model (Phase 4.3): `notification`, `seadoc`, `seadoc-ws` and `thumbnail` in
      both Seafile stacks carry the four positions with `SIDE_TRAEFIK_LIMIT=limit-none`,
      the effective value they had, and the stack's headers profile. Issue #39's
      per-endpoint acceptance test stays the host check for the headers on those
      paths (`core/traefik/docs/middleware-model-migration.md`, section 1.3)
- [ ] `business/openproject` after `internal: true` — whether mail leaves `worker`
      and whether first-run seeding completes without an outbound path. If either
      fails, `worker` and `cron` get a second network, not a removed flag.
      `business/vikunja` carries the same change with only `db` behind it

- [ ] Cloudflare Tunnel with a connector outside Traefik's network — not a shipped
      mode, measured on v0.9.4 in a lab on 2026-10-29. `access-lan` and
      `access-lan-vpn` check the connecting address (`ipAllowList` without
      `ipStrategy`), so a connector with a private address makes every request it
      relays "LAN", including requests from the Internet to a private hostname the
      tunnel routes. The connector is not in `forwardedHeaders.trustedIPs`, so
      CrowdSec sees only the connector and its decisions do not reach the client.
      Open: whether the blueprint names the connector as a trusted proxy, and a
      network rule that keeps the connector off routes it must not reach. Until then
      a tunnel routes only public hostnames
- [ ] After a Docker restart the CrowdSec plugin refused every request for about
      75 seconds, and CrowdSec registered a second bouncer because the bouncer's
      address changed (lab, v0.9.4, 2026-10-29). Whether this is known upstream was
      not checked; document it in `core/crowdsec` or pin the address

## Open decisions for the maintainer

Listed with context in [`state.md`](state.md). Nothing proceeds on these until decided.
The core audit of 2026-10-15 proposes an answer to each as its decision D9.

## Doable without a host

- [x] Fill the `## Backup` section in every stack README — done for every stack
      except `backup/borgmatic`, which is `n/a` by declaration: the backup tool
      cannot describe backing itself up with itself. Coverage is the Backup docs
      column in `LIFECYCLE.md`. Evidence 2026-10-16: that column reads `documented`
      for every stack except `core/host-watchdog` — added 2026-09-18, host-installed —
      and `n/a` for borgmatic
- [x] `backup/urbackup` has no restore section — restoring a *client* backup is a
      real procedure and the one gap left in that column. Done — the README has
      carried a Restore section since 2026-08-18; `LIFECYCLE.md`'s Restore docs
      column shows it
- [x] **`core/traefik` off the 3.6 line.** Done 2026-09-13 — pin is `traefik:v3.7`.
      **The bump has not run on a host.** Original finding: Security support for 3.6 ended 2026-08-16
      and six advisories from 2026-09-07/10 are patched only in 3.7.12 / 3.7.13
      (CVE-2026-88007 critical, 88004 / 88008 / 88009 high). Move `TRAEFIK_IMAGE` to
      `traefik:v3.7`, work through the migration table now in
      [`../core/traefik/UPSTREAM.md`](../core/traefik/UPSTREAM.md), and re-pull — the
      test host ran 3.6.10 against a tag resolving to 3.6.25. Touches the live reverse
      proxy, so it needs a host window. Evidence: `TRAEFIK_IMAGE=traefik:v3.7` in
      `../core/traefik/.env.example`; `Last verified` 2026-09-13 (v3.7.13)
- [x] **`core/dnsmasq` — the image is not receiving fixes.** Done 2026-09-13 — now
      `dockurr/dnsmasq:2.93`. **Not started on a host.** Original finding: `4km3/dnsmasq:2.90-r3` was
      built 2025-11-18 and upstream's last commit is from the same date. Six dnsmasq
      CVEs published in 2026 (CVE-2026-2291 cache poisoning, CVE-2026-4892 DHCPv6 heap
      write to root, CVE-2026-4890, -4893, -5172) were fixed in Alpine's 2.91-r1 on
      2026-05-14. Decide between an image built on current Alpine and replacing the stack.
      Evidence: `APP_TAG=2.93` with the `dockurr/dnsmasq` image in `../core/dnsmasq`
- [x] **Apply the 2026-09-13 sweep.** Done 2026-09-13 — 46 pins. Original scope: 16 stacks sit inside a published advisory range —
      the list and the affected ranges are in
      [`../docs/audits/dependency-sweep-2026-09-13.md`](../docs/audits/dependency-sweep-2026-09-13.md).
      Same-line patches first (`core/portainer` 2.39.7 for CVE-2026-72533 critical,
      `core/authentik` 2026.5.7, `apps/vaultwarden` 1.37.3, `business/zammad` 7.1.3-0012),
      then the ones that cross a major (`apps/adminer` 6.0.2, `apps/homepage` 2.x,
      `apps/librephotos` semver). Evidence: 46 pin lines changed across 42
      `.env.example` files between 2026-09-13 and 2026-09-14; `../CHANGELOG.md` v0.8.1
- [ ] **Make the CrowdSec bouncer key reproducible.** The key is generated once by
      hand with `cscli bouncers add` and lives in the engine's volume. Lose the
      volume and the bouncer is unregistered, while the reverse-proxy middleware
      keeps answering 403 on every route it covers — the failure flags make that the
      safe direction, which is also the direction that looks like an outage.
      `validate.sh` catches an empty key and `runbook.md` documents regenerating one,
      so nothing here is undocumented; it is manual. An idempotent step is not a
      one-liner: `cscli bouncers add` fails on an existing name, so it needs a
      delete-then-add or a parse of `cscli bouncers list -o json`, and it has to work
      without leaving the key in shell history. Design it before writing it
- [x] **Check CrowdSec 1.8.x against this blueprint.** The pin holds at v1.7.8 and
      the reason is in `core/crowdsec/UPSTREAM.md`: the 1.8.0 advisories cover
      datasources this deployment does not configure, and 1.8.0's bot detection
      changes what the WAF serves to clients. One external lab reported 1.8.1
      running. What needs checking here is the challenge and fingerprinting page
      against the routes this repository puts in front of the engine, and whether
      `acquis.yaml` and `appsec.yaml` still parse unchanged. Closed 2026-09-13 by
      decision: the pin holds at `v1.7.8` with the reasons in
      `core/crowdsec/UPSTREAM.md`, and the check named here is the condition for
      revisiting it
- [x] **Gate the CrowdSec integration on a variable in `render.sh`.** Done 2026-09-13:
      `CROWDSEC_BOUNCER_ENABLED`, with the migration in `core/traefik/README.md`.
      The test host was migrated on 2026-09-14 (dry run, semantic diff, live render, no
      restart). Original finding: The README
      enables it by uncommenting blocks in two tracked templates; a `git pull` puts the
      comments back and the next render silently drops the plugin and the middleware
      from `config/` while the container keeps running with both. Seen on a host on
      2026-09-13: templates pristine, rendered files enabled, plugin at a version the
      template no longer names. A `CROWDSEC_BOUNCER_ENABLED` switch that `render.sh`
      honours — emitting the plugin block and the middleware when set — makes the
      rendered state a function of `.env` again. `validate.sh` already refuses an empty
      key once a `crowdsec-*` middleware is present. Evidence:
      `CROWDSEC_BOUNCER_ENABLED` in `../core/traefik/ops/scripts/render.sh`
- [x] **Verify the 2026-09-13 sweep on a host — the stacks that host runs.** Done
      2026-09-13: `core/traefik` 3.6.10 → 3.7.13 with socket-proxy v0.5.0 (preflighted,
      13 routes identical, HTTP/3 answers, bouncer polling), `apps/whoami`,
      `monitoring/uptime-kuma`, `monitoring/changedetection`, `apps/nextcloud` 34.0.4
      (in-place upgrade), `business/invoiceninja` 5.13.40 (migrations), `apps/caldiy`
      database to 17.11. Two stacks failed their first `up -d` on an orphan from the
      earlier service rename — `TROUBLESHOOTING.md` §5.3. Not on that host, still
      unverified: `core/dnsmasq` (new publisher), `apps/homepage` (major with its own
      auth), `apps/librephotos` (tag scheme), and the other 36 pins. Evidence:
      `Last verified` 2026-09-13 in the six stacks' `UPSTREAM.md`; Cal.diY's database
      move is recorded in its `UPSTREAM.md`, the application pin is not re-verified
- [ ] **Verify the 2026-09-13 sweep on a host.** 46 pins moved and nothing was
      deployed, so every bumped stack's `Last verified` line still names the version
      before the bump. Four need more than a restart: `core/dnsmasq` changed publisher
      (`dockurr/dnsmasq` — confirm it answers a wildcard lookup and caches),
      `core/traefik` moved to 3.7 (the migration table in its `UPSTREAM.md` lists what
      changed; `apps/seafile` and `apps/seafile-pro` strip a prefix and 3.7.3 rejects a
      non-normalized result), `apps/homepage` crosses a major that adds its own auth,
      `apps/librephotos` changes tag scheme. Order: Traefik first — everything else is
      behind it
- [x] Three `Based on version` fields named a tag their stack does not pin
      (`core/acme-certs` 3.1.2 vs 0.2.1, `apps/it-tools` a tag absent from the
      registry, `apps/monicahq` `5-apache` vs `4.1.2-apache`). Corrected on
      2026-09-13 (v0.8.1); all three match their pins
- [ ] **`Last verified` missing from `UPSTREAM.md` files** — 27 when this was
      written, 43 on 2026-10-15 after the stacks added since. The sweep reads the
      field first, so a missing one costs a stack its check. The count is the `—`
      entries in `LIFECYCLE.md`'s Last verified column; each closes through S1
      (§2). Candidate for `check-coverage.py`
- [ ] **`apps/vaultwarden` → Docker Secrets.** The blocker recorded in `UPSTREAM.md`
      was wrong: Vaultwarden does support `_FILE`. The real obstacle is that the
      password sits inside `DATABASE_URL`, so the secret must carry the whole URL
      (`DATABASE_URL_FILE`) or an entrypoint must assemble it. Needs a host test —
      it changes how a ✅ stack starts
- [x] `business/invoiceninja` → Docker Secrets via entrypoint wrapper (Phase 2).
      Genuinely upstream-limited: Laravel has no `_FILE` for `APP_KEY`/`DB_PASSWORD`.
      Done — `business/invoiceninja/ops/entrypoint.sh` reads the secrets and exports
      them before handing over to the image's entrypoint, since 2026-07-29
- [ ] Decide the three questions in [`../docs/renovate-proposal.md`](../docs/renovate-proposal.md):
      marker comments vs. normalising 28 outliers · Renovate App vs. self-hosted
      Action · whether `site/` npm rides along. Nothing runs until then. Now D6 in
      [`../docs/audits/core-v1-readiness-2026-10-15.md`](../docs/audits/core-v1-readiness-2026-10-15.md)
- [x] **`docker-compose.local.yml` per stack** — the Local column in
      [`../LIFECYCLE.md`](../LIFECYCLE.md) holds the count. Eight have none,
      because run alone they show nothing: `apps/adminer`, `core/traefik`,
      `core/acme-certs`, `core/dnsmasq`, `core/crowdsec`, `core/hawser`,
      `core/portainer-agent`, `monitoring/beszel-agent`. The rule is in
      `docs/standards/compose-structure.md`; the site's entry point is
      `site/src/content/docs/infrastructure/index.md`, ahead of Traefik. Evidence:
      `../LIFECYCLE.md` — 111 of 121 stacks carry one
- [x] Decide the `TROUBLESHOOTING.md` / `docs/standards/troubleshooting.md` overlap
      — index and method, declared in both files and in the File Map. Evidence:
      [`decisions.md`](decisions.md), 2026-07 · Two troubleshooting documents, one
      entry point; both rows in the File Map of `../docs/maintenance.md`
- [ ] Decide `-f` per HTTP healthcheck. 18 checks across 12 files (counted 2026-10-15) run
      `curl -sS -o /dev/null --max-time 5`, which succeeds on any answer including
      a 5xx — a broken application reports healthy and only a connection error or
      timeout fails the check. The comment blamed redirects; `curl --fail` triggers
      at 400 and above and never on a 3xx, so that reason was wrong and the
      comments are corrected. What each endpoint answers during startup decides
      whether `-f` can go in. `apps/euro-office`, `core/dockhand` and
      `apps/paperless-ngx` already use `curl -fsS`
- [ ] Decide `apps/dify`'s local stack form. It is the one stack with a
      `docker-compose.local.yml` and no `.env.local.example`: the file hardcodes all
      eight image references and reads no variable, and its own header documents a
      start without `--env-file`. Internally consistent, and every pin agrees with
      production, but it is the only deviation from the form in
      `docs/standards/compose-structure.md`. Either give it the companion file or
      state the exception there — `local-pin-drift` covers it under both
- [ ] **W8 research coverage — a standing activity, not a stabilization item.** The system
      is complete: schema, provenance rules, generation, the per-stack marker and the check
      that refuses a stack stating neither a date nor `not yet`. Nothing in the baseline
      waits on this. What continues is reading upstream terms, one stack at a time.
      **The count is generated:** `scripts/ci/sovereignty-report.py` writes it into
      `site/src/data/sovereignty.json`; 36 of 101 was the figure on 2026-09-23.

      **Pages already read that do not answer the question — do not retry these:**
      `apps/onlyoffice` (the Enterprise pricing page prices per user and never compares
      Community; the Docs download page does not compare either), `apps/qdrant` (the pricing
      page describes Cloud tiers, not self-hosted OSS), `business/zammad` (the pricing page
      covers the hosted service and says only that self-hosting runs "on **your** servers"),
      `monitoring/healthchecks` (the self-hosting docs give the licence but no feature
      comparison; the pricing page mentions self-hosting nowhere), `apps/bookstack` (the
      about page mentions support plans and donations and states nothing about editions),
      `apps/velociraptor` (the docs overview calls it open source and says nothing about
      Rapid7 commercial offerings), `business/dolibarr` (the features page returns 404),
      `core/shellhub` (the pricing page lists Cloud, Managed and On Premises with identical
      feature lists and never says what Community omits).

      **A search summary is not a source.** A web search claimed JumpServer gates SSO behind
      Enterprise; the vendor's own comparison page says OIDC, SAML2, OAuth2, LDAP, CAS and
      RADIUS are all in the Community edition. Always read the vendor page the search points
      at rather than the summary of it.

      **Two sweeps are done for every stack and must not be repeated.** They are research
      progress, not a per-stack verdict:

      1. Every recorded licence has been checked against the upstream licence file
         (`gh api repos/<owner>/<repo>/license -q .content | base64 -d`). It found seven
         wrong records, four of them a plain GPL where the file is the Affero GPL.
      2. No remaining repository carries an `ee/`, `enterprise/` or `LICENSE_EE` carve-out
         in its root.

      **Neither is enough to mark a stack checked, and an earlier batch wrongly treated
      them as if they were.** `business/matomo` is the standing counterexample: its licence
      is plain GPL-3.0, its repository has no enterprise directory, and SAML single sign-on
      is still sold as a separate plugin under the InnoCraft EULA. Gating lives wherever the
      vendor puts it, which is often a marketplace, a pricing page or a docs page and not
      the source tree. A date may only be set once a source has actually been read that
      speaks to edition gating and the commercial model — not merely to the licence.

      The two exceptions that legitimately need no vendor source: `core/host-watchdog`,
      which is first-party to this repository so no upstream can gate it, and
      `apps/nextcloud`, whose Enterprise page was read and sells support, early patches,
      SLAs and branding rather than gating SSO, LDAP or audit logging.
- [ ] Resolve `apps/hemmelig`'s licence — two upstream sources disagree. The README states
      an "O'Saasy License Agreement — Copyright © 2025 ... a modified MIT license that
      prohibits using the software to compete with the original licensor as a hosted SaaS
      product", while `LICENSE` on `main` is the unmodified MIT text with a 2021 copyright
      line and no SaaS, competition or branding clause. This repository records the README's
      version, and `license_class: source-available` rests on it. Nothing was recorded as a
      use restriction because neither source can be relied on while they disagree; ask
      upstream which governs.
- [ ] Source `core/infisical`'s edition gating. Its `LICENSE` places content under any
      `ee/` directory under a separate licence, which is recorded, but the docs page that
      would name the gated features returns 404. The feature list needs a reachable source
      before it can be stated.
- [ ] Decide `apps/collabora`'s entry. CODE is widely described as carrying a
      concurrent-connection and document limit, but the upstream page that would state it is
      behind bot protection and the product page does not mention one. Nothing was recorded
      rather than record it from memory.
- [ ] Keep the Tailscale range out of `access-lan`. `fd7a:115c:a1e0::/48` lies inside
      `fc00::/7`, so on a dual-stack install `access-lan` admits a tailnet client over
      IPv6 — recorded as a known limitation in
      [`../docs/standards/traefik-security.md`](../docs/standards/traefik-security.md),
      "Access Policies". `ipAllowList` has no exclusion; the ULA range would have to be
      listed in parts around the Tailscale range, which `TAILSCALE_CIDR_V6` can change.
      Decide the shape, then a test that `access-lan` refuses a tailnet address
