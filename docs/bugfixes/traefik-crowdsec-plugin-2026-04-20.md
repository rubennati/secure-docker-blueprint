# Traefik CrowdSec plugin — first-setup bugs — 2026-04-20

Two independent issues observed on a fresh Phase 2 activation. Both produce
the same visible failure mode (routers with `sec-crowdsec@file` in their
middleware chain return HTTP 403 or 404), so it is worth listing both and
the discriminator between them.

---

## Bug #1 — Plugin disabled by read-only root filesystem

### Symptom

After enabling the CrowdSec bouncer plugin in Traefik's static config
(`experimental.plugins.bouncer`) and the `sec-crowdsec` middleware in
`integrations.yml`, Traefik logs show:

```
{"level":"info","plugins":["bouncer"],"message":"Loading plugins..."}
{"level":"error","plugins":["bouncer"],
 "error":"unable to create plugins manager: unable to create directory
          /plugins-storage/sources: mkdir plugins-storage:
          read-only file system",
 "message":"Plugins are disabled because an error has occurred."}
```

And any router that references the CrowdSec middleware fails:

```
{"level":"error","routerName":"whoami@docker",
 "error":"invalid middleware \"sec-crowdsec@file\" configuration:
          invalid middleware type or middleware does not exist"}
```

Routers with the broken middleware return HTTP 404 to clients.

## Root cause

Traefik's container is started with `read_only: true` as baseline
security hardening. When `experimental.plugins` is configured, Traefik
needs a writable path at `/plugins-storage/` to download the plugin
source, compile it, and cache the result. On a read-only root FS that
`mkdir` fails, the plugin manager shuts down, and every middleware the
plugin would have registered is reported as non-existent.

The `sec-crowdsec` middleware is defined by the plugin, so it only
appears in Traefik's registry once the plugin loads successfully.

## Fix

Mount a writable directory at `/plugins-storage/` in
`core/traefik/docker-compose.yml` while keeping the rest of the root FS
read-only:

```yaml
volumes:
  - ./config/traefik.yml:/etc/traefik/traefik.yml:ro
  - ./config/dynamic:/etc/traefik/dynamic:ro
  - ./volumes/letsencrypt:/etc/traefik/acme
  - ./volumes/logs:/var/log/traefik
  - ./volumes/plugins-storage:/plugins-storage   # NEW
```

## Apply

```bash
cd core/traefik
mkdir -p volumes/plugins-storage
docker compose up -d --force-recreate traefik
```

First boot after the change: plugin download + compile takes ~30–90
seconds. Subsequent boots reuse the cached compiled plugin.

## Verify

```bash
# 1. Plugin loaded without error (look for "Plugin bouncer loaded" / no
#    "Plugins are disabled")
docker compose logs traefik 2>&1 | grep -iE "plugin|bouncer" | head -10

# 2. Bouncer now pulls from CrowdSec (Last API pull gets a timestamp)
docker exec crowdsec cscli bouncers list

# 3. Router serves normally (no more 404)
curl -I https://<whoami-host>
# Expected: HTTP/2 200
```

## Why the default was read-only in the first place

`read_only: true` is a good baseline for any container. Traefik writes
nothing persistent in its root FS when plugins are disabled — ACME
state goes to `./volumes/letsencrypt`, logs to `./volumes/logs`, and
sockets to the `/tmp` tmpfs. It only gets tripped when a feature
requires an extra writable path.

Adding plugin storage as a dedicated bind mount keeps the root FS
read-only, preserves the security posture, and fixes the plugin load
path in one line.

---

## Bug #2 — AppSec enabled by default, fail-closed on every request

### Symptom

The plugin loads cleanly (no "Plugins are disabled" in logs), the
bouncer shows up in `cscli bouncers list` with a recent `Last API
pull`, and `cscli decisions list` is empty — yet every request
through a router with `sec-crowdsec@file` returns HTTP 403:

```
$ curl -I https://whoami.example.com
HTTP/2 403

$ docker exec crowdsec cscli decisions list
No active decisions.
```

Traefik logs show the bouncer plugin refusing the request without
any decision in play.

### Root cause

The `integrations.yml.tmpl` template shipped with three AppSec flags
set to `true`:

```yaml
crowdsecAppsecEnabled: true
crowdsecAppsecFailureBlock: true
crowdsecAppsecUnreachableBlock: true
```

AppSec is a separate CrowdSec component (WAF) that listens on
port 7422 and must be wired up independently. When the plugin is
told AppSec is enabled but cannot reach the AppSec server, the
`UnreachableBlock: true` flag tells it to fail closed — block every
request. No decision needed, no ban required: the plugin denies on
inability to consult the WAF.

### Fix

Flip the AppSec defaults to `false` in
`core/traefik/ops/templates/dynamic/integrations.yml.tmpl`:

```yaml
# AppSec (WAF) is a separate CrowdSec component that requires extra
# server-side config. Keep disabled by default — enable only after
# the AppSec server at :7422 is wired up and reachable.
crowdsecAppsecEnabled: false
crowdsecAppsecFailureBlock: false
crowdsecAppsecUnreachableBlock: false
```

### Apply

```bash
cd core/traefik
# Re-render dynamic config from the template
./ops/render.sh   # or whichever render entrypoint the repo uses
docker compose up -d --force-recreate traefik
```

### Verify

```bash
# 1. No active decisions — confirms we're testing the AppSec path,
#    not a real ban
docker exec crowdsec cscli decisions list

# 2. Router serves normally
curl -I https://<whoami-host>
# Expected: HTTP/2 200

# 3. Ban test still works end-to-end — add a decision for your own
#    IP, confirm 403, then delete it
docker exec crowdsec cscli decisions add --ip <your-ip> --duration 1m
curl -I https://<whoami-host>   # Expected: 403
docker exec crowdsec cscli decisions delete --ip <your-ip>
```

---

## How to tell which bug you have

Both bugs produce 403 / 404 on routers with `sec-crowdsec@file`.
The discriminator is in Traefik's startup logs and in
`cscli bouncers list`:

| Signal                                           | Bug #1 (read-only FS) | Bug #2 (AppSec default) |
|--------------------------------------------------|-----------------------|-------------------------|
| `"Plugins are disabled"` in Traefik logs         | ✅ yes                | ❌ no                   |
| `cscli bouncers list` shows `Last API pull`      | ❌ never              | ✅ recent timestamp     |
| Router returns                                    | 404                   | 403                     |
| `cscli decisions list`                            | (irrelevant)          | empty                   |

Bug #1 is infrastructure: the plugin never loaded, so the middleware
does not exist in Traefik's registry → router config invalid → 404.

Bug #2 is policy: the plugin loaded, the bouncer is healthy, but
the default config tells it to block on AppSec unreachability → 403
on every request regardless of decisions.

Fix #1 first. If 403 persists after `cscli bouncers list` shows a
fresh `Last API pull`, you are in Bug #2 territory.
