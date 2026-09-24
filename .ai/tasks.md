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
- [x] Upstream requests, filed by the maintainer; drafts are in the local
      `inbox/upstream-requests/` working area. Filed and linked where the rule says
      — the stack's `UPSTREAM.md` where one exists, the candidate evaluation
      otherwise: the FacturaScripts installer fix NeoRazorX/facturascripts#2041 ·
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
      holds one whole first load and both ship it, measured without a `429` ·
      ERPNext's realtime service — a second nginx listener for `/socket.io` gives
      its session check an address it can reach from `app-internal` · Akaunting —
      the stack stays, and the runtime gate is a decision fact in its
      `../business/akaunting/UPSTREAM.md`: every `…/create` page asks
      `api.akaunting.com` for the plan limits with an akaunting.com account's API
      key, and the code has no switch to skip it.
- [ ] Still open from that session: rclone-web's sign-in — `/login?url=…` applies
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

- [ ] Batches H–V, each its own pull request, in this order:
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
      Which of them have landed is in [`../CHANGELOG.md`](../CHANGELOG.md).
      Each stack ships `scaffolded` — verified on its image, not yet behind
      Traefik.
- [ ] Build candidates — Live Helper Chat, DayOtter, Bareos: ask upstream to
      publish an image first; otherwise a fork and an image built here under
      `../docs/standards/custom-application.md`.
- [ ] paperless-ai: revisit once upstream's announced rewrite is released or the
      repository is maintained again — its README says it is not.
- [ ] `backup/borgmatic/README.md` counts database engines as "24 · 16 · 13
      stacks" for PostgreSQL · MySQL · MariaDB. Counting `image:` lines by stack
      on 2026-09-23 gives 27 · 3 · 15; the MySQL figure is far enough apart that
      the table is counting something else. Establish the rule, then correct the
      table or state the rule beside it.
