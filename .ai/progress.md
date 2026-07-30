# Progress

Milestone-level history. Per-release detail is in [`../CHANGELOG.md`](../CHANGELOG.md);
session-level detail is in the Progress Log of
[`../docs/maintenance.md`](../docs/maintenance.md).

| Release | Date | What it established |
|---|---|---|
| v0.1.0 | 2026-04-16 | Initial public release — core infrastructure plus ten hardened apps, standards, Apache 2.0 |
| v0.2.0 | 2026-04-18 | Structure Stable Baseline — five top-level categories forks can rely on |
| v0.3.0 | 2026-04-20 | Core complete — every core service validated on a fresh install; both multi-host management paths proven |
| v0.4.0 | 2026-04-20 | CrowdSec bouncer enforcing at the proxy, proven end-to-end |
| v0.5.0 | 2026-05-03 | Authentik Forward-Auth, two reusable patterns proven end-to-end |
| v0.5.1 | 2026-05-03 | Network isolation fix, tag pinning standard, ✅ Ready Criteria formalised |
| v0.6.0 | 2026-06-04 | CrowdSec complete — firewall bouncer, runbook, AppSec and geoblocking guidance |
| v0.7.0 | in progress | Backup — designed and configured; closes with one performed restore |

**The through line:** every release since v0.2.0 is defined by something *proven on a
fresh install*, not by something written. That is why status carries verification
dates, why ✅ has ten criteria, and why v0.7.0 does not end with a working
configuration.

## Since v0.6.0, outside the plan

Recorded in `ROADMAP.md` under "Since v0.6.0 — work outside the plan": a repo-wide
dependency sweep, the reference app and structure checker, four new previews, the
Cal.diY fork and hardening track, supply-chain hardening, and the unified status
model with a generated lifecycle view. None of it changed the milestone order.

## The operator site — 2026-07-30/31

The site became a product of its own rather than a mirror of the repository. It
is named **SecDockBlue**; `secure-docker-blueprint` stays the repository name and
the technical source of truth. Domain moved to `secdockblue.rubennati.at` —
still one line in `site/astro.config.mjs`, still no deploy job, still held to
v1.0.0. 37 pages.

**What changed structurally**

- Navigation names subjects, not steps. `core/` became `infrastructure/` because
  the old route was a repository directory name; OnlyOffice moved to
  `applications/` because nothing breaks without it.
- Automatic prev/next is off. It survives only on the start path, where one page
  genuinely cannot be done before another.
- A standalone **Security** section of twelve pages — firewalls, TLS, identity,
  cryptography, isolation, host, detection, resilience — ordered along the chain
  a request passes through. It holds whether or not the Compose files are used;
  the blueprint appears as a worked example.
- Trust layer: footer, legal notice and privacy as fork-safe templates,
  accessibility findings, source methodology.

**Two gates now stand under it**

- `site/scripts/check-content.mjs` — ten rules over documented commands, plus
  dead links and anchors. Every rule carries a fixture it must catch and a
  near-miss it must not, and CI runs that self-test *before* the gate.
- Citations resolve through `site/src/data/sources.ts`. An entry without an
  HTTPS URL, a check date, or a line saying what it is cited *for* fails the
  build, as does a citation to an unknown id. All 28 URLs were resolved before
  being added.

**What this cost, and what it bought**

Four documented commands did not do what they said — a `restart` that cannot
apply a changed `.env`, a `docker run` whose tag expanded to nothing, an
emergency flush covering only IPv4. All four were in guides written by someone
who had walked the installation. That is the argument for the content gate, and
the reason the remaining application stacks got a catalogue entry rather than a
guide: fifteen are listed with what they solve and what they cost, and the page
says plainly that nobody has walked their installation here.

**Open — not started, rather than half-built**

1. Guide content pass — Nextcloud, Invoice Ninja, Seafile Pro and the backup
   page have never been read end to end. Both pages that were read carried stale
   claims, so assume the others do too.
2. Walked-through guides for catalogued stacks. **BookStack is the assessed first
   candidate**: its MariaDB already carries the capabilities its entrypoint needs,
   and it has a real trap worth documenting — `DB_PWD_INLINE` must match
   `.secrets/db_pwd.txt` verbatim, because BookStack cannot read the password
   from a file. A local run cannot verify TLS, routing or access policy.
3. The local-evaluation path stays unwritten. `docker-compose.local.yml` does not
   start: the postgres services carry `cap_drop: [ALL]` while the official
   entrypoint needs `CHOWN`, `FOWNER`, `DAC_OVERRIDE`, `SETUID` and `SETGID`.
   Verified by isolation test, affects `_reference` (production file too),
   caldiy, documenso and infisical. **This blocks the site's best entry point.**
4. Licence for site content — undecided, and the footer says so rather than
   assuming the repository's Apache-2.0 extends to prose.
5. No 404 page.
