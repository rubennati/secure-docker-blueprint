# Leantime

Project management for teams without a project manager — projects, milestones,
tasks, time tracking, retrospectives and goals, with a deliberate focus on
people who find conventional project tools hard to stay in. Upstream:
[leantime/leantime](https://github.com/leantime/leantime).

Single sign-on is part of the open-source core here, not a paid add-on: OIDC
and LDAP are configuration. Neither has been exercised in this stack.

## Architecture

```text
Traefik ──http──→ leantime-app :8080          (nginx + php-fpm + scheduler)
                        │
                        └──→ leantime-db :3306 (MySQL, app-internal only)

volumes/userfiles         attachments
volumes/public-userfiles  logo and anything served without a session
volumes/storage           Laravel cache, compiled views, session files
volumes/plugins           whatever is installed from the marketplace
volumes/mysql             the database
```

Everything Leantime holds is in the database. The four application volumes hold
uploads and derived state.

## Setup

The order matters. Until the schema exists, Leantime answers an
**unauthenticated installer form** that creates the first account — the owner.
Creating the schema from the command line first means that form never has
anything to do:

```bash
cp .env.example .env            # host name, site name, language
ops/init.sh                     # secrets and volume directories
sudo chown -R 1000:1000 volumes/userfiles volumes/public-userfiles \
    volumes/storage volumes/plugins

docker compose up -d leantime-db     # the database alone
ops/install.sh                       # prompts for the administrator
docker compose up -d                 # now the application
```

`ops/install.sh` prompts for the administrator's email, password, name and
company and passes none of them as arguments, so the password stays out of the
process list and out of your shell history.

### Updating

`ops/install.sh` is also the migration step: on a populated database
`db:migrate` applies what is pending and creates nothing. Run it after every
`docker compose pull`.

### Running a command by hand

`/start.sh` ignores its arguments — it always execs supervisord — so a plain
`docker compose exec … php bin/leantime …` reaches the database with no
password. The `LEAN_*_FILE` variables have to be resolved first, which is what
`ops/install.sh` does; copy its shell wrapper for any other command.

## Try it locally

Runs on `http://localhost:8080` without Traefik, and here the web installer is
what sets it up — on a loopback port that is fine.

```bash
cp .env.local.example .env.local
mkdir -p .secrets volumes/mysql volumes/userfiles volumes/public-userfiles \
    volumes/storage volumes/plugins
openssl rand -hex 24 | tr -d '\n' > .secrets/db_pwd.txt
openssl rand -hex 24 | tr -d '\n' > .secrets/db_root_pwd.txt
openssl rand -hex 32 | tr -d '\n' > .secrets/session_password.txt
docker compose -f docker-compose.local.yml --env-file .env.local up -d
# http://localhost:8080 — the installer creates the administrator and hands
# out an invite link to set the password
docker compose -f docker-compose.local.yml --env-file .env.local down
```

## Security model

- **The installer is closed before the host name is live.** `ops/install.sh`
  creates the schema and the owner from the command line. This matters more
  than it looks: the installer form is served *even after installation* —
  upstream's guard returns a redirect that the framework discards — so the page
  is reachable for as long as the router is. It cannot take over an instance
  that already has a schema (the re-run aborts on the first `CREATE TABLE`,
  measured), but on an empty one it hands out ownership to whoever asks first.
- **`acc-tailscale` by default**, because a project management instance holds
  the customer names, rates and deadlines of everything the company runs.
- **Both outbound calls are off.** Telemetry posts to `telemetry.leantime.io`
  once a day from the scheduler; the news panel pulls an RSS feed from
  `leantime.io`. Upstream ships telemetry on — `LEAN_ALLOW_TELEMETRY=false` and
  `LEAN_NEWS_ENABLED=false` turn both off, verified against the effective
  configuration. Installing a plugin still contacts `marketplace.leantime.io`,
  because that is what the marketplace is.
- **`read_only: true`, `cap_drop: ALL`, `no-new-privileges`, non-root** —
  verified against 3.9.8. Four bind mounts and four tmpfs are the only writable
  paths; upstream's own compose example grants CHOWN, SETGID and SETUID, and
  none of them are needed.
- **The database is on `app-internal`** with no published port, reachable only
  from the application container.
- **Session cookies** are `secure; httponly; samesite=lax`, and the salt is a
  Docker Secret rather than the fixed one in upstream's sample configuration.

## Known limits

- **`sec-2` is not measured against this application.** The chain ships as the
  default for a new app; no page of Leantime's has been loaded through it.
- **Mail is not configured.** The scheduler sends notifications and a daily
  digest, and without `LEAN_EMAIL_*` they go nowhere. The image reads
  `LEAN_EMAIL_SMTP_PASSWORD_FILE`, so an SMTP password can be a Docker Secret
  like the others — see `config/sample.env` in the image for the full set.
- **OIDC and LDAP are untested here**, though both are in the core.
- **Plugins are a paid marketplace.** The platform is free and AGPL; the
  advanced functionality is not. `volumes/plugins` exists so that what you buy
  survives a recreate.
- **Nothing here has run behind this repository's Traefik yet.** The stack is
  `scaffolded`.

## Backup

| | |
|---|---|
| **The database** | `./volumes/mysql` — everything the application holds. Dump it rather than copying the files: `docker compose exec leantime-db sh -c 'mysqldump -u root -p"$(cat /run/secrets/DB_ROOT_PWD)" --single-transaction leantime' > leantime.sql` |
| **Uploads** | `./volumes/userfiles` and `./volumes/public-userfiles` — file attachments and the logo. Not in the database |
| **Bought** | `./volumes/plugins` — marketplace plugins, which are licensed rather than reproducible |
| **The key** | `.secrets/session_password.txt` — not a data key. Losing it signs everyone out; it does not lose anything |
| **Reproducible** | `./volumes/storage` — cache, compiled views and sessions |
| **Quiescing** | `--single-transaction` is enough for InnoDB. Copying `volumes/mysql` from a running container is not |

```yaml
# /etc/borgmatic/config.yaml
source_directories:
  - /srv/secure-docker-blueprint/business/leantime/volumes/userfiles
  - /srv/secure-docker-blueprint/business/leantime/volumes/public-userfiles
  - /srv/secure-docker-blueprint/business/leantime/volumes/plugins
```

Restore: put the volumes back with their ownership at `1000:1000`, restore the
secrets, start the database, load the dump, then start the application.
