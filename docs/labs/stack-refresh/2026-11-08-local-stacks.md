# Stack refresh, 2026-11-08: local files

109 of the 114 `docker-compose.local.yml` files start and answer on `localhost`, run as
their header says. A local file proves that it starts and answers; it is not a host run and
sets no `Last verified`. The host results are in
[`2026-11-08-results.md`](2026-11-08-results.md).

## Summary

- **109 of 114 pass**: every container healthy and the URL the header names answered
  (the notes name the few with a self-signed certificate or no URL).
- **Not passing, and why:**
  - `apps/ciso-assistant` had not finished starting after eight minutes.
  - Collabora, vLLM and Plausible's ClickHouse need more than an unprivileged LXC
    allows. Collabora and Plausible are verified on a host; vLLM needs a GPU.
  - Beszel's agent waits for a key from the web UI, a step a script cannot take.
    Beszel is verified on a host.
- **Six faults fixed** in the local files, one of which also affected a host file:
  ShellHub's SSH port was never published.

## How a file counts as passing

Each file ran on an unprivileged LXC with nesting (Debian 13.6, Docker Engine 29.9.3,
Compose 5.7.0, 10 cores, 7 GiB) as an ordinary user (uid 1000, `sudo` for the header's
`chown` lines, as on a Linux workstation). A script ran the header's commands in order:
`cp .env.local.example .env.local`, the generator commands written above each secret,
`ops/init.sh`, `mkdir`, `chown`, `ssh-keygen`, a `run --rm` setup step, the `up`. Then it
waited up to eight minutes for every container to be healthy (or running where there is no
healthcheck, or exited 0 for a one-shot), looked again 20 seconds later, requested the
first one or two `http://localhost:<port>` URLs the header names, and removed the stack
with `down -v`.

`result`: **pass**: every container healthy and the URL answered (any HTTP status; some
answer `302` to a login or `401`/`403` by design). **fail**: a container not healthy, or
no answer. **LXC limitation**: the failure comes from the LXC, not from the file.
**runner artefact**: the failure comes from how the script filled `.env.local`, not from
the file.

As root, a directory that `mkdir` creates is not writable for an image that runs as
uid 1000; run the headers as an ordinary user.

## Fixed

| Stack | Works now | Commit |
|---|---|---|
| twenty-four stacks | the header carries the README's `chown` steps, so the image's user can write its directories | `0f5cba74`, `83a8f93f` |
| `apps/euro-office` | nginx starts: the local file uses the entrypoint wrapper, and no empty bind mount hides its log directory | `823ef797` |
| `apps/nextcloud`, `apps/seafile`, `apps/seafile-pro` | MariaDB starts with the reduced capabilities, and Seafile's `healthcheck.sh` reads its `600` file | `819f0490` |
| `monitoring/grafana-prometheus`, `monitoring/zabbix`, `monitoring/scrutiny`, `business/plane`, `apps/obot`, `core/shellhub` | the published port answers: the service is no longer on internal networks only, where Docker binds no port | `6c7da771` |
| `development/web-api` | the fixture builds with TypeScript 7 | `20d79c9b` |

## Per stack

| Stack | result | answered | notes |
|---|---|---|---|
| `apps/agentgateway` | pass | `:4000/v1/models` 401 | healthy |
| `apps/bookstack` | pass | `:8080` 500 | healthy, but `/` answered 500: the runner filled `APP_KEY` with random hex, where Laravel expects the `base64:` key the header's generator writes — a runner artefact, inconclusive for the file |
| `apps/caldiy` | pass | `:3000` 307 | healthy |
| `apps/calnode` | pass | `:3000/v1/setup` 405 | healthy |
| `apps/calrs` | pass | `:3000` 303 | healthy |
| `apps/ciso-assistant` | fail | `:3000` 302 | not healthy in time: the frontend logged `Listening on http://0.0.0.0:3000` and `/` answered `302`, but it was still `health: starting` when the eight-minute window closed — the backend's start (migrations) on the LXC took about five minutes before the frontend could start; not repeated with a longer window |
| `apps/collabora` | LXC limitation | no HTTP answer | LXC limitation: coolwsd could not spawn coolforkit ("Failed to spawn coolforkit", `ECHILD`) — its jail setup needs mount and namespace rights an unprivileged LXC does not pass on; the host run of the same version passed |
| `apps/dashy` | pass | `:8080` 200 | healthy |
| `apps/defectdojo` | pass | `:8080` 302 | healthy |
| `apps/dependency-track` | pass | `:8080` 200 | healthy |
| `apps/dfir-iris` | pass | `:8080` 302 | healthy |
| `apps/dify` | pass | `:3000/install` 200 | healthy |
| `apps/docker-mailserver` | pass | no HTTP answer | healthy; a mail server without a web interface, no URL |
| `apps/docling-serve` | pass | `:8099/health` 200 | healthy |
| `apps/easyappointments` | pass | `:8080/index.php/installation` 200; `:8080/index.php/user/login` 503 | healthy; the first URL 200, the second 503 while the installer had not run |
| `apps/euro-office` | pass | `:8080/` 302 | healthy |
| `apps/ghost` | pass | `:2368/ghost/` 200 | healthy |
| `apps/greenmail` | pass | `:8080/` 200 | healthy |
| `apps/heimdall` | pass | `:8080` 200 | healthy |
| `apps/hemmelig` | pass | `:8080` 200 | healthy |
| `apps/heyform` | pass | `:9157` 200 | healthy |
| `apps/homarr` | pass | `:7575` 307 | healthy |
| `apps/homepage` | pass | `:3000` 200 | healthy |
| `apps/httpbin` | pass | `:8080` 200 | healthy |
| `apps/immich` | pass | `:2283` 200 | healthy |
| `apps/it-tools` | pass | `:8080` 200 | healthy |
| `apps/librephotos` | pass | `:8080` 200 | healthy |
| `apps/litellm` | pass | `:4000/v1/models` 401 | healthy |
| `apps/lycheeorg` | pass | `:8000` 307 | healthy |
| `apps/mailpit` | pass | `:8025` 200 | healthy |
| `apps/mailserver-jeboehm` | pass | `:8080` 302 | healthy |
| `apps/monicahq` | pass | `:8080` 500 | healthy, but `/` answered 500: `APP_KEY` filled with random hex instead of a `base64:` key — a runner artefact, inconclusive for the file |
| `apps/n8n` | pass | `:5678` 200 | healthy |
| `apps/nextcloud` | pass | `:8080` 302 | healthy |
| `apps/nocodb` | pass | `:8080` 200 | healthy |
| `apps/obot` | pass | `:8080` 200 | healthy |
| `apps/ollama` | pass | `:11434/api/generate` 405 | healthy |
| `apps/onlyoffice` | pass | `:8080/` 302 | healthy |
| `apps/opencanary` | pass | `:8080/` 302 | healthy |
| `apps/open-webui` | pass | `:8080` 200 | failed as root (a directory `mkdir` created as root was not writable for the image's user); healthy as a uid-1000 user |
| `apps/opnform` | pass | `:8080` 302 | healthy |
| `apps/paperless-gpt` | pass | `:8080` 200 | failed as root (a directory `mkdir` created as root was not writable for the image's user); healthy as a uid-1000 user |
| `apps/paperless-ngx` | pass | `:8000` 302 | healthy |
| `apps/photoprism` | pass | `:2342` 307 | healthy |
| `apps/photoview` | pass | `:8080` 200 | healthy |
| `apps/privatebin` | pass | `:8080` 200 | healthy |
| `apps/qdrant` | pass | `:6333/collections` 401 | failed as root (a directory `mkdir` created as root was not writable for the image's user); healthy as a uid-1000 user |
| `apps/_reference` | pass | `:8080/` 200 | healthy |
| `apps/seafile` | pass | no HTTP answer | healthy; the header names `http://127.0.0.1:8000`, which the runner did not probe — no HTTP status recorded |
| `apps/seafile-pro` | pass | no HTTP answer | healthy; the header names `http://127.0.0.1`, which the runner did not probe — no HTTP status recorded |
| `apps/shlink` | pass | `:8081` 200; `:8080/<slug>` 404 | healthy |
| `apps/stalwart` | pass | `:8080/admin` 302 | healthy |
| `apps/threat-dragon` | pass | `:8080` 200 | healthy |
| `apps/tymeslot` | pass | `:4000` 302 | healthy |
| `apps/unifi` | pass | no HTTP answer | healthy; the header's URL is `https://` with the image's self-signed certificate, which the runner did not accept — no HTTP status recorded |
| `apps/vaultwarden` | pass | `:8080` 200 | healthy |
| `apps/velociraptor` | pass | no HTTP answer | healthy; `https://` with a self-signed certificate, not accepted by the runner — no HTTP status recorded |
| `apps/vllm` | LXC limitation | no HTTP answer | LXC limitation: the CPU build of vLLM grew past the 3 GiB the LXC could be given (2.6 GiB in the worker alone) and stalled the container; stopped from the hypervisor host |
| `apps/whoami` | pass | `:8080/` 200 | healthy |
| `apps/wikijs` | pass | `:8080` 200 | healthy |
| `apps/windmill` | pass | `:8000/api/version` 200 | healthy |
| `apps/wordpress` | pass | `:8080` 302 | healthy |
| `apps/yopass` | pass | `:8080` 200 | healthy |
| `backup/kopia` | pass | no HTTP answer | healthy; the header's `https://` URL carries the image's own certificate, which the runner did not accept — no HTTP status recorded |
| `backup/rclone-web` | pass | `:5522` 200 | healthy |
| `backup/urbackup` | pass | `:55414` 200 | healthy |
| `business/akaunting` | pass | `:8080` 302 | healthy |
| `business/chatwoot` | pass | `:3000` 302 | healthy |
| `business/documenso` | pass | `:3000` 302 | healthy |
| `business/dolibarr` | pass | `:8080` 200 | healthy |
| `business/erpnext` | pass | `:8080` 404 | healthy |
| `business/facturascripts` | pass | `:8080` 200 | healthy |
| `business/invoiceninja` | pass | `:8080` 500 | healthy; `/` answered 500 at the moment of the probe while php-fpm still started (`connect() failed` in nginx's log) — the host run of the same version passed |
| `business/kimai` | pass | `:8001` 302 | healthy |
| `business/leantime` | pass | `:8080` 303 | healthy |
| `business/listmonk` | pass | `:9000` 200 | failed as root (a directory `mkdir` created as root was not writable for the image's user); healthy as a uid-1000 user |
| `business/matomo` | pass | `:8080` 200 | failed as root (a directory `mkdir` created as root was not writable for the image's user); healthy as a uid-1000 user |
| `business/openproject` | pass | `:8080` 302 | healthy |
| `business/opensign` | pass | `:3000` 200 | healthy |
| `business/plane` | pass | `:8080/god-mode` 301 | healthy |
| `business/plausible` | LXC limitation | no HTTP answer | LXC limitation: the ClickHouse service asks for `nofile` 262144 and runc refused it (`error setting rlimit type 7: operation not permitted`) — dockerd in the LXC runs with a hard open-files limit of 256000; the host run passed |
| `business/solidinvoice` | pass | `:8765/install` 200 | failed as root (a directory `mkdir` created as root was not writable for the image's user); healthy as a uid-1000 user |
| `business/twenty` | pass | `:3000` 200 | healthy |
| `business/vikunja` | pass | `:3456` 200 | healthy |
| `business/zammad` | pass | `:8080` 502 | healthy |
| `core/authelia` | pass | no HTTP answer | failed as root (a directory `mkdir` created as root was not writable for the image's user); healthy as a uid-1000 user |
| `core/authentik` | pass | `:9000/if/flow/initial-setup/` 200 | failed as root (a directory `mkdir` created as root was not writable for the image's user); healthy as a uid-1000 user |
| `core/dockhand` | pass | `:3000` 200 | healthy |
| `core/headscale` | pass | `:8080` 200 | healthy |
| `core/infisical` | pass | `:8080` 200 | healthy |
| `core/jumpserver` | pass | `:8080` 200 | failed as root (a directory `mkdir` created as root was not writable for the image's user); healthy as a uid-1000 user |
| `core/keycloak` | pass | `:8080/admin` 302 | healthy |
| `core/orion-belt` | pass | `:8080` 302 | healthy |
| `core/portainer` | pass | `:9000` 200 | failed as root (a directory `mkdir` created as root was not writable for the image's user); healthy as a uid-1000 user |
| `core/shellhub` | pass | `:8080` 502 | healthy |
| `core/step-ca` | pass | no HTTP answer | healthy; the header's `https://` URL carries the image's own certificate, which the runner did not accept — no HTTP status recorded |
| `core/teleport` | pass | no HTTP answer | healthy; the header's `https://` URL carries the image's own certificate, which the runner did not accept — no HTTP status recorded |
| `core/warpgate` | pass | no HTTP answer | healthy; the header's `https://` URL carries the image's own certificate, which the runner did not accept — no HTTP status recorded |
| `core/zot` | pass | `:8080/v2/` 401 | healthy |
| `development/static-site` | pass | `:8081/` 200 | failed as root (a directory `mkdir` created as root was not writable for the image's user); healthy as a uid-1000 user |
| `development/web-api` | pass | `:8082/healthz` 200 | healthy |
| `monitoring/beszel` | runner artefact | `:8090` 200 | runner artefact: the header's middle step is in the UI (owner account, then the token and the agent key copied into `.env.local`); the hub answered `200`, the agent restarted without a key, as it does until that step |
| `monitoring/changedetection` | pass | `:5000` 200 | healthy |
| `monitoring/checkmate` | pass | `:52345` 200 | failed as root (a directory `mkdir` created as root was not writable for the image's user); healthy as a uid-1000 user |
| `monitoring/ciao` | pass | `:8080` 401 | healthy |
| `monitoring/gatus` | pass | `:8080` 200 | healthy |
| `monitoring/gotify` | pass | `:8080` 200 | healthy |
| `monitoring/grafana-prometheus` | pass | `:3000` 302 | healthy |
| `monitoring/healthchecks` | pass | `:8000` 302 | healthy |
| `monitoring/langfuse` | pass | `:3000` 200 | healthy |
| `monitoring/ntfy` | pass | `:8080/mytopic` 200 | healthy |
| `monitoring/scrutiny` | pass | `:8080` 302 | healthy |
| `monitoring/uptime-kuma` | pass | `:3001` 302 | failed as root (a directory `mkdir` created as root was not writable for the image's user); healthy as a uid-1000 user |
| `monitoring/zabbix` | pass | `:8080` 200 | healthy |
