# Upstream Reference

## Source

- **Traefik image:** https://hub.docker.com/_/traefik
- **Traefik docs:** https://doc.traefik.io/traefik/
- **Traefik GitHub:** https://github.com/traefik/traefik
- **Socket proxy image:** https://hub.docker.com/r/tecnativa/docker-socket-proxy
- **Socket proxy GitHub:** https://github.com/Tecnativa/docker-socket-proxy
- **CrowdSec bouncer plugin:** https://github.com/maxlerebourg/crowdsec-bouncer-traefik-plugin
- **License:** MIT
- **Origin:** France · Traefik Labs · EU
- **Based on versions:** Traefik `v3.6`, docker-socket-proxy `v0.4.2`
- **Last checked:** 2026-04-16

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
| `TLS_DEFAULT_OPTION` + three named profiles (`tls-basic`, `tls-aplus`, `tls-modern`) | Lets each router escalate or relax its TLS profile without rewriting the server's cipher list. |
| Host-exposed ports explicit (`TRAEFIK_HTTP_PORT`, `TRAEFIK_HTTPS_PORT`) | Allows binding Traefik to non-privileged ports when running behind another LB or on a port-forwarded VPS. |

## Version / tag notes

- `traefik:v3.6` is pinned to the 3.6 minor line. Traefik v2 → v3 was a breaking upgrade; **do not** jump majors without reading the migration guide: https://doc.traefik.io/traefik/migration/v2-to-v3/
- `tecnativa/docker-socket-proxy:v0.4.2` is pinned. Minor releases change the set of default-enabled endpoints — re-confirm `CONTAINERS`/`NETWORKS`/`ALLOW_*` flags after each bump.
- CrowdSec plugin is pinned to `v1.4.5` in `traefik.yml.tmpl`. Pin to a newer tag only after verifying it compiles against the running Traefik version.

## Upgrade checklist

### Minor bump (`v3.6` → `v3.x`)

1. Read the Traefik release notes: https://github.com/traefik/traefik/releases
2. Bump `TRAEFIK_IMAGE` in `.env`
3. Re-render (no changes expected, but catches any env drift):
   ```bash
   ./ops/scripts/render.sh
   ./ops/scripts/validate.sh
   ```
4. `docker compose pull && docker compose up -d`
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
