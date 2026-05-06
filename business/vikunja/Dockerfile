# vikunja/vikunja is based on scratch — no shell, no utilities.
# We add a minimal POSIX shell from busybox so that the secrets-injection
# entrypoint (config/entrypoint.sh) can run without plain-text credentials
# in environment variables.
#
# Only /bin/sh is copied — nothing else from busybox is included.
ARG APP_TAG=2.3.0
FROM busybox:musl AS shell
FROM vikunja/vikunja:${APP_TAG}
COPY --from=shell /bin/sh /bin/sh
