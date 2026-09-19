# Upstream Reference

## Source

- **Image:** https://github.com/DependencyTrack/dependency-track/pkgs/container/apiserver · https://github.com/DependencyTrack/dependency-track/pkgs/container/frontend
- **GitHub:** https://github.com/DependencyTrack/dependency-track
- **Docs:** https://docs.dependencytrack.org
- **License:** Apache-2.0
- **Origin:** OWASP Foundation project · United States (OWASP Foundation) · non-EU
- **Based on version:** `5.1.0`
- **Verification snapshot:** 2026-09-19 — local Compose stack booted, all
  three services healthy, real Docker Secrets and migrations exercised
  against a live container; not yet run behind a real Traefik host

## What we use

- `dependencytrack/apiserver:5.1.0` + `dependencytrack/frontend:5.1.0` —
  the v5 "Hyades" architecture, where API server and frontend are separate
  images (v4's bundled image no longer exists)
- `postgres:16-alpine` — the only supported database in v5; H2, MySQL and
  SQL Server were dropped upstream, confirmed against the docs

## The `latest` tag is a trap on this image specifically

Verified directly against upstream's own container-images reference, not
assumed: **`latest` on both `dependencytrack/apiserver` and
`dependencytrack/frontend` still points to the old v4 line**, which
upstream states reaches end-of-life in December 2026. Anyone pulling
`latest` today gets v4, not v5 — this is called out as a known trap in
upstream's own documentation, not an inference. This stack pins the full
`5.1.0` tag, as upstream's own production guidance requires regardless of
this trap.

## What we changed vs. upstream's documented example

| Change | Reason |
|--------|--------|
| Real PostgreSQL, not the bundled/simplified path | v5 has no bundled database option at all — this is not a choice this stack made, it is the only supported architecture |
| `DT_DATASOURCE_PASSWORD` / `DT_SECRET_MANAGEMENT_DATABASE_KEK` via Docker Secrets and upstream's own `${file::...}` value syntax | Verified by reading upstream's configuration reference directly — this is Dependency-Track's real equivalent of the `_FILE` pattern, expressed as a value prefix rather than an env-var-name suffix. Requires `$$` escaping in the compose file so Docker Compose's own interpolation does not try to resolve `${file::...}` itself — verified against a live container that the literal string reaches the application correctly |
| `read_only: true` + `tmpfs: /tmp:exec` on the API server | Verified against a live container: the JVM extracts a native library (`libzstd-jni`) into `/tmp` and `dlopen()`s it; without exec permission on the tmpfs, extraction succeeds but loading fails with `UnsatisfiedLinkError: ... Operation not permitted` |
| No `read_only` on the frontend (documented, not silently dropped) | Verified against a live container: the entrypoint bakes `API_BASE_URL` and OIDC settings into `static/config.json`, inside the same directory that serves the built SPA. A read-only filesystem does not crash the container — it silently fails the write and the app falls back to unconfigured defaults, which is worse than not hardening this one property. Same class as this repository's existing ShellHub `ui` exception |
| Two Traefik routers on two subdomains, real `DT_CORS_ALLOWED_ORIGINS` | Upstream's own architecture has the frontend calling the API server directly from the browser as a separate origin — CORS is not optional here, and upstream's own default (`*`) is looser than this stack ships |
| Port `9000` (health/metrics) not exposed via Traefik | Upstream's own guidance: point user traffic at `8080`, probes/scrapers at `9000` |

## What was actually verified, and how

- `docker inspect dependencytrack/apiserver:5.1.0` — confirmed `User:
  "1000"`, `tini` entrypoint, and the image's own baked-in `HEALTHCHECK`
  (`curl ... http://127.0.0.1:9000/health`).
- `docker inspect dependencytrack/frontend:5.1.0` — confirmed `User:
  "101"` (nginx-unprivileged pattern).
- Read `docs/guides/administration/deploying-to-production.md`,
  `configuring-database.md`, `configuring-secret-management.md` and the
  configuration property reference directly from the
  `DependencyTrack/docs` repository — not assumed from the getting-started
  page, which only shows a minimal two-service example with no database.
- Ran the full three-service stack end to end with real Docker Secrets:
  Postgres came up healthy, the API server logged `Loading KEK from
  config`, ran `database-migration`, `dex-engine-database-migration`,
  `database-partition-maintenance` and `database-seeding` to completion,
  and reported healthy. `GET /api/version` returned 200 against a directly
  published test port.
- Ran the API server additionally under `--read-only --tmpfs /tmp` (no
  exec): failed with `UnsatisfiedLinkError`. Re-ran with `--tmpfs
  /tmp:exec`: identical clean start to the above.
- Ran the frontend under `--read-only`: the entrypoint logged `can not
  modify config.json — ENV configuration will be ignored` and served the
  page anyway, with `API_BASE_URL` never actually applied. Re-ran without
  `read_only`: `config.json` correctly reflected `API_BASE_URL` and the
  OIDC placeholders, confirmed via `GET /static/config.json`.
- **Not verified:** a real BOM upload and vulnerability analysis pass
  through the UI, OIDC sign-in against Authentik or Keycloak, TLS/Traefik
  behind a real domain across two subdomains, and multi-instance file
  storage (the `s3` provider).

## Upgrade checklist

1. Watch [Dependency-Track releases](https://github.com/DependencyTrack/dependency-track/releases)
2. Read the changelog — check `docs/guides/administration/upgrading-instances.md`
   for whether a given release needs a full-stop maintenance window
3. Back up the database, the KEK, and `./volumes/data` together before
   upgrading — see README.md#backup
4. Bump `APP_TAG` in `.env` (verify the tag exists on both `apiserver` and
   `frontend` — they should move together)
5. `docker compose pull && docker compose up -d`
6. Confirm `/health` on port 9000 reports `UP` and a sign-in still works

## Known limitations

- **`latest` resolves to the old v4 line** — see above. Always pin
  explicitly.
- **Single-instance deployment** — no shared file storage, no multi-node
  coordination configured. Upstream documents both for scale-out; this
  stack does not need them yet.
- **OIDC/LDAP not configured** — see README.md#authentication.
- **No real BOM upload or vulnerability scan has been exercised.**
