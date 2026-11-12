# Seafile Pro

Cloud file storage with collaboration, search, and antivirus scanning.

Project, source, licence and origin: [`UPSTREAM.md`](UPSTREAM.md).

## Services

| Service | Image | Purpose |
|---|---|---|
| seafile-pro-app | seafile-pro-mc | Main Seafile server |
| db | mariadb | Database |
| redis | redis | Cache/Sessions |
| seafile-pro-seadoc | sdoc-server | Collaborative document editing |
| seafile-pro-notification | notification-server | Real-time file change updates |
| md-server | seafile-md-server | File metadata management |
| seafile-pro-thumbnail | thumbnail-server | Image/video previews |
| seasearch | seasearch | Full-text search |
| clamav | clamav | Antivirus scanning |

## Try it locally

Runs on `http://127.0.0.1:8001` without Traefik, DNS or a certificate.

```bash
# Local settings; the secrets ship empty, so fill the ones this stack needs
cp .env.local.example .env.local
printf 'INIT_SEAFILE_MYSQL_ROOT_PASSWORD=%s\n' "$(openssl rand -base64 32 | tr -d '\n')" >> .env.local
printf 'SEAFILE_MYSQL_DB_PASSWORD=%s\n' "$(openssl rand -base64 32 | tr -d '\n')" >> .env.local
printf 'REDIS_PASSWORD=%s\n' "$(openssl rand -hex 32)" >> .env.local
printf 'INIT_SEAFILE_ADMIN_PASSWORD=%s\n' "$(openssl rand -base64 32 | tr -d '\n')" >> .env.local
printf 'JWT_PRIVATE_KEY=%s\n' "$(openssl rand -base64 48 | tr -d '\n')" >> .env.local

mkdir -p volumes/local/mysql volumes/local/redis volumes/local/seafile-data
sudo chown 999:999 volumes/local/mysql   # the mariadb image's mysql user — the db service has no CHOWN
docker compose -f docker-compose.local.yml --env-file .env.local up -d
# http://127.0.0.1:8001
docker compose -f docker-compose.local.yml --env-file .env.local down
```

`.env.local` holds plain values, not Docker Secrets — local only.

## Quick Start

```bash
# 1. Copy and configure
cp .env.example .env
nano .env  # Set APP_TRAEFIK_HOST, SEAFILE_ADMIN_EMAIL, ONLYOFFICE_HOST, TZ

# 2. Create the secrets (Docker Secrets in .secrets/, see Secrets below)
mkdir -p .secrets
openssl rand -base64 32 | tr -d '\n' > .secrets/db_root_pwd.txt
openssl rand -base64 32 | tr -d '\n' > .secrets/seafile_db_pwd.txt
openssl rand -base64 24 | tr -d '\n' > .secrets/seafile_admin_pwd.txt
openssl rand -base64 48 | tr -d '\n' > .secrets/jwt_key.txt
openssl rand -hex 32    | tr -d '\n' > .secrets/redis_pwd.txt
# OnlyOffice JWT secret — copy from the OnlyOffice server (must match exactly);
# an empty file keeps the integration off. SMTP password — empty without SMTP.
: > .secrets/onlyoffice_jwt_secret.txt
: > .secrets/smtp_pwd.txt
chmod 600 .secrets/*.txt

# 3. Pull images
docker compose pull

# 4. Start
docker compose up -d

# 5. Wait for app healthy (first boot initialises databases — takes ~3 min)
docker compose ps

# 6. Inject Blueprint configs (runs once — see Config injection)
docker compose restart seafile-pro-app

# 7. Build search index
docker exec seafile-pro-app /opt/seafile/seafile-server-latest/pro/pro.py search --update
```

## Verify

```bash
docker compose ps                                          # All services up
docker exec seafile-pro-app grep "SEASEARCH" /shared/seafile/conf/seafevents.conf  # Search configured
docker exec seafile-pro-app grep "virus_scan" /shared/seafile/conf/seafile.conf    # Antivirus configured
curl -s https://your-domain/notification/ping              # {"ret": "pong"}
docker exec seafile-pro-app grep "Blueprint" /shared/seafile/conf/seahub_settings.py   # settings injected
docker exec seafile-pro-app sh -c 'tr "\0" "\n" < /proc/$(pgrep -f "gunicorn.*seahub" | head -1)/environ | grep -c ^JWT_PRIVATE_KEY='   # 1: the key reaches Seahub
docker exec seafile-pro-app bash -c "curl -s https://secure.eicar.org/eicar.com.txt | clamdscan -"  # FOUND
```

## OnlyOffice

OnlyOffice needs a server-to-server network path to Seafile's configured hostname (`APP_TRAEFIK_HOST`). This path can be public internet, Tailscale, or any direct route. If DNS for `APP_TRAEFIK_HOST` resolves to a Tailscale address on the OnlyOffice server, traffic routes via Tailscale automatically — no public internet exposure required.

**The integrations call back past a closed policy, each by its own mechanism.** No closed policy — `access-vpn`, `access-trusted`, `access-trusted-vpn` — admits a request from a Docker container ([DEC-076](../../.ai/decisions.md#dec-076)). SeaDoc calls Seafile over the internal network (`SEAHUB_SERVICE_URL` in `seadoc.yml`) and needs nothing. OnlyOffice fetches the document from `/seafhttp/files/<token>/…` and saves by calling `/onlyoffice/editor-callback/`, both at Seafile's public name, the only address Seafile hands it; the token is a fileserver access token valid for one hour, and the callback is acted on only for a document key Seafile issued — seahub verifies no JWT on it. `onlyoffice-callback.yml` opens exactly those two paths with `access-public`; a Document Server on another host reaches a closed instance instead when its address is in `TRUSTED_RANGES` or on the VPN. Add the file to `COMPOSE_FILE` when you run OnlyOffice; the rest of the instance stays closed (`apps/seafile/README.md`, "Access policy", has the detail).

**`APP_TRAEFIK_ACCESS` is a Traefik middleware setting, not a network exposure setting.** `access-public` removes Traefik's source-IP allowlist; it does not bypass upstream firewalls. `access-vpn` enforces a source-IP allowlist but may reject Tailscale-routed traffic if Docker bridge masquerades the source IP before Traefik sees it — see `UPSTREAM.md` and `TROUBLESHOOTING.md §4.4` for the known caveat and investigation steps.

On the OnlyOffice server, add the Seafile domain to `ONLYOFFICE_ALLOWED_ORIGINS` so browsers can embed the editor in an iframe — see `apps/onlyoffice/.env.example`. **Changes to `ONLYOFFICE_ALLOWED_ORIGINS` require container recreation** (`docker compose up -d --force-recreate` on the OnlyOffice server), not just restart — the value is baked into a Traefik label at container creation time.

## Secrets

Every password and key is a Docker Secret in `.secrets/` (gitignored); `.env.example`
lists the seven files and how to create them. Seafile's services read these values from
the environment only and know no `_FILE` variant, so `config/secrets-env.sh` runs in
front of each service: it exports the secrets that container mounts under the names the
service reads, then starts the image's own command. The values reach the service's
processes, including those `my_init` starts, and stand neither in `.env` nor in
`docker inspect`.

`docker exec <container> env` does not show them: it lists the container's configured
environment, not that of the running service. Check a process instead, as in Verify.

The MariaDB container reads `MYSQL_ROOT_PASSWORD_FILE` itself; Redis reads its password
from the secret file in its command.

## Config injection

`config/seahub_custom.py` is appended to `seahub_settings.py` **once** — on the container start after first boot creates the config files. After that initial injection, the marker prevents it from running again.

Settings that use `os.environ.get()` (OnlyOffice URL, SMTP host, etc.) are evaluated at Django startup on every restart, so changing those values in `.env` takes effect after `docker compose restart seafile-pro-app` — no re-injection needed.

Adding a brand-new setting that was absent from `seahub_custom.py` at injection time requires either editing `seahub_settings.py` directly in the volume, or removing the marker line (`# --- Blueprint custom settings ---`) and everything after it, updating `config/seahub_custom.py`, then restarting.

`seafevents.conf` (SeaSearch) and `seafile.conf` (ClamAV) are injected the same way, once, each behind its own marker.

## Backup

| | |
|---|---|
| **Database** | MariaDB · container `seafile-pro-db` · **three databases**: `ccnet_db`, `seafile_db`, `seahub_db` · user `seafile` |
| **Password** | `.secrets/seafile_db_pwd.txt` — the file the borgmatic snippet below reads |
| **State** | `./volumes/mysql` (databases) · **`./volumes/seafile-data`** — the file store · `./volumes/seadoc-data` |
| **Reproducible** | `./volumes/redis` (cache) · the Elasticsearch volume · `./volumes/seasearch-data` — both search indexes, rebuildable |
| **Quiescing** | Not needed for the dumps. Content-addressed blocks tolerate a mid-write copy. |

```yaml
mariadb_databases:
    - name: ccnet_db
      container: seafile-pro-db
      username: seafile
      password: "{credential file /srv/docker/apps/seafile-pro/.secrets/seafile_db_pwd.txt}"
    - name: seafile_db
      container: seafile-pro-db
      username: seafile
      password: "{credential file /srv/docker/apps/seafile-pro/.secrets/seafile_db_pwd.txt}"
    - name: seahub_db
      container: seafile-pro-db
      username: seafile
      password: "{credential file /srv/docker/apps/seafile-pro/.secrets/seafile_db_pwd.txt}"
```

**Three databases, not one** — `ccnet_db` for users and groups, `seafile_db` for
file metadata, `seahub_db` for the web layer and shares. Any one missing restores
to something that starts and does not work.

The two search indexes are excluded deliberately and cost a reindex after a
restore. Until it completes, search returns nothing while every file is present —
which looks like data loss and is not.

**Restore order:** databases first, then the block store, then the app, then
trigger the reindex.

A dump holds the databases, not the account Seafile connects with. Restored into a
fresh `db` container, the app starts and every request fails with `Access denied
for user 'seafile'`. Create the account before starting the app:

```bash
docker compose up -d db
# restore the three dumps, then:
docker compose exec -T db sh -c 'mariadb -uroot -p"$(cat /run/secrets/DB_ROOT_PWD)"' <<SQL
CREATE USER IF NOT EXISTS 'seafile'@'%' IDENTIFIED BY '$(cat .secrets/seafile_db_pwd.txt)';
GRANT ALL PRIVILEGES ON ccnet_db.* TO 'seafile'@'%';
GRANT ALL PRIVILEGES ON seafile_db.* TO 'seafile'@'%';
GRANT ALL PRIVILEGES ON seahub_db.* TO 'seafile'@'%';
SQL
docker compose up -d
```

## Open findings

<!-- findings:start — generated by scripts/ci/lifecycle-report.py from upstream-status.json; edit the text around it -->

**Findings in the upstream images** at the pin `13.0.29` — upstream has released `14.0.9` since. Scanned 2026-11-09; counted are findings with a published fix, as CRITICAL · HIGH. They come with the images as upstream publishes them.

| Image | Base system | Libraries | Programs |
|---|---|---|---|
| `clamav/clamav:1.5.4` | — | — | — |
| `elasticsearch:8.19.23` | 0 · 1 | 0 · 3 | — |
| `mariadb:10.11.19` | 0 · 1 | — | 1 · 25 |
| `redis:8.10.3-alpine` | — | — | — |
| `seafileltd/notification-server:13.0.29` | 0 · 1 | — | — |
| `seafileltd/sdoc-server:2.0.11` | 0 · 1 | 2 · 40 | — |
| `seafileltd/seafile-ai:13.0.10` | 10 · 616 | 11 · 71 | — |
| `seafileltd/seafile-md-server:13.0.28` | 0 · 2 | — | 0 · 25 |
| `seafileltd/seafile-pro-mc:13.0.29` | 0 · 1 | 0 · 16 | 0 · 1 |
| `seafileltd/seasearch:1.0.8` | 0 · 2 | — | 0 · 13 |
| `seafileltd/thumbnail-server:13.0.29` | 0 · 1 | 1 · 14 | — |

<!-- findings:end -->

The findings of the community edition apply here too: PyJWT CVE-2026-102268 and
`proxy-addr` CVE-2026-90711 in SeaDoc 2.0.11, PyJWT in the thumbnail server
13.0.29, and the `gosu` helper in MariaDB 10.11 (CVE-2025-68121). The optional
Seafile AI image 13.0.10 carries 21 CRITICAL vulnerabilities, among them LiteLLM
authentication bypasses and Pillow image-decoding overflows; no newer Seafile 13
build of it exists, and Seafile 14 is not yet stable.

**Risk:** as in `apps/seafile` for the core images. Seafile AI is off by default
and not part of `COMPOSE_FILE`; once enabled, its findings are reachable. Leave
it off unless you need it, and watch for a stable Seafile 14.

## Details

- [UPSTREAM.md](UPSTREAM.md) — Full setup guide, troubleshooting, upgrade checklist
- [docs/bugfixes/seafile-pro-2026-04-13.md](../../docs/bugfixes/seafile-pro-2026-04-13.md) — Known issues and fixes
