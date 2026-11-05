# Upstream Reference

## Source

- **Image:** https://quay.io/repository/keycloak/keycloak
- **GitHub:** https://github.com/keycloak/keycloak
- **Docs:** https://www.keycloak.org/guides
- **Release notes:** https://www.keycloak.org/docs/latest/release_notes/
- **License:** Apache-2.0
- **Decision facts checked:** not yet
- **Origin:** US · Red Hat, Inc. (CNCF incubating project) · non-EU
- **Domain:** Identity, access and secrets
- **Role:** Identity provider for applications that speak OpenID Connect or SAML, with LDAP and AD federation
- **Based on version:** `26.8.1`
- **Last verified:** 2026-09-07 (v26.7.3)

What that date covers: boot under `cap_drop: ALL` as uid 1000, the healthcheck
on the management port, Traefik routing under `acc-tailscale`, and the OIDC
discovery document carrying the public issuer. Not covered: the admin console
in a browser, a realm, a client, an application signing in.

## What we use

- The official image, pinned to the patch release, started with `kc.sh start`
  — production mode, not `start-dev`
- `postgres:17.11-alpine` as the database, `KC_DB=postgres`
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
| Traefik labels, `access-vpn`, `limit-standard`, `headers-application-owned` with `header-permissions@file` before it | Blueprint standard; the admin console is a single-page application and sets its own headers, lacking only the `Permissions-Policy` |

## Version notes

- Moved to `26.8.1` on 2026-11-05 (released 2026-10-13), not run on a host at
  this tag; 26.7.4, 26.7.5 and 26.8.0 lie between. Every statement above marked
  "verified against 26.7.3" — no working `_FILE` variant, the rebuild into
  `lib/quarkus` at every start — is a record of 26.7.3 and is not yet verified on
  26.8.1. No option this stack sets is renamed or removed. 26.8.0 changes
  behaviour: a client's secret is hidden from callers with only `view-clients`;
  disabled clients are left out of the `aud` claim; identity provider mappers
  cannot grant admin roles unless `allowAdminRoleMapping` is set; refresh tokens
  expire no later than the session idle timeout; login failures are stored in the
  database; `client-secret-rotation` and `scim-api` are enabled by default;
  organization identity provider links are migrated to many-to-many at start;
  offline session indexes are rebuilt at start (above 300,000 rows the SQL is
  logged for a manual run); Quarkus 3.33 to 3.40; the login page's identity
  provider buttons are redesigned, which can break custom themes. Upgrading
  guide: https://www.keycloak.org/docs/latest/upgrading/. Advisories fixed —
  26.7.4: CVE-2026-90997 (GHSA-xpwp-2pcm-8xq3), CVE-2026-79651, CVE-2026-74909,
  CVE-2026-19607, CVE-2026-17526, CVE-2026-18212; 26.7.5: CVE-2026-16103,
  CVE-2026-18206, CVE-2026-18203, CVE-2026-18207, CVE-2026-18208,
  CVE-2026-18211, CVE-2026-18217, CVE-2026-89298, CVE-2026-88770,
  CVE-2026-93999 and dependency CVEs; 26.8.1: CVE-2026-15943, CVE-2026-18569,
  CVE-2026-82968, CVE-2026-94001, CVE-2026-94000, CVE-2026-94218,
  CVE-2026-94215, CVE-2026-94213, CVE-2026-94217, CVE-2026-96446,
  CVE-2026-96445, CVE-2026-97177, CVE-2026-95503, CVE-2026-97311,
  CVE-2026-97846, CVE-2026-101333, CVE-2026-103884, CVE-2026-107121 and
  dependency CVEs.

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
