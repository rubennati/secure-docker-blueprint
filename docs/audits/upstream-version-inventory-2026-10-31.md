# Upstream version inventory and update programme — 2026-10-31

What every image pin in the tree stands against upstream on 2026-10-31, and the
order in which the pins move. The inventory is a snapshot and the programme is a
plan; neither moves a pin. A pin moves through the Version Chain in
[`../maintenance.md`](../maintenance.md#version-chain), one stack per commit, and
the record of each move is the stack's `UPSTREAM.md` and `CHANGELOG.md`.

## How the inventory was taken

For each of the 201 image references `scripts/ci/list-images.sh` resolves, the
newest tag on the registry with the same shape as the pin: the same `v` prefix,
the same suffix (`-alpine`, `-slim`, `-pg16`), the same number of version
components, and no pre-release marker (`rc`, `beta`, `alpha`, `dev`, `nightly`).
Docker Hub and ghcr.io answered; quay.io, lscr.io, docker.elastic.co,
docker.langfuse.com, public.ecr.aws and cr.agentgateway.dev were not reachable
from the session that took the inventory, and those pins stand under *Not
checked*. A tag whose shape is not a version (`alpine-7.0.31`,
`version-v26.05.4`, a date, `RELEASE.…`) is not compared.

`CRITICAL pairs` is the count for the image repository in `.trivy-baseline.json`
after the scan of 2026-10-31. It says how many known CRITICAL findings the
current pin carries. It does not say how many a newer tag removes: only a scan of
the new tag shows that, and most of the pairs are packages of the base image,
which a newer application release removes only when upstream rebuilt on a newer
base.

Totals: 35 patch · 69 minor · 43 major · 30 current ·
24 not checked or not compared. A *patch* row shares major and minor
with the pin; a *minor* row shares the major; a *major* row is a release-line
change, which for a database is a data migration and never a pin bump alone.
The state in the last column is the stack's state in `LIFECYCLE.md` on
2026-10-31 before batch 1.

## The programme

### Rules that hold for every batch

1. **One pull request per batch, one commit per stack**, each commit moving
   `.env.example` and `.env.local.example` together and recording the move under
   *Version notes* in the stack's `UPSTREAM.md`: date, from and to, what
   upstream's release notes say about breaking changes, migrations, variables
   and advisories, and whether the stack ran at the new tag.
2. **The measurement is the image scan of the pull request from `dev` to
   `main`**, which runs in full when an `.env.example` changed. The baseline
   record that follows it states which recorded pairs the new tags removed and
   which they did not (DEC-043). A batch is not judged by how many pairs it
   removes; it is judged by whether every move is recorded.
3. **A `baseline-aligned` stack keeps its state only with a host run at the new
   tag** in the same batch, because `Last verified` names a version and the
   lifecycle report marks a newer pin as `pin-drifted`. A batch that moves such a
   stack is a host session, or it accepts the fall to `scaffolded` and says so,
   as batch 1 did for `monitoring/changedetection` and `business/invoiceninja`.
4. **A major release is a decision per stack, not a bump.** The decision names
   the migration path in `UPSTREAM.md` before the pin moves, and a database
   family moves once, with one procedure, not twelve times.
5. **`LIFECYCLE.md`, `site/src/data/lifecycle.json` and
   `site/src/data/catalogue.json` are regenerated in the batch's last commit**
   (`lifecycle-report.py --write`, `site-catalogue.py`), and the checkers run
   before the push.

### Batch 1 — the seven patch releases with the most recorded pairs (done)

`monitoring/uptime-kuma`, `monitoring/changedetection`, `apps/heyform`,
`apps/opencanary`, `apps/easyappointments`, `apps/wikijs`,
`business/invoiceninja` — pull request #292 of 2026-10-31. None ran on a host at
the new tag.

### Batch 2 — the remaining 28 patch releases

No release-line change, so no migration is expected; the release notes still
have to be read per stack, and every move recorded. Stacks that are
`baseline-aligned` and fall without a host run: `apps/defectdojo`, `apps/dify`, `apps/greenmail`, `business/chatwoot`.

| Image | Pinned | Newest, same shape | CRITICAL pairs | Stacks (state) |
|---|---|---|---|---|
| `langgenius/dify-plugin-daemon` | `0.6.10-local` | `0.6.13-local` | 9 | `apps/dify` (baseline-aligned) |
| `pgvector/pgvector` | `0.8.1-pg16` | `0.8.7-pg16` | 7 | `apps/dify` (baseline-aligned), `business/chatwoot` (baseline-aligned) |
| `makeplane/plane-space` | `v1.4.2` | `v1.4.3` | 6 | `business/plane` (scaffolded) |
| `ghcr.io/analogj/scrutiny` | `v0.9.4-web` | `v0.9.5-web` | 5 | `monitoring/scrutiny` (scaffolded) |
| `makeplane/plane-live` | `v1.4.2` | `v1.4.3` | 5 | `business/plane` (scaffolded) |
| `greenmail/standalone` | `2.1.13` | `2.1.15` | 4 | `apps/greenmail` (baseline-aligned) |
| `valkey/valkey` | `9.1.2-alpine` | `9.1.3-alpine` | 4 | `apps/defectdojo` (baseline-aligned) |
| `vaultwarden/server` | `1.37.3` | `1.37.4` | 4 | `apps/vaultwarden` (scaffolded) |
| `fnsys/dockhand` | `v1.0.47` | `v1.0.56` | 3 | `core/dockhand` (scaffolded) |
| `ghcr.io/shlinkio/shlink` | `5.1.7` | `5.1.8` | 3 | `apps/shlink` (scaffolded) |
| `memcached` | `1.6.41` | `1.6.45` | 3 | `business/zammad` (scaffolded) |
| `seafileltd/seasearch` | `1.0.3` | `1.0.8` | 3 | `apps/seafile-pro` (scaffolded) |
| `ghcr.io/finsys/hawser` | `0.2.47` | `0.2.53` | 2 | `core/hawser` (scaffolded) |
| `makeplane/plane-backend` | `v1.4.2` | `v1.4.3` | 2 | `business/plane` (scaffolded) |
| `apache/tika` | `3.3.1.0` | `3.3.3.0` | 1 | `apps/paperless-ngx` (scaffolded) |
| `ghcr.io/jeboehm/mailserver-mda` | `8.0.8` | `8.0.18` | 1 | `apps/mailserver-jeboehm` (scaffolded) |
| `ghcr.io/jeboehm/mailserver-web` | `8.0.8` | `8.0.18` | 1 | `apps/mailserver-jeboehm` (scaffolded) |
| `makeplane/plane-admin` | `v1.4.2` | `v1.4.3` | 1 | `business/plane` (scaffolded) |
| `makeplane/plane-frontend` | `v1.4.2` | `v1.4.3` | 1 | `business/plane` (scaffolded) |
| `makeplane/plane-proxy` | `v1.4.2` | `v1.4.3` | 1 | `business/plane` (scaffolded) |
| `collabora/code` | `26.04.3.2.1` | `26.04.5.2.1` | 0 | `apps/collabora` (scaffolded) |
| `ghcr.io/jeboehm/mailserver-filter` | `8.0.8` | `8.0.18` | 0 | `apps/mailserver-jeboehm` (scaffolded) |
| `ghcr.io/jeboehm/mailserver-mta` | `8.0.8` | `8.0.18` | 0 | `apps/mailserver-jeboehm` (scaffolded) |
| `ghcr.io/jeboehm/mailserver-unbound` | `8.0.8` | `8.0.18` | 0 | `apps/mailserver-jeboehm` (scaffolded) |
| `ghcr.io/juanfont/headscale` | `v0.29.4` | `v0.29.7` | 0 | `core/headscale` (scaffolded) |
| `ghcr.io/project-zot/zot` | `v2.1.21` | `v2.1.22` | 0 | `core/zot` (scaffolded) |
| `ghcr.io/velocidex/velociraptor-server` | `0.77.2` | `0.77.3` | 0 | `apps/velociraptor` (scaffolded) |
| `rclone/rclone` | `1.75.1` | `1.75.2` | 0 | `backup/rclone-web` (scaffolded) |

### Batch 3 — minor releases of applications (60)

A minor release can carry a changed variable, a dropped feature or a
database migration the release notes name. Each move reads them and records
what applies. Images of one project move together (`makeplane/plane-*`,
`seafileltd/*`, `langgenius/dify-*`).

| Image | Pinned | Newest, same shape | CRITICAL pairs | Stacks (state) |
|---|---|---|---|---|
| `frappe/erpnext` | `v16.35.0` | `v16.53.0` | 20 | `business/erpnext` (baseline-aligned) |
| `ghcr.io/paperless-ngx/paperless-ngx` | `3.1.3` | `3.4.1` | 19 | `apps/paperless-ngx` (scaffolded) |
| `defectdojo/defectdojo-django` | `3.3.100` | `3.4.304` | 15 | `apps/defectdojo` (baseline-aligned) |
| `vllm/vllm-openai` | `v0.30.0` | `v0.32.0` | 15 | `apps/vllm` (scaffolded) |
| `lycheeorg/lychee` | `v7.8.3` | `v7.12.0` | 13 | `apps/lycheeorg` (scaffolded) |
| `gotenberg/gotenberg` | `8.21` | `8.39` | 11 | `apps/paperless-ngx` (scaffolded) |
| `openproject/openproject` | `17.8.0-slim` | `17.9.6-slim` | 10 | `business/openproject` (scaffolded) |
| `wordpress` | `7.0.4-php8.3-apache` | `7.1.4-php8.3-apache` | 10 | `apps/wordpress` (scaffolded) |
| `ghcr.io/bluewave-labs/checkmate` | `v3.12.0` | `v3.13.1` | 9 | `monitoring/checkmate` (scaffolded) |
| `hemmeligapp/hemmelig` | `v7.4.8` | `v7.6.1` | 9 | `apps/hemmelig` (scaffolded) |
| `infisical/infisical` | `v0.165.10` | `v0.167.4` | 9 | `core/infisical` (scaffolded) |
| `ghcr.io/goauthentik/server` | `2026.5.7` | `2026.8.5` | 8 | `core/authentik` (scaffolded) |
| `ghcr.io/intuitem/ciso-assistant-community/backend` | `v4.0.9` | `v4.1.5` | 8 | `apps/ciso-assistant` (scaffolded) |
| `ghcr.io/docling-project/docling-serve-cpu` | `v1.34.0` | `v1.38.2` | 7 | `apps/docling-serve` (baseline-aligned) |
| `luka1thb/tymeslot` | `1.15.1-slim` | `1.35.0-slim` | 7 | `apps/tymeslot` (baseline-aligned) |
| `reallibrephotos/librephotos` | `1.2.1` | `1.5.0` | 6 | `apps/librephotos` (scaffolded) |
| `facturascripts/facturascripts` | `2026.5` | `2026.72` | 5 | `business/facturascripts` (baseline-aligned) |
| `ghcr.io/windmill-labs/windmill` | `1.814.0` | `1.855.1` | 5 | `apps/windmill` (baseline-aligned) |
| `jhumanj/opnform-api` | `2.5.0` | `2.8.1` | 5 | `apps/opnform` (scaffolded) |
| `kimai/kimai2` | `2.66.0` | `2.71.0` | 5 | `business/kimai` (scaffolded) |
| `nocodb/nocodb` | `2026.09.0` | `2026.10.1` | 5 | `apps/nocodb` (scaffolded) |
| `qdrant/qdrant` | `v1.19.1-unprivileged` | `v1.20.0-unprivileged` | 5 | `apps/qdrant` (baseline-aligned) |
| `twentycrm/twenty` | `v2.41.0` | `v2.54.0` | 5 | `business/twenty` (baseline-aligned) |
| `brotandgames/ciao` | `1.10.1` | `1.12.0` | 4 | `monitoring/ciao` (scaffolded) |
| `ghcr.io/gethomepage/homepage` | `v2.3.0` | `v2.7.0` | 4 | `apps/homepage` (scaffolded) |
| `chatwoot/chatwoot` | `v4.18.0` | `v4.19.1` | 3 | `business/chatwoot` (baseline-aligned) |
| `ghcr.io/berriai/litellm-non_root` | `v1.101.4` | `v1.106.6` | 3 | `apps/litellm` (scaffolded) |
| `ghcr.io/calnode/calnode` | `0.9.0` | `0.12.0` | 3 | `apps/calnode` (baseline-aligned) |
| `ghcr.io/olivierlambert/calrs` | `1.17.1` | `1.21.0` | 3 | `apps/calrs` (baseline-aligned) |
| `ghcr.io/warp-tech/warpgate` | `0.29.0` | `0.30.2` | 3 | `core/warpgate` (scaffolded) |
| `leantime/leantime` | `3.9.8` | `3.13.2` | 3 | `business/leantime` (scaffolded) |
| `dependencytrack/apiserver` | `5.1.0` | `5.2.1` | 2 | `apps/dependency-track` (scaffolded) |
| `ghcr.io/icereed/paperless-gpt` | `v0.28.0` | `v0.31.0` | 2 | `apps/paperless-gpt` (scaffolded) |
| `ghcr.io/obot-platform/obot` | `v0.26.0` | `v0.27.0` | 2 | `apps/obot` (scaffolded) |
| `ghost` | `6.63.0-alpine` | `6.73.0-alpine` | 2 | `apps/ghost` (scaffolded) |
| `matomo` | `5.13.0-apache` | `5.14.2-apache` | 2 | `business/matomo` (scaffolded) |
| `privatebin/nginx-fpm-alpine` | `2.0.6` | `2.1.0` | 2 | `apps/privatebin` (scaffolded) |
| `crowdsecurity/crowdsec` | `v1.7.8` | `v1.8.2` | 1 | `core/crowdsec` (baseline-aligned) |
| `dependencytrack/frontend` | `5.1.0` | `5.2.1` | 1 | `apps/dependency-track` (scaffolded) |
| `documenso/documenso` | `v2.20.0` | `v2.21.1` | 1 | `business/documenso` (scaffolded) |
| `ghcr.io/intuitem/ciso-assistant-community/frontend` | `v4.0.9` | `v4.1.5` | 1 | `apps/ciso-assistant` (scaffolded) |
| `ghcr.io/orion-belt-dev/orion-belt-server` | `1.2.0` | `1.4.0` | 1 | `core/orion-belt` (scaffolded) |
| `ghcr.io/shlinkio/shlink-web-client` | `4.8.1` | `4.9.0` | 1 | `apps/shlink` (scaffolded) |
| `grafana/grafana` | `13.2.2` | `13.3.0` | 1 | `monitoring/grafana-prometheus` (scaffolded) |
| `jhumanj/opnform-client` | `2.5.0` | `2.8.1` | 1 | `apps/opnform` (scaffolded) |
| `reallibrephotos/librephotos-proxy` | `1.2.1` | `1.5.0` | 1 | `apps/librephotos` (scaffolded) |
| `axllent/mailpit` | `v1.31.1` | `v1.33.0` | 0 | `apps/mailpit` (baseline-aligned) |
| `binwiederhier/ntfy` | `v2.28.0` | `v2.35.0` | 0 | `monitoring/ntfy` (baseline-aligned) |
| `clamav/clamav` | `1.4` | `1.5` | 0 | `apps/seafile-pro` (scaffolded) |
| `clickhouse/clickhouse-server` | `26.8.10.6-alpine` | `26.10.3.7-alpine` | 0 | `business/plausible` (scaffolded) |
| `defectdojo/defectdojo-nginx` | `3.3.100` | `3.4.304` | 0 | `apps/defectdojo` (baseline-aligned) |
| `henrygd/beszel` | `0.19.0` | `0.21.1` | 0 | `monitoring/beszel` (baseline-aligned) |
| `henrygd/beszel-agent` | `0.19.0` | `0.21.1` | 0 | `monitoring/beszel` (baseline-aligned), `monitoring/beszel-agent` (scaffolded) |
| `lissy93/dashy` | `4.8.7` | `4.9.11` | 0 | `apps/dashy` (scaffolded) |
| `ollama/ollama` | `0.34.2` | `0.40.13` | 0 | `apps/ollama` (baseline-aligned) |
| `portainer/portainer-ce` | `2.39.7` | `2.45.3` | 0 | `core/portainer` (scaffolded) |
| `prom/prometheus` | `v3.14.0` | `v3.15.1` | 0 | `monitoring/grafana-prometheus` (scaffolded) |
| `reallibrephotos/librephotos-frontend` | `1.2.1` | `1.5.0` | 0 | `apps/librephotos` (scaffolded) |
| `solidinvoice/solidinvoice` | `3.0.1` | `3.1.2` | 0 | `business/solidinvoice` (baseline-aligned) |
| `twinproduction/gatus` | `v5.36.0` | `v5.38.0` | 0 | `monitoring/gatus` (scaffolded) |

### Batch 4 — minor releases of databases and infrastructure images (9)

Same release line, so the data format does not change; the move is a pull and a
restart per stack, and the family moves in one pull request.

| Image | Pinned | Newest, same shape | CRITICAL pairs | Stacks (state) |
|---|---|---|---|---|
| `postgres` | `18.0` | `18.6` | 8 | `core/shellhub` (scaffolded) |
| `nginx` | `1.29` | `1.31` | 6 | `apps/opnform` (scaffolded) |
| `nginx` | `1.29-alpine` | `1.31-alpine` | 6 | `business/invoiceninja` (baseline-aligned) |
| `nginx` | `1.29-alpine-slim` | `1.31-alpine-slim` | 6 | `apps/nextcloud` (ops-proven) |
| `valkey/valkey` | `9.1-alpine` | `9.2-alpine` | 4 | `core/shellhub` (scaffolded) |
| `nginxinc/nginx-unprivileged` | `1.29-alpine` | `1.31-alpine` | 1 | `apps/_reference` (?) |
| `alpine` | `3.19` | `3.24` | 0 | `core/authentik` (scaffolded) |
| `redis` | `8.2.10-alpine` | `8.10.3-alpine` | 0 | `apps/mailserver-jeboehm` (scaffolded) |
| `redis` | `8.6-alpine` | `8.10-alpine` | 0 | `business/erpnext` (baseline-aligned), `business/invoiceninja` (baseline-aligned) |

### Batch 5 — major releases of applications (20): a decision each

Each row is a release-line change. Upstream's migration guide is read first,
and nothing in this table was read for this document: what a line change
requires — a changed configuration, a dropped feature, a data migration — is
established per stack when its row comes up, and the decision and the path go
into `UPSTREAM.md` before the pin moves.

| Image | Pinned | Newest, same shape | CRITICAL pairs | Stacks (state) |
|---|---|---|---|---|
| `seafileltd/sdoc-server` | `2.0.9` | `3.0.7` | 34 | `apps/seafile` (scaffolded), `apps/seafile-pro` (scaffolded) |
| `seafileltd/seafile-mc` | `13.0.20` | `14.0.9` | 34 | `apps/seafile` (scaffolded) |
| `seafileltd/thumbnail-server` | `13.0.20` | `14.0.7` | 33 | `apps/seafile` (scaffolded), `apps/seafile-pro` (scaffolded) |
| `seafileltd/seafile-pro-mc` | `13.0.21` | `14.0.9` | 31 | `apps/seafile-pro` (scaffolded) |
| `seafileltd/seafile-ai` | `13.0.10` | `14.0.9` | 21 | `apps/seafile-pro` (scaffolded) |
| `jumpserver/jms_all` | `v4.10.19` | `v5.1.1` | 20 | `core/jumpserver` (scaffolded) |
| `ghcr.io/homarr-labs/homarr` | `v1.77.1` | `v2.10.1` | 8 | `apps/homarr` (scaffolded) |
| `n8nio/n8n` | `2.41.7` | `3.0.1` | 8 | `apps/n8n` (scaffolded) |
| `healthchecks/healthchecks` | `v4.4` | `v5.0` | 6 | `monitoring/healthchecks` (baseline-aligned) |
| `nextcloud` | `34.0.4-fpm-alpine` | `35.0.2-fpm-alpine` | 3 | `apps/nextcloud` (ops-proven) |
| `kopia/kopia` | `0.23.1` | `20261031.0.35233` | 2 | `backup/kopia` (scaffolded) |
| `adminer` | `5.5.1-standalone` | `6.2.0-standalone` | 1 | `apps/adminer` (scaffolded) |
| `seafileltd/notification-server` | `13.0.10` | `14.0.8` | 1 | `apps/seafile` (scaffolded), `apps/seafile-pro` (scaffolded) |
| `stalwartlabs/stalwart` | `v0.16.24` | `v1.0.1` | 1 | `apps/stalwart` (scaffolded) |
| `clickhouse/clickhouse-server` | `25.12` | `26.10` | 0 | `monitoring/langfuse` (scaffolded) |
| `dolibarr/dolibarr` | `23.0.4` | `24.0.2` | 0 | `business/dolibarr` (scaffolded) |
| `jhaals/yopass` | `14.10.0` | `16.0.1` | 0 | `apps/yopass` (scaffolded) |
| `onlyoffice/documentserver` | `9.4.0` | `10.0.0` | 0 | `apps/onlyoffice` (scaffolded) |
| `portainer/agent` | `2.39.7` | `3.0.0` | 0 | `core/portainer-agent` (scaffolded) |
| `seafileltd/seafile-md-server` | `13.0.20` | `14.0.7` | 0 | `apps/seafile` (scaffolded), `apps/seafile-pro` (scaffolded) |

### Batch 6 — major releases of databases (23): one procedure per family

PostgreSQL moves 8 pins across 23 stacks to the 18 line: a
`pg_upgrade` or a dump and restore per stack, which `apps/librephotos` already
does through `pgautoupgrade/pgautoupgrade`. The procedure is written once,
tested on one stack on a host, then applied. Valkey 9 and MariaDB 11.8 follow
the same rule, one procedure per family; what nginx 1.31 changes against 1.29
is read from its release notes before the family moves.

| Image | Pinned | Newest, same shape | CRITICAL pairs | Stacks (state) |
|---|---|---|---|---|
| `postgres` | `15.14-alpine` | `18.6-alpine` | 8 | `apps/dify` (baseline-aligned) |
| `postgres` | `15.19-alpine` | `18.6-alpine` | 8 | `business/plane` (scaffolded) |
| `postgres` | `16-alpine` | `18-alpine` | 8 | `apps/_reference` (?), `apps/dependency-track` (scaffolded), `apps/opnform` (scaffolded), `business/documenso` (scaffolded), `business/listmonk` (scaffolded), `business/zammad` (scaffolded), `core/authentik` (scaffolded), `core/dockhand` (scaffolded), `core/infisical` (scaffolded), `core/orion-belt` (scaffolded) |
| `postgres` | `16.14` | `18.6` | 8 | `apps/ciso-assistant` (scaffolded), `apps/paperless-ngx` (scaffolded), `business/twenty` (baseline-aligned) |
| `postgres` | `17-alpine` | `18-alpine` | 8 | `business/openproject` (scaffolded), `business/vikunja` (scaffolded) |
| `postgres` | `17.11` | `18.6` | 8 | `apps/caldiy` (scaffolded) |
| `postgres` | `17.11-alpine` | `18.6-alpine` | 8 | `apps/tymeslot` (baseline-aligned), `core/authelia` (scaffolded), `core/keycloak` (baseline-aligned), `monitoring/zabbix` (scaffolded) |
| `postgres` | `17.6` | `18.6` | 8 | `monitoring/langfuse` (scaffolded) |
| `pgautoupgrade/pgautoupgrade` | `16-bookworm` | `17-bookworm` | 7 | `apps/librephotos` (scaffolded) |
| `elasticsearch` | `8.15.0` | `9.5.5` | 5 | `apps/seafile-pro` (scaffolded) |
| `valkey/valkey` | `7.2.14-alpine` | `9.1.3-alpine` | 4 | `business/plane` (scaffolded) |
| `valkey/valkey` | `8.1.4-alpine` | `9.1.3-alpine` | 4 | `apps/heyform` (scaffolded) |
| `valkey/valkey` | `8.1.6` | `9.1.3` | 4 | `apps/immich` (scaffolded) |
| `mysql` | `8.4` | `26.10` | 2 | `apps/ghost` (scaffolded), `business/invoiceninja` (baseline-aligned) |
| `mysql` | `8.4.11` | `26.10.0` | 2 | `apps/mailserver-jeboehm` (scaffolded), `business/leantime` (scaffolded) |
| `mariadb` | `10.11` | `13.0` | 1 | `apps/seafile` (scaffolded), `apps/seafile-pro` (scaffolded) |
| `mariadb` | `11.4` | `13.0` | 1 | `apps/bookstack` (scaffolded), `apps/easyappointments` (scaffolded), `apps/lycheeorg` (scaffolded), `apps/monicahq` (scaffolded), `apps/photoprism` (scaffolded), `apps/photoview` (scaffolded), `apps/vaultwarden` (scaffolded), `apps/wordpress` (scaffolded), `business/akaunting` (baseline-aligned), `business/dolibarr` (scaffolded), `business/facturascripts` (baseline-aligned), `business/kimai` (scaffolded), `business/matomo` (scaffolded) |
| `mariadb` | `11.8` | `13.0` | 1 | `apps/nextcloud` (ops-proven), `business/erpnext` (baseline-aligned) |
| `mongo` | `8.0` | `9.0` | 1 | `apps/unifi` (scaffolded), `business/opensign` (scaffolded) |
| `mongo` | `8.0.32` | `9.0.4` | 1 | `apps/heyform` (scaffolded), `monitoring/checkmate` (scaffolded) |
| `rabbitmq` | `3-management-alpine` | `4-management-alpine` | 1 | `apps/dfir-iris` (scaffolded) |
| `rabbitmq` | `3.13.7-management-alpine` | `4.4.0-management-alpine` | 1 | `business/plane` (scaffolded) |
| `redis` | `7.4-alpine` | `8.10-alpine` | 0 | `apps/caldiy` (scaffolded), `apps/dify` (baseline-aligned), `apps/lycheeorg` (scaffolded), `apps/nextcloud` (ops-proven), `apps/opnform` (scaffolded), `apps/paperless-ngx` (scaffolded), `apps/seafile` (scaffolded), `apps/seafile-pro` (scaffolded), `business/chatwoot` (baseline-aligned), `business/twenty` (baseline-aligned), `business/zammad` (scaffolded), `core/authelia` (scaffolded), `core/authentik` (scaffolded), `core/infisical` (scaffolded), `monitoring/langfuse` (scaffolded) |

### Batch 7 — what the inventory could not compare

Floating tags (`opensign/*:main` by digest) get a release pin or a recorded
reason; release-candidate pins (`shellhubio/*:v0.27.0-rc.11`) get the release
when upstream publishes one; date and distribution tags (`photoprism`,
`zabbix`, `bookstack`) are compared by hand against upstream's tag list; the
registries this session could not reach are checked from one that can.
`quay.io/minio/minio` stays withdrawn (`.trivy-baseline.json`, `unscanned`).

| Image | Pinned | Newest, same shape | CRITICAL pairs | Stacks (state) |
|---|---|---|---|---|
| `opensign/opensignserver` | `main` | `` | 32 | `business/opensign` (scaffolded) |
| `opensign/opensign` | `main` | `` | 31 | `business/opensign` (scaffolded) |
| `langgenius/dify-api` | `1.17.1` | `` | 14 | `apps/dify` (baseline-aligned) |
| `ghcr.io/immich-app/postgres` | `14-vectorchord0.4.3-pgvectors0.2.0` | `` | 10 | `apps/immich` (scaffolded) |
| `lscr.io/linuxserver/unifi-network-application` | `10.6.101` | `` | 10 | `apps/unifi` (scaffolded) |
| `ghcr.io/immich-app/immich-server` | `v3.2.0` | `` | 9 | `apps/immich` (scaffolded) |
| `photoprism/photoprism` | `260919` | `` | 7 | `apps/photoprism` (scaffolded) |
| `docker.elastic.co/elasticsearch/elasticsearch` | `8.17.4` | `` | 5 | `business/zammad` (scaffolded) |
| `quay.io/keycloak/keycloak` | `26.7.3` | `` | 4 | `core/keycloak` (baseline-aligned) |
| `docker.langfuse.com/langfuse/langfuse` | `4.50.0` | `` | 3 | `monitoring/langfuse` (scaffolded) |
| `langgenius/dify-web` | `1.17.1` | `` | 3 | `apps/dify` (baseline-aligned) |
| `lscr.io/linuxserver/bookstack` | `version-v26.05.4` | `` | 3 | `apps/bookstack` (scaffolded) |
| `docker.langfuse.com/langfuse/langfuse-worker` | `4.50.0` | `` | 2 | `monitoring/langfuse` (scaffolded) |
| `lscr.io/linuxserver/heimdall` | `2.8.3` | `` | 2 | `apps/heimdall` (scaffolded) |
| `shellhubio/server` | `v0.27.0-rc.11` | `` | 2 | `core/shellhub` (scaffolded) |
| `zabbix/zabbix-web-nginx-pgsql` | `alpine-7.0.31` | `` | 2 | `monitoring/zabbix` (scaffolded) |
| `cr.agentgateway.dev/agentgateway` | `v1.5.0` | `` | 1 | `apps/agentgateway` (baseline-aligned) |
| `ghcr.io/zammad/zammad` | `7.2.0-0004` | `` | 1 | `business/zammad` (scaffolded) |
| `zabbix/zabbix-server-pgsql` | `alpine-7.0.31` | `` | 1 | `monitoring/zabbix` (scaffolded) |
| `lscr.io/linuxserver/socket-proxy` | `3.4.4` | `` | 0 | `core/portainer` (scaffolded) |
| `public.ecr.aws/gravitational/teleport-distroless` | `18.11.0` | `` | 0 | `core/teleport` (scaffolded) |
| `quay.io/minio/minio` | `RELEASE.2025-09-07T16-13-09Z` | `` | 0 | `business/plane` (scaffolded), `monitoring/langfuse` (scaffolded) |
| `shellhubio/gateway` | `v0.27.0-rc.11` | `` | 0 | `core/shellhub` (scaffolded) |
| `shellhubio/ui` | `v0.27.0-rc.11` | `` | 0 | `core/shellhub` (scaffolded) |

### Current on 2026-10-31

| Image | Pinned | Newest, same shape | CRITICAL pairs | Stacks (state) |
|---|---|---|---|---|
| `ghcr.io/rubennati/cal.diy` | `v6.2.0-6` | `v6.2.0-6` | 24 | `apps/caldiy` (scaffolded) |
| `ghcr.io/dfir-iris/iriswebapp_app` | `v2.4.29` | `v2.4.29` | 21 | `apps/dfir-iris` (scaffolded) |
| `akaunting/akaunting` | `3.1.21` | `3.1.21` | 19 | `business/akaunting` (baseline-aligned) |
| `ghcr.io/open-webui/open-webui` | `v0.11.3` | `v0.3.13` | 19 | `apps/open-webui` (baseline-aligned) |
| `ghcr.io/immich-app/immich-machine-learning` | `v3.2.0` | `v1.116.2` | 11 | `apps/immich` (scaffolded) |
| `ghcr.io/docker-mailserver/docker-mailserver` | `16.0.1` | `16.0.1` | 8 | `apps/docker-mailserver` (scaffolded) |
| `postgres` | `18.6` | `18.6` | 8 | `apps/litellm` (scaffolded), `apps/windmill` (baseline-aligned) |
| `postgres` | `18.6-alpine` | `18.6-alpine` | 8 | `apps/defectdojo` (baseline-aligned), `apps/obot` (scaffolded), `apps/shlink` (scaffolded), `apps/wikijs` (scaffolded), `business/plausible` (scaffolded) |
| `ghcr.io/dfir-iris/iriswebapp_db` | `v2.4.29` | `v2.4.29` | 6 | `apps/dfir-iris` (scaffolded) |
| `langgenius/dify-sandbox` | `0.2.15` | `0.2.15` | 5 | `apps/dify` (baseline-aligned) |
| `photoview/photoview` | `2.4.0` | `2.4.0` | 5 | `apps/photoview` (scaffolded) |
| `ghcr.io/psf/httpbin` | `0.10.4` | `0.10.4` | 4 | `apps/httpbin` (baseline-aligned) |
| `influxdb` | `2.9.1` | `2.9.1` | 4 | `monitoring/scrutiny` (scaffolded) |
| `smallstep/step-ca` | `0.30.2` | `0.30.2` | 4 | `core/step-ca` (scaffolded) |
| `uroni/urbackup-server` | `2.5.x` | `2.5.x` | 4 | `backup/urbackup` (scaffolded) |
| `ghcr.io/rubennati/cert-ops-tool` | `0.2.1` | `0.2.1` | 3 | `core/acme-certs` (scaffolded) |
| `memcached` | `1.6-alpine` | `1.6-alpine` | 3 | `apps/seafile` (scaffolded), `apps/yopass` (scaffolded), `business/openproject` (scaffolded) |
| `monica` | `4.1.2-apache` | `4.1.2-apache` | 3 | `apps/monicahq` (scaffolded) |
| `ghcr.io/corentinth/it-tools` | `2024.10.22-7ca5933` | `2024.10.22-7ca5933` | 2 | `apps/it-tools` (baseline-aligned) |
| `ghcr.io/gotify/server` | `3.1.1` | `3.1.1` | 2 | `monitoring/gotify` (scaffolded) |
| `owasp/threat-dragon` | `v2.6.2` | `v2.6.2` | 2 | `apps/threat-dragon` (scaffolded) |
| `listmonk/listmonk` | `v6.2.0` | `v6.2.0` | 1 | `business/listmonk` (scaffolded) |
| `authelia/authelia` | `4.39.28` | `4.39.28` | 0 | `core/authelia` (scaffolded) |
| `dockurr/dnsmasq` | `2.93` | `2.93` | 0 | `core/dnsmasq` (scaffolded) |
| `ghcr.io/euro-office/documentserver` | `v9.3.4-hotfix.1` | `v9.3.4-hotfix.1` | 0 | `apps/euro-office` (scaffolded) |
| `ghcr.io/plausible/community-edition` | `v3.2.1` | `v3.2.1` | 0 | `business/plausible` (scaffolded) |
| `tecnativa/docker-socket-proxy` | `v0.5.0` | `v0.5.0` | 0 | `apps/obot` (scaffolded), `core/dockhand` (scaffolded), `core/traefik` (scaffolded), `monitoring/beszel` (baseline-aligned), `monitoring/beszel-agent` (scaffolded) |
| `traefik` | `v3.7` | `v3.7` | 0 | `core/traefik` (scaffolded) |
| `traefik/whoami` | `v1.12.0` | `v1.12.0` | 0 | `apps/whoami` (baseline-aligned) |
| `ubuntu/squid` | `6.6-24.04_edge` | `6.6-24.04_edge` | 0 | `apps/dify` (baseline-aligned) |

## After the programme

The inventory was taken with registry queries that nothing in the repository
repeats. Dependabot cannot read `image: app:${APP_TAG}`; the durable answer is
Renovate with custom managers, proposed and not activated in
[`../renovate-proposal.md`](../renovate-proposal.md). Until that decision is
taken, the inventory is retaken by hand before each batch, and a batch that
starts from a stale inventory re-reads the registry for its own rows.
