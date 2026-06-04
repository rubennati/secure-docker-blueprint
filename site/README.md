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
