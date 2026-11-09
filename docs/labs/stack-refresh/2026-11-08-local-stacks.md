# Stack refresh — local test stacks, 2026-11-08

Every stack's `docker-compose.local.yml` started on **the lab container (LXC)** — an
unprivileged LXC with nesting, Debian 13.6, Docker Engine 29.9.3, Compose 5.7.0; 4 vCPU and
4 GiB at the start (3 GiB for a while), 10 cores and 7 GiB from the middle of the run. The
host runs are in `docs/labs/stack-refresh/2026-11-08-results.md` on the branch
`lab/stack-refresh-2026-11-08`. A local stack proves that the file starts and answers; it is
not a host run and sets no `Last verified`.

## How each stack was run

A script read the header of each `docker-compose.local.yml` and ran its commands in order —
`cp .env.local.example .env.local`, `ops/init.sh`, `mkdir`, `chown`, the `up` — but not
`down`, `logs -f`, `exec` or `run`. Every `__REPLACE_ME__` in `.env.local` got a random
48-character hex value. Then it waited up to eight minutes for every container to be healthy
(or running, where there is no healthcheck, or exited 0 for a one-shot), looked again 20
seconds later, requested the first one or two `http://localhost:<port>` URLs the header
names, recorded the last log lines, and took the stack down with `down -v`, its data and
images removed.

Three passes:

1. **As root, at `origin/dev` (`c665fe7d`)** — every stack.
2. **As an ordinary user** (uid 1000, `sudo` for the header's `chown` lines — the way the
   file is used on a Linux workstation), same commit — the stacks that failed the first
   pass. Several first-pass failures were the root pass itself: a directory that `mkdir`
   creates as root is not writable for an image that runs as uid 1000.
3. **As the ordinary user, at the head of `lab/stack-refresh-2026-11-08`** — the stacks still
   failing, now with every correction of the host runs: the local files carry the same
   fixes (Silo, capabilities, the UrBackup and Lychee corrections) and, since `0f5cba74`,
   the README's `chown` steps that twenty headers lacked.

For the last fifteen stacks of the third pass the script followed the header more closely:
it ran the generator command written above a placeholder in `.env.local.example` (`echo
"base64:$(openssl rand -base64 32)"`, `openssl rand -base64 64`, …) instead of hex, joined
lines continued with `\`, ran `ssh-keygen` and `VAR=… ops/init.sh`, and ran a `run --rm`
setup step that comes before the `up`. Before that, every placeholder was 48 hex characters,
which a Laravel `APP_KEY`, a 64-byte Phoenix `SECRET_KEY_BASE` or Infisical's 32-character
`ENCRYPTION_KEY` rejects.

The result column takes the last pass a stack ran in.

`result`: **pass** — every container healthy and the URL answered (any HTTP status: some
answer `302` to a login or `401`/`403` by design); **fail** — a container not healthy, or no
answer; **LXC limitation** — the failure comes from the LXC, not from the file;
**runner artefact** — the failure comes from how the script filled `.env.local`, not from
the file.

## Status

Interim: the third pass is still running (31 stacks re-checked with the changed local files, then the fifteen stacks named above). Rows marked `fail` here may still change; the final version replaces this one.

## Results

pass: 90 · fail: 20 · LXC limitation: 3 · runner artefact: 1 · not run: 0

| Stack | result | answered | notes |
|---|---|---|---|
| `apps/agentgateway` | fail | no HTTP answer | not healthy: agentgateway-local-app: Restarting (1) 6 seconds ago |
| `apps/bookstack` | pass | `:8080` 500 | healthy, but `/` answered 500: the runner filled `APP_KEY` with random hex, where Laravel expects the `base64:` key the header's generator writes — a runner artefact, inconclusive for the file |
| `apps/caldiy` | pass | `:3000` 307 | healthy in the first pass |
| `apps/calnode` | pass | `:3000/v1/setup` 405 | failed as root (a directory `mkdir` created as root was not writable for the image's user); healthy as a uid-1000 user |
| `apps/calrs` | pass | `:3000` 303 | healthy at the head of the lab branch, with the corrections of the host runs |
| `apps/ciso-assistant` | fail | no HTTP answer | not healthy: ciso-assistant-local-huey: Created, ciso-assistant-local-frontend: Created, ciso-assistant-local-backend: Up 14 minutes (health: starting) |
| `apps/collabora` | LXC limitation | no HTTP answer | LXC limitation: coolwsd could not spawn coolforkit ("Failed to spawn coolforkit", `ECHILD`) — its jail setup needs mount and namespace rights an unprivileged LXC does not pass on; the host run of the same version passed |
| `apps/dashy` | pass | `:8080` 200 | healthy in the first pass |
| `apps/defectdojo` | pass | `:8080` 302 | healthy at the head of the lab branch, with the corrections of the host runs |
| `apps/dependency-track` | pass | `:8080` 200 | healthy in the first pass |
| `apps/dfir-iris` | pass | `:8080` 302 | healthy in the first pass |
| `apps/dify` | pass | `:3000/install` 200 | healthy in the first pass |
| `apps/docker-mailserver` | pass | no HTTP answer | healthy; a mail server without a web interface, no URL |
| `apps/docling-serve` | pass | `:8099/health` 200 | healthy in the first pass |
| `apps/easyappointments` | pass | `:8080/index.php/installation` 200; `:8080/index.php/user/login` 503 | healthy; the first URL 200, the second 503 while the installer had not run |
| `apps/euro-office` | pass | `:8080/` 302 | healthy at the head of the lab branch, with the corrections of the host runs |
| `apps/ghost` | pass | `:2368/ghost/` 200 | healthy in the first pass |
| `apps/greenmail` | pass | `:8080/` 200 | healthy in the first pass |
| `apps/heimdall` | pass | `:8080` 200 | healthy in the first pass |
| `apps/hemmelig` | pass | `:8080` 200 | healthy in the first pass |
| `apps/heyform` | pass | `:9157` 200 | healthy at the head of the lab branch, with the corrections of the host runs |
| `apps/homarr` | pass | `:7575` 307 | healthy at the head of the lab branch, with the corrections of the host runs |
| `apps/homepage` | pass | `:3000` 200 | healthy in the first pass |
| `apps/httpbin` | pass | `:8080` 200 | healthy in the first pass |
| `apps/immich` | pass | `:2283` 200 | healthy in the first pass |
| `apps/it-tools` | pass | `:8080` 200 | healthy in the first pass |
| `apps/librephotos` | pass | `:8080` 200 | healthy in the first pass |
| `apps/litellm` | pass | `:4000/v1/models` 401 | healthy at the head of the lab branch, with the corrections of the host runs |
| `apps/lycheeorg` | fail | no HTTP answer | not healthy: lychee-local-app: Restarting (1) 37 seconds ago |
| `apps/mailpit` | pass | `:8025` 200 | healthy in the first pass |
| `apps/mailserver-jeboehm` | fail | `:8080` 302 | not healthy: mailserver-jeboehm-local-mta: Created, mailserver-jeboehm-local-filter: Up 6 minutes (unhealthy) |
| `apps/monicahq` | pass | `:8080` 500 | healthy, but `/` answered 500: `APP_KEY` filled with random hex instead of a `base64:` key — a runner artefact, inconclusive for the file |
| `apps/n8n` | pass | `:5678` 200 | healthy in the first pass |
| `apps/nextcloud` | pass | `:8080` 302 | healthy in the first pass |
| `apps/nocodb` | pass | `:8080` 200 | healthy in the first pass |
| `apps/obot` | pass | no HTTP answer | healthy; the header names no URL |
| `apps/ollama` | pass | `:11434/api/generate` 405 | failed as root (a directory `mkdir` created as root was not writable for the image's user); healthy as a uid-1000 user |
| `apps/onlyoffice` | pass | `:8080/` 302 | healthy in the first pass |
| `apps/opencanary` | pass | `:8080/` 302 | healthy in the first pass |
| `apps/open-webui` | pass | `:8080` 200 | failed as root (a directory `mkdir` created as root was not writable for the image's user); healthy as a uid-1000 user |
| `apps/opnform` | fail | `:8080` 200 | not healthy: opnform-local-nginx: Up 5 minutes (unhealthy) |
| `apps/paperless-gpt` | pass | `:8080` 200 | failed as root (a directory `mkdir` created as root was not writable for the image's user); healthy as a uid-1000 user |
| `apps/paperless-ngx` | pass | `:8000` 302 | healthy in the first pass |
| `apps/photoprism` | pass | `:2342` 307 | healthy in the first pass |
| `apps/photoview` | pass | `:8080` 200 | healthy in the first pass |
| `apps/privatebin` | pass | `:8080` 200 | healthy in the first pass |
| `apps/qdrant` | pass | `:6333/collections` 401 | failed as root (a directory `mkdir` created as root was not writable for the image's user); healthy as a uid-1000 user |
| `apps/_reference` | pass | `:8080/` 200 | healthy in the first pass |
| `apps/seafile` | pass | no HTTP answer | healthy; the header names `http://127.0.0.1:8000`, which the runner did not probe — no HTTP status recorded |
| `apps/seafile-pro` | pass | no HTTP answer | healthy; the header names `http://127.0.0.1`, which the runner did not probe — no HTTP status recorded |
| `apps/shlink` | pass | `:8081` 200; `:8080/<slug>` 404 | healthy at the head of the lab branch, with the corrections of the host runs |
| `apps/stalwart` | pass | `:8080/admin` 302 | healthy in the first pass |
| `apps/threat-dragon` | pass | `:8080` 200 | healthy in the first pass |
| `apps/tymeslot` | fail | no HTTP answer | not healthy: tymeslot-local-app: Restarting (1) 14 seconds ago |
| `apps/unifi` | fail | no HTTP answer | healthy; the header's URL is `https://` with the image's self-signed certificate, which the runner did not accept — no HTTP status recorded |
| `apps/vaultwarden` | pass | `:8080` 200 | healthy in the first pass |
| `apps/velociraptor` | fail | no HTTP answer | healthy; `https://` with a self-signed certificate, not accepted by the runner — no HTTP status recorded |
| `apps/vllm` | LXC limitation | no HTTP answer | LXC limitation: the CPU build of vLLM grew past the 3 GiB the LXC could be given (2.6 GiB in the worker alone) and stalled the container; stopped from the hypervisor host |
| `apps/whoami` | pass | `:8080/` 200 | healthy in the first pass |
| `apps/wikijs` | pass | `:8080` 200 | healthy in the first pass |
| `apps/windmill` | fail | `:8000/api/version` 200 | not healthy: windmill-local-worker: Restarting (101) 3 seconds ago |
| `apps/wordpress` | pass | `:8080` 302 | healthy in the first pass |
| `apps/yopass` | pass | `:8080` 200 | healthy in the first pass |
| `backup/kopia` | fail | no HTTP answer | not healthy: kopia-local-server: Restarting (1) 35 seconds ago |
| `backup/rclone-web` | pass | `:5522` 200 | healthy in the first pass |
| `backup/urbackup` | pass | `:55414` 200 | healthy at the head of the lab branch, with the corrections of the host runs |
| `business/akaunting` | pass | `:8080` 302 | healthy at the head of the lab branch, with the corrections of the host runs |
| `business/chatwoot` | pass | `:3000` 302 | healthy at the head of the lab branch, with the corrections of the host runs |
| `business/documenso` | pass | `:3000` 302 | healthy in the first pass |
| `business/dolibarr` | pass | `:8080` 200 | healthy in the first pass |
| `business/erpnext` | pass | `:8080` 404 | healthy in the first pass |
| `business/facturascripts` | pass | `:8080` 200 | healthy in the first pass |
| `business/invoiceninja` | pass | `:8080` 500 | healthy; `/` answered 500 at the moment of the probe while php-fpm still started (`connect() failed` in nginx's log) — the host run of the same version passed |
| `business/kimai` | pass | `:8001` 302 | healthy in the first pass |
| `business/leantime` | fail | `:8080` 500 | not healthy: leantime-local-app: Up 20 seconds (health: starting) |
| `business/listmonk` | pass | `:9000` 200 | failed as root (a directory `mkdir` created as root was not writable for the image's user); healthy as a uid-1000 user |
| `business/matomo` | pass | `:8080` 200 | failed as root (a directory `mkdir` created as root was not writable for the image's user); healthy as a uid-1000 user |
| `business/openproject` | pass | `:8080` 302 | failed as root (a directory `mkdir` created as root was not writable for the image's user); healthy as a uid-1000 user |
| `business/opensign` | pass | `:3000` 200 | failed as root (a directory `mkdir` created as root was not writable for the image's user); healthy as a uid-1000 user |
| `business/plane` | fail | no HTTP answer | not healthy: plane-local-migrator: Exited (0) About a minute ago |
| `business/plausible` | LXC limitation | no HTTP answer | LXC limitation: the ClickHouse service asks for `nofile` 262144 and runc refused it (`error setting rlimit type 7: operation not permitted`) — dockerd in the LXC runs with a hard open-files limit of 256000; the host run passed |
| `business/solidinvoice` | pass | `:8765/install` 200 | failed as root (a directory `mkdir` created as root was not writable for the image's user); healthy as a uid-1000 user |
| `business/twenty` | pass | `:3000` 200 | healthy at the head of the lab branch, with the corrections of the host runs |
| `business/vikunja` | pass | `:3456` 200 | failed as root (a directory `mkdir` created as root was not writable for the image's user); healthy as a uid-1000 user |
| `business/zammad` | pass | `:8080` 502 | failed as root (a directory `mkdir` created as root was not writable for the image's user); healthy as a uid-1000 user |
| `core/authelia` | pass | no HTTP answer | failed as root (a directory `mkdir` created as root was not writable for the image's user); healthy as a uid-1000 user |
| `core/authentik` | pass | `:9000/if/flow/initial-setup/` 200 | failed as root (a directory `mkdir` created as root was not writable for the image's user); healthy as a uid-1000 user |
| `core/dockhand` | pass | `:3000` 200 | failed as root (a directory `mkdir` created as root was not writable for the image's user); healthy as a uid-1000 user |
| `core/headscale` | fail | no HTTP answer | not healthy:  |
| `core/infisical` | fail | no HTTP answer | not healthy: infisical-local-app: Restarting (1) 54 seconds ago |
| `core/jumpserver` | pass | `:8080` 200 | failed as root (a directory `mkdir` created as root was not writable for the image's user); healthy as a uid-1000 user |
| `core/keycloak` | pass | `:8080/admin` 302 | failed as root (a directory `mkdir` created as root was not writable for the image's user); healthy as a uid-1000 user |
| `core/orion-belt` | pass | `:8080` 302 | healthy at the head of the lab branch, with the corrections of the host runs |
| `core/portainer` | pass | `:9000` 200 | failed as root (a directory `mkdir` created as root was not writable for the image's user); healthy as a uid-1000 user |
| `core/shellhub` | fail | `:8080` 500 | not healthy: shellhub-local-db: Created, shellhub-local-valkey: Created, shellhub-local-ui: Created |
| `core/step-ca` | fail | no HTTP answer | not healthy:  |
| `core/teleport` | fail | no HTTP answer | not healthy: teleport-local-app: Restarting (1) 19 seconds ago |
| `core/warpgate` | fail | no HTTP answer | not healthy: warpgate-local-app: Restarting (1) 35 seconds ago |
| `core/zot` | pass | `:8080/v2/` 401 | healthy at the head of the lab branch, with the corrections of the host runs |
| `development/static-site` | pass | `:8081/` 200 | failed as root (a directory `mkdir` created as root was not writable for the image's user); healthy as a uid-1000 user |
| `development/web-api` | fail | no HTTP answer | not healthy:  |
| `monitoring/beszel` | runner artefact | `:8090` 200 | runner artefact: the header's middle step is in the UI (owner account, then the token and the agent key copied into `.env.local`); the hub answered `200`, the agent restarted without a key, as it does until that step |
| `monitoring/changedetection` | pass | `:5000` 200 | failed as root (a directory `mkdir` created as root was not writable for the image's user); healthy as a uid-1000 user |
| `monitoring/checkmate` | pass | `:52345` 200 | failed as root (a directory `mkdir` created as root was not writable for the image's user); healthy as a uid-1000 user |
| `monitoring/ciao` | pass | `:8080` 401 | healthy at the head of the lab branch, with the corrections of the host runs |
| `monitoring/gatus` | pass | `:8080` 200 | healthy at the head of the lab branch, with the corrections of the host runs |
| `monitoring/gotify` | pass | `:8080` 200 | healthy at the head of the lab branch, with the corrections of the host runs |
| `monitoring/grafana-prometheus` | fail | no HTTP answer | not healthy:  |
| `monitoring/healthchecks` | pass | `:8000` 302 | healthy at the head of the lab branch, with the corrections of the host runs |
| `monitoring/langfuse` | pass | `:3000` 200 | healthy at the head of the lab branch, with the corrections of the host runs |
| `monitoring/ntfy` | pass | `:8080/mytopic` 200 | healthy at the head of the lab branch, with the corrections of the host runs |
| `monitoring/scrutiny` | pass | `:8080` 500 | failed as root (a directory `mkdir` created as root was not writable for the image's user); healthy as a uid-1000 user |
| `monitoring/uptime-kuma` | pass | `:3001` 302 | failed as root (a directory `mkdir` created as root was not writable for the image's user); healthy as a uid-1000 user |
| `monitoring/zabbix` | pass | `:8080` 500 | failed as root (a directory `mkdir` created as root was not writable for the image's user); healthy as a uid-1000 user |
