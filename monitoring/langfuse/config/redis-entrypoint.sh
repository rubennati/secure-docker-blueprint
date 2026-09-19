#!/bin/sh
set -e

# Redis takes its password as a command-line argument, which would be visible in
# the process list. Write a config file to tmpfs instead and start from it.
umask 077
{
  printf 'requirepass %s\n' "$(cat /run/secrets/REDIS_AUTH)"
  printf 'maxmemory-policy noeviction\n'
  printf 'dir /data\n'
} > /tmp/redis.conf

exec redis-server /tmp/redis.conf
