# Vaultwarden Bugfixes — 2026-04-14

## Bug #1: InvalidConnectionUrl — base64 password breaks DATABASE_URL

**Symptom:** Vaultwarden crashes in loop with:
```
InvalidConnectionUrl("MySQL connection URLs must be in the form mysql://...")
```

**Root cause:** `openssl rand -base64 32` generates passwords with `+`, `/`, `=` characters. These break the `DATABASE_URL=mysql://user:password@host/db` because they have special meaning in URLs.

**Fix:** Use `openssl rand -hex 32` instead. Hex output only contains `[0-9a-f]` — no URL-unsafe characters.

**Lesson:** Any password used inside a URL (DATABASE_URL, Redis session handler, DSN strings) must avoid `+`, `=`, `/`, `&`, `?`. Use hex encoding. Same fix was applied for Redis at Nextcloud.
