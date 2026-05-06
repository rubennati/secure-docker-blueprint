# vikunja/vikunja is FROM scratch — no shell, no utilities.
# We add the minimum needed from busybox:musl:
#   /bin/sh  — for the secrets-injection entrypoint
#   /bin/cat — for reading Docker Secret files in the entrypoint
#
# We also fix /app/vikunja/files ownership.
# FROM scratch images have no /etc/passwd — USER + RUN fails with
# "unable to find user" for both names and numeric UIDs.
# COPY --chown sets directory ownership in the new image layer without
# executing any commands, which works on scratch-based images.
ARG APP_TAG=2.3.0
FROM busybox:musl AS shell
RUN mkdir /files-init

FROM vikunja/vikunja:${APP_TAG}
COPY --from=shell /bin/sh /bin/sh
COPY --from=shell /bin/cat /bin/cat
# Create /app/vikunja/files owned by uid=1000 gid=0.
# Vikunja runs as uid=1000 — without this the named volume is initialized
# root-owned and Vikunja fails with "permission denied" on startup.
COPY --chown=1000:0 --from=shell /files-init /app/vikunja/files
