# Provenance — licence, jurisdiction, and who owns it

Every stack states two facts in its `UPSTREAM.md`:

```markdown
- **License:** AGPL-3.0
- **Origin:** Germany · Nextcloud GmbH · EU
```

Both were already there for most stacks before this area existed. What was
missing was a view — nothing could answer "which of these are EU-governed, and
which are not actually open source" without opening fifty-nine files.

## The fields

**`License:`** — the licence the *upstream project* publishes, in its own
spelling. Where a project is genuinely split, say so rather than picking the
flattering half: `EULA (Ubiquiti) / GPL-3 (LSIO scripts)`.

**`Origin:`** — `Country · Entity · Bloc`, where bloc is `EU`, `non-EU`, or
`no single jurisdiction`:

| Origin | Meaning |
|---|---|
| `Germany · Nextcloud GmbH · EU` | a company, a registered address, EU law |
| `US · Documenso Inc · non-EU (development largely from Hamburg, Germany)` | the entity governs; where the developers sit is a footnote |
| `Community · borgmatic-collective (Dan Helfman) · no single jurisdiction` | no company to point at — not a failing, but a different answer |
| `Finsys · **no country or legal entity stated** — no imprint on fnsys.pro` | looked, found nothing |

That last row is a real finding, not a gap in the research. Two `core/` stacks
come from an organisation that publishes no imprint, no country and no legal
entity. The row records that; leaving the field blank would hide it.

**The entity governs, not the developers.** Documenso's founder works from
Hamburg, but Documenso Inc is a US company — a US court order reaches the
company, not the postcode of whoever wrote the commit. The country of
development goes in parentheses because it locates the people, not the legal
reach.

## Licence classes

The generator sorts licences into four classes, because "open source" is claimed
more often than it applies:

| Class | Meaning | In this repository |
|---|---|---|
| `osi` | OSI-approved | 51 |
| `mixed` | open core, or genuinely dual-licensed | 4 |
| `source-available` | source published, use restricted | 3 |
| `proprietary` | neither | 1 |

The three source-available ones are named here, since each restricts something a
self-hoster might assume they may do:

- **`core/dockhand`** — BSL 1.1. Free for personal, internal business,
  non-profit and educational use; offering it as a hosted service is not
  permitted. Converts to Apache-2.0 on 2029-01-01.
- **`business/invoiceninja`** — Elastic License 2.0. No providing it to others
  as a hosted or managed service, and no circumventing the licence key
  functionality.
- **`apps/n8n`** — Sustainable Use License. Internal and commercial use is fine;
  reselling it as a service is not.

None of these is a reason to avoid the software. They are a reason not to build
a business on reselling it without reading the licence first.

## As of 2026-07-30

59 stacks, no gaps in either field:

| Bloc | Stacks |
|---|---|
| EU | 26 |
| non-EU | 27 |
| no single jurisdiction | 6 |

Most-represented countries: US (10), Germany (9), France (6), UK (5),
New Zealand (3), Canada (2), China (2), India (2).

Note that the UK counts as non-EU here. That is a statement about jurisdiction,
not about quality — Collabora and BookStack are not worse software for it. Where
the line matters is in which legal regime can compel what.

## Keeping it honest

```bash
python3 scripts/ci/sovereignty-report.py          # regenerate
python3 scripts/ci/sovereignty-report.py --check  # what CI runs
```

`--check` fails on a stale JSON file, a missing field, or a licence spelling the
classifier does not recognise. That last one is deliberate: a new licence should
force a decision about which class it belongs to, not default into `osi` because
the string was unfamiliar.

## When adding a stack

Fill both fields from the **official source** — the project's own `LICENSE` file
and its imprint or legal page. Not a directory site, not a summary, and not from
memory: this repository has already been wrong about a licence it was confident
about (`core/whoami` is Apache-2.0, not MIT).

If the project states no jurisdiction, write that. An honest blank is worth more
than a plausible guess.
