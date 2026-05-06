# vikunja/vikunja is FROM scratch — no shell, no utilities.
# We add the minimum needed from busybox:musl:
#   /bin/sh   — for the secrets-injection entrypoint
#   /bin/cat  — for reading Docker Secret files in the entrypoint
#
# We also fix /app/vikunja/files permissions:
# The upstream image leaves the directory root-owned (uid=0 gid=0, mode 755).
# Vikunja runs as uid=1000 gid=0 — chmod g+w gives the process write access
# without a full chown (group 0 = root group, which the process already has).
ARG APP_TAG=2.3.0
FROM busybox:musl AS shell
FROM vikunja/vikunja:${APP_TAG}
COPY --from=shell /bin/sh /bin/sh
COPY --from=shell /bin/cat /bin/cat
COPY --from=shell /bin/chmod /bin/chmod
USER 0
RUN ["/bin/chmod", "g+w", "/app/vikunja/files"]
RUN ["/bin/sh", "-c", "rm /bin/chmod"]
USER 1000
