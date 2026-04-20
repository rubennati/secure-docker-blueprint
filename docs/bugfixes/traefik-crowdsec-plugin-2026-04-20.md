# Traefik CrowdSec plugin disabled by read-only root filesystem — 2026-04-20

## Symptom

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
