# Upstream Reference

## Source

- **Image:** https://github.com/homarr-labs/homarr/pkgs/container/homarr
- **GitHub:** https://github.com/homarr-labs/homarr
- **Docs:** https://homarr.dev/
- **License:** Apache-2.0 (fork heritage: originally forked from `ajnart/homarr`, which was MIT; `homarr-labs/homarr` ships the Apache licence)
- **Decision facts checked:** not yet
- **Origin:** Community · homarr-labs · EU contributors
- **Domain:** Dashboards
- **Role:** Dashboard with integrations into the services you run
- **Last verified:** 2026-05-02 (v1.60.0)

## What we use

- Official `ghcr.io/homarr-labs/homarr` image
- Built-in SQLite (no external DB)
- Bind-mount `./volumes/appdata/` for persistent state

## What we changed and why

| Change | Reason |
|--------|--------|
| Traefik labels instead of port `:8001:7575` | Blueprint routes via Traefik |
| Pinned `APP_TAG` | Inbox had `:latest` |
| `SECRET_ENCRYPTION_KEY` moved to `.env` variable (placeholder `__REPLACE_ME__`) | Inbox source had a hardcoded key value — that would have been a backdoor if copied verbatim. Every instance needs its own key. |
| Docker socket mount commented out | Direct `/var/run/docker.sock` mount gives Homarr full Docker control, a risk unreasonable for a dashboard. Socket-proxy pattern recommended; documented in README. |
| `security_opt: no-new-privileges` | Blueprint baseline |
| Access default `access-vpn`, `limit-standard` and `headers-standard` | Personal dashboard pattern |
| Healthcheck runs `node` against `/api/health/live` | Since v2 the image is Debian-based without `wget` or `curl`; the check mirrors the image's own `HEALTHCHECK` and also covers the database and the internal Redis |
| `BASE_URL=https://${APP_TRAEFIK_HOST}` | v2 uses it as the canonical origin for MCP OAuth metadata and origin checks; upstream requires an HTTPS origin behind a TLS-terminating proxy |
| `HOMARR_TRUSTED_PROXIES` passed through, empty by default | v2's bundled nginx trusts no forwarded client address unless listed; empty is upstream's safe default, see `.env.example` |

## Upgrade checklist

1. Check [GitHub releases](https://github.com/homarr-labs/homarr/releases) — breaking changes and DB migration notes
2. Back up `./volumes/appdata/`:

   ```bash
   tar czf homarr-appdata-$(date +%Y%m%d).tgz volumes/appdata/
   ```

3. Bump `APP_TAG`
4. `docker compose pull && docker compose up -d`
5. Next.js migrations run on start; watch logs

### Rollback

Restore appdata tarball, revert `APP_TAG`.

## Version notes

- Moved to `v2.12.0` on 2026-11-08 and run on the lab host (VM). A minor
  release; its notes name no breaking change. A new instance answers `/` with a
  redirect to the setup wizard at `/init`.
- Moved to `v2.11.1` on 2026-11-05 (released 2026-11-05), across the v2.0.0
  major (2026-10-02), not run on a host at this tag; the verification above was
  against `v1.60.0`. The v1 line ends at `v1.77.2`, which still ships Next.js
  `16.3.0-preview.9` and does not fix the CRITICAL findings at `v1.77.1`
  (Next.js, `dompurify`, `protobufjs`, `tar`); v2.11.1 ships Next.js `16.4.2`,
  `dompurify` `3.4.17` and `protobufjs` `7.6.6`, and its runtime image no longer
  carries npm (and its `tar`). Upgrade: back up the stopped `./volumes/appdata/`
  and the encryption key first — v2 migrates the SQLite database in place at
  start, v1 cannot open it afterwards, and rollback means restoring that
  pre-upgrade copy, not only reverting `APP_TAG`. No separate migration step;
  `/appdata`, port `7575` and `SECRET_ENCRYPTION_KEY` are unchanged. Breaking in
  v2.0.0: MySQL support is dropped (not used here); the runtime image moves
  from Alpine to Debian trixie-slim without `wget`, so the healthcheck now uses
  `node`; `PUID`/`PGID` drop privileges with `setpriv` instead of `su-exec`
  (neither is set here, the container still starts as root as before); boards
  use fixed 200 × 200 cells and scale to the width, so migrated 12-column
  boards can look smaller — reduce the column count in the board layout
  settings after a backup. New in v2: `BASE_URL` (set here),
  `HOMARR_TRUSTED_PROXIES` (empty here), `ENABLE_DOCKER` (default `true`; the
  page stays empty without a socket), an opt-in Assistant that sends prompts
  and tool results to the provider an administrator selects, and the Workshop,
  which connects to `homarr.dev` when browsed. Telemetry to PostHog is still
  present, so "What it sends outward" in the README still applies. No Homarr
  GHSA is published for v2; the move is for the dependency findings above.
  Sources: <https://github.com/homarr-labs/homarr/releases/tag/v2.0.0>,
  <https://homarr.dev/docs/getting-started/installation/docker#update>,
  <https://homarr.dev/docs/advanced/proxy#trusted-request-identity>,
  <https://homarr.dev/docs/advanced/environment-variables>.

## Useful commands

```bash
# Shell
docker compose exec app sh

# Regenerate SECRET_ENCRYPTION_KEY (destroys stored integration creds!)
openssl rand -hex 32
# Update .env, docker compose restart app
```
