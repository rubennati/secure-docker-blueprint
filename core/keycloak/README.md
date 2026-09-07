# Keycloak

Identity and access management: OpenID Connect and SAML for applications that
speak them, user federation from LDAP and Active Directory, social login, and
an admin console for realms, clients, roles and users. Java on Quarkus with
PostgreSQL. Apache-2.0, a CNCF project stewarded by Red Hat.

This is the second identity provider in `core/`, beside
[Authentik](../authentik/). They are alternatives; [Choosing](#choosing-between-keycloak-and-authentik)
below says which fits which situation.

## Architecture

| Service | Image | Purpose |
|---------|-------|---------|
| `keycloak-app` | `quay.io/keycloak/keycloak` | Admin console, realms, OIDC and SAML endpoints on 8080; health on 9000 |
| `db` | `postgres:17` | Realms, clients, users, sessions — on `app-internal` only |

## Setup

```bash
# 1. Create .env
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, TZ

# 2. Secrets and data directories
mkdir -p .secrets volumes/postgres volumes/data
openssl rand -hex 32    | tr -d '\n' > .secrets/db_pwd.txt
openssl rand -base64 24 | tr -d '\n' > .secrets/bootstrap_admin_pwd.txt
chmod 700 .secrets && chmod 600 .secrets/*.txt
sudo chown 1000:0 volumes/data          # the server runs as uid 1000

# 3. Start
docker compose up -d
docker compose logs keycloak-app --follow   # "Keycloak … started in" = up
```

The first start rebuilds the server for the configured database (about 30
seconds), then creates the master realm and a **temporary** administrator from
`BOOTSTRAP_ADMIN_USERNAME` and the password file. Sign in at
`https://<APP_TRAEFIK_HOST>/admin`, create a permanent administrator with the
`admin` role in the master realm, sign in as that user, and delete the
temporary one. Keycloak marks it as temporary in the console until you do.

Then create a realm for your applications. The master realm administers
Keycloak; it is not where clients belong.

## Verify

```bash
docker compose ps                                                  # both healthy
curl -fsSI https://<APP_TRAEFIK_HOST>/admin/                        # 302 to the login
curl -fsS  https://<APP_TRAEFIK_HOST>/realms/master/.well-known/openid-configuration | grep -o '"issuer":"[^"]*"'
```

The issuer must read `https://<APP_TRAEFIK_HOST>/realms/master`. Any other
scheme or host means the proxy headers are not arriving.

## Connecting an application

Every application that speaks OIDC gets a client in your realm: *Clients →
Create client*, type OpenID Connect, the application's redirect URI, client
authentication on. The application receives the issuer URL
(`https://<APP_TRAEFIK_HOST>/realms/<realm>`), the client ID and the secret;
its discovery document tells it everything else.

Keycloak has no proxy of its own. An application without OIDC or SAML cannot
be put behind Keycloak with what this stack ships — that is what Authentik's
embedded outpost and the `sec-authentik` Traefik middleware do.

## Security model

- **The issuer is the hostname.** `KC_HOSTNAME` fixes it, and a request for
  any other host is refused. Behind Traefik the scheme and the client address
  come from `X-Forwarded-*`, which `KC_PROXY_HEADERS=xforwarded` makes the
  server trust from any peer — safe only because no listener is reachable
  except through Traefik. Never publish 8080.
- **Access policy follows the applications.** An identity provider is
  reachable by whatever it protects. The stack ships `acc-tailscale`; a
  Keycloak in front of public applications is public, with CrowdSec ahead of
  it.
- **Secrets through the entrypoint.** `KC_*_FILE` variables are accepted into
  the configuration without a warning and do nothing — `KC_DB_PASSWORD_FILE`
  leaves the driver reporting that no password was provided. The wrapper in
  `config/entrypoint.sh` exports both passwords from `/run/secrets/`.
- **No read-only root filesystem.** `start` rebuilds the application at every
  boot into `/opt/keycloak/lib/quarkus`, and a tmpfs there hides the files it
  builds from. Upstream's answer is a custom image built with `kc.sh build`
  and started with `--optimized`; this stack keeps the official image and
  carries the deviation.
- **Non-root, no capabilities.** The image runs as uid 1000; `cap_drop: ALL`
  holds, and no capability is re-added.
- **Two more listeners inside the container.** Port 9000 serves `/health/*`
  (and `/metrics` when enabled); JGroups opens a discovery port because
  Keycloak assumes it may be clustered. Both are reachable by other containers
  on `proxy-public` and by nothing else. `KC_CACHE=local` would switch the
  cluster off on a single node.
- **No telemetry found.** Nothing in the log, no option for it, no outbound
  connection observed.

## Choosing between Keycloak and Authentik

| | Authentik | Keycloak |
|---|---|---|
| Containers | five: init, PostgreSQL, Redis, server, worker | two: PostgreSQL, server |
| Memory limits as shipped | 2 G server, 2 G worker, 1 G database, 256 M Redis | 1.5 G server, 512 M database |
| Runtime | Python | Java |
| Licence · origin | MIT · Netherlands, EU | Apache-2.0 · US, CNCF |
| Secrets | native `file://` | entrypoint wrapper |
| A login in front of an application that has no OIDC | yes — embedded outpost, wired into Traefik as `sec-authentik` | no — needs a separate proxy such as oauth2-proxy, which this repository does not ship |
| Protocols | OIDC, SAML, LDAP and RADIUS through outposts, SCIM | OIDC, SAML, LDAP and Active Directory federation, SCIM |
| Configuration as code | blueprints, YAML | realm export and import, JSON |
| Telemetry | error reporting, switched off in the compose file | none found |
| Age and ecosystem | since 2019, one company | since 2014, adapters in most application frameworks, Red Hat's supported edition |

**Take Authentik** when the point is putting a login in front of applications
that have none: the proxy path is wired and verified here. **Take Keycloak**
when the applications speak OIDC or SAML themselves and you want the provider
most of them were tested against, when you federate an existing LDAP or
Active Directory, or when Keycloak is already the standard where you work.
Neither is small, and neither is a setting to switch on; running both is a
way to have two places where users exist.

## Backup

| | |
|---|---|
| **Database** | PostgreSQL · container `keycloak-db` · database `keycloak` · user `keycloak` — realms, clients, users, sessions |
| **Password** | `.secrets/db_pwd.txt` |
| **State** | `./volumes/postgres` (database) · `./volumes/data` (import and export staging, otherwise empty) — bind mounts |
| **Reproducible** | `./volumes/data`, when nothing was exported into it |
| **Quiescing** | Not needed for the dump. `kc.sh export` produces a realm-level JSON as a second, portable copy. |

```yaml
postgresql_databases:
    - name: keycloak
      container: keycloak-db
      username: keycloak
      password: "{credential file /srv/docker/core/keycloak/.secrets/db_pwd.txt}"
```

**Restore order:** database, then the container. Keycloak migrates the schema
at boot and refuses to start on a schema newer than its own version.

## Known issues

- **A minor release may migrate the schema and rename options.** Read the
  upgrading guide before moving `APP_TAG`; the checklist is in `UPSTREAM.md`.
- **Cold start is slow.** The rebuild at every boot costs about 30 seconds
  before the server listens; `start_period` in the healthcheck allows for it.
- **The admin console has not been exercised in a browser here.** Boot,
  health, routing and the discovery document have.

## Details

- [UPSTREAM.md](UPSTREAM.md) — source, licence, upgrade checklist
- `docker-compose.local.yml` — the stack on one machine, no proxy
