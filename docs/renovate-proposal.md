# Proposal — automated dependency updates

**Status: `renovate.json` is committed at the repository root; the Renovate
GitHub App is not yet installed.** Until it is, nothing here runs — see
[Activation](#activation) for the one action left. The configuration below
now describes what is actually committed, with two corrections found while
implementing it (`baseBranches` → `baseBranchPatterns`, a rename Renovate's
own `renovate-config-validator` flagged as required — `managerFilePatterns`
needed no such change) and two additions this document's own later section
had already implied but never fed back into the config: `npm` and
`github-actions` are explicitly disabled, because both ecosystems this
repository has are already Dependabot's ("GitHub Actions are already
covered," below, and `site/`'s `package-lock.json` since 2026-09-13) — a
second bot managing the same files is exactly the "uncontrolled PR flood"
risk this proposal exists to avoid, not a second problem to solve.

No image pins carry a `# renovate:` marker comment yet. Per Sequencing below,
that is deliberately a separate, later, independently-reviewable change —
until it lands, the custom managers below are correctly configured but will
detect nothing. This was validated directly: the regex was run against real
`.env.example` lines from this repository, including one with no marker
(`business/opensign`'s deliberately-locked `DB_TAG=8.0`), which correctly
produced no match.

## Why this matters here specifically

The value proposition of this blueprint is that images are pinned **and current**.
Half of that is enforced: `check-structure.py` fails on `:latest` and on
major-only tags. The other half is not watched at all.

What that costs, measurably: the last dependency sweep was done by hand, and nine
major versions have been pinned but never started since. Nothing reported them —
they were found by reading.

There are **118 pins** across the repository, in two shapes:

| Shape | Count | Example |
|---|---|---|
| `*_TAG=` — tag only, image name lives in the compose file | ~110 | `APP_TAG=6.7-php8.3-fpm-alpine` |
| `*_IMAGE=` — full reference | ~8 | `TRAEFIK_IMAGE=traefik:v3.7` |

Four carry a digest (`tag@sha256:…`).

## The anchor problem — measured, not assumed

`env-structure.md` prescribes the image name as a comment above the pin:

```env
# wordpress (https://hub.docker.com/_/wordpress)
APP_TAG=6.7-php8.3-fpm-alpine
```

A regex manager could read the image name from that line. It was checked against
every pin in the repository before proposing it:

**90 of 118 pins have a parseable image comment directly above. 28 do not.**

The 28 are not sloppiness — they are continuation lines, a URL on its own line, or
a note that matters more than the image name:

```env
# MongoDB — MUST stay at 4.4. UniFi does NOT support 5.x or later.
DB_TAG=4.4
```

A convention written for humans is a poor machine anchor, and one that is 76%
consistent is worse than none: it would silently mis-assign 28 dependencies rather
than fail loudly.

**Recommendation: an explicit marker comment**, which is the documented approach
for exactly this case:

```env
# renovate: datasource=docker depName=wordpress
# wordpress (https://hub.docker.com/_/wordpress)
APP_TAG=6.7-php8.3-fpm-alpine
```

It costs one line per pin and it is unambiguous. The prose comment stays — it is
for the reader; the marker is for the tool. The two never disagree, because the
tool no longer reads the prose.

The `*_IMAGE=` pins need no marker: the image name is in the value.

**That is the first decision.** Adding 110 marker lines is mechanical but it is a
change to every `.env.example` in the repository, and it should be a deliberate
yes rather than something that arrives inside a config commit. The alternative —
normalising the 28 outliers so the prose convention becomes the anchor — trades
one line per pin for a rule that breaks again the next time someone writes a
useful comment.

## GitHub Actions are already covered

`.github/dependabot.yml` exists and has since the OpenSSF Scorecard work: the
`github-actions` ecosystem, weekly, all actions grouped into one pull request,
limited to five open at a time. Since 2026-09-13 it also carries an `npm` entry
for `site/`, grouped the same way, and both entries target `dev` — before that,
its pull requests opened against `main` and had to be re-targeted by hand. Dependabot updates a SHA pin *and* the version
comment beside it, so it maintains exactly what `check-workflows.py` enforces.

Nothing to add there. **This half of the problem is solved** — which narrows the
question to the image pins alone.

Dependabot cannot extend to those. Its `docker` ecosystem reads `image:` lines out
of a compose file, and every image in this repository is written as
`image: wordpress:${APP_TAG}` — the tag is an interpolated variable Dependabot
does not resolve. That indirection is deliberate and documented in
`env-structure.md`: one place to see what is pinned. It is also precisely what
puts these pins beyond Dependabot's reach and into Renovate's custom-manager
territory.

## Committed configuration

[`renovate.json`](../renovate.json) at the repository root — read it there
rather than here, so this document cannot quietly drift from what actually
runs the way the numbers in "Why this matters" already have. Validated with
`renovate-config-validator` (clean; the one required rename was
`baseBranches` → `baseBranchPatterns`, applied directly rather than left to
auto-migrate). The customManager regexes were also run against real
`.env.example` lines from this repository, including a digest-pinned one
(`apps/tymeslot`, `apps/caldiy`) and an `_IMAGE=` one (`core/traefik`) — see
[Validation evidence](#validation-evidence).

### What each choice is doing

**`schedule` + `prConcurrentLimit`** — without these the first run opens a pull
request per outdated pin. With 118 pins and a hand sweep months old, that is a
wall of PRs that gets ignored wholesale. Five at a time, once a week, overnight.

**`dependencyDashboardApproval` on majors** — a major bump here is never a merge
decision, it is a host session. Paperless 3.x needs a search-index migration;
Uptime Kuma 1.x → 2.x is a real migration. Those belong on the dashboard until
someone picks them up deliberately, not in an open pull request implying it is
ready.

**Grouping infrastructure images** — Postgres, MariaDB and Redis appear in a dozen
stacks each. Ungrouped, one Redis patch is twelve pull requests. `mongo` was
added to the list committed in `renovate.json` — `apps/unifi` and
`business/opensign` both run it, and the original list predates checking
that.

**`config:recommended`** rather than a hand-built base — the preset is maintained
upstream and its defaults are sane. Deviations above are the interesting part.
Its own extend chain is read directly out of the installed package
(`config/presets/internal/config.js`, `.../group.js`):
it pulls in dependency-dashboard, semantic commit prefixes, monorepo/package
grouping, merge-confidence badges, changelog helpers and replacement
suggestions, and nothing that enables automerge anywhere in that chain.

**`npm`/`github-actions` disabled** — not a deviation the original proposal
considered, because both became true only after parts of it were written.
`config:recommended` would otherwise auto-detect `site/package-lock.json`
and `.github/workflows/*.yml` as dependency manifests on its own and start
proposing updates for files Dependabot already manages — two bots managing
the same file is the "uncontrolled PR flood" and duplicate-update risk this
proposal names as a design goal to avoid, applied to a case its author
didn't have in front of them yet.

## Open decisions

1. **Marker comments, or normalise the 28 (now more, the repository has grown)
   outliers?** Still open, deferred — see Sequencing. Recommendation
   unchanged: markers. They are explicit and do not break when someone writes
   a useful comment.
2. **Renovate App, or self-hosted Action?** Decided: the App. A self-hosted
   Action would itself be a new CI/CD workflow — the exact kind of change the
   scope that implemented `renovate.json` was explicitly told not to make —
   and installing it is an account-level action only the maintainer can take
   regardless, so the repository side of this decision was never a choice
   between two committable options. See [Activation](#activation).
3. **Scope — images only, or also the site's npm dependencies?** Decided:
   images only. This section was stale by the time `renovate.json` was
   written — "GitHub Actions are already covered," above, already states that
   Dependabot has watched `site/`'s `package-lock.json` since 2026-09-13, so
   "nothing currently watches" it, this item's own premise, is no longer
   true. `renovate.json` disables the `npm` manager explicitly rather than
   letting `config:recommended` pick the file up a second time.

## Activation

`renovate.json` takes effect on the Renovate App's next scheduled run after
it is installed — nothing else in this repository can turn it on:

1. Install the [Renovate GitHub App](https://github.com/apps/renovate) on
   `rubennati/secure-docker-blueprint`. Free for a public repository; an
   account-level action only the repository owner can take.
2. Nothing else. `renovate.json` is already committed and validated
   (`renovate-config-validator`, clean). The first run follows `schedule`
   (Mondays, 00:00–06:00 UTC) unless triggered manually from the app's
   dashboard.

Until then, the custom managers have nothing to detect regardless — see the
status note at the top of this document.

## Validation evidence

Run directly, not assumed, when `renovate.json` was written:

- `npx --package renovate -- renovate-config-validator renovate.json` —
  passed after the `baseBranchPatterns` rename above; zero warnings on the
  second run.
- The two customManager regexes, run against real repository content in
  Node (Renovate's own regex engine) with a marker line prepended: a normal
  tag (`apps/wordpress`, `APP_TAG=7.0.4-php8.3-apache`) parsed correctly; two
  digest-pinned tags (`apps/tymeslot`, `apps/caldiy`) parsed with
  `currentDigest` correctly captured; the `_IMAGE=` pattern parsed
  `core/traefik`'s `TRAEFIK_IMAGE=traefik:v3.7` correctly with no marker
  needed; an unrelated variable (`TZ=UTC`) produced no match; and, the
  case that matters most, a real pin with **no** marker
  (`business/opensign`'s deliberately-locked `DB_TAG=8.0`) also produced no
  match — confirming the design decision in "The anchor problem" actually
  holds against this repository's real, messier comments, not just the
  clean examples above.
- `config:recommended`'s resolved extend chain, read out of the installed
  package, contains no `"automerge": true` at any level.

## Sequencing

Nothing here should land in one commit. `renovate.json` landed ahead of
marker comments (reversing the order below) as its own reviewable,
independently-scoped change — it validates cleanly and is provably inert
without a step before it that was not part of that change. Suggested order
for what is left:

1. Marker comments across `.env.example`, with `renovate.json` already
   present but producing nothing until they land. Reviewable as a pure
   documentation diff, and it can be done a category at a time.
2. A checker rule that fails when a pin has no marker — the same pattern as
   `check-workflows.py`, so the anchors cannot rot back out once added.
3. Install the Renovate App — see [Activation](#activation). The only step
   that starts producing pull requests, and by then the anchors are in place
   and reviewed.

GitHub Actions need no step: Dependabot already covers them.
