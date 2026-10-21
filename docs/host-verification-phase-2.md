# Host verification — core audit Phase 2 (2a–2e)

The test plan for what Phase 2 changed and no test in CI can establish: the
behaviour of a rendered proxy, of files under `/etc`, of a login gate and of a
CrowdSec exemption on a real host. Every result below is **not run** until a
row says otherwise, with the date and the evidence beside it. The plan is
written before the host exists; it changes no host.

What it covers, by pull request: #232 (2a entrypoint and validation, 2b host
files), #235 (2c Authentik switch, 2d stack fixes, 2e administrative exemption).

## Rules

- **A disposable host, never a production one.** Nothing here runs on a host
  that serves anyone. The host carries throwaway data and is reinstalled or
  discarded afterwards.
- **The administrative path is secured before anything can close it.** Before
  any CrowdSec enforcement is switched on, the hoster's console (VNC or serial)
  has been opened once and found working, a second SSH session is kept open for
  the whole session, and the reboot guard of
  [`core/crowdsec/docs/firewall-bouncer.md`](../core/crowdsec/docs/firewall-bouncer.md)
  is armed. The Authentik gate goes on `apps/whoami` only.
- **Automated where the check reads state** — `scripts/verify-phase-2.sh`
  prints `PASS`, `FAIL` or `SKIP` per check and changes nothing. **Manual where
  the step changes the host** — install a file, switch a setting, ban an
  address; those rows say *manual*.
- **A phase is verified only by its rows.** A green script run is one input;
  the manual rows and the evidence decide. Record a failure as a failure.

## Prerequisites

| | |
|---|---|
| Host | Debian 12 or 13, Docker 24+ with Compose v2, `envsubst`, `curl`, `jq`, `nft`; public IPv4, IPv6 where the hoster offers it; the hoster's console tested |
| Checkout | `git clone`, then `git checkout feature/crowdsec-allowlist` (2c–2e on top of `dev` with 2a–2b) — or `dev` once #235 is merged; `./scripts/overview.sh` states the commit |
| DNS | one test zone with a wildcard or three names: `whoami`, `vault`, `matomo` — with Cloudflare DNS-01, or HTTP-01 on a host reachable on 80 and 443 |
| VPN | the host joined to a test tailnet; one administrative device with an IPv4 and an IPv6 tailnet address, both known |
| Stacks | `core/traefik`, `apps/whoami`, `core/crowdsec`, `core/authentik`, `apps/vaultwarden`, `business/matomo`, `backup/borgmatic` (host-installed) — each from its README, `.env` filled with test values, no real secret |
| Values for the script | `export WHOAMI_HOST=… VAULT_HOST=… MATOMO_HOST=… ADMIN_V4=… ADMIN_V6=…` in the shell that runs `scripts/verify-phase-2.sh` |

## 2a — entrypoint and validation (#232)

| ID | Test | How | Expected | Pass when |
|---|---|---|---|---|
| A1 | validate → render → validate | automated | all three exit 0; `config/traefik.yml` carries `respondingTimeouts` with `60s`, `0s`, `180s` on `web` and `websecure`; `trustedIPs` lists exactly the ranges of `ops/cloudflare-ips.txt` | every assertion holds |
| A2 | the proxy starts on the rendered configuration | automated | `docker compose ps` shows both services healthy; `traefik.log` carries no `ERR` since start | healthy and no error |
| A3 | the published ranges match the file | automated | `check-cloudflare-ips.py --online` exits 0 | equal sets |
| A4 | an invalid timeout is refused before render | automated | `TRAEFIK_WRITE_TIMEOUT=ten` → `validate.sh` exits 1 naming the variable; `config/` unchanged | refused, nothing rendered |
| A5 | a write timeout ends a slow download | **manual** | set `TRAEFIK_WRITE_TIMEOUT=15s`, render, `--force-recreate traefik`; from a client `curl --limit-rate 50k` on a 2 MB file behind the proxy → transfer cut after ~15 s; set back to `0s`, render, recreate → the same transfer completes | both observations; the value is **not** carried to any host with users |
| A6 | `validate.sh` names every rendered file | automated | remove `config/dynamic/servers-transports.yml` → `validate.sh` exits 1 naming it; render restores it | refused, then green |

## 2b — host files (#232)

| ID | Test | How | Expected | Pass when |
|---|---|---|---|---|
| B1 | render into `config/host/` | automated | `scripts/host-files.sh render core/traefik backup/borgmatic` exits 0; the rendered stanza carries the checkout path and no placeholder; nothing under `/etc` changed (compare `find /etc -newer` before and after) | all hold |
| B2 | install through the printed commands | **manual** | run the lines `install-commands core/traefik` prints; `logrotate -d /etc/logrotate.d/traefik` lists both logs | both logs listed |
| B3 | the states, one after the other | **manual**, read by the script | after B2: `identical` for the stanza, `not installed` for the four watchdog files; edit one byte of the installed stanza → `differs` with both paths and the `diff` command; `chmod 600` → `differs (mode 600, manifest 0644)`; `chmod 000` → `unreadable`; `rm` → `missing`; reinstall → `identical` | every state produced and reported as named |
| B4 | a derived file | **manual** | install the watchdog env through the printed line, fill in `CONTAINER_NAME` and `HEALTHCHECKS_PING_URL` → `adapted`; delete the `PING_URL` line → `differs (missing setting(s): HEALTHCHECKS_PING_URL)`; add `EXTRA=1` → `adapted … not in the example: EXTRA` | the three verdicts |
| B5 | a secret | **manual** | `/root/.borg-passphrase` with mode 600 → `identical (present)`; mode 644 → `differs (mode 644, manifest 0600)`; the script output never contains the file's content | verdicts, and no content in any output |
| B6 | `overview.sh --host` | automated | exit 0 when every row is `identical`, `adapted` or `not installed`; exit 1 as soon as one row is `differs`, `missing` or `unreadable` | exit codes as stated |

## 2c — Authentik switch (#235)

| ID | Test | How | Expected | Pass when |
|---|---|---|---|---|
| C1 | switch off | automated | `AUTHENTIK_FORWARD_AUTH_ENABLED=false` → no `config/dynamic/authentik.yml`, `validate.sh` exits 0, `whoami` answers 200 | all hold |
| C2 | switch on, gate attached | **manual** then automated | Authentik running with the embedded outpost and a provider for `whoami`; `true`, render; `whoami`'s router gains `auth-authentik@file`; `curl -sI https://$WHOAMI_HOST/` → `302` with `Location` on the Authentik host | 302 to Authentik |
| C3 | a session passes and the headers arrive | **manual** | log in through the browser; `whoami` shows `X-Authentik-Username` and `X-Authentik-Email` among the request headers | both headers present |
| C4 | the outpost unreachable fails closed | automated | `docker stop authentik-server` → `curl -sI` answers 5xx or 403, never 200; `docker start` → 302 again | never 200 |
| C5 | switching off while a router names the gate | automated | `false`, render → `render.sh` prints the NOTICE; `whoami` answers 404 (router disabled), not 200 | 404, not open |
| C6 | the drift guard | automated | with the file rendered, remove the variable from `.env`, render → exit 1 naming the variable, file still present | refused |
| C7 | the other functions do not depend on the gate | automated | with the switch off, an `acc-tailscale` route still refuses a public client and admits the tailnet device; a `sec-*` route still sends its headers | unchanged |

## 2d — stack fixes (#235)

| ID | Test | How | Expected | Pass when |
|---|---|---|---|---|
| D1 | Vaultwarden's own frame header passes | automated | `curl -skI https://$VAULT_HOST/` → `X-Frame-Options: SAMEORIGIN` (the application's value), not `DENY`; `curl -skI https://$VAULT_HOST/connector.html` → no `X-Frame-Options` | both |
| D2 | Matomo's widget pages carry no proxy header | automated | `curl -skI "https://$MATOMO_HOST/index.php?module=Widgetize&action=iframe"` → no `X-Frame-Options`; the reporting UI (`/index.php`) → `deny` from Matomo | both |
| D3 | Keycloak unchanged | automated, where the stack is deployed | `/admin/master/console/` → `SAMEORIGIN` from Keycloak; `3p-cookies/step1.html` → none | both; `SKIP` when the stack is absent |
| D4 | `local` as the daemon's log driver | **manual** | `daemon.json` as in `deployment-lifecycle.md` §1, `systemctl restart docker`; `docker info --format '{{.LoggingDriver}}'` → `local`; a container recreated afterwards reports `local` in `docker inspect … LogConfig.Type`; one not recreated still reports `json-file` | all three observations |
| D5 | `docker compose logs` still works under `local` | automated | `docker compose logs --tail 5 traefik` prints lines | lines printed |

## 2e — the administrative exemption (#235)

These rows touch enforcement. The console has been tested, the second session
is open, and the host-firewall bouncer stays **off** until E6.

| ID | Test | How | Expected | Pass when |
|---|---|---|---|---|
| E1 | apply with both families | **manual** then automated | `CROWDSEC_ALLOWLIST_ADMIN=$ADMIN_V4,$ADMIN_V6`, `ops/allowlist.sh apply` → list created, two added; `check` answers "allowlisted" for each | both allowlisted |
| E2 | apply is idempotent and never removes | automated | second `apply` → `0 added, 2 already present`; remove one address from `.env`, `apply` → still 2 in `inspect` | both |
| E3 | the engine still sees the device | automated | requests from the device appear in `cscli metrics show acquisition` (lines read grow) | lines grow |
| E4 | a manual decision against an exempt address | **manual** | `cscli decisions add --ip $ADMIN_V4 --duration 5m` → is it listed by `cscli decisions list`? does `curl` from the device through the Traefik bouncer (`crowdsec-basic` on `whoami`) still answer 200 within 90 s? Record both answers — this is the open behaviour question | recorded, whatever the answer; the README is corrected to it |
| E5 | `--bypass-allowlist` | **manual** | `cscli decisions add --ip $ADMIN_V4 --duration 5m --bypass-allowlist` → listed and enforced by the Traefik bouncer (403 from the device within 90 s); `cscli decisions delete --ip $ADMIN_V4 --all` → 200 again | enforced, then lifted |
| E6 | the host-firewall bouncer follows both | **manual, console open** | bouncer on with the reboot guard; E4's decision → the address is **not** in `crowdsec-blacklists`; E5's decision → it **is**, and a *new* SSH connection from the device over the management interface is refused; delete → admitted again | all four observations |
| E7 | recovery drill from the console | **manual, console** | with E5's decision active on both families: no VPN access; from the console: `systemctl stop crowdsec-firewall-bouncer`, `cscli decisions delete --ip … --all` for each family, `ops/allowlist.sh apply`, `systemctl start crowdsec-firewall-bouncer`; a new connection from the device works | path works end to end, in the order the runbook states |
| E8 | a whole range is named | automated | `.env` with `100.64.0.0/10` → `apply` prints the WARNING and applies | both |

## Results

Filled in as the session runs; a row without a date was not run.

| Phase | ID | Result | Date | Evidence |
|---|---|---|---|---|
| 2a | A1–A6 | not run | | |
| 2b | B1–B6 | not run | | |
| 2c | C1–C7 | not run | | |
| 2d | D1–D5 | not run | | |
| 2e | E1–E8 | not run | | |

## Open points carried from the audit

Outside this plan, and still open after it: the rate-limit measurements per
application (D2 — synchronisation, large transfers, APIs, long-lived
connections), the Cloudflare mode (D3, Phase 3), the chain model (D1, Phase 4),
and the Trivy baseline before the next release.
