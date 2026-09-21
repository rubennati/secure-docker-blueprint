#!/bin/sh
set -e

# Redis takes its password as a command-line argument, which would be visible in
# the process list. Write a config file to tmpfs instead and start from it.
#   cache — nothing persisted, least recently used keys evicted at the limit
#   queue — persisted to /data, nothing evicted: jobs must not be lost
umask 077
{
  printf 'requirepass %s\n' "$(cat /run/secrets/REDIS_PWD)"
  case "$1" in
    cache)
      printf 'maxmemory 256mb\nmaxmemory-policy allkeys-lru\n'
      printf 'save ""\nappendonly no\ndir /tmp\n'
      ;;
    queue)
      printf 'maxmemory-policy noeviction\ndir /data\n'
      ;;
    *)
      echo "usage: redis-entrypoint.sh cache|queue" >&2
      exit 1
      ;;
  esac
} > /tmp/redis.conf

exec redis-server /tmp/redis.conf
