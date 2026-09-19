# Upstream Reference

## Source

- **Image:** https://hub.docker.com/r/jhaals/yopass
- **GitHub:** https://github.com/jhaals/yopass
- **Docs:** https://yopass.se/docs
- **License:** Apache-2.0
- **Origin:** Sweden · Jonas Haals (individual maintainer, corporate-adjacent — Spotify, Doddle and Gumtree Australia are named as users, not owners) · EU
- **Based on version:** `14.10.0`
- **Verification snapshot:** 2026-09-19 — local Compose stack booted and exercised (see README.md's Preview → Ready gate); not yet run behind a real Traefik host

## What we use

- `jhaals/yopass:14.10.0`, distroless build, runs as a fixed non-root UID
- `memcached:1.6-alpine` as the ephemeral store — the upstream-documented
  default backend, matching every value Yopass stores: TTL-based, no
  durability required or wanted

## Secret Requests is a paid feature, not part of this stack

Verified directly against the upstream README (2026-09-19), not assumed from
this task's brief: Yopass's own "Business" feature list includes *"Collect a
secret through an end-to-end encrypted request link (license required)"*, and
a separate hosted/licensed product (`yopass.se`) is referenced for
authentication, custom themes, audit logging and webhooks. The open-source
server this repository deploys has none of that — only the standard
sender-creates-a-link flow. Nothing in this stack's configuration can turn
Secret Requests on; it requires a different, licensed product from upstream.

## What we changed vs. upstream compose

| Change | Reason |
|--------|--------|
| `read_only: true` + `cap_drop: ALL` with **no** `cap_add` on either service | Verified directly against live containers — the app image is distroless and already non-root, and the official Memcached image already starts as its own service user. Neither needed a capability re-added, unlike the Postgres/Redis-style images this repository usually documents an exception for |
| No Docker Secrets section | Verified: nothing in this stack is a secret. No admin account, no database password, no signing key — everything Yopass stores is user-supplied ciphertext with its own TTL |
| Memcached kept off `proxy-public` and given no host port | Only `yopass-app` needs to reach it |

## What was actually verified, and how

- `docker inspect jhaals/yopass:14.10.0` — confirmed `User: "1000"`, a
  distroless base, and no built-in `HEALTHCHECK` (the compose file supplies
  one using the binary's own `--health-check` subcommand, matching upstream's
  documented insecure-deployment example).
- Ran the full local Compose stack (`docker-compose.local.yml`) under
  `--cap-drop=ALL --security-opt=no-new-privileges:true --read-only` on both
  containers — both reported healthy, and `GET /` returned 200.
- Confirmed the built-in healthcheck subcommand correctly fails when it
  cannot reach Memcached, and passes once the `MEMCACHED` env var points at a
  reachable instance — it genuinely checks the backend, not just that the
  process is alive.
- **Not verified:** an actual secret created and retrieved through the web
  UI, TLS/Traefik behind a real domain, the Redis backend option (Memcached
  only), Argon2 key derivation, and file/S3 storage backends.

## Upgrade checklist

1. Watch [Yopass releases](https://github.com/jhaals/yopass/releases) —
   the project ships frequently (multiple releases most months)
2. Read the changelog for the release notes between the current and target
   version
3. Nothing to back up — see README.md#backup
4. Bump `APP_TAG` in `.env`
5. `docker compose pull && docker compose up -d`
6. Confirm the healthcheck passes and a test secret round-trips

## Known limitations

- **Secret Requests / credential intake is not available in this stack** —
  it is a separate, licensed upstream product. See "Secret Requests is a
  paid feature" above.
- **Memcached backend only** — Yopass also supports Redis and file/S3
  storage; this stack does not use them, since Memcached already matches
  every value stored here (TTL-based, no durability needed).
- **Not yet run behind a real Traefik host or TLS.**
