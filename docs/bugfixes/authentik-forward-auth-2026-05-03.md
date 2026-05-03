# Bugfixes — Authentik Forward-Auth + SPA Rate Limiting (2026-05-03)

Three bugs discovered and fixed during v0.5.0 live testing of the Authentik
Forward-Auth integration (Dashy, Heimdall, Paperless-ngx `/admin`).

---

## 1 — Traefik path-scoped router priority too low

**Affected:** `apps/paperless-ngx/docker-compose.yml`,
`core/authentik/docker-compose.yml`

**Symptom:** The `-admin` (and `/_static/`) router had `priority=10` set
explicitly. Requests to `/admin/` were handled by the main catch-all router
instead — Authentik Forward-Auth was never invoked.

**Root cause:** Traefik auto-calculates priority from the rule string length
when no explicit value is set. The main router rule
`Host(\`paperless.example.com\`)` is ~29 characters long → auto-priority 29.
An explicit `priority=10` overrides the auto-calculation and loses to 29.
Any explicit priority must be higher than the auto-calculated value of all
competing routers.

**Fix:** `priority=10` → `priority=100` on all path-scoped secondary routers.

---

## 2 — Authentik Pattern 2 External Host must include the protected path

**Affected:** Authentik Provider configuration for path-scoped Forward-Auth

**Symptom:** After successful Authentik login, the browser was redirected to
the app root (`https://paperless.example.com/`) instead of the protected path
(`/admin/`). For Paperless-ngx, the root URL serves the Angular frontend —
the user has no Paperless account → Angular router showed `/404`.

**Root cause:** In Authentik Forward Auth (single application), the
**External host** field is used as the post-login redirect target, not just
as a matching hint. Setting it to the domain root causes Authentik to redirect
there after login.

**Fix:**
- Pattern 1 (full app): External host = `https://app.example.com` — correct,
  the whole app is protected and the user lands on the homepage.
- Pattern 2 (path-scoped): External host = `https://app.example.com/<path>/`
  — must include the protected path so Authentik redirects there after login.

For Paperless: `https://paperless.example.com/admin/`

Documented in `core/authentik/README.md` Pattern 2, Step 2a.

---

## 3 — SPA 429 rate-limit on first page load (NocoDB, n8n, Authentik login)

**Affected:** `apps/nocodb/.env.example`, `apps/n8n/.env.example`,
`core/authentik/docker-compose.yml`,
`core/traefik/ops/templates/dynamic/security-blocks.yml.tmpl`,
`core/traefik/ops/templates/dynamic/security-chains.yml.tmpl`

**Symptom:** NocoDB and n8n returned HTTP 429 on first page load. Authentik's
login page also returned 429 on JS/CSS assets when `sec-3` was active.
Temporary workaround was `APP_TRAEFIK_SECURITY=sec-1` (no rate limit).

**Root cause:** All three apps are code-split SPAs. Vite/webpack splits
every route and component into a separate JS/CSS chunk. On first visit the
browser fires 100+ parallel HTTP requests for these chunks. Traefik's token
bucket (`rl-soft`: `average: 100, burst: 50`) starts with 50 tokens — they
are exhausted in milliseconds, and the remaining requests receive 429.

This is by-design SPA behaviour; it cannot be configured away at the
application level.

**Fix — two-part:**

**Part 1 — `rl-spa` rate limit block (VPN-only SPAs):**
New `rl-spa` middleware with `burst: 200` absorbs the initial chunk load.
`average: 100` still applies steady-state. Safe only behind a network-level
access control (e.g. `acc-tailscale`).

New chains added:
- `sec-2-spa` — basic headers + rl-spa + compress
- `sec-3-spa` — strict headers + rl-spa + compress + permissions-policy

NocoDB and n8n updated: `APP_TRAEFIK_SECURITY=sec-1` → `sec-3-spa`.

**Part 2 — Router splitting for the Authentik login page (public access):**
`rl-spa` is not appropriate for public-facing apps. Instead, Authentik's
`/_static/` path (static JS/CSS assets) gets a dedicated Traefik router with
`sec-1@file` (no rate limit) and `priority=100`. The main Authentik router
keeps `sec-3` for all other paths (API, flow endpoints).

This is the canonical Traefik OSS approach for per-path middleware — no
Enterprise license required.

**Files changed:**
- `security-blocks.yml.tmpl`: added `rl-spa`
- `security-chains.yml.tmpl`: added `sec-2-spa`, `sec-3-spa`; updated table
- `apps/nocodb/.env.example`: `sec-1` → `sec-3-spa`
- `apps/n8n/.env.example`: `sec-1` → `sec-3-spa`
- `core/authentik/docker-compose.yml`: added `/_static/` router
