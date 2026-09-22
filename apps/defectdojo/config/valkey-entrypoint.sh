#!/bin/sh
set -e

# Valkey takes its password as a command-line argument, which would be visible in
# the process list. Write a config file to tmpfs instead and start from it.
umask 077
{
  printf 'requirepass %s\n' "$(cat /run/secrets/VALKEY_PWD)"
  printf 'maxmemory-policy noeviction\n'
  printf 'dir /data\n'
} > /tmp/valkey.conf

exec valkey-server /tmp/valkey.conf
