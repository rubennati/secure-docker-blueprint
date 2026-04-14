# Vaultwarden Bugfixes — 2026-04-14

## Bug #1: InvalidConnectionUrl — base64 password breaks DATABASE_URL

**Symptom:** Vaultwarden crashes in loop with:
```
InvalidConnectionUrl("MySQL connection URLs must be in the form mysql://...")
```

**Root cause:** `openssl rand -base64 32` generates passwords with `+`, `/`, `=` characters. These break the `DATABASE_URL=mysql://user:password@host/db` because they have special meaning in URLs.

**Fix:** Use `openssl rand -hex 32` instead. Hex output only contains `[0-9a-f]` — no URL-unsafe characters.

**Lesson:** Any password used inside a URL (DATABASE_URL, Redis session handler, DSN strings) must avoid `+`, `=`, `/`, `&`, `?`. Use hex encoding. Same fix was applied for Redis at Nextcloud.

---

## Bug #2: HTTP Response validation Error — Header conflicts with sec-4

**Symptom:** Vaultwarden Admin → Diagnostics shows "HTTP Response validation Error":
```
Header: 'x-frame-options' does not contain 'SAMEORIGIN'
Header: 'referrer-policy' does not contain 'same-origin'
Header: 'x-xss-protection' does not contain '0'
```

**Root cause:** Traefik's `sec-4` file-provider middleware sets strict security headers (`X-Frame-Options: DENY`, `Referrer-Policy: strict-origin`, `X-XSS-Protection: 1`). Vaultwarden expects different values (`SAMEORIGIN`, `same-origin`, `0`).

First attempt: Adding a second Docker-level `headers` middleware to override. **Failed** — Traefik only applies one headers middleware per chain; the second one's values are ignored.

**Fix:** Replaced `sec-4` file-provider middleware entirely with a custom Docker-level middleware (same pattern as OnlyOffice). The custom middleware sets:
- `customFrameOptionsValue=SAMEORIGIN`
- `referrerPolicy=same-origin`
- `browserXssFilter=false` (sets X-XSS-Protection: 0)
- `forceSTSHeader=true` + `stsSeconds=63072000` (HSTS kept)
- `contentTypeNosniff=true` (kept)

**Remaining warning:** "2FA Connector calls" still show header warnings in Diagnostics. These are internal API calls within Vaultwarden that don't go through Traefik — unkritisch, no fix needed.

**Lesson:** Traefik's file-provider security middlewares (sec-1 to sec-4) can't be partially overridden. If an app needs different headers, use a complete custom Docker-level middleware instead. Document this per app.
