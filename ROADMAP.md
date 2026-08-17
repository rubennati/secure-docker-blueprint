# Roadmap

Direction reviewed 2026-07-31.

What remains to be built, what blocks it, and what proves it finished. Shipped
work belongs to [`CHANGELOG.md`](CHANGELOG.md), per-stack status to the tables in
[`README.md`](README.md) and the generated [`LIFECYCLE.md`](LIFECYCLE.md), and
per-category detail to the `README.md` in each top-level directory.

---

## Direction

Pre-1.0 tags are set when a natural milestone is reached, not on a fixed cadence. The single criterion for v1.0 is: **could someone fork this and run it without needing my mental model?** — subjective but unambiguous when met.

### v0.8.0 — Monitoring

Backup tells you what to do when something breaks. Monitoring tells you that something broke — and ideally before it causes data loss or downtime.

Six services are already in place, spanning the axes described in [`monitoring/README.md`](monitoring/README.md). The milestone is reached when each axis has **one verified service** — not when all six are verified, and not one axis per operator:

| Axis | In place | Verified for the milestone |
|---|---|---|
| Host & container metrics | Beszel + agent | Beszel |
| Uptime & endpoints | Uptime Kuma, Gatus | either one — they are a preference pair, not a hierarchy |
| Scheduled-job liveness | Healthchecks | Healthchecks — also the receiver for backup run monitoring |
| Content change | changedetection.io | changedetection.io |
| Disk health | *(Scrutiny planned)* | out of scope — needs physical-disk passthrough |
| **Alerting** | notification integrations in the services above, plus `monitoring/ntfy` as a receiver | at least one channel proven to actually arrive |

**Alerting is the cross-cutting layer, not a fifth service.** It is delivered by the services above rather than by a separate tool, and it is the one thing that turns a dashboard nobody watches into monitoring. A notification path that has never fired is worth as little as a backup that has never been restored.

Log aggregation (Loki/Grafana) stays out of scope — heavier infrastructure for a later pass.

**Blocked by** the same host the backup milestone ran on. Backup's proof layer
waits here too: borgmatic's run monitoring reports to Healthchecks or Uptime
Kuma, so those have to work before the timer is switched on.

### v0.9.0 — Measured resource limits

**Every service now carries a ceiling**, and the healthcheck question is decided
for every service — either one is defined or the compose file states why the image
cannot have one. `python3 scripts/ci/check-structure.py` is the progress bar for
both: it reports `no-resources` and `no-healthcheck` per service, and currently
reports neither.

**What remains is the values.** The ceilings in place were derived — from what a
component budgets for itself, from a peak where one was available, and generously
on purpose, because a limit the normal workload reaches kills an import and looks
like an application fault. Several stacks say so in the compose file: *starting
values, not measured ones*. Turning them into measured values needs a running
install per stack, which is why this milestone is late rather than early. The
procedure is in [`docs/resource-measurement.md`](docs/resource-measurement.md) —
what to sample, under which load states, and how a peak becomes a limit;
[`docs/standards/compose-structure.md`](docs/standards/compose-structure.md)
owns the target values and the rule that derives them.

**Done when** every `✅` stack's limits come from a measurement on a real install
rather than from the derivation rule.

**The Operator Site is live** at [secdockblue.rubennati.at](https://secdockblue.rubennati.at) since 2026-07-31, ahead of the milestone that used to hold it. It is the operator-facing entry point; the repository remains the technical source of truth and nothing moved out of it. Deliberately small and curated rather than a mirror of the repository, so it grows by review rather than by export.

### v1.0 — Complete and hand-off ready

The criterion: someone else could fork this and deploy it without needing this conversation.

Before v1.0 is tagged:

- Every app verified at least once on a clean install (continuous — not a last-minute sprint)
- No stack left at `scaffolded` without a documented reason
- No `__REPLACE_ME__` in any verified file
- Honest review of every `scaffolded` stack — a state rises only on evidence
- CI baseline complete: the jobs exist — compose validation, secret scan, security baseline, canonical structure, status model, checker coverage, docs QA (markdown lint, links, prose register) and workflow supply chain. Two gaps remain: **Trivy runs with `exit-code: 0`** and blocks nothing until the existing CRITICAL findings have been assessed once, and **`Checker coverage`, `Docs QA` and `Workflow supply chain` are not in the required set** — a branch-protection setting, not a file in this repository
- Secret & Password Generation Standard consolidated into `docs/standards/`
- Secrets rotation guidance in `docs/standards/`
- License review — every live app checked against the license policy below
- **Status freshness system active** — `Last verified` stamps in place, a major upstream update retires the verification anchor; tactical work moves to GitHub Issues
- Status model applied end to end — [`docs/standards/status-model.md`](docs/standards/status-model.md) defines what each symbol promises, [LIFECYCLE.md](LIFECYCLE.md) is generated from the owning files, and CI fails on a status claim that is not backed

---

## Continuous — not tied to a version

**App testing runs in parallel to everything above.** Any time there is bandwidth: pick a `scaffolded` app, run the App Chain, record the verified version. This does not block or trigger a release. The bar for the bar rises with the repository — an app verified today must meet the current baseline-aligned criteria in [`docs/maintenance.md`](docs/maintenance.md), not the bar from v0.1.

Apps still to re-verify on a clean install, because the standards have moved since
they were last checked: Vaultwarden, WordPress, Nextcloud, Seafile / Seafile Pro,
Invoice Ninja.

Pinned to a new major during the dependency sweep and not yet run anywhere:
Paperless-ngx 3.x, WordPress 7.x, Immich 3.x, Healthchecks 4.x, NocoDB (CalVer
switch), Adminer 5.x, Homepage 1.13.x, OpnForm 2.2.x, Uptime Kuma 2.x. Each is
`scaffolded` until it starts on a host — [`LIFECYCLE.md`](LIFECYCLE.md) carries the current
pin and status per stack.

**Cal.diY hardening** ([`apps/caldiy/docs/hardening-plan.md`](apps/caldiy/docs/hardening-plan.md))
runs on its own track, tied to no version. Phase 0 and Phase 1 configuration has
landed; the Phase 0 acceptance checks are open and Phases 2 and 3 have not started.

**Operator Site work is continuous and tied to no version** — content, structure and review loops are ongoing, and each push to `main` that touches `site/` publishes. What is written there is public the moment it lands, which is the reason for the content gate in front of it.

---

## A public repository should not carry personal data

The legal notice and the privacy statement hold a name, a postal address and an
e-mail. The repository is public and meant to be forked, so those values travel
with every copy.

The case to prevent is not someone taking them deliberately. It is the fork
that builds and goes live without anyone looking — and then a stranger's site
carries this author's imprint, and the people who read it write to **him** about
a site he has nothing to do with. Nobody had to act in bad faith for that to
happen.

Beyond the nuisance, a template that anyone can fork and build ought to be free
of its author's identity by construction. Keeping personal data out of a
public, copyable artefact is both the cleaner engineering answer and the correct
one under data-protection law.

**Direction, not yet a decision.** Encrypt the pages that carry personal data,
commit the ciphertext, and ship a placeholder in their place. What is secret is
the key, not the file: the repository holds a blob anyone can copy and nobody
can read, and a fork inherits a template that visibly asks for its own details.
It still builds on the first try, because the placeholder is a valid page.

`age` looks like the right size: one binary, no keyring, no web of trust, no
expiry, and a key pair that is two lines of text. SOPS earns its place when
single fields inside a YAML stay readable, which is not the case here — whole
files are encrypted, so it would be one layer over the same age. A repository
secret alone will not do either: a secret holds a value, so the imprint would
become an unversioned blob in a form field instead of a file with a history and
a diff.

Two key holders, both able to decrypt:

| Where | Holds |
|---|---|
| GitHub Actions secret | the key the deploy uses, decrypting into the runner's own workspace |
| a password manager | the same key for local editing, alongside the SSH keys already kept there |

An offline backup recipient belongs in the recipients file as well, so a lost
laptop does not take the imprint with it.

**Scope: everything personal, not only the two legal pages.** A fork inherits
the name and address in the legal notice, the contact address in
`security.txt`, the domain in `astro.config.mjs`, and the repository URLs in
the footer and the reference lists. Encrypting the imprint alone would still
leave a stranger's site pointing at this one.

**A fork builds, with the fields empty.** The placeholder is a valid page that
visibly asks for its own details, so nobody has to fix anything before the
first build succeeds.

That works for prose. It does not work for every value: the site URL feeds the
canonical tags and the sitemap, and an empty one produces a broken build rather
than an obvious gap. Values the build needs get a neutral placeholder —
`example.com` and the repository's own URL — while name, address and e-mail go
empty. The distinction is between a field a reader should notice is blank and a
value the build cannot do without.

**One data module rather than encrypted pages.** The values live in a single
module the pages and the config import. `site.ts` is committed and holds the
placeholders; `site.local.ts` is decrypted, gitignored, and wins when present.
That is a better shape than encrypting the markdown: one file to encrypt, one
import to resolve, and nothing in the working tree that a fork could mistake
for its own.

It also dissolves most of the trap. Decrypting over a committed placeholder
invites a thoughtless `git add` that puts real values back into a history that
keeps them; a gitignored file cannot be added by accident. A pre-commit hook
guarding against a forced add is then a belt on top of braces rather than the
only thing standing between the repository and a permanent mistake.

Locally the key never reaches the filesystem, because process substitution
hands `age` a descriptor instead of a path:

```bash
age -d -i <(op read "op://Private/age-signing-key/notesPlain") \
    -o site/src/data/site.local.ts secrets/site.age
```

The runner needs the same care for the opposite reason: writing the key to a
file and deleting it afterwards leaves a window, however short, so the key
should reach `age` on a descriptor there too.

This concerns the site. The rule that no secret-management tooling belongs in
the blueprint itself stands: no stack gains a dependency, and none of this is
offered to an operator as a way to hold their own credentials.

## In the backlog — individual app paths

App-level work that does not drive version tags.

### Choice-matrix categories — pick-one-per-install decisions

Once verified on real data, pick the default and deprioritise the rest:

- **Dashboards** — Dashy, Heimdall, Homarr, Homepage (`apps/`)
- **Photo galleries** — Immich, LibrePhotos, Lychee, PhotoPrism, Photoview (`apps/`)
- **Scheduling** — Cal.diy (MIT community), Easy!Appointments (`apps/`). Cal.com was retired — upstream moved the production codebase to a proprietary licence.
- **Business wikis** — BookStack is live; Wiki.js and Outline are planned (`apps/`)
- **Forms** — OpnForm is in place; Formbricks and HeyForm are planned (`apps/`)
- **Office / document servers** — OnlyOffice is live; Euro-Office (EU-governed fork) and Collabora (lighter, LibreOffice-based) are drafted (`core/`)
- **E-signatures** — OpenSign and Documenso, both drafted (`business/`)

### Categories with roadmaps in their own READMEs

Each of these owns its own planned list, including which services are on disk and
which are named only:

- [`monitoring/README.md`](monitoring/README.md) — the five monitoring axes plus the notification receiver; planned additions include Grafana + Prometheus and Scrutiny
- [`business/README.md`](business/README.md) — planned additions include Plane, Leantime, AppFlowy, Ackee, Plausible CE, Live Helper Chat and Eramba GRC
- [`backup/README.md`](backup/README.md) — Borgmatic has been backed up from and restored from; UrBackup has never been started. Kopia and Bareos are named, not built

### Project management — to evaluate

Three candidates to assess before committing to a default recommendation:

| App | Angle | License | Notes |
|---|---|---|---|
| **Plane** | Jira alternative — issues, cycles, modules, analytics | AGPL-3.0 | Multi-service stack (web, worker, beat, minio); richer than Vikunja, lighter than OpenProject |
| **Leantime** | PM designed for non-project-managers — goals, tasks, time tracking | AGPL-3.0 | Single-container option available; different UX philosophy than the others |
| **AppFlowy** | Notion alternative — docs, databases, kanban, AI | AGPL-3.0 | ⚠️ Non-standard deployment: only the backend (AppFlowy Cloud) runs in Docker — users connect via desktop or mobile app, not a browser. Evaluate whether this fits the blueprint model before including. |

Evaluation criteria: self-hosted Docker complexity, SSO/OIDC support, `_FILE` secret support, active maintenance, CE feature set vs paid gating.

---

## Evaluating

### License policy

This blueprint is for personal self-hosted infrastructure. The following applies:

**Accepted for self-hosted personal use:**

- MIT, Apache 2.0, BSD — permissive, no conditions on use
- GPL-2.0 / GPL-3.0 — copyleft applies to distribution, not to running the software
- AGPL-3.0 — the most common license in this space (Nextcloud, Authentik, Vaultwarden, Zammad). Self-hosting for personal use is explicitly allowed. If you expose the service to others (even within a company), the AGPL requires that you make your modifications available — running unmodified upstream images means no obligation.
- BSL / Commercial Source — time-limited source-available licenses (e.g. MariaDB BSL). Generally fine for self-hosting; verify the "Change Date" and "Additional Use Grant" per project.

**Requires case-by-case review:**

- Commercial dual-license (e.g. Cal.com AGPL + commercial) — self-hosting is free under the AGPL tier; check if the feature set you need requires the commercial tier
- Source-available without redistribution rights — usable, but you cannot fork or modify

**Not included in this blueprint:**

- Proprietary closed-source images with no self-hosting rights

Every app documents its license in `UPSTREAM.md`. The baseline-aligned criteria require this field before a stack is recorded as as ready.

---

### App configuration tiering (concept — no fixed timeline)

Most apps currently have one level of configuration: "it runs." A tiered approach would give each app a clearly defined Minimum (smallest working set, no hidden required settings), an Advanced layer (performance, storage, integration options — commented out by default), and optionally an Expert layer (deep tuning, references upstream docs). Paperless-ngx Phase 4 is the first concrete example of what this looks like.

This is a concept to develop continuously — not a version milestone. Picked up app by app as they are re-verified.

### App Evaluation Criteria (concept — no fixed timeline)

Structured per-app metadata to help make informed decisions before deploying. Not a rating scale — factual criteria that each person weighs themselves. License and Origin are already covered in `UPSTREAM.md`. Remaining candidates:

- **Stack size**: number of containers, minimum RAM
- **Security features**: Docker Secrets / `_FILE` support, 2FA, SSO / OIDC integration, audit log
- **Active development**: release cadence, last commit, community size
- **Privacy posture**: what gets logged, telemetry / phone-home behaviour, GDPR posture

Still open: where this lives and how to keep it from becoming a maintenance burden.

### Deploy script

`./deploy.sh <server> core/traefik apps/nextcloud` — rsync selected app directories to a server, no git / docs / inbox on target. Portable app deployments without the full blueprint on each host.

### Alternative container runtimes

Long-term consideration beyond standard Docker — Podman, Docker Swarm, K3s. Not blocking v1.0.

### MCP connectors

Expose selected apps via Model Context Protocol for AI-assisted operation. Candidates: Paperless-ngx document search, Vaultwarden secret retrieval. Blueprint defines the pattern; individual MCP servers live in their own repos.

---

## Out of scope here

- `core/acme-certs/` — being extracted to its own repository. The blueprint stub remains `scaffolded` but is no longer actively maintained in this repo.
- Paperless-mcp — template exists in the Paperless CONFIG.md extension notes but will live in its own repo once built.
