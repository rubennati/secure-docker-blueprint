# Tasks

Current work items. Larger direction lives in [`../ROADMAP.md`](../ROADMAP.md);
this file is the short list.

## Blocked on a host

v0.8.0 closed on 2026-09-08 — the record is
[`../docs/host-session-v0.8.0.md`](../docs/host-session-v0.8.0.md); what v0.7.0's
session left open is in
[`../docs/host-session-v0.7.0.md`](../docs/host-session-v0.7.0.md)

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
- [ ] Point `monitoring/beszel` and `monitoring/beszel-agent` at a socket proxy — the
      hub stack was verified as shipped on 2026-09-08, the proxy variant was not. Upstream supports `DOCKER_HOST`, and documents a proxy with
      `CONTAINERS=1` as the safer setup — so the exception's old claim that Beszel
      has no proxy support was wrong. The agent runs in host network mode, so the
      proxy binds `127.0.0.1:2375`. Until then the agent holds the full Docker API,
      which is root on the host; `:ro` on the socket does not change that
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
- [ ] Count the first-load requests for the four photo galleries — `apps/photoprism`,
      `apps/librephotos`, `apps/lycheeorg`, `apps/photoview`. All four sit at `sec-2`,
      whose `rl-soft` allows a burst of 50 per client address, and a thumbnail grid
      is the shape that exceeds it. `apps/immich` already needed `sec-2-spa` for the
      same reason. The method is in `docs/standards/traefik-security.md` under
      Choosing the level for an app; above 50 the answer is the `-spa` variant, which
      leaves the sustained rate untouched. `apps/it-tools` is the same question — a
      Vue single-page app at `sec-3`, never counted. `core/portainer` first: it runs
      `sec-4`, whose burst is 40, and its interface is a single-page app. Load it
      once with an empty cache and read the request count
- [ ] Decide `APP_TRAEFIK_SECURITY` for Seafile's four path-scoped routers.
      They carry the access policy; the chain is deliberately absent until an
      instance shows what it survives. `/sdoc-server` is the open one — `sec-2`
      sets `frameDeny` and upstream documents neither the header nor whether
      SeaDoc is framed, so it is `sec-2` or `sec-2e` and only a running editor
      answers it. `/socket.io` and `/notification` are WebSockets and
      `/thumbnail` issues many parallel requests, all against `rl-soft`
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
- [ ] Add `Checker coverage`, `Docs QA` and `Workflow supply chain` to the required
      checks in branch protection — all three run, but nothing blocks on them yet
- [ ] Decide `-f` per HTTP healthcheck. 19 checks across 17 files run
      `curl -sS -o /dev/null --max-time 5`, which succeeds on any answer including
      a 5xx — a broken application reports healthy and only a connection error or
      timeout fails the check. The comment blamed redirects; `curl --fail` triggers
      at 400 and above and never on a 3xx, so that reason was wrong and the
      comments are corrected. What each endpoint answers during startup decides
      whether `-f` can go in. `core/euro-office`, `core/dockhand` and
      `apps/paperless-ngx` already use `curl -fsS`
