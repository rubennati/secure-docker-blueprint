# Seafile Pro Bugfixes — 2026-04-13

## Bug #1: notification-server + md-server exit 127

**Symptom:** Both containers crash with exit code 127 (command not found).

**Root cause:** Our entrypoint wrapper was set as a single `entrypoint:` array including the original command. Docker overrides the original CMD when you set entrypoint, but doesn't append the original CMD to it. The `exec "$@"` in our wrapper had nothing to execute.

**Fix:** Split into `entrypoint` (our wrapper) + `command` (the original CMD):
```yaml
entrypoint: ["/bin/sh", "/config/entrypoint.sh"]
command: ["/opt/seafile/notification-server", "-c", "/opt/seafile", "-l", "..."]
```

**Why CE worked:** CE services all use `/sbin/my_init -- /scripts/enterpoint.sh` which was passed as args to our wrapper correctly. Pro services have different entrypoints (Go binary, different script path).

**Lesson:** Always check the original ENTRYPOINT/CMD of each image with `docker inspect`. Don't assume all services in a stack use the same pattern.

---

## Bug #2: seadoc + thumbnail "Waiting Nginx" infinite loop

**Symptom:** Both containers spam "Waiting Nginx" in logs and never start their actual service.

**Root cause:** These images internally check if an HTTP proxy (Caddy/Nginx) is reachable before starting. In the official setup, Caddy sits in front. In our setup with Traefik, there's no Caddy — but the containers need to be reachable via Traefik to pass this check.

**Fix:** Added Traefik labels + proxy-public network to seadoc and thumbnail (copied from working CE setup):
- seadoc: routers for `/socket.io/` and `/sdoc-server`
- thumbnail: router for `/thumbnail`

**Why CE worked:** CE already had Traefik labels on seadoc, notification, and thumbnail.

**Lesson:** I assumed the main Seafile container routes all sub-paths internally. Wrong — check the CE reference and official docs first. Each service with an external URL path needs its own Traefik router.

---

## OPEN: Thumbnail 403 Forbidden

**Status:** Container runs, but browser gets 403 when requesting `/thumbnail/...`

**Suspected cause:** Traefik routes `/thumbnail` to the main Seafile router (which has access/security middlewares) instead of the thumbnail-specific router. Both routers match the same Host — need to set higher priority on the PathPrefix router.

**Next step:** Add `priority` to thumbnail Traefik labels, or check if the thumbnail router needs the same middlewares.

---

## OPEN: SeaSearch not initialized / Wiki Search 500

**Status:** Container runs but shows only "idle script". Wiki search returns 500.

**Root cause:** `SS_FIRST_ADMIN_PASSWORD` environment variable is empty. SeaSearch needs it for initialization. In the original setup this comes from `INIT_SEAFILE_ADMIN_PASSWORD` in .env. In our setup the admin password is a Docker Secret, but SeaSearch doesn't have the entrypoint wrapper.

**Next step:** Add entrypoint wrapper to SeaSearch (same pattern as notification-server: `entrypoint` + `command` split). Original CMD: `["bash", "-c", "/opt/scripts/entrypoint.sh"]`
