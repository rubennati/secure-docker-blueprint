# Secure Docker Blueprint — Operator Site

This folder contains the source for the Operator Site: an Astro/Starlight static site published via GitHub Pages.

**The repository is the technical source of truth.** Compose files, secrets handling, configuration, and implementation details live in the repository root. This site is the operator-facing view — guidance, reference, and operational context for day-to-day use.

Public publication is planned for the v0.9.0 Operator Site launch milestone. This scaffold is built and validated in CI, but not yet deployed.

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

## Structure

```
site/
  src/content/docs/    — page content (.md / .mdx)
  astro.config.mjs     — site config, navigation, sidebar
  public/              — static assets
```
