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

## Bug #3 — Plugin loaded, bouncer never pulls because no router uses it

### Symptom

The plugin loads cleanly (`"Plugins loaded."`, no `"Plugins are
disabled"` in Traefik's logs), but `cscli bouncers list` never gets a
`Last API pull` or `IP Address` — indefinitely, not just slow to
appear:

```
$ docker exec crowdsec cscli bouncers list
 Name             IP Address  Valid  Last API pull  Type  Version  Auth Type
 traefik-bouncer              ✔️                                   api-key
```

No errors anywhere — Traefik logs are clean, `cscli lapi status` is
healthy, the bouncer's API key is valid. There is simply nothing to
debug in the conventional sense: nothing is failing, something is
just never starting.

### Root cause

Declaring the plugin (`experimental.plugins.bouncer` in
`traefik.yml.tmpl`) and defining the `sec-crowdsec` middleware
(`integrations.yml.tmpl`) only registers the middleware in Traefik —
it does not run it. The bouncer plugin's polling loop (the thing that
produces `Last API pull`) only starts once the middleware is actually
**attached to at least one router's middleware list**. This is
[step 5 in the README's "Wire the plugin" section](../../core/crowdsec/README.md#phase-2-traefik-bouncer-plugin) —
easy to skip because steps 1–4 (key, plugin, middleware, render +
restart) already make the plugin *look* fully configured, and the
4-step verify sequence right after it can be run (and fail silently
at step 2) without ever circling back to step 5.

### Fix

Add `sec-crowdsec@file` to the middleware list of at least one
router — first to a low-stakes test app to confirm Phase 2 end to
end, for example `core/whoami/docker-compose.yml`:

```yaml
- "traefik.http.routers.${COMPOSE_PROJECT_NAME}.middlewares=sec-crowdsec@file,${APP_TRAEFIK_ACCESS}@file,${APP_TRAEFIK_SECURITY}@file"
```

`sec-crowdsec@file` goes first in the chain (matches the example in
`core/traefik/README.md`'s CrowdSec section).

### Apply

```bash
cd core/whoami   # or whichever app's compose file you edited
docker compose up -d --force-recreate
```

### Verify

```bash
# Stream mode polls every 60s — wait before checking
sleep 65
docker exec crowdsec cscli bouncers list
# Expected: IP Address (the Traefik container's own address on
# proxy-public), a recent "Last API pull" timestamp, Type and Version
# populated
```

---

## How to tell which bug you have

All three bugs can show up on a first Phase 2 activation. The
discriminator is in Traefik's startup logs and in
`cscli bouncers list`:

| Signal                                           | Bug #1 (read-only FS) | Bug #2 (AppSec default) | Bug #3 (no router attached) |
|--------------------------------------------------|-----------------------|--------------------------|------------------------------|
| `"Plugins are disabled"` in Traefik logs         | ✅ yes                | ❌ no                    | ❌ no                        |
| `cscli bouncers list` shows `Last API pull`      | ❌ never              | ✅ recent timestamp      | ❌ never                     |
| Any router actually has `sec-crowdsec@file`      | (irrelevant)          | ✅ yes                   | ❌ no                        |
| Router returns                                    | 404                   | 403                      | normal (middleware not active) |
| `cscli decisions list`                            | (irrelevant)          | empty                    | (irrelevant)                 |

Bug #1 is infrastructure: the plugin never loaded, so the middleware
does not exist in Traefik's registry → router config invalid → 404.

Bug #2 is policy: the plugin loaded, the bouncer is healthy, but
the default config tells it to block on AppSec unreachability → 403
on every request regardless of decisions.

Bug #3 is an incomplete setup, not a failure: every prior step
succeeded, but the bouncer was never wired into any router's request
path, so it has nothing to do and never starts polling. No error
appears anywhere because nothing is actually broken — the setup is
just not finished.

Fix #1 first. If `cscli bouncers list` still never gets a `Last API
pull` after that, and no router yet has `sec-crowdsec@file` in its
middleware list, you are in Bug #3 territory — finish step 5. If a
router does have it and you still get 403 once a fresh `Last API
pull` appears, that is Bug #2.
