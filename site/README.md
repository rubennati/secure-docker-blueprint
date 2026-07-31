# SecDockBlue — the operator site

The public brand for this site is **SecDockBlue**; the repository it stands on
keeps the name **Secure Docker Blueprint**. They are two things and the names
are not interchangeable — the site is the operator-facing product, the
repository is the technical source of truth. Prose about the Compose files still
calls them the Blueprint.

The wordmark is one word. Never `SEC DOCK BLUE`, never hyphenated: the three
parts are distinguished by weight and colour in
[`SiteTitle.astro`](src/components/SiteTitle.astro) and by nothing else.

This folder contains the source for the Operator Site: an Astro/Starlight static site published via GitHub Pages.

**The repository is the technical source of truth.** Compose files, secrets handling, configuration, and implementation details live in the repository root. This site provides guided documentation for operators working with the Blueprint.

**Live at [secdockblue.rubennati.at](https://secdockblue.rubennati.at) since 2026-07-31.** `.github/workflows/site.yml` builds, checks and publishes: a push to `main` that touches `site/` deploys, a pull request builds and is checked but produces nothing publishable. The launch was brought forward — the milestone plan had it at v0.9.0 and a later decision at v1.0.0, and neither is what happened.

## Local development

```bash
cd site
npm install
npm run dev        # dev server at http://localhost:4321
```

## Checks

Two gates, both run in `.github/workflows/site.yml`. Run them before pushing:

```bash
npm run check:self   # do the rules still catch what they claim?
npm run build
npm run check        # the gate itself — needs dist/, so it runs after the build
```

[`scripts/check-content.mjs`](scripts/check-content.mjs) exists because this site
tells people to paste commands into a root shell. That makes it a distribution
channel: anyone who can land text in these pages can land a command in someone's
terminal. Ten rules cover pipe-to-shell installs, disabled TLS verification,
`chmod 777`, recursive deletes an unset variable turns into a delete from `/`,
`--privileged`, a mounted Docker socket, `:latest`, reverse-shell shapes,
credential-looking literals and private hostnames. Dead internal links and
anchors are checked against `dist/` in the same pass.

**A rule can be waived only in the `ALLOW` list in that file, and only with a
reason** — four pages discuss `--privileged` and the socket as the thing to
avoid. A waiver without a reason fails the run.

**Every rule carries a fixture it must catch and a near-miss it must not**, and
`check:self` runs before the gate in CI. A regex that has quietly stopped
matching reports "clean", which is worse than having no rule at all; this is not
hypothetical, the private-hostname rule shipped matching only one label and the
self-test caught it.

The repository-wide checks in `scripts/ci/` also cover this folder — in
particular `check-prose.py`, which treats everything under `site/` as
reader-facing and **blocks** on register violations there while only warning
elsewhere. Ranking importance for the reader ("worth knowing", "the one that
actually matters"), self-justification and aphorisms are the usual ones to trip
over.

## Build

```bash
cd site
npm install
npm run build      # production build output to ./dist/
```

## Preview

```bash
cd site
npm run preview    # serve the production build locally
```

## Structure

```text
site/
  src/content/docs/    — page content (.md / .mdx)
  src/pages/           — generated text routes (see below)
  astro.config.mjs     — site config, navigation, sidebar
  public/              — static assets served verbatim
```

### Generated text routes

`site` in `astro.config.mjs` holds the production address. Canonicals, Open Graph URLs, the sitemap and the three routes below derive from it, so nothing under `public/` should repeat the domain. No `base` — the site runs at the root of its own domain.

| Route | Derived from |
|---|---|
| `robots.txt` | `site` |
| `.well-known/security.txt` | `site`, plus a review date in the route file |
| `llms.txt` | `site`, plus every page's title and description |

`llms.txt` reads the content collection because the hand-written copy had drifted: it listed one application while three were published. A section matching no pages fails the build.

`@astrojs/sitemap` needs no setup — Starlight registers it, but it emits nothing until `site` is set.

## Content conventions

Binding for every guide page — anything under Infrastructure and security, Applications, or added later. Established after a review found earlier drafts mixing explanation and action, leaving Starlight's component toolkit unused, and including unsourced "planned" claims.

### Page order

1. **One-sentence framing** — what the service does for the reader. No explanation of how this repository or "the Blueprint" is organized; the reader came to install something, not to learn the project's internal taxonomy.
2. **Installation** — the shortest path to a working result, using sensible defaults. No decision content (alternatives, trade-offs, "it depends") blocks this section — if a choice exists, it takes the simplest default and links to where the alternative lives. The name is `Installation` wherever there is one path. `Quickstart` is reserved for an optional, objectively shorter entry that exists *alongside* the full installation, and it says what it leaves out — see [section contracts](../docs/standards/documentation-workflow.md#section-contracts).
3. **Verify** — concrete checks that the installation worked.
4. **Going further** — decisions, alternatives, and hardening that aren't needed for a first working setup. This is where "should I use X or Y" content lives.
5. **Troubleshooting** — real, confirmed problems and their fixes.
6. **Updates**
7. **Repository files** — links to the canonical source (READMEs, `.env.example`, compose files) for full reference.

This separation follows the [Diátaxis](https://diataxis.fr/) framework's distinction between task-oriented and understanding-oriented content: a reader trying to *do* something should never have to read *why* first.

### Component mapping

Use Starlight's built-in components instead of plain prose/tables for these cases — they're available (`Steps`, `Aside`, `Tabs`, `LinkCard`, `Badge`, `Card`/`CardGrid`) and underused on this site so far:

| Use this | For |
|---|---|
| `<Steps>` | Any ordered sequence of commands (the Installation section, primarily) |
| `<Aside type="caution">` | A real, confirmed gotcha — not a hypothetical one |
| `<Aside type="tip">` / `<Aside type="note">` | Optional context that would otherwise be a bolded paragraph |
| `<Tabs>` | Mutually exclusive choices (e.g. IPv4-only vs. dual-stack) instead of a decision table that blocks the installation |

### What does not belong on this site

Site-specific, in addition to the register rules that apply everywhere — the
customer row in [`writing-style.md`](../docs/standards/writing-style.md#audience-per-file)
owns those.

- **"Available now" / "Planned later" / "Coming soon"** or any other status-of-the-site commentary. A guide either exists — link to it — or it doesn't — don't mention it.
- **Unconfirmed or speculative claims.** A statement about what's planned must trace to an actual source (`ROADMAP.md`, or explicit maintainer confirmation). If it can't be traced, omit it rather than guess.
- **Repository-internal framing** (directory structure rationale, "core vs. apps" taxonomy, etc.) — that belongs in the repository's own docs, not in a guide aimed at someone installing a service.
- **The repository's lifecycle vocabulary** — `scaffolded`, `baseline-aligned`, `ops-proven` and the like answer a maintainer's question about what to work on next. A visitor is asking something else. See "Evidence, not status" below.

### Navigation

**Sidebar sections name subjects, not steps.** A heading phrased as an
instruction ("Set up the foundation") promises an order the site cannot keep —
Traefik is required, CrowdSec is optional, and a restore is not "after" adding an
application. Section labels are therefore stable subject areas; page titles stay
outcome-shaped. A section label must also match the role of everything under it:
that is why OnlyOffice sits with Applications and not with the infrastructure.

**A sidebar label and its page title must agree.** They need not be identical —
a section already supplies context, so "What each one is for" under Applications
is fine for a page titled "What each application is for" — but a reader must not
have to guess that two names are the same page.

**Pagination is off** (`pagination: false`). Automatic previous/next arrows
invent a reading order between unrelated guides. Re-enable it per page, in
frontmatter, only where one page genuinely cannot be done before another. Today
that is the start path alone: `/getting-started/` → `server-setup` → `traefik`.

**Overview pages orient, they do not describe the site.** An overview answers
what each thing under it is for, what it needs, and where the choice is not
obvious. "Which services have a guide" and "What this section covers" describe
the editorial state of the website, which no visitor came for.

### Evidence, not status

Guide pages carry `<StackEvidence>`, which reads generated facts from
`src/data/lifecycle.json` and renders only what a visitor can weigh: the version
the guide is written against, the verification date where one exists, and whether
data has been restored from a backup on a live host.

- **No repository tier names are rendered**, and no overall grade is implied.
- **`gap="…"` is mandatory where there is no anchored verification date** — the
  build fails without one. A stack that has not been checked needs a sentence
  naming what specifically was not exercised; a generic hedge ("may well work",
  "nothing has been established") warns without telling anyone what to do.
- **A named gap is useful on verified stacks too.** Prefer one.
