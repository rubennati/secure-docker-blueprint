# Host session — plan and backlog

The working plan for taking stacks from "configured" to "verified in production
use", and the backlog this session produced. One place to tick things off.

Findings that need a decision before they can be worked on live in
[`host-session-findings.md`](host-session-findings.md); this file is what happens
next.

**Status keys:** `[ ]` open · `[x]` done · `[~]` in progress · `[?]` needs a
decision from the maintainer.

---

## Rules established this session

These are binding from now on and are written where they belong, not only here.

1. **Pin the newest version the project recommends for production.**
   Not the newest that exists, not one behind for comfort. Check the end-of-life
   date before pinning. → `docs/standards/env-structure.md`
2. **Every stack starts restricted.** `acc-tailscale` (or another network-level
   restriction) is the shipped default. Switching to `acc-public` is a deliberate
   manual edit after the app is configured, verified and stable.
3. **Unattended installation beats a setup wizard.** Where an image can install
   itself from environment variables and secrets, that is the path — it is
   repeatable, reviewable, and it removes the window in which an unauthenticated
   setup form is reachable.
4. **Best-practice defaults belong in `.env.example`**, not only in the README.
   The file someone copies is the file that must carry the guidance.
5. **Write for a reader with no context.** No history, no justification of past
   decisions, no self-description. State what to set, what can be chosen, and
   link the official source. Reasoning goes to `docs/architecture.md`,
   `UPSTREAM.md`, `CHANGELOG.md` or `docs/bugfixes/` — never into a
   `.env.example`. → `docs/standards/documentation-workflow.md`
6. **Performance is part of the definition of done.** A stack that is secure and
   slow is not finished. Tuning values come from the project's own
   recommendations, and the minimum requirements are stated so a machine can be
   sized before deployment.
7. **Every app gets its proxy configuration reviewed, not inherited.** Access
   policy, security chain and TLS profile are checked against what the app
   actually needs and verified against its own diagnostics. The proxy is there to
   make an app safe *and* fast; where it makes one slow or broken, the proxy is
   what changes.
8. **Link the official sources.** Every operator-facing page carries links to the
   project's own documentation and to the registry page for the pinned image, so
   a reader can go deeper without asking.

---

## Phase A — Nextcloud, production-grade

The reference case: it is needed for a real deployment, and it exercises the
hardest patterns. What comes out of it becomes the template for every app after.

- [x] Version decided: newest recommended for production, EOL recorded
- [x] Container self-resolution — the instance reaches itself through the proxy
- [x] Outbound access decided and documented — narrow egress for `app` and `cron`
- [x] Rebuilt on that version from an empty volume
- [x] Unattended install via `NEXTCLOUD_ADMIN_USER_FILE` / `_PASSWORD_FILE` — no wizard
- [x] Redis password moved from the environment into a secret — one source
- [x] `acc-tailscale` as the shipped default in `.env.example`
- [x] Hardening via `occ` before first login — applied, sourced from the admin manual
- [x] Minimal app set — telemetry and UI-noise apps disabled `[?]` federation still open
- [x] Preview generation bounded to 2048px / 25 MB
- [x] Skeleton files disabled for new users
- [x] **Admin overview free of warnings** — 60 checks pass, 0 warnings, 0 errors.
      Twelve were shown after the first clean install
- [x] **SMTP is not optional.** Password reset does not work without it. Settings
      and the secret are in `.env.example`, the transport choice is explained, and
      delivery was confirmed end to end — four test messages sent with `occ
      user:welcome`, all four received
- [x] **PHP and container tuning to documented values.** `pm.max_children` now
      follows Nextcloud's own formula against a measured worker size — 65–107 MB,
      not the 200–300 MB the file asserted — giving 32 rather than 10. OPcache
      needed nothing: the official image already ships the recommended settings,
      verified on the instance
- [x] **Minimum requirements stated.** Upstream's per-process figures, plus what
      this stack measured idle, translated into a machine an operator can order
- [x] **The healthcheck was logging two errors every 30 seconds.** `occ` ran as
      root, which cannot read the two group-readable secrets, so the instance
      reported errors in its own log — 2880 entries a day. Now runs as the web
      user
- [x] **The database now runs the recommended version.** 10.11 → 11.8 on the
      live instance: row counts unchanged, `CHECK TABLE` clean, no configuration
      change needed. Removed `--innodb-file-per-table`, deprecated in 11.8 and
      the default since 5.6
- [ ] Two-factor: providers are available but not enforced — decide
- [ ] Rate limits checked against real usage — the app must not stall behind them
- [ ] Desktop and mobile client connect and sync
- [x] CrowdSec integrated at a basic level and confirmed to see the traffic —
      engine deployed, acquisition parsing cleanly, scenarios firing. Confirmed
      it also cannot see traffic a network restriction rejects: 120 requests,
      3 log lines (finding 25)
- [ ] Record `Supported until` in `UPSTREAM.md`
- [ ] Site: an operator-facing Nextcloud page — setup, the `occ` commands that
      matter, what to check after, with links to the official documentation and
      the registry page for the pinned image
- [ ] Status to ✅ once every point above is verified, not before

### Still open on this instance

- [x] `.well-known/caldav` — resolved. The stack's own nginx configuration
      already issued the documented 301; a Traefik middleware rewrote the path
      before nginx saw it, so the redirect never fired. Middleware removed
- [ ] Redirect goes out relative and arrives as `http://` before Traefik lifts it
      to `https://` — one extra hop, correct result. Worth tidying
- [x] SMTP — configured and delivering. `ssl` on 465 is the documented default,
      587 the fallback where the host blocks it (finding 18)
- [ ] Two-factor available but not enforced — decide whether the blueprint
      enforces it
- [ ] Server ID unset — only relevant across multiple PHP servers; decide and
      record
- [ ] AppAPI deploy daemon unset — needed only for external apps; likely out of
      scope, state it
- [ ] Admin surface: can `/settings/admin` be restricted separately, to VPN or an
      allowlist, while the rest stays reachable? A path-scoped router with its own
      access policy is the mechanism the repository already uses. Evaluate, and
      compare against putting Authentik in front

## Phase A2 — Traefik as a first-class part of every app

Traefik was designed before the apps it now carries. The naming and the levels were
reasoned about in the abstract; several turned out not to fit once a real app was
verified against them. Treat it as a component that keeps being adjusted, not as
settled ground.

- [x] `sec-3e-spa` added — the combination Nextcloud needs did not exist
- [x] Corrected the claim that SPA rate limits belong behind a VPN only. `rl-soft`
      and `rl-spa` share the same sustained rate; only the burst differs, so the
      restriction bought 429s in normal use and no protection
- [ ] **Rename for comprehension.** `sec-1e`, `rl-spa`, `hdr-strict-embed` mean
      nothing to someone arriving. Names should say what they do — a reader should
      not have to open the template to find out what they picked
- [ ] **Make the axes explicit.** Header strictness, frame policy and rate limit
      are independent; the current names bundle them, which is why 10 of 16
      combinations exist and the missing one was the one needed
- [ ] **TLS profiles per app.** `tls-basic`, `tls-aplus`, `tls-modern` are assigned
      by habit. Check what each app's clients actually support — a password
      manager and a mobile sync client have different floors
- [ ] **Review every app's proxy settings** against its own diagnostics, the way
      Nextcloud was. Record the result per app
- [ ] **The render workflow.** Configuration is generated by a script, and adding
      a zone or a chain means editing a template and re-rendering, which silently
      discards hand edits. Automate it or make the failure loud
- [x] **The threat axis exists as a variable.** `APP_TRAEFIK_THREAT`, prepended
      to the middleware list, empty by default — the three axes in
      `profiles.md` are now expressible on a router (finding 26)
- [ ] Roll `APP_TRAEFIK_THREAT` out to the remaining stacks as each is reviewed
- [ ] **Prove the egress claims on the wire, when monitoring is deployed.**
      Reading source establishes that a call exists; it cannot establish that
      none does. gatus and healthchecks are recorded as *not currently known
      to* rather than *does not*. Attach the stack to a default-deny egress
      network and read the refusals for 48 h — long enough to catch Uptime
      Kuma's interval
- [?] **The community blocklist is a two-way arrangement, on by default.**
      15,880 addresses arrive; this host's own detections leave. Not the request
      content — `context` is off. Worth it by the numbers (14 hours of local
      detection produced two genuine findings), and CrowdSec is EU-based, but it
      is a data flow that should be decided rather than inherited
- [ ] **A dropped packet leaves no trace.** `cscli decisions list --ip` is the
      only way to answer "the site does not load for me", and it belongs at the
      start of that conversation. Written into the README and the site; it also
      belongs in an operating runbook once one exists
- [x] **CrowdSec Phase 3 in place.** Firewall bouncer installed with safe_range
      set before first start; a decision reaches the kernel in ~15s and clears in
      ~10s, both address families. It inherited ~15,880 community decisions that
      had been collected but never enforced, plus one locally detected scanner
      (finding 30)
- [x] **CrowdSec verified end to end.** Engine, bouncer, a real ban producing
      403 for an external client, and AppSec blocking a CVE signature. Two
      defects found on the way: the AppSec config was mounted where the engine
      never reads it, and the middleware label had no slot for the threat axis
      (findings 26–28)
- [ ] Correct the AppSec documentation: it is virtual patching, not a WAF, and
      the deferral of `crowdsec-appsec` over false positives overstates the risk
- [ ] Neither Traefik nor CrowdSec may be the reason an app is slow. Where they
      are, they change

## Phase B — Backup chain on Nextcloud

Closes v0.7.0. The proof is a restore, not a configuration.

- [x] Borgmatic configured against the running stack with the database hook
- [x] Maintenance mode around the file capture — the one stack where it matters.
      The error hook was proven by two failed runs: the instance came back out of
      maintenance mode both times
- [x] First backup, verified to contain what it claims — 27,840 files,
      912 MB → 440 MB, the dump complete to its closing line
- [x] **Restore into a scratch location, content checked** — the milestone.
      131 tables and the file index into a throwaway container; `config.php`
      byte-identical to the live one apart from the maintenance flag
- [x] Scoping proven against a second, unrelated deployment on the same host
- [x] The upgrade rehearsal: backup → major upgrade → verified. MariaDB 10.11 to
      11.8 with an archive taken first; the restore path was exercised separately
      rather than by rolling this one back
- [ ] Retention tied to a stated recovery objective
- [ ] Run monitoring reporting somewhere it will be noticed
- [ ] An SSH target and append-only — the local repository proved the mechanism,
      not the off-site half
- [~] Site: backup and restore from the operator's point of view

## Phase C — Operating documentation

- [ ] The `occ` commands an operator needs, with what each is for
- [ ] Update versus upgrade: what differs, what to do before each
- [ ] Maintenance window — what actually needs doing, and how often
- [ ] Incident response: what to check first, in what order
- [ ] Split cleanly — repository keeps the reasoning, site carries the procedure

## Phase D — Maturity model

Deliberately after A–C. A model written before the first case describes wishes.

- [ ] Minimum every stack must meet to be in the blueprint at all
- [ ] A higher tier for stacks holding confidential data
- [ ] Where backup, monitoring and access control sit in each tier
- [ ] `Supported until` as a tracked field, since nothing notices EOL today
- [ ] Position the existing stacks in the model honestly

## Phase E — The next applications

- [ ] Invoice Ninja — needed for a live deployment, on a host that already runs
      the reverse proxy and CrowdSec
- [ ] Ghost
- [ ] Each following the pattern from A–C rather than reinventing it

---

## Backlog from this session

Grouped by what it takes to resolve. Detail for each is in
[`host-session-findings.md`](host-session-findings.md).

### Fix while the context is fresh

- [x] Nextcloud: root-owned files — dissolved, the unattended install never creates them (finding 12)
- [x] Nextcloud: SQLite trap — dissolved, there is no wizard to offer it (finding 16)
- [x] Nextcloud: exposure of the setup form — dissolved on both counts (finding 15)
- [x] Borgmatic install instruction yields a version too old for the feature the
      architecture depends on (finding 5) — README now checks the packaged
      version first and installs via pipx into `/usr/local/bin`
- [ ] Database collation is `utf8mb4_general_ci`; upstream documents
      `utf8mb4_bin`

### Needs a decision first

- [?] Dual-stack: make it the default, or keep it opt-in with a louder warning
      (finding 1)
- [?] `acc-public` paired with `sec-3-spa` contradicts the security-chain rule —
      one of the two has to give (finding 13)
- [?] Denied requests produce no access-log line, so CrowdSec cannot see probes
      against protected endpoints. Needs upstream research before it can be
      called a defect (finding 2)
- [?] Dependency automation — three questions in
      [`renovate-proposal.md`](renovate-proposal.md)
- [?] `core/` composition: three document servers fail the repository's own test
      for what belongs there
- [?] The six open decisions in `.ai/state.md`

### Smaller, mechanical

- [x] Access-log buffer reduced from 100 to 0 (finding 3)
- [x] Logrotate: `maxsize 100M` added to the shipped config, with the point that
      makes it meaningful — the conditions are only evaluated when logrotate
      runs, daily on Debian. Installed and dry-run on a host (finding 4)
- [ ] dnsmasq template overwrites hand-added zones on re-render (finding 6)
- [ ] Dashboard requests its own certificate although the wildcard covers it
      (finding 7)
- [ ] `excludedIPs` warning next to the access policies (finding 8)
- [ ] Startup ordering against a VPN dependency, as a troubleshooting entry
      (finding 9)
- [ ] Syslog fallback for backup failures (finding 10)
- [ ] Non-standard backup targets: port and remote-path options (finding 11)
- [ ] Stale artefacts from an earlier deployment block a fresh one — no guidance
      exists for deploying alongside one (finding 14)
- [ ] `docker-compose.local.yml` for every stack — 6 of 57 have one
- [x] Secret rotation replaces the file's identity and the mount keeps the old
      one; every stack mounting a secret as a single file is affected. Written up
      in `docs/standards/compose-structure.md` alongside the `uid`/`mode` trap
      (finding 17)

### Repository-wide, carried from before this session

- [ ] Add `Checker coverage`, `Docs QA` and `Workflow supply chain` to the
      required checks in branch protection
- [ ] `backup/urbackup` has no restore section
- [ ] Vaultwarden and Invoice Ninja still hold their database password in `.env`
- [ ] Markdown lint is in place; the v1.0 CI baseline is otherwise complete

---

## How this list is worked

Recording during, deciding after. Fixing mid-session biases toward whatever was
annoying at the time, and it makes the cause of the next failure ambiguous.

Each item is closed by evidence, not by intent: a check that passes, a page that
loads, a restore whose content was read. `[x]` means it was seen working.
