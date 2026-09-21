# Tasks

Current work items. Larger direction lives in [`../ROADMAP.md`](../ROADMAP.md);
this file is the short list.

## Open after v0.9.1

State at the v0.9.1 tag (2026-09-19): `dev` and `main` level, no open pull requests,
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
      `APP_TRAEFIK_ACCESS=acc-public`.
- [ ] Trivy gate: block only on CRITICAL findings absent from the recorded facts.
- [ ] Catalogue page: show the facts (counts, fix available, age, licence limits) in
      neutral wording; no judgement of the project.
- [ ] For OpenSign and Uptime Kuma: check whether upstream has published a newer image;
      if so bump the pin (normal upgrade), if not record the facts.

### 2. Host verification of the scaffolded stacks (audit S1)

[`../docs/host-session-priority-1.md`](../docs/host-session-priority-1.md) is the ordered
run: Traefik with TLS, a refused client, restart, restore, and each stack's own open
items. Needs a host; nothing in the 26 new stacks has one. Until then they stay
`scaffolded`.

### 3. Personal data on the public site (audit W7 / D3)

A decision, with a possible v1.0 impact — see [`decisions.md`](decisions.md) and
`../ROADMAP.md`. Not decided.

### 4. Operator site

- [ ] The catalogue is live and lists all 89 stacks; only stacks with a guide appear in
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

### 6. Fifteen proposed products — evaluated 2026-09-21

Full evidence per product in
[`../docs/audits/candidate-evaluation-2026-09-21.md`](../docs/audits/candidate-evaluation-2026-09-21.md):
what each publishes, where its compose actually lives, the licence splits, and what
was verified by running it. Three of the fifteen already ship.

- [ ] Eleven products have a version-tagged image and can be written as stacks, in
      six batches (A calrs+Calnode · B SolidInvoice+FacturaScripts+Akaunting ·
      C Twenty+Chatwoot · D CISO Assistant+DefectDojo · E obot · F ERPNext).
      Batch A shipped (#140). Batch B: Akaunting and SolidInvoice shipped,
      FacturaScripts held (#145). Batch C: Twenty and Chatwoot shipped — see the
      evaluation's *Findings from implementation*.
- [ ] Four publish no image (DayOtter, Dapta Calendars, MAILFLOW-AI, Crater) and
      stay evaluation entries. Proposed: ask DayOtter's maintainer to publish a tag;
      record the other three with the reason. No fork is proposed.
- [ ] Adding these while `../ROADMAP.md` holds applications is a deliberate
      exception and needs recording where the hold is stated.

### 7. Held: Priority 2 and other candidates

No application is added while the v1.0 items are open — S1 (verification), C1
(above) and D3. Candidates are in `../ROADMAP.md` under "On hold": the per-category
planned lists, Plane / Leantime / AppFlowy, Suricata, Coraza. The AI candidates that were
held are shipped.

### 8. Milestone v0.10.0 — measured resource limits

Every `✅` stack's limits from a measurement on a real install
([`../docs/resource-measurement.md`](../docs/resource-measurement.md)). Needs a host.

### 9. Small items

- Vikunja's `.env.example` carries `smtp-relay.brevo.com` as the mailer host with the
  mailer disabled — a vendor value where the convention is `example.com` or empty.
- The five AI stacks and Dify/Langfuse have no restore procedure performed; the READMEs
  document one.
- The Trivy scan does not cover images built locally (Cal.diY, the vikunja layer).

---

## Blocked on a host

v0.8.0 closed on 2026-09-08 — the record is
[`../docs/host-session-v0.8.0.md`](../docs/host-session-v0.8.0.md); what v0.7.0's
session left open is in
[`../docs/host-session-v0.7.0.md`](../docs/host-session-v0.7.0.md)

- [ ] Verify the Priority 1 stacks behind Traefik with TLS and restore each —
      [`../docs/host-session-priority-1.md`](../docs/host-session-priority-1.md).
      Until then they stay `scaffolded`.

- [x] Borgmatic: install, initialise repository, first backup, export the key off-host
- [x] **Restore rehearsal — closed v0.7.0** and produced the first `ops-proven` stack
- [ ] Exercise append-only over a remote repository — the one Borgmatic mechanism
      a local rehearsal cannot establish. Not about owning an off-site target;
      about whether the documented protection behaves as written
- [ ] UrBackup: verify against the gate list in `backup/urbackup/README.md`
- [ ] Verify the nine pending major versions
- [ ] Decide the legacy verification stamps, per app — `LIFECYCLE.md` marks them ⚠️
- [x] Verify `monitoring/healthchecks` and `monitoring/uptime-kuma` — done 2026-09-08,
      closed circuit and down/up both on a phone
- [ ] Point borgmatic's run monitoring at a real Healthchecks check — the receiver
      exists now; this is what turns the backup timer's silence into an alert
- [x] Point `monitoring/beszel` and `monitoring/beszel-agent` at a socket proxy —
      done 2026-09-16: `tecnativa/docker-socket-proxy` with `CONTAINERS=1` only
      (`POST=0`, everything else 0), matching what the agent's Docker client
      actually calls (`agent/docker.go` upstream: list, inspect, stats, logs).
      The agent's `network_mode: host` has no Docker network to resolve a
      service name on, so the proxy publishes `127.0.0.1:2375` and the agent's
      `DOCKER_HOST` points there. `docker compose config` validated on both
      stacks. Per-container metrics through the proxy are unverified on a real
      daemon — issue #36 holds that acceptance test open.
- [x] Verify `monitoring/ntfy` — done 2026-09-08: `read_only` holds, a message
      arrived on an iPhone through the public read-only router; a publish burst
      against the rate limit is still unmeasured
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
      `.env.example`
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
      and for `apps/it-tools`, a Vue single-page app at `sec-3`. All five sit
      behind `rl-soft`, whose burst is 50 per client address, and a thumbnail
      grid is the shape that exceeds it; `apps/immich` already needed
      `sec-2-spa` for the same reason. Method in
      `docs/standards/traefik-security.md` under Choosing the level for an app.
      `core/portainer` is the same measurement and is tracked as issue #37
- [ ] Decide `APP_TRAEFIK_SECURITY` for Seafile's four path-scoped routers —
      issue #39 carries the per-endpoint acceptance test
- [ ] `business/openproject` after `internal: true` — whether mail leaves `worker`
      and whether first-run seeding completes without an outbound path. If either
      fails, `worker` and `cron` get a second network, not a removed flag.
      `business/vikunja` carries the same change with only `db` behind it

## Open decisions for the maintainer

Listed with context in [`state.md`](state.md). Nothing proceeds on these until decided.

## Doable without a host

- [x] Fill the `## Backup` section in every stack README — done for every stack
      except `backup/borgmatic`, which is `n/a` by declaration: the backup tool
      cannot describe backing itself up with itself. Coverage is the Backup docs
      column in `LIFECYCLE.md`
- [ ] `backup/urbackup` has no restore section — restoring a *client* backup is a
      real procedure and the one gap left in that column
- [x] **`core/traefik` off the 3.6 line.** Done 2026-09-13 — pin is `traefik:v3.7`.
      **The bump has not run on a host.** Original finding: Security support for 3.6 ended 2026-08-16
      and six advisories from 2026-09-07/10 are patched only in 3.7.12 / 3.7.13
      (CVE-2026-88007 critical, 88004 / 88008 / 88009 high). Move `TRAEFIK_IMAGE` to
      `traefik:v3.7`, work through the migration table now in
      [`../core/traefik/UPSTREAM.md`](../core/traefik/UPSTREAM.md), and re-pull — the
      test host ran 3.6.10 against a tag resolving to 3.6.25. Touches the live reverse
      proxy, so it needs a host window
- [x] **`core/dnsmasq` — the image is not receiving fixes.** Done 2026-09-13 — now
      `dockurr/dnsmasq:2.93`. **Not started on a host.** Original finding: `4km3/dnsmasq:2.90-r3` was
      built 2025-11-18 and upstream's last commit is from the same date. Six dnsmasq
      CVEs published in 2026 (CVE-2026-2291 cache poisoning, CVE-2026-4892 DHCPv6 heap
      write to root, CVE-2026-4890, -4893, -5172) were fixed in Alpine's 2.91-r1 on
      2026-05-14. Decide between an image built on current Alpine and replacing the stack
- [x] **Apply the 2026-09-13 sweep.** Done 2026-09-13 — 46 pins. Original scope: 16 stacks sit inside a published advisory range —
      the list and the affected ranges are in
      [`../docs/audits/dependency-sweep-2026-09-13.md`](../docs/audits/dependency-sweep-2026-09-13.md).
      Same-line patches first (`core/portainer` 2.39.7 for CVE-2026-72533 critical,
      `core/authentik` 2026.5.7, `apps/vaultwarden` 1.37.3, `business/zammad` 7.1.3-0012),
      then the ones that cross a major (`apps/adminer` 6.0.2, `apps/homepage` 2.x,
      `apps/librephotos` semver)
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
- [ ] **Check CrowdSec 1.8.x against this blueprint.** The pin holds at v1.7.8 and
      the reason is in `core/crowdsec/UPSTREAM.md`: the 1.8.0 advisories cover
      datasources this deployment does not configure, and 1.8.0's bot detection
      changes what the WAF serves to clients. One external lab reported 1.8.1
      running. What needs checking here is the challenge and fingerprinting page
      against the routes this repository puts in front of the engine, and whether
      `acquis.yaml` and `appsec.yaml` still parse unchanged
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
      key once a `crowdsec-*` middleware is present
- [x] **Verify the 2026-09-13 sweep on a host — the stacks that host runs.** Done
      2026-09-13: `core/traefik` 3.6.10 → 3.7.13 with socket-proxy v0.5.0 (preflighted,
      13 routes identical, HTTP/3 answers, bouncer polling), `apps/whoami`,
      `monitoring/uptime-kuma`, `monitoring/changedetection`, `apps/nextcloud` 34.0.4
      (in-place upgrade), `business/invoiceninja` 5.13.40 (migrations), `apps/caldiy`
      database to 17.11. Two stacks failed their first `up -d` on an orphan from the
      earlier service rename — `TROUBLESHOOTING.md` §5.3. Not on that host, still
      unverified: `core/dnsmasq` (new publisher), `apps/homepage` (major with its own
      auth), `apps/librephotos` (tag scheme), and the other 36 pins
- [ ] **Verify the 2026-09-13 sweep on a host.** 46 pins moved and nothing was
      deployed, so every bumped stack's `Last verified` line still names the version
      before the bump. Four need more than a restart: `core/dnsmasq` changed publisher
      (`dockurr/dnsmasq` — confirm it answers a wildcard lookup and caches),
      `core/traefik` moved to 3.7 (the migration table in its `UPSTREAM.md` lists what
      changed; `apps/seafile` and `apps/seafile-pro` strip a prefix and 3.7.3 rejects a
      non-normalized result), `apps/homepage` crosses a major that adds its own auth,
      `apps/librephotos` changes tag scheme. Order: Traefik first — everything else is
      behind it
- [ ] **`Last verified` missing from 27 `UPSTREAM.md` files**, and three `Based on
      version` fields name a tag their stack does not pin (`core/acme-certs` 3.1.2 vs
      0.2.1, `apps/it-tools` a tag absent from the registry, `apps/monicahq` `5-apache`
      vs `4.1.2-apache`). The sweep reads these fields first, so a wrong one costs a
      stack its check. Candidate for `check-coverage.py`
- [ ] **`apps/vaultwarden` → Docker Secrets.** The blocker recorded in `UPSTREAM.md`
      was wrong: Vaultwarden does support `_FILE`. The real obstacle is that the
      password sits inside `DATABASE_URL`, so the secret must carry the whole URL
      (`DATABASE_URL_FILE`) or an entrypoint must assemble it. Needs a host test —
      it changes how a ✅ stack starts
- [ ] `business/invoiceninja` → Docker Secrets via entrypoint wrapper (Phase 2).
      Genuinely upstream-limited: Laravel has no `_FILE` for `APP_KEY`/`DB_PASSWORD`
- [ ] Decide the three questions in [`../docs/renovate-proposal.md`](../docs/renovate-proposal.md):
      marker comments vs. normalising 28 outliers · Renovate App vs. self-hosted
      Action · whether `site/` npm rides along. Nothing runs until then
- [x] **`docker-compose.local.yml` per stack** — the Local column in
      [`../LIFECYCLE.md`](../LIFECYCLE.md) holds the count. Eight have none,
      because run alone they show nothing: `apps/adminer`, `core/traefik`,
      `core/acme-certs`, `core/dnsmasq`, `core/crowdsec`, `core/hawser`,
      `core/portainer-agent`, `monitoring/beszel-agent`. The rule is in
      `docs/standards/compose-structure.md`; the site's entry point is
      `site/src/content/docs/infrastructure/index.md`, ahead of Traefik
- [x] Decide the `TROUBLESHOOTING.md` / `docs/standards/troubleshooting.md` overlap
      — index and method, declared in both files and in the File Map
- [ ] Decide `-f` per HTTP healthcheck. 19 checks across 17 files run
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
- [ ] Continue W8 until every stack states a research date rather than `not yet`.
      **24 of 95 are researched — 22 with facts, 2 checked and clear — and 71 remain.**

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
