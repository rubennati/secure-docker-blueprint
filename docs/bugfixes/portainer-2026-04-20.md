# Portainer — 2026-04-20

## Custom healthcheck used `wget`, which the Portainer image does not ship

**Symptom:**

After `docker compose up -d`, the portainer-app container reported
`(unhealthy)` after 3 minutes. Exec diagnostics:

```bash
docker exec portainer-app wget -qO- http://127.0.0.1:9000/api/status
# OCI runtime exec failed: exec: "wget": executable file not found in $PATH
```

Traefik was then unable to route requests reliably while the container
was marked unhealthy.

**Root cause:**

The Portainer CE image is a distroless-style build — no shell, no
`wget`, no `curl`. Any healthcheck relying on a shelled command cannot
execute. Our compose had:

```yaml
healthcheck:
  test: ["CMD-SHELL", "wget -qO- http://127.0.0.1:9000/api/status ..."]
```

This fails on startup, fails every interval, container is marked unhealthy.
Additionally the path `/api/system/status` was not canonical in 2.x — the
standard is `/api/status` — but the missing `wget` was the primary bug.

**Fix:**

Remove the custom healthcheck entirely. Portainer's image has no baked-in
HEALTHCHECK either, so the container simply runs without a health gate —
acceptable for a management UI that's monitored externally.

```yaml
# --- Health & Observability ---
# Portainer's image ships no wget / curl / shell, so any custom test
# will fail. No built-in HEALTHCHECK in the image either — monitor
# externally (Uptime Kuma, Gatus, etc.).
```

**Apply:**

```bash
cd core/portainer
docker compose up -d --force-recreate
```

---

## Quick-reference: service name vs container name

During diagnostics it is easy to confuse the two. For Portainer:

- `container_name: portainer-app` — how `docker ps` lists it
- service name in compose is just `app` (not `portainer-app`)

So `docker compose up -d --force-recreate portainer-app` fails with
`no such service: portainer-app`. Either use `app` or recreate without
a service argument.
