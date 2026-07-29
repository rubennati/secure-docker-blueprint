# Proposal — automated dependency updates

**Status: proposal.** Nothing in this document is active. The configuration below
is written out so it can be read before it runs, not committed as
`renovate.json`. A `renovate.json` at the repository root takes effect the moment
the Renovate App is installed on the repository.

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
| `*_IMAGE=` — full reference | ~8 | `TRAEFIK_IMAGE=traefik:v3.6` |

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
limited to five open at a time. Dependabot updates a SHA pin *and* the version
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

## Proposed Renovate configuration

Syntax verified against the current upstream documentation on 2026-07-28.
`managerFilePatterns` is the current option name; `fileMatch` is the former name
and is auto-migrated, so most examples found online are one rename behind.

```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": ["config:recommended"],

  "timezone": "Europe/Vienna",
  "schedule": ["* 0-6 * * 1"],

  "prConcurrentLimit": 5,
  "prHourlyLimit": 2,

  "dependencyDashboard": true,

  "customManagers": [
    {
      "customType": "regex",
      "managerFilePatterns": ["/\\.env\\.example$/"],
      "matchStrings": [
        "# renovate: datasource=(?<datasource>\\S+) depName=(?<depName>\\S+)\\s+(?:#[^\\n]*\\n)?[A-Z_]+_TAG=(?<currentValue>[^@\\s]+)(?:@(?<currentDigest>sha256:\\S+))?"
      ],
      "datasourceTemplate": "docker"
    },
    {
      "customType": "regex",
      "managerFilePatterns": ["/\\.env\\.example$/"],
      "matchStrings": [
        "[A-Z_]+_IMAGE=(?<depName>[^:\\s]+):(?<currentValue>[^@\\s]+)(?:@(?<currentDigest>sha256:\\S+))?"
      ],
      "datasourceTemplate": "docker"
    }
  ],

  "packageRules": [
    {
      "description": "Infrastructure images move together — they are upgraded as a set or not at all.",
      "matchDatasources": ["docker"],
      "matchPackageNames": [
        "postgres", "mariadb", "mysql", "redis", "valkey", "memcached", "nginx"
      ],
      "groupName": "infrastructure images"
    },
    {
      "description": "A major bump needs a host and a working core function. Never automatic.",
      "matchUpdateTypes": ["major"],
      "dependencyDashboardApproval": true,
      "addLabels": ["major", "needs-host-session"]
    },
    {
      "description": "Digest-only movement on a rolling tag is what digest pinning exists to catch.",
      "matchUpdateTypes": ["digest"],
      "groupName": "digest re-pins"
    }
  ]
}
```

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
stacks each. Ungrouped, one Redis patch is twelve pull requests.

**`config:recommended`** rather than a hand-built base — the preset is maintained
upstream and its defaults are sane. Deviations above are the interesting part.

## Open decisions

1. **Marker comments, or normalise the 28 outliers?** Recommendation: markers.
   They are explicit and do not break when someone writes a useful comment.
2. **Renovate App, or self-hosted Action?** The App is the standard path and free
   for public repositories, but installing it is an account-level action that
   only the maintainer can take. The Action keeps everything in the repository at
   the cost of a token to manage. Recommendation: the App, because a self-hosted
   runner that silently stops running is the failure mode this whole change is
   meant to remove.
3. **Scope — images only, or also the site's npm dependencies?** `site/` carries
   a `package-lock.json` that nothing currently watches. Renovate would pick it
   up automatically under `config:recommended`. Recommendation: include it, but
   grouped and non-urgent — it is a static site generator, not a runtime.

## Sequencing

Nothing here should land in one commit. Suggested order, each verifiable on its
own:

1. Marker comments across `.env.example`, with no `renovate.json` present. Inert
   by itself, reviewable as a pure documentation diff, and it can be done a
   category at a time.
2. A checker rule that fails when a pin has no marker — the same pattern as
   `check-workflows.py`, so the anchors cannot rot back out once added.
3. `renovate.json` plus installing the App — the only step that starts producing
   pull requests, and by then the anchors are in place and reviewed.

GitHub Actions need no step: Dependabot already covers them.
