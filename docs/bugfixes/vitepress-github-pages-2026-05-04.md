# VitePress — GitHub Pages deployment

**Project:** cert-ops-tool (applies to any VitePress site on GitHub Pages)  
**Date:** 2026-05-04  
**VitePress version:** ^1.6.0

## Summary

Setting up a VitePress docs site on GitHub Pages required fixing four independent issues — each one was only visible after the previous was resolved. Documented here as a reference for future VitePress deployments (e.g. secure-docker-blueprint docs).

---

## Issue 1 — ESM error: `"vitepress" cannot be loaded by require`

**Symptom:**
```
Error: "vitepress" resolved to an ESM file. ESM file cannot be loaded by `require`.
failed to load config from docs/.vitepress/config.ts
```

**Root cause:** `package.json` lacked `"type": "module"`. Node treated the project as CommonJS; VitePress is ESM-only and cannot be `require()`-d.

**Fix:**
```json
{
  "type": "module"
}
```

**Note:** VitePress's own scaffolding (`npx vitepress init`) adds this automatically. When creating `package.json` by hand it is easy to miss.

---

## Issue 2 — `npm ci` fails: missing `@esbuild/linux-*` platform packages

**Symptom:**
```
npm error `npm ci` can only install packages when your package.json and
package-lock.json are in sync.
npm error Missing: @esbuild/linux-x64@0.21.5 from lock file
npm error Missing: @rollup/rollup-linux-x64-gnu@4.60.3 from lock file
... (44 missing entries)
```

**Root cause:** The lockfile was generated on macOS arm64 with npm 8 (`lockfileVersion: 2`). npm 8 on macOS does not include optional platform-specific binaries for other platforms. npm 10 on the Linux CI runner requires all platform entries to be present.

**Fix:** Remove `package-lock.json` from git, add it to `.gitignore`, and use `npm install` in the workflow instead of `npm ci`. For a docs-only project with a pinned version in `package.json` this is safe — CI resolves the correct platform packages fresh on each run.

**Alternative (not used):** Generate the lockfile on a Linux machine (or inside a Docker container) with npm 10, which produces `lockfileVersion: 3` with all platform entries.

---

## Issue 3 — Build fails immediately without `actions/configure-pages`

**Symptom:** Build job exits with code 1 in ~10 seconds. No meaningful error in annotations beyond "Process completed with exit code 1".

**Root cause:** The `actions/configure-pages` step was missing from the workflow. This step initialises the GitHub Pages deployment environment and sets the correct base URL. Without it, the subsequent `upload-pages-artifact` and `deploy-pages` steps have no environment to target and the job fails silently.

**Fix:** Add as a required step before the build:
```yaml
- name: Setup Pages
  uses: actions/configure-pages@v6
```

**Note:** The official VitePress deployment docs include this step. It is easy to miss when adapting or simplifying the template.

---

## Issue 4 — Actions running on deprecated Node 20

**Symptom:** Annotation warning: _"Node.js 20 actions are deprecated. actions/configure-pages@v4 will be forced to run on Node.js 24."_

**Root cause:** The VitePress deployment documentation references outdated action versions (`configure-pages@v4`, `upload-pages-artifact@v3`, `deploy-pages@v4`) that still use Node 20 internally.

**Fix:** Use the current Node 24 versions (confirmed from GitHub releases, 2026-05-04):

| Action | VitePress docs (outdated) | Correct (Node 24) |
|---|---|---|
| `actions/checkout` | `@v5` | `@v6` |
| `actions/setup-node` | `@v6` | `@v6` ✅ |
| `actions/configure-pages` | `@v4` | `@v6` |
| `actions/upload-pages-artifact` | `@v3` | `@v5` |
| `actions/deploy-pages` | `@v4` | `@v5` |

**Lesson:** Always verify action versions directly on GitHub releases — framework docs frequently lag behind.

---

## Final working workflow

```yaml
name: Deploy docs to GitHub Pages

on:
  push:
    branches: [main]
    paths:
      - 'docs/**'
      - 'package.json'
      - '.github/workflows/docs.yml'
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: false

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v6
        with:
          fetch-depth: 0
      - name: Setup Node
        uses: actions/setup-node@v6
        with:
          node-version: 24
      - name: Setup Pages
        uses: actions/configure-pages@v6
      - name: Install dependencies
        run: npm install
      - name: Build with VitePress
        run: npm run docs:build
      - name: Upload artifact
        uses: actions/upload-pages-artifact@v5
        with:
          path: docs/.vitepress/dist

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v5
```
