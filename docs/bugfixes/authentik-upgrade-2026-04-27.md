# Authentik — version-jump migration failure — 2026-04-27

## Symptom

Upgrading from `2024.12.3` directly to `2026.2.2`. Both `server` and
`worker` enter a crash loop on every startup. The migration
`authentik_core.0056_user_roles` fails with:

```
django.core.exceptions.FieldError: Cannot resolve keyword 'group_id'
into field. Choices are: ak_groups, initialpermissions, managed, name,
rolemodelpermission, roleobjectpermission, users, uuid
```

Gunicorn dies immediately after:

```
authentik-server | gunicorn process died, restarting
authentik-server | gunicorn failed to start, restarting
```

## Root cause

Migration `0056_user_roles` was written against an intermediate schema
state that existed between `2024.12` and `2026.2`. The migration
filters `Role.objects.filter(group_id=group_id)`, but `group_id` was
removed from the `Role` model in a version between the two. When
jumping directly from `2024.12.3` to `2026.2.2`, the migration runs
against a schema that has already had `group_id` removed — the field
no longer exists and Django raises a `FieldError`.

This is the standard Django migration hazard when skipping multiple
major versions: intermediate data-migration scripts that reference
fields only present in the intermediate schema will fail against a
schema built from scratch at the target version.

## Fix

**For a blueprint test environment (no production data):**

```bash
cd core/authentik
docker compose down
rm -rf volumes/postgres volumes/data volumes/redis
docker compose up -d
docker compose logs -f
```

A fresh database has no intermediate migration state to confuse.
All migrations run from `0001` in order and succeed cleanly.

**For a production environment with existing user data:**

Upgrade incrementally through each major release:

```
2024.12.x → 2025.2.x → 2025.6.x → 2025.10.x → 2026.2.x
```

Start each intermediate version, let all migrations complete, verify
the app starts cleanly, then move to the next version.

## Lesson for the blueprint

Always test upgrades on a clean copy of the data volume before
applying to production. The `.env.example` pins to a specific tested
version — the reason is exactly this: untested version jumps can break
migration paths with no obvious fix except a data restore.

## Verify (after fresh start)

```bash
docker compose ps
# Expected: server = Up (healthy), worker = Up, db = healthy, redis = healthy

curl -fsSI https://<APP_TRAEFIK_HOST>/-/health/live/
# Expected: HTTP/2 200

# Initial-setup flow reachable:
# https://<APP_TRAEFIK_HOST>/if/flow/initial-setup/
```
