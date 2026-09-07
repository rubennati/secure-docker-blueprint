# Upstream Reference

## Source

- **Image:** https://quay.io/repository/keycloak/keycloak
- **GitHub:** https://github.com/keycloak/keycloak
- **Docs:** https://www.keycloak.org/guides
- **Release notes:** https://www.keycloak.org/docs/latest/release_notes/
- **License:** Apache-2.0
- **Origin:** US · Red Hat, Inc. (CNCF incubating project) · non-EU
- **Based on version:** `26.7.3`
- **Last verified:** 2026-09-07 (v26.7.3)

What that date covers: boot under `cap_drop: ALL` as uid 1000, the healthcheck
on the management port, Traefik routing under `acc-tailscale`, and the OIDC
discovery document carrying the public issuer. Not covered: the admin console
in a browser, a realm, a client, an application signing in.

## What we use

- The official image, pinned to the patch release, started with `kc.sh start`
  — production mode, not `start-dev`
- `postgres:17-alpine` as the database, `KC_DB=postgres`
- The image's own `kc.sh` behind the secret-injection entrypoint

## Architecture

```text
Client → Traefik (TLS, 443) → keycloak-app :8080  (admin console, realms, OIDC/SAML endpoints)
                                    ├─ :9000        (health — no router, containers only)
                                    └─ db :5432     (keycloak-internal)
```

## What we changed and why

| Change | Reason |
|--------|--------|
| `config/entrypoint.sh` | `KC_*_FILE` is silently ignored: `KC_DB_PASSWORD_FILE` appears in `kc.sh show-config` and the driver still reports no password; `KC_BOOTSTRAP_ADMIN_PASSWORD_FILE` leaves the bootstrap admin unset and the start fails |
| `cap_drop: ALL`, nothing re-added | Both ports are above 1024; verified by boot |
| No `read_only` | `start` writes the rebuilt application to `/opt/keycloak/lib/quarkus` at every boot; a tmpfs there shadows the files it builds from and fails the same way. The official image cannot run read-only |
| `KC_HOSTNAME` as a full URL, `KC_PROXY_HEADERS=xforwarded`, `KC_HTTP_ENABLED=true` | Traefik terminates TLS; the issuer and every redirect derive from the public URL |
| `KC_HEALTH_ENABLED=true`, healthcheck through `bash /dev/tcp` | The image ships neither curl nor wget; the management port answers `/health/ready` |
| Traefik labels, `acc-tailscale`, `sec-2-spa` | Blueprint standard; the admin console is a single-page application |

## Upgrade checklist

1. Release notes, and the upgrading guide at
   https://www.keycloak.org/docs/latest/upgrading/ — a minor release may
   migrate the schema and rename options, and options that vanish are
   reported as errors at start
2. Back up the database; `kc.sh export --dir /opt/keycloak/data/export` for a
   realm-level copy
3. `APP_TAG` in `.env.example` and `.env`; `docker compose pull && docker compose up -d`
4. `docker compose logs keycloak-app | grep -E 'started in|Migrat'`; sign in;
   one application still authenticates

## Useful commands

```bash
docker compose logs keycloak-app --follow
docker compose exec keycloak-app /opt/keycloak/bin/kc.sh show-config
docker compose exec keycloak-app /opt/keycloak/bin/kc.sh export --dir /opt/keycloak/data/export --users skip
```
