# Upstream Reference

## Source

- **Traefik image:** https://hub.docker.com/_/traefik
- **Traefik docs:** https://doc.traefik.io/traefik/
- **Traefik GitHub:** https://github.com/traefik/traefik
- **Socket proxy image:** https://hub.docker.com/r/tecnativa/docker-socket-proxy
- **Socket proxy GitHub:** https://github.com/Tecnativa/docker-socket-proxy
- **CrowdSec bouncer plugin:** https://github.com/maxlerebourg/crowdsec-bouncer-traefik-plugin
- **License:** MIT
- **Decision facts checked:** not yet
- **Origin:** France · Traefik Labs · EU
- **Domain:** Infrastructure
- **Role:** Reverse proxy: TLS, access policies and security headers in front of every other service
- **Based on versions:** Traefik `v3.7`, docker-socket-proxy `v0.4.2`
- **Last verified:** 2026-09-13 (v3.7.13, socket-proxy v0.5.0) — moved from 3.6.10 on a live host with the dual-stack overlay: 13 routed hosts plus one external consumer answered with the same status codes before and after, HTTP/3 answered a `--http3-only` request, the CrowdSec bouncer plugin loaded and polled the LAPI within one second of start, and the socket proxy served the Docker API on the unchanged template. Nothing in the rendered configuration changed for the move.
- **Support window:** upstream policy since 3.6 is six months of support from a minor's GA date, with the last minor of a major supported for two years after the next major — https://doc.traefik.io/traefik/deprecation/releases/. 3.7 went GA 2026-05-05 and is the current line. **3.6 left security support on 2026-08-16** and 2.11 on 2026-09-07; neither is a pin target. Check this date before the next bump, not the version number alone.

## What we use

- Official `traefik` image, major version `v3.x`
- `tecnativa/docker-socket-proxy` as HAProxy-based Docker API filter — Traefik never touches `/var/run/docker.sock` directly
- Templated configuration: `.tmpl` files under `ops/templates/` are rendered via `envsubst` into `config/` by `ops/scripts/render.sh`
- File provider for all dynamic routing (middlewares, TLS profiles, access policies, system router) — Docker labels are used only by apps advertising their own routes
- Static config in `ops/templates/traefik.yml.tmpl`; dynamic config split into purpose-specific files under `ops/templates/dynamic/`

## What we changed and why

| Change | Reason |
|--------|--------|
| Two-container deployment (Traefik + socket-proxy) | Hardens the Docker API surface — Traefik only ever sees the filtered endpoints (`CONTAINERS`, `NETWORKS`, `INFO`, `EVENTS`, `PING`, `VERSION`) the socket-proxy allows. Start/stop/exec are denied by default. |
| `read_only: true` + `tmpfs: /tmp` on Traefik | Entire filesystem is immutable; only `/tmp` is writable, only in memory. Stops a compromise from persisting anywhere except the mounted ACME + log volumes. |
| `read_only: true` + `tmpfs: /run, /tmp` on socket-proxy | Same reasoning — HAProxy doesn't need a writable root. |
| `socket_proxy_net` is `internal: true` | Only Traefik can reach the proxy; nothing from `proxy-public` can pivot onto the Docker API. |
| Envsubst template pipeline (`ops/scripts/render.sh`) | Traefik's dynamic provider does not substitute `${VARS}` inside YAML. Rendering templates externally keeps `.env` as the single source of truth and avoids hand-maintained config drift. |
| `ops/scripts/validate.sh` | Pre-flight: required vars present, `__REPLACE_ME__` sentinels still in place, rendered files free of unresolved `${…}` references. |
| Access policies split into 5 chains (`acc-public` / `acc-local` / `acc-tailscale` / `acc-private` / `acc-deny`) | Lets every router pick its exposure separately from its security posture — two orthogonal axes instead of one entangled list. |
| Security posture split into blocks + preset chains (`sec-0` … `sec-5` + embed variants) | Quick presets for the 90% path, composable blocks for the rest. Documented in `README.md`. |
| No Traefik labels on the Traefik container itself | The dashboard router lives in `config/dynamic/routers-system.yml` (file provider) so the Traefik container stays configuration-free beyond static flags. |
| CrowdSec bouncer plugin in static config, middleware in dynamic config | Static plugin registration requires a restart; the routing middleware is hot-reloaded. Splitting them keeps day-to-day changes zero-downtime. |
| `CROWDSEC_BOUNCER_ENABLED` in `.env` renders both halves of the integration — the plugin block between the `crowdsec-bouncer` markers in `traefik.yml.tmpl` and the middleware file `dynamic/crowdsec.yml.tmpl` | The previous flow had the operator uncomment blocks in two tracked templates. A checkout restored the comments, and the next render silently dropped the plugin and the middlewares while the container kept running with both — a host was found in exactly that state on 2026-09-13. With the switch, the rendered state is a function of `.env`, `render.sh` refuses to render over an enabled `config/` that `.env` does not declare, and the CI gate renders both switch states instead of grepping templates. |
| `TLS_DEFAULT_OPTION` + three named profiles (`tls-basic`, `tls-aplus`, `tls-modern`) | Lets each router escalate or relax its TLS profile without rewriting the server's cipher list. |
| Host-exposed ports explicit (`TRAEFIK_HTTP_PORT`, `TRAEFIK_HTTPS_PORT`) | Allows binding Traefik to non-privileged ports when running behind another LB or on a port-forwarded VPS. |
| Dual-stack `proxy-public` as an opt-in Compose overlay (`network-dual-stack.yml`) rather than baked into `docker-compose.yml` | Docker cannot mix "IPv6 subnet present" with "IPv6 disabled" in one static network block, and an unconditional IPv6 default would risk existing deployments whose `proxy-public` was auto-assigned an IPv4 subnet. The overlay pattern (same mechanism as `apps/paperless-ngx/sso.yml`) keeps IPv4-only the default with dual-stack fully opt-in. See `docs/ipv6-dual-stack.md`. |
| `render.sh` places every output by rename (temporary file + `mv`) | Traefik re-reads `config/dynamic/` on any change; a truncate-then-fill write can be read as an empty file, which drops every middleware that file defines and disables every router naming one for a reload cycle. Seen on a host on 2026-09-14 (18 routers, one cycle). A rename is atomic, so the watcher only sees complete files. |
| Logrotate: one stanza per log, `copytruncate` for `traefik.log` | Traefik 3 reopens only the access log on `USR1`; the main log descriptor stays on the renamed file, the visible `traefik.log` stays empty, and the next rotation compresses what Traefik is writing to. Measured on v3.7.13, 2026-09-14. The main log is opened `O_APPEND`, so truncating in place is safe. |
| `forwardedHeaders.trustedIPs` (Cloudflare ranges) added to `traefik.yml.tmpl` | Without this, Traefik has no way to distinguish a real client IP forwarded by Cloudflare from one a client could spoof in its own request headers — `docs/security-verification.md` (control #12) flagged this as an open gap. Hardcoded directly in the template (not `.env`) for the same reason `acc-local`'s RFC1918 ranges are hardcoded: `envsubst` can't render a multi-entry YAML list from one variable. |

## Version / tag notes

- `traefik:v3.7` is pinned to the 3.7 minor line, which resolves to `3.7.13`. It was
  moved off `v3.6` on 2026-09-13 because 3.6 had left security support on 2026-08-16
  and six advisories published 2026-09-07 and 2026-09-10 have no fix on any 3.6
  release: CVE-2026-88007 (critical, HTTP/3 backend NTLM connection reuse),
  CVE-2026-88008 (high, request smuggling), CVE-2026-88004 (high, entrypoint
  header-name sanitization bypassed via request trailers), CVE-2026-88009 (high,
  rootless HTTP/1 request target routes as `/` but is forwarded verbatim, bypassing
  path-scoped routing and middleware), CVE-2026-88011 and CVE-2026-88012. All are
  patched in 3.7.12 or 3.7.13. The full finding is in
  [`../../docs/audits/dependency-sweep-2026-09-13.md`](../../docs/audits/dependency-sweep-2026-09-13.md).
- **Moved on a host on 2026-09-13**, from 3.6.10 straight to 3.7.13 with the rendered
  configuration untouched. The bouncer plugin at `v1.4.5` — the version that host had
  rendered, older than the `v1.7.1` this template names — loaded under 3.7.13 without
  change, so the plugin/interpreter boundary held across the minor. A throwaway
  `traefik:v3.7` container run against a copy of the live configuration with the ACME
  resolvers and the Docker provider removed answered that question before the live
  container was touched; it is a cheap preflight and it is what the checklist below
  now asks for.
- **The CrowdSec integration is switched in `.env`, not in the templates.**
  `CROWDSEC_BOUNCER_ENABLED=true` makes `render.sh` emit the plugin block and
  `config/dynamic/crowdsec.yml`; `false` removes both. A host that enabled the
  integration the old way — by uncommenting tracked templates — is refused by
  `render.sh` until `.env` declares the switch, because rendering over that state
  would drop the plugin and the middlewares while the container keeps running with
  both. The migration is in the README under "Migrating an installation that
  enabled the integration before the switch" and ran on a host on 2026-09-14: dry run
  into a copy, semantically identical to the live `config/`, then the live render —
  no restart, the routers carrying `crowdsec-basic` unchanged, the bouncer still
  polling.
- Traefik v2 → v3 was a breaking upgrade; **do not** jump majors without reading the migration guide: https://doc.traefik.io/traefik/migration/v2-to-v3/
- **`tlsResolver` (TLS-ALPN-01) was exercised on a live host on 2026-09-15**, restart and
  all: `apps/whoami`'s router set to it, `docker compose up -d` on `whoami`, then Traefik
  force-recreated to load the resolver into the running process. The mechanism is sound —
  Traefik started with no error against the resolver itself, `whoami@docker`'s router
  carried `certificateResolver: tlsResolver` with no complaint, every other route answered
  identically before and after, and the bouncer kept polling. **No certificate was actually
  requested.** This host runs wildcard mode (`ACME_WILDCARD_DOMAIN=dob.qode.at`), and
  `whoami.dob.qode.at` is already covered by the stored wildcard certificate — Traefik
  matches an incoming SNI against every certificate in its store regardless of which
  resolver owns it, finds the wildcard already satisfies `whoami.dob.qode.at`, and never
  proceeds to ask `tlsResolver`'s ACME provider for a new one. `acme.json` confirms it:
  two minutes after the restart, `tlsResolver`'s bucket was still empty. **A resolver
  cannot be proven to actually issue on a wildcard-mode host** for any hostname the
  wildcard already covers — only for one it does not, which on this host meant no
  hostname could be tested without either using a domain outside `*.dob.qode.at` or
  disabling wildcard coverage, neither of which this verification did. The change was
  reverted afterward: `whoami` back to `cloudflare-dns`, template unaffected.
- `tecnativa/docker-socket-proxy:v0.5.0` is pinned, moved from `v0.4.2` on 2026-09-13. Minor releases change the set of default-enabled endpoints — re-confirm `CONTAINERS`/`NETWORKS`/`ALLOW_*` flags after each bump. v0.5.0 updates the HAProxy base and adds `ALLOW_PAUSE` / `ALLOW_UNPAUSE`, both in upstream's revoked-by-default group, so the permitted surface is unchanged.
- CrowdSec bouncer plugin version comes from `CROWDSEC_BOUNCER_PLUGIN_VERSION` in `.env`; `.env.example` ships `v1.7.1`, and `render.sh` falls back to that when the variable is absent. Releases: https://github.com/maxlerebourg/crowdsec-bouncer-traefik-plugin/releases
  - The options this blueprint uses — `crowdsecMode`, `crowdsecLapiScheme`, `crowdsecLapiHost`, `crowdsecLapiKey`, `updateIntervalSeconds`, `crowdsecAppsecEnabled`, `crowdsecAppsecHost`, `crowdsecAppsecFailureBlock`, `crowdsecAppsecUnreachableBlock` — are unchanged from `v1.4.5` through `v1.7.1`. The only deprecations in that range are `BanHTMLFilePath` → `BanFilePath` and `CaptchaHTMLFilePath` → `CaptchaFilePath` (v1.7.0), neither of which this blueprint sets.
  - Verified against the upstream release notes only for `v1.7.1`. `v1.4.5` is the release that has run: a host carried it through Traefik 3.6.10 and then 3.7.13 (2026-09-13), and it loaded under both. Pin a newer tag only after verifying it compiles against the running Traefik version — the preflight in the upgrade checklist answers that without touching the live container. Traefik fetches and interprets the plugin at startup, so a bump takes effect on restart, not on reload.

## Upgrade checklist

### Minor bump (`v3.6` → `v3.x`)

A minor bump inside v3 still changes request handling. Read the per-version migration
notes, not only the release notes — https://doc.traefik.io/traefik/migrate/v3/ carries a
section per patch release. Between 3.6 and 3.7.13 these apply to this blueprint:

| Version | Change | What it touches here |
|---|---|---|
| 3.7.13 | `Upgrade: h2c` and `HTTP2-Settings` are no longer forwarded; use the `h2c://` scheme | any backend negotiating cleartext HTTP/2 |
| 3.7.13 | rootless request targets rejected with 400 (RFC 9112) | clients sending non-conforming targets |
| 3.7.12 | `underscoreHeadersStrategy` deprecated in favour of `aliasHeadersStrategy` (`keep` default, `delete`, `reject`) | neither is set in `traefik.yml.tmpl`. **3.7.12+ logs a warning per entrypoint at every start while the option is unset** — `aliasHeadersStrategy is not configured: the request headers whose name aliases another header name … are forwarded`. Expected at the default; the option and its values are documented in the template |
| 3.7.9 | HTTP/1 `CONNECT` rejected with 501 | no router here uses CONNECT |
| 3.7.7 | bare `` Host(`*`) `` becomes a catch-all | no rule here uses a bare `*` |
| 3.7.3 | `StripPrefix` / `StripPrefixRegex` reject with 400 when stripping yields a non-normalized path; `BasicAuth` with no users returns 404 | `apps/seafile` and `apps/seafile-pro` strip `/sdoc-server` |
| 3.6.14 | `trustForwardHeader` on ForwardAuth deprecated in favour of entrypoint-level `forwardedHeaders.trustedIPs` | the commented Authentik block in `integrations.yml.tmpl` sets it; the entrypoint list is already present, so drop the option when uncommenting |

1. Read the Traefik release notes: https://github.com/traefik/traefik/releases
2. Bump `TRAEFIK_IMAGE` in `.env`
2a. Preflight the plugin and the configuration against the new image before touching
    the running container. Copy `config/` somewhere outside the tree, strip
    `certificatesResolvers` and `providers.docker` from the copy of `traefik.yml` and
    every `certResolver:` line from the dynamic files, then:

    ```bash
    docker run -d --name tf-preflight -v /path/to/copy:/etc/traefik:ro \
      traefik:v3.x --configFile=/etc/traefik/traefik.yml
    sleep 30 && docker logs tf-preflight 2>&1 | grep -iE 'plugin|error'
    docker rm -f tf-preflight
    ```

    No ports are published and no resolver is present, so it can neither take traffic
    nor talk to an ACME endpoint. "Plugins loaded." with no error line is the answer.
3. Re-render (no changes expected, but catches any env drift):

   ```bash
   ./ops/scripts/render.sh
   ./ops/scripts/validate.sh
   ```

4. `docker compose pull && docker compose up -d` — `pull` is what moves a running
   container onto a new patch of the same minor tag. Without it, `v3.6` keeps the digest
   it started with: the test host ran 3.6.10 (built 2026-03-06) while the tag resolved to
   3.6.25. Confirm with `docker exec <container> traefik version`, not with the tag.
5. Verify:

   ```bash
   docker compose ps                      # traefik healthy
   docker compose logs traefik --tail 100 # no plugin / config errors
   curl -fsSI https://<TRAEFIK_DASHBOARD_HOST>/api/rawdata
   ```

### Major bump (`v3` → `v4`, when released)

1. **Stop.** Read the full migration guide end-to-end before touching anything.
2. Back up rendered config + ACME state:

   ```bash
   tar czf traefik-$(date +%Y%m%d).tgz config/ volumes/letsencrypt/
   ```

3. Port the templates to the new format — router, middleware, and TLS option schemas tend to change between majors.
4. Test in a separate host or with a throwaway cert resolver before swapping the production container.

### Socket-proxy bump

1. Read the release notes: https://github.com/Tecnativa/docker-socket-proxy/releases
2. Confirm the `ALLOW_*` / `CONTAINERS=1` etc. knobs still mean the same thing (the image occasionally adds new defaults).
3. Bump `SOCKET_PROXY_IMAGE`, restart, and verify Traefik still discovers containers:

   ```bash
   docker compose restart
   docker compose logs traefik | grep -i "provider.docker"
   ```

## Related images to keep in sync

- `tecnativa/docker-socket-proxy` — always bump alongside Traefik if the API surface changed; otherwise independent.
- CrowdSec bouncer plugin — independent of the Traefik image, but must work against the running Traefik major.

## Useful commands

```bash
# Render all templates (.tmpl -> config/)
./ops/scripts/render.sh

# Verify env + rendered files
./ops/scripts/validate.sh

# Full wipe of rendered output (templates stay)
./ops/scripts/reset-templates.sh

# Live view of current router + middleware table
curl -s https://<TRAEFIK_DASHBOARD_HOST>/api/rawdata | jq '.routers, .middlewares | keys'

# Check what the socket-proxy actually exposes
docker compose exec docker-socket-proxy env | grep -E "^(CONTAINERS|SERVICES|NETWORKS|VOLUMES|IMAGES|SYSTEM|EXEC|POST|DELETE|ALLOW_)"

# Tail access log (if enabled in .env)
tail -f volumes/logs/access.log

# Inspect current ACME cert store
docker compose exec traefik cat /etc/traefik/acme/acme.json | jq '.[] | keys'

# Force cert renewal for one domain (clean way: delete entry + restart)
# Do NOT delete acme.json wholesale — you'll hit Let's Encrypt rate limits.
```

## Related docs in this repo

- `README.md` — user-facing setup, security policies, CrowdSec integration guide, incident runbook
- `ops/templates/` — all `.tmpl` source files
- `ops/scripts/validate.sh` — canonical list of required env vars
