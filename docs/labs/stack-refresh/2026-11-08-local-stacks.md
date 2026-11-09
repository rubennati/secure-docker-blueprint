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
3. **As the ordinary user, on `lab/stack-refresh-2026-11-08`** — the stacks still failing,
   and every stack whose local file the run changed, now with the corrections of the host
   runs: the local files carry the same fixes (Silo, capabilities, the UrBackup and Lychee
   corrections) and, since `0f5cba74`, the README's `chown` steps that twenty headers
   lacked. Most of this pass ran at `30cb5424`, with the local corrections found in it
   applied before they were committed (`83a8f93f`, `823ef797`, `819f0490`); the last five
   stacks — `development/web-api`, `apps/seafile`, `apps/seafile-pro`, `apps/calrs` and
   `apps/n8n`, whose local files changed after that — ran at `0dda59d4`, and the five whose
   port correction came last (`monitoring/grafana-prometheus`, `monitoring/zabbix`,
   `monitoring/scrutiny`, `business/plane`, `apps/obot`) at `0dda59d4` with `6c7da771`
   applied, as committed.

From the fifteen stacks re-run after the first analysis of the third pass on, the script
followed the header more closely:
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

## Summary

- **109 of 114 local files pass** on the lab container (LXC): every container healthy
  and the URL the header names answered where the runner could ask it (the notes name the
  few with a self-signed certificate or no URL).
- **1 fails**, not because of the file as far as measured: `apps/ciso-assistant` was
  still starting when the eight-minute window closed.
- **3 are LXC limitations** (Collabora, vLLM, Plausible's ClickHouse), and
  **1 is a runner artefact** (Beszel's agent waits for a key from the UI).
  Collabora, Plausible and Beszel passed their host runs; vLLM ran on neither machine
  (no GPU on the lab host).
- **Six corrections** to the repository came out of the local runs, among them one that
  also affected a host file: ShellHub's SSH port was never published.

## What the local runs corrected

All on `lab/stack-refresh-2026-11-08`, each run again on the lab container (LXC) after the
correction:

| Commit | Stack | What was wrong in the local file |
|---|---|---|
| `0f5cba74` | twenty stacks | the header lacked the README's `chown` steps, so a directory the image's user must write was the operator's |
| `83a8f93f` | `apps/litellm`, `apps/windmill`, `apps/mailserver-jeboehm` | the ownership steps `ops/init.sh` prints, or the worker cache directory, were missing from the header |
| `823ef797` | `apps/euro-office` | the local file started the image without the entrypoint wrapper; an empty log bind mount hid nginx's log directory and nginx exited |
| `819f0490` | `apps/nextcloud`, `apps/seafile`, `apps/seafile-pro` | a regression of the capability change `c5eea782`: MariaDB could not take over `volumes/local/mysql` without `CHOWN`, and in Seafile `healthcheck.sh` could not read its `600` file without `DAC_OVERRIDE`; the host files are not affected |
| `6c7da771` | `monitoring/grafana-prometheus`, `monitoring/zabbix`, `monitoring/scrutiny`, `business/plane`, `apps/obot` | the published service sat on an internal network only, so Docker bound no port and nothing answered on it, although every container was healthy; the same fault left `core/shellhub`'s SSH port unpublished on the host |
| `20d79c9b` | `development/web-api` | the fixture no longer built after the Dependabot move to TypeScript 7 (the production file builds the same fixture) |

## What came from the script, not from the files

- Every placeholder was filled with 48 hex characters until the last part of the third
  pass; Laravel, Phoenix, Infisical and Homarr reject such keys. With the generator
  commands of `.env.local.example` the same stacks passed.
- Lines continued with `\`, `VAR=… ops/init.sh`, `ssh-keygen` and `run --rm` setup steps
  were skipped at first (Leantime, Kopia, ShellHub, Teleport, Warpgate); run as written,
  those stacks passed.
- A URL at the end of a sentence (`http://localhost:8080.`) was probed with the full stop.
- An interrupted run left `keycloak-local` holding port 8080 and spoiled stacks after it;
  the script removes leftover `-local-` containers before each stack since.

## Per stack

| Stack | result | answered | notes |
|---|---|---|---|
| `apps/agentgateway` | pass | `:4000/v1/models` 401 | healthy at the head of the lab branch, with the corrections of the host runs |
| `apps/bookstack` | pass | `:8080` 500 | healthy, but `/` answered 500: the runner filled `APP_KEY` with random hex, where Laravel expects the `base64:` key the header's generator writes — a runner artefact, inconclusive for the file |
| `apps/caldiy` | pass | `:3000` 307 | healthy in the first pass |
| `apps/calnode` | pass | `:3000/v1/setup` 405 | healthy at the head of the lab branch, with the corrections of the host runs |
| `apps/calrs` | pass | `:3000` 303 | healthy at the head of the lab branch, with the corrections of the host runs |
| `apps/ciso-assistant` | fail | `:3000` 302 | not healthy in time: the frontend logged `Listening on http://0.0.0.0:3000` and `/` answered `302`, but it was still `health: starting` when the eight-minute window closed — the backend's start (migrations) on the LXC took about five minutes before the frontend could start; not repeated with a longer window |
| `apps/collabora` | LXC limitation | no HTTP answer | LXC limitation: coolwsd could not spawn coolforkit ("Failed to spawn coolforkit", `ECHILD`) — its jail setup needs mount and namespace rights an unprivileged LXC does not pass on; the host run of the same version passed |
| `apps/dashy` | pass | `:8080` 200 | healthy at the head of the lab branch, with the corrections of the host runs |
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
| `apps/immich` | pass | `:2283` 200 | healthy at the head of the lab branch, with the corrections of the host runs |
| `apps/it-tools` | pass | `:8080` 200 | healthy in the first pass |
| `apps/librephotos` | pass | `:8080` 200 | healthy in the first pass |
| `apps/litellm` | pass | `:4000/v1/models` 401 | healthy at the head of the lab branch, with the corrections of the host runs |
| `apps/lycheeorg` | pass | `:8000` 307 | healthy at the head of the lab branch, with the corrections of the host runs |
| `apps/mailpit` | pass | `:8025` 200 | healthy at the head of the lab branch, with the corrections of the host runs |
| `apps/mailserver-jeboehm` | pass | `:8080` 302 | healthy at the head of the lab branch, with the corrections of the host runs |
| `apps/monicahq` | pass | `:8080` 500 | healthy, but `/` answered 500: `APP_KEY` filled with random hex instead of a `base64:` key — a runner artefact, inconclusive for the file |
| `apps/n8n` | pass | `:5678` 200 | healthy at the head of the lab branch, with the corrections of the host runs |
| `apps/nextcloud` | pass | `:8080` 302 | healthy at the head of the lab branch, with the corrections of the host runs |
| `apps/nocodb` | pass | `:8080` 200 | healthy at the head of the lab branch, with the corrections of the host runs |
| `apps/obot` | pass | `:8080` 200 | healthy at the head of the lab branch, with the corrections of the host runs |
| `apps/ollama` | pass | `:11434/api/generate` 405 | healthy at the head of the lab branch, with the corrections of the host runs |
| `apps/onlyoffice` | pass | `:8080/` 302 | healthy in the first pass |
| `apps/opencanary` | pass | `:8080/` 302 | healthy in the first pass |
| `apps/open-webui` | pass | `:8080` 200 | failed as root (a directory `mkdir` created as root was not writable for the image's user); healthy as a uid-1000 user |
| `apps/opnform` | pass | `:8080` 302 | healthy at the head of the lab branch, with the corrections of the host runs |
| `apps/paperless-gpt` | pass | `:8080` 200 | failed as root (a directory `mkdir` created as root was not writable for the image's user); healthy as a uid-1000 user |
| `apps/paperless-ngx` | pass | `:8000` 302 | healthy at the head of the lab branch, with the corrections of the host runs |
| `apps/photoprism` | pass | `:2342` 307 | healthy in the first pass |
| `apps/photoview` | pass | `:8080` 200 | healthy at the head of the lab branch, with the corrections of the host runs |
| `apps/privatebin` | pass | `:8080` 200 | healthy in the first pass |
| `apps/qdrant` | pass | `:6333/collections` 401 | failed as root (a directory `mkdir` created as root was not writable for the image's user); healthy as a uid-1000 user |
| `apps/_reference` | pass | `:8080/` 200 | healthy in the first pass |
| `apps/seafile` | pass | no HTTP answer | healthy; the header names `http://127.0.0.1:8000`, which the runner did not probe — no HTTP status recorded |
| `apps/seafile-pro` | pass | no HTTP answer | healthy; the header names `http://127.0.0.1`, which the runner did not probe — no HTTP status recorded |
| `apps/shlink` | pass | `:8081` 200; `:8080/<slug>` 404 | healthy at the head of the lab branch, with the corrections of the host runs |
| `apps/stalwart` | pass | `:8080/admin` 302 | healthy in the first pass |
| `apps/threat-dragon` | pass | `:8080` 200 | healthy in the first pass |
| `apps/tymeslot` | pass | `:4000` 302 | healthy at the head of the lab branch, with the corrections of the host runs |
| `apps/unifi` | pass | no HTTP answer | healthy; the header's URL is `https://` with the image's self-signed certificate, which the runner did not accept — no HTTP status recorded |
| `apps/vaultwarden` | pass | `:8080` 200 | healthy in the first pass |
| `apps/velociraptor` | pass | no HTTP answer | healthy; `https://` with a self-signed certificate, not accepted by the runner — no HTTP status recorded |
| `apps/vllm` | LXC limitation | no HTTP answer | LXC limitation: the CPU build of vLLM grew past the 3 GiB the LXC could be given (2.6 GiB in the worker alone) and stalled the container; stopped from the hypervisor host |
| `apps/whoami` | pass | `:8080/` 200 | healthy in the first pass |
| `apps/wikijs` | pass | `:8080` 200 | healthy at the head of the lab branch, with the corrections of the host runs |
| `apps/windmill` | pass | `:8000/api/version` 200 | healthy at the head of the lab branch, with the corrections of the host runs |
| `apps/wordpress` | pass | `:8080` 302 | healthy in the first pass |
| `apps/yopass` | pass | `:8080` 200 | healthy at the head of the lab branch, with the corrections of the host runs |
| `backup/kopia` | pass | no HTTP answer | healthy; the header's `https://` URL carries the image's own certificate, which the runner did not accept — no HTTP status recorded |
| `backup/rclone-web` | pass | `:5522` 200 | healthy at the head of the lab branch, with the corrections of the host runs |
| `backup/urbackup` | pass | `:55414` 200 | healthy at the head of the lab branch, with the corrections of the host runs |
| `business/akaunting` | pass | `:8080` 302 | healthy at the head of the lab branch, with the corrections of the host runs |
| `business/chatwoot` | pass | `:3000` 302 | healthy at the head of the lab branch, with the corrections of the host runs |
| `business/documenso` | pass | `:3000` 302 | healthy in the first pass |
| `business/dolibarr` | pass | `:8080` 200 | healthy in the first pass |
| `business/erpnext` | pass | `:8080` 404 | healthy at the head of the lab branch, with the corrections of the host runs |
| `business/facturascripts` | pass | `:8080` 200 | healthy at the head of the lab branch, with the corrections of the host runs |
| `business/invoiceninja` | pass | `:8080` 500 | healthy; `/` answered 500 at the moment of the probe while php-fpm still started (`connect() failed` in nginx's log) — the host run of the same version passed |
| `business/kimai` | pass | `:8001` 302 | healthy in the first pass |
| `business/leantime` | pass | `:8080` 303 | healthy at the head of the lab branch, with the corrections of the host runs |
| `business/listmonk` | pass | `:9000` 200 | failed as root (a directory `mkdir` created as root was not writable for the image's user); healthy as a uid-1000 user |
| `business/matomo` | pass | `:8080` 200 | failed as root (a directory `mkdir` created as root was not writable for the image's user); healthy as a uid-1000 user |
| `business/openproject` | pass | `:8080` 302 | healthy at the head of the lab branch, with the corrections of the host runs |
| `business/opensign` | pass | `:3000` 200 | healthy at the head of the lab branch, with the corrections of the host runs |
| `business/plane` | pass | `:8080/god-mode` 301 | healthy at the head of the lab branch, with the corrections of the host runs |
| `business/plausible` | LXC limitation | no HTTP answer | LXC limitation: the ClickHouse service asks for `nofile` 262144 and runc refused it (`error setting rlimit type 7: operation not permitted`) — dockerd in the LXC runs with a hard open-files limit of 256000; the host run passed |
| `business/solidinvoice` | pass | `:8765/install` 200 | failed as root (a directory `mkdir` created as root was not writable for the image's user); healthy as a uid-1000 user |
| `business/twenty` | pass | `:3000` 200 | healthy at the head of the lab branch, with the corrections of the host runs |
| `business/vikunja` | pass | `:3456` 200 | healthy at the head of the lab branch, with the corrections of the host runs |
| `business/zammad` | pass | `:8080` 502 | healthy at the head of the lab branch, with the corrections of the host runs |
| `core/authelia` | pass | no HTTP answer | failed as root (a directory `mkdir` created as root was not writable for the image's user); healthy as a uid-1000 user |
| `core/authentik` | pass | `:9000/if/flow/initial-setup/` 200 | failed as root (a directory `mkdir` created as root was not writable for the image's user); healthy as a uid-1000 user |
| `core/dockhand` | pass | `:3000` 200 | healthy at the head of the lab branch, with the corrections of the host runs |
| `core/headscale` | pass | `:8080` 200 | healthy at the head of the lab branch, with the corrections of the host runs |
| `core/infisical` | pass | `:8080` 200 | healthy at the head of the lab branch, with the corrections of the host runs |
| `core/jumpserver` | pass | `:8080` 200 | failed as root (a directory `mkdir` created as root was not writable for the image's user); healthy as a uid-1000 user |
| `core/keycloak` | pass | `:8080/admin` 302 | healthy at the head of the lab branch, with the corrections of the host runs |
| `core/orion-belt` | pass | `:8080` 302 | healthy at the head of the lab branch, with the corrections of the host runs |
| `core/portainer` | pass | `:9000` 200 | failed as root (a directory `mkdir` created as root was not writable for the image's user); healthy as a uid-1000 user |
| `core/shellhub` | pass | `:8080` 502 | healthy at the head of the lab branch, with the corrections of the host runs |
| `core/step-ca` | pass | no HTTP answer | healthy; the header's `https://` URL carries the image's own certificate, which the runner did not accept — no HTTP status recorded |
| `core/teleport` | pass | no HTTP answer | healthy; the header's `https://` URL carries the image's own certificate, which the runner did not accept — no HTTP status recorded |
| `core/warpgate` | pass | no HTTP answer | healthy; the header's `https://` URL carries the image's own certificate, which the runner did not accept — no HTTP status recorded |
| `core/zot` | pass | `:8080/v2/` 401 | healthy at the head of the lab branch, with the corrections of the host runs |
| `development/static-site` | pass | `:8081/` 200 | failed as root (a directory `mkdir` created as root was not writable for the image's user); healthy as a uid-1000 user |
| `development/web-api` | pass | `:8082/healthz` 200 | healthy at the head of the lab branch, with the corrections of the host runs |
| `monitoring/beszel` | runner artefact | `:8090` 200 | runner artefact: the header's middle step is in the UI (owner account, then the token and the agent key copied into `.env.local`); the hub answered `200`, the agent restarted without a key, as it does until that step |
| `monitoring/changedetection` | pass | `:5000` 200 | healthy at the head of the lab branch, with the corrections of the host runs |
| `monitoring/checkmate` | pass | `:52345` 200 | failed as root (a directory `mkdir` created as root was not writable for the image's user); healthy as a uid-1000 user |
| `monitoring/ciao` | pass | `:8080` 401 | healthy at the head of the lab branch, with the corrections of the host runs |
| `monitoring/gatus` | pass | `:8080` 200 | healthy at the head of the lab branch, with the corrections of the host runs |
| `monitoring/gotify` | pass | `:8080` 200 | healthy at the head of the lab branch, with the corrections of the host runs |
| `monitoring/grafana-prometheus` | pass | `:3000` 302 | healthy at the head of the lab branch, with the corrections of the host runs |
| `monitoring/healthchecks` | pass | `:8000` 302 | healthy at the head of the lab branch, with the corrections of the host runs |
| `monitoring/langfuse` | pass | `:3000` 200 | healthy at the head of the lab branch, with the corrections of the host runs |
| `monitoring/ntfy` | pass | `:8080/mytopic` 200 | healthy at the head of the lab branch, with the corrections of the host runs |
| `monitoring/scrutiny` | pass | `:8080` 302 | healthy at the head of the lab branch, with the corrections of the host runs |
| `monitoring/uptime-kuma` | pass | `:3001` 302 | failed as root (a directory `mkdir` created as root was not writable for the image's user); healthy as a uid-1000 user |
| `monitoring/zabbix` | pass | `:8080` 200 | healthy at the head of the lab branch, with the corrections of the host runs |
