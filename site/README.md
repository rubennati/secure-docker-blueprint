# Secure Docker Blueprint — Operator Site

This folder contains the source for the Operator Site: an Astro/Starlight static site published via GitHub Pages.

**The repository is the technical source of truth.** Compose files, secrets handling, configuration, and implementation details live in the repository root. This site provides guided documentation for operators working with the Blueprint.

Public publication is planned for the v0.9.0 milestone. This scaffold is built and validated in CI, but not yet deployed.

## Local development

```bash
cd site
npm install
npm run dev        # dev server at http://localhost:4321
```

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

```
site/
  src/content/docs/    — page content (.md / .mdx)
  astro.config.mjs     — site config, navigation, sidebar
  public/              — static assets
```

## Content conventions

Binding for every guide page (Core Infrastructure, Applications, and anything added later). Established after a review found earlier drafts mixing explanation and action, leaving Starlight's component toolkit unused, and including unsourced "planned" claims.

### Page order

1. **One-sentence framing** — what the service does for the reader. No explanation of how this repository or "the Blueprint" is organized; the reader came to install something, not to learn the project's internal taxonomy.
2. **Quickstart** — the shortest path to a working result, using sensible defaults. No decision content (alternatives, trade-offs, "it depends") blocks this section — if a choice exists, the quickstart takes the simplest default and links to where the alternative lives.
3. **Verify** — concrete checks that the quickstart worked.
4. **Going further** — decisions, alternatives, and hardening that aren't needed for a first working setup. This is where "should I use X or Y" content lives.
5. **Troubleshooting** — real, confirmed problems and their fixes.
6. **Updates**
7. **Repository files** — links to the canonical source (READMEs, `.env.example`, compose files) for full reference.

This separation follows the [Diátaxis](https://diataxis.fr/) framework's distinction between task-oriented and understanding-oriented content: a reader trying to *do* something should never have to read *why* first.

### Component mapping

Use Starlight's built-in components instead of plain prose/tables for these cases — they're available (`Steps`, `Aside`, `Tabs`, `LinkCard`, `Badge`, `Card`/`CardGrid`) and underused on this site so far:

| Use this | For |
|---|---|
| `<Steps>` | Any ordered sequence of commands (the Quickstart section, primarily) |
| `<Aside type="caution">` | A real, confirmed gotcha — not a hypothetical one |
| `<Aside type="tip">` / `<Aside type="note">` | Optional context that would otherwise be a bolded paragraph |
| `<Tabs>` | Mutually exclusive choices (e.g. IPv4-only vs. dual-stack) instead of a decision table that blocks the Quickstart |

### What does not belong on this site

- **"Available now" / "Planned later" / "Coming soon"** or any other status-of-the-site commentary. A guide either exists — link to it — or it doesn't — don't mention it.
- **Unconfirmed or speculative claims.** A statement about what's planned must trace to an actual source (`ROADMAP.md`, or explicit maintainer confirmation). If it can't be traced, omit it rather than guess.
- **Repository-internal framing** (directory structure rationale, "core vs. apps" taxonomy, etc.) — that belongs in the repository's own docs, not in a guide aimed at someone installing a service.
