#!/bin/sh
set -e

# RabbitMQ 3.13 rejects RABBITMQ_DEFAULT_PASS_FILE: the entrypoint lists it
# among deprecated variables and exits with
# `error: RABBITMQ_DEFAULT_PASS_FILE is set but deprecated`. The alternative it
# suggests is a configuration file — which would put the password in a file on
# the host. Exporting it here keeps it in the container.

_rabbitmq_password="$(cat /run/secrets/RABBITMQ_PASSWORD)"
export RABBITMQ_DEFAULT_PASS="$_rabbitmq_password"
unset _rabbitmq_password

exec docker-entrypoint.sh "$@"
