# Upstream Reference

- **Last verified:** 2026-11-08 (16.1.0) — over IPv4: an OpenPGP-encrypted secret stored through `/create/secret`, read once and `404` on the second read, before and after `down`/`up`; the route is public by design (docs/labs/stack-refresh/2026-11-08-results.md)

## Source

- **Image:** https://hub.docker.com/r/jhaals/yopass
- **GitHub:** https://github.com/jhaals/yopass
- **Docs:** https://yopass.se/docs
- **License:** Apache-2.0
- **Decision facts checked:** not yet
- **Origin:** Sweden · Jonas Haals (individual maintainer, corporate-adjacent — Spotify, Doddle and Gumtree Australia are named as users, not owners) · EU
- **Domain:** Identity, access and secrets
- **Role:** Self-destructing links for handing someone a credential once
- **Verification snapshot:** 2026-09-19 — local Compose stack booted and
  exercised

## What we use

- `jhaals/yopass:16.1.0`, distroless build, runs as a fixed non-root UID
- `memcached:1.6.45-alpine` as the ephemeral store — the upstream-documented
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

## Version notes

- Moved to `16.1.0` on 2026-11-08. Upstream calls
  16.1.0 a drop-in replacement with the same frontend, flags and environment
  variables; the API path is `/create/secret`.
- Moved to `16.0.1` on 2026-11-05 (released 2026-10-23), across two majors
  ; the checks under "What was actually verified" ran
  on 14.10.0. Nothing this stack sets changes: `MEMCACHED`, `PORT` and the
  `--health-check` subcommand keep their names
  (https://yopass.se/docs/server-options), and with no `FILE_STORE` set, files
  still go to the database, so no writable path is needed beside the `/tmp`
  tmpfs. Breaking changes, none of them touching this configuration
  (https://github.com/jhaals/yopass/releases):
  - 15.0.0: request deadlines of 30 s and, for file transfers, 5 min
    (`REQUEST_TIMEOUT`, `FILE_TRANSFER_TIMEOUT`); a proxy with a shorter limit
    cuts requests first. Forwarded client addresses are trusted only from
    `TRUSTED_PROXIES`, which is not set here. OIDC logins need
    `email_verified` (licensed feature, not used).
  - 16.0.0: clients must send the `key_version` from the lookup when fetching a
    secret (`412` otherwise), receipt errors answer `404` and `503`, session
    cookies no longer authenticate cross-origin requests or direct browser GETs
    to the API, `OIDC_ALLOWED_DOMAIN` is replaced by `OIDC_ALLOWED_DOMAINS`
    (the server refuses to start with the old one), Argon2 memory above 128 MiB
    and OpenPGP packets expanding beyond 1 MiB are rejected, request headers
    are capped at 16 KiB, webhook payloads carry `delivery_id`, and disk and S3
    file stores must exist and be private to the server account. The bundled
    web UI follows the API changes; an outside client written against 14.x
    may not.
  - Security: 16.0.0 addresses 27 findings from an audit (15 medium, 12 low),
    among them disk file operations confined to the storage root and a race in
    which a retried Redis write could recreate a consumed one-time secret;
    15.0.0 stops trusting spoofed forwarded addresses. 16.0.1 is rebuilt with
    Go 1.27.3 for CVE-2026-111943 (certificate chains through distrusted
    intermediates).

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
