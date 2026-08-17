# vikunja/vikunja is FROM scratch — no shell, no utilities.
# We add the minimum needed from busybox:musl:
#   /bin/sh   — for the secrets-injection entrypoint
#   /bin/cat  — for reading Docker Secret files in the entrypoint
#   /bin/wget — for the HTTP healthcheck
#              (`vikunja healthcheck` spawns a new process without the
#               env vars set by the entrypoint, so it fails DB auth.
#               An HTTP check against the running server is more reliable.)
#
# We also fix /app/vikunja/files ownership.
# FROM scratch images have no /etc/passwd — USER + RUN fails with
# "unable to find user" for both names and numeric UIDs.
# COPY --chown sets directory ownership in the new image layer without
# executing any commands, which works on scratch-based images.
# Both the tag and the digest come from .env, which is where this repository
# keeps a pin. The tag alone is mutable — a registry push can replace it without
# the name changing — so the digest is what actually fixes the image, and the tag
# stays because it is the readable half. Re-resolve both together on an upgrade:
#   docker buildx imagetools inspect vikunja/vikunja:<tag> --format '{{.Manifest.Digest}}'
ARG APP_TAG=2.3.0
ARG APP_DIGEST=sha256:f6b80393c1998cd5cd0dc38d24762c59ab4c10000a6f1032ef5b554e262cab93
FROM busybox:1.38.0-musl@sha256:8635836765b0c4c43970660219739baa58b0883c2e429e4b8918f7dd1519455c AS shell
RUN mkdir /files-init

FROM vikunja/vikunja:${APP_TAG}@${APP_DIGEST}
COPY --from=shell /bin/sh /bin/sh
COPY --from=shell /bin/cat /bin/cat
COPY --from=shell /bin/wget /bin/wget
# Create /app/vikunja/files owned by uid=1000 gid=0.
# Vikunja runs as uid=1000 — without this the named volume is initialized
# root-owned and Vikunja fails with "permission denied" on startup.
COPY --chown=1000:0 --from=shell /files-init /app/vikunja/files
# HTTP healthcheck via wget (busybox). The compose healthcheck mirrors this;
# Compose overrides the Dockerfile instruction at runtime.
HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=30s \
  CMD ["/bin/wget", "-qO-", "http://localhost:3456/api/v1/info"]
# Upstream vikunja/vikunja runs as uid=1000; declare it explicitly so
# static analysis tools do not report an implicit root user.
USER 1000
