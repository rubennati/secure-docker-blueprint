# The middleware model — the cut, router by router

The middleware model of `core/traefik` (decisions D1–D8 of 2026-10-18, applied
2026-10-22) replaces the `sec-*` chains, the `acc-*` policies and the
`tls-basic|aplus|modern` profiles with four positions on every router, defined
once in [`config/dynamic/model.yml`](../ops/templates/dynamic/model.yml.tmpl).
Nothing of the vocabulary before it remains: there is no alias, and CI refuses
a stack that still carries a name from before (`retired-name`,
`router-positions`). This document records what the cut changes for every
router of the repository, measured against the tree before it, and what an
existing installation does to move. Section 4 has run once, on a disposable
test installation; the section at the end says what only a host can show.

**This is a breaking change for every existing installation.** A checkout
updated to this release without the migration serves nothing: every router's
label names `APP_TRAEFIK_LIMIT`, `APP_TRAEFIK_HEADERS` and `APP_TRAEFIK_AUTH`,
which an `.env` from before the model does not set, and Traefik disables a
router whose middleware does not exist; `render.sh` refuses the old
`TLS_DEFAULT_OPTION` in `core/traefik/.env` before that. Section 4 is the way
through; it has to run before the stacks are recreated.

| Function | Before the model | In the model |
|---|---|---|
| threat | `APP_TRAEFIK_THREAT` per router, empty by default | `threat-crowdsec` on the `websecure` entrypoint when `CROWDSEC_BOUNCER_ENABLED`, in front of every router; AppSec by `CROWDSEC_APPSEC_ENABLED` |
| access | `acc-public` · `acc-local` · `acc-tailscale` · `acc-private` · `acc-deny` | `access-public` · `access-lan` · `access-vpn` · `access-lan-vpn` · `access-blocked` — `APP_TRAEFIK_ACCESS` |
| rate limit | inside the chain: `rl-soft` 125/200, `rl-spa` 125/500, `rl-spa-xl` 125/1000, `rl-sync` 1000/1000, `rl-hard` 20/40 | `limit-standard` 125/500 · `limit-extra-large` 125/1000 · `limit-sync` 1000/1000 · `limit-strict` 20/40 · `limit-none` — `APP_TRAEFIK_LIMIT` |
| headers | inside the chain: `hdr-basic`, `hdr-basic-embed`, `hdr-strict`, `hdr-strict-embed`, `permissions-policy`, `csp-enforce`; `strip-xfo` in three stacks | `headers-standard` · `headers-application-owned` · `headers-none` — every profile starts with the HSTS base — plus a per-app block before the profile (`frame-self`, `csp-self-only`, `hsts-include-subdomains`, `header-*`) — `APP_TRAEFIK_HEADERS` |
| auth | appended by hand where a stack had a gate | `auth-none@file` · `auth-authentik@file` · the stack's own `<project>-auth@docker` — `APP_TRAEFIK_AUTH`, on every router |
| compression | inside every chain | `compress` on the entrypoint, for every router, with exact `excludedContentTypes` |
| TLS | `tls.options=${APP_TRAEFIK_TLS_OPTION}@file` on every router | the file provider's `default` option, built from `TLS_DEFAULT_OPTION` in `core/traefik/.env`; a router names an option only as a documented exception |
| backend compatibility | `-proto` / `-headers` Docker middlewares copied into six stacks | `forwarded-proto-https` after the four, where the application needs the header |

## 1. Behaviour changes

Counts are routers, not stacks: a stack's secondary routers (`-api`, `-ui`,
`-static`, Seafile's four side routers, Ghost's ActivityPub overlay) are
counted on their own. 131 routers in 110 stacks and `core/traefik`'s
dashboard were compared, the tree before commit 2 of the cut against the tree
after commit 4, each router resolved with its stack's `.env.example` the way
Compose resolves it. Section 3 lists every router.

### 1.1 Rate limits

**95 routers count a burst of 500 instead of 200** — every router that carried
`sec-2`, `sec-2e`, `sec-3` or `sec-3e` (D3). The sustained rate, 125 requests
per second per address, is unchanged. What the wider bucket costs is 300 more
requests per address before the first `429`, on every one of these routers at
once; what it buys is the end of the `-spa` special cases of ten stacks, and a default
under which every first load measured in September except Twenty's and
Windmill's fits. Behaviour over time — crawling, password guessing, probing —
is CrowdSec's layer, not the counter's.

`core/authelia`, `core/authentik`, `core/headscale`, `core/jumpserver`, `core/orion-belt`, `core/shellhub`, `core/warpgate`, `core/zot`, `apps/_reference` reference, `apps/agentgateway`, `apps/agentgateway` agentgateway-ui, `apps/bookstack`, `apps/caldiy`, `apps/calnode`, `apps/calrs`, `apps/dashy`, `apps/defectdojo`, `apps/dependency-track` dependency-track-api, `apps/dependency-track`, `apps/dfir-iris`, `apps/docling-serve`, `apps/easyappointments`, `apps/ghost` ghost-ap, `apps/ghost`, `apps/greenmail`, `apps/heimdall`, `apps/hemmelig`, `apps/heyform`, `apps/homarr`, `apps/homepage`, `apps/httpbin`, `apps/it-tools`, `apps/librephotos`, `apps/litellm`, `apps/lycheeorg` lychee, `apps/mailpit`, `apps/mailserver-jeboehm`, `apps/monicahq` monica, `apps/obot`, `apps/ollama`, `apps/opnform`, `apps/paperless-gpt`, `apps/paperless-ngx` paperless, `apps/photoprism`, `apps/photoview`, `apps/privatebin`, `apps/qdrant`, `apps/shlink` shlink-api, `apps/shlink`, `apps/shlink` shlink-client, `apps/stalwart`, `apps/threat-dragon`, `apps/tymeslot`, `apps/unifi`, `apps/vaultwarden`, `apps/vllm`, `apps/wikijs`, `apps/wordpress`, `apps/yopass`, `business/akaunting`, `business/chatwoot`, `business/documenso`, `business/dolibarr`, `business/erpnext`, `business/erpnext` erpnext-socketio, `business/facturascripts`, `business/invoiceninja`, `business/kimai`, `business/leantime`, `business/listmonk`, `business/matomo`, `business/openproject`, `business/plane`, `business/plausible`, `business/solidinvoice`, `business/vikunja`, `business/zammad`, `monitoring/beszel`, `monitoring/changedetection`, `monitoring/checkmate`, `monitoring/ciao`, `monitoring/gatus`, `monitoring/gotify`, `monitoring/grafana-prometheus` grafana, `monitoring/healthchecks`, `monitoring/langfuse`, `monitoring/scrutiny`, `monitoring/uptime-kuma`, `monitoring/zabbix`, `backup/kopia`, `backup/rclone-web`, `backup/rclone-web` rclone-web-api, `backup/urbackup`, `development/static-site`, `development/web-api`.

Every other router keeps its numbers: thirteen routers in ten stacks that
carried `-spa` were at 125/500 already (`core/dockhand`, `core/infisical`,
`core/keycloak`, `apps/ciso-assistant` and its `-api`, `apps/dify` — `-web`
and `-api` —, `apps/immich`, `apps/n8n`, `apps/nocodb`, `apps/open-webui`,
`business/opensign` — `-ui` and `-api`),
`limit-extra-large` keeps 125/1000 on Twenty and Windmill, `limit-sync` keeps
1000/1000 on Nextcloud, Seafile and Seafile Pro, `limit-strict` keeps 20/40 on
Adminer, Portainer, whoami, ntfy (both routers) and the dashboard, and twelve
routers that had no counter have none:

`core/authentik` authentik-static, `apps/collabora`, `apps/euro-office`, `apps/onlyoffice`, `apps/seafile` seafile-notification, `apps/seafile` seafile-seadoc-ws, `apps/seafile` seafile-seadoc, `apps/seafile` seafile-thumbnail, `apps/seafile-pro` seafile-pro-notification, `apps/seafile-pro` seafile-pro-seadoc-ws, `apps/seafile-pro` seafile-pro-seadoc, `apps/seafile-pro` seafile-pro-thumbnail.

### 1.2 HSTS

Every router sends `Strict-Transport-Security: max-age=63072000` from the
profile's `hsts-base` (`HSTS_MAX_AGE` in `core/traefik/.env`). `includeSubDomains`
and `preload` are a decision per host name, never a default (H2, 2026-10-18).

**52 routers stop sending `includeSubDomains` and `preload`** — every router
that carried the `sec-3` tier, `sec-4` or `sec-5`, and the dashboard. For a
browser that has already stored the policy with `includeSubDomains`, nothing
changes until the stored `max-age` runs out; for a host name submitted to the
browsers' preload list, the submission requires the header to keep both
directives, and a host name on that list has to restore them. To restore them
deliberately, place `hsts-include-subdomains@file` before
`${APP_TRAEFIK_HEADERS}@file` in the stack's `docker-compose.yml`; the block
stands before the profile so that it is applied after it on the response and
wins (measured 2026-10-18).

`core/authelia`, `core/authentik`, `core/dockhand`, `core/infisical`, `core/jumpserver`, `core/orion-belt`, `core/portainer`, `core/shellhub`, `core/warpgate`, `apps/adminer`, `apps/caldiy`, `apps/dashy`, `apps/dependency-track` dependency-track-api, `apps/dependency-track`, `apps/dfir-iris`, `apps/heimdall`, `apps/hemmelig`, `apps/homarr`, `apps/homepage`, `apps/it-tools`, `apps/mailpit`, `apps/monicahq` monica, `apps/n8n`, `apps/nextcloud`, `apps/nocodb`, `apps/paperless-ngx` paperless, `apps/privatebin`, `apps/threat-dragon`, `apps/tymeslot`, `apps/unifi`, `apps/vaultwarden`, `apps/whoami`, `apps/yopass`, `business/documenso`, `business/dolibarr`, `business/invoiceninja`, `business/kimai`, `business/matomo`, `business/openproject`, `business/opensign` opensign-api, `business/opensign` opensign-ui, `business/vikunja`, `business/zammad`, `monitoring/beszel`, `monitoring/changedetection`, `monitoring/gatus`, `monitoring/healthchecks`, `monitoring/ntfy`, `monitoring/ntfy` ntfy-ui, `monitoring/uptime-kuma`, `backup/urbackup`, `core/traefik`.

**8 routers send HSTS for the first time** — Seafile's and Seafile Pro's four
side routers, which carried an access policy and nothing else. They serve the
stack's host name, whose main router has sent the header all along, so a
browser already holds the policy; nothing changes for a client.

The six routers on `headers-application-owned` keep the proxy's base as
before. Keycloak's own `max-age=31536000; includeSubDomains` was already
replaced by the chain's two-year `max-age` before the cut, so its clients
receive what they received.

### 1.3 The other response headers

**76 routers gain `Permissions-Policy` and 75 gain
`Referrer-Policy: strict-origin-when-cross-origin`** — the `sec-1` and `sec-2`
tier, whose `hdr-basic` set HSTS, `nosniff` and the frame header only. Both are
restrictions on the browser, not on the application.

`core/authentik` authentik-static, `core/headscale`, `core/keycloak`, `core/zot`, `apps/_reference` reference, `apps/agentgateway`, `apps/agentgateway` agentgateway-ui, `apps/bookstack`, `apps/calnode`, `apps/calrs`, `apps/ciso-assistant` ciso-assistant-api, `apps/ciso-assistant`, `apps/defectdojo`, `apps/dify` dify-api, `apps/dify` dify-web, `apps/docling-serve`, `apps/easyappointments`, `apps/ghost` ghost-ap, `apps/ghost`, `apps/greenmail`, `apps/heyform`, `apps/httpbin`, `apps/immich`, `apps/librephotos`, `apps/litellm`, `apps/lycheeorg` lychee, `apps/mailserver-jeboehm`, `apps/obot`, `apps/ollama`, `apps/open-webui`, `apps/opnform`, `apps/paperless-gpt`, `apps/photoprism`, `apps/photoview`, `apps/qdrant`, `apps/seafile` seafile-notification, `apps/seafile` seafile-seadoc-ws, `apps/seafile` seafile-seadoc, `apps/seafile`, `apps/seafile` seafile-thumbnail, `apps/seafile-pro` seafile-pro-notification, `apps/seafile-pro` seafile-pro-seadoc-ws, `apps/seafile-pro` seafile-pro-seadoc, `apps/seafile-pro`, `apps/seafile-pro` seafile-pro-thumbnail, `apps/shlink` shlink-api, `apps/shlink`, `apps/shlink` shlink-client, `apps/stalwart`, `apps/vllm`, `apps/wikijs`, `apps/windmill`, `apps/wordpress`, `business/akaunting`, `business/chatwoot`, `business/erpnext`, `business/erpnext` erpnext-socketio, `business/facturascripts`, `business/leantime`, `business/listmonk`, `business/plane`, `business/plausible`, `business/solidinvoice`, `business/twenty`, `monitoring/checkmate`, `monitoring/ciao`, `monitoring/gotify`, `monitoring/grafana-prometheus` grafana, `monitoring/langfuse`, `monitoring/scrutiny`, `monitoring/zabbix`, `backup/kopia`, `backup/rclone-web`, `backup/rclone-web` rclone-web-api, `development/static-site`, `development/web-api`.

**52 routers stop sending the report-only CSP and the `Vary` header** of
`hdr-strict` — the same routers that lose the HSTS extension. The report-only
policy blocked nothing and reported to no endpoint, because no stack
configured one; the `Vary: Origin` header belonged to a CORS allow-list no stack
set. An enforcing policy stays where a stack had one: whoami's `csp-enforce`
is the block `csp-self-only`, the same policy string.

**The 8 Seafile side routers gain the whole standard set** — HSTS, `nosniff`,
`X-Frame-Options: DENY`, the referrer policy and the Permissions-Policy — where
they sent nothing from the proxy. Their paths are a long-poll endpoint, a
websocket, the SeaDoc server's API and thumbnail images; none of them is a
page a browser frames, as far as the repository knows. Whether SeaDoc loads
anything from `/sdoc-server` in a frame has not been checked on a host; if it
does, `frame-self@file` before the profile on that router is the correction.

**Six routers are `headers-application-owned`**: the proxy sets the HSTS base
and what the compose file names, and the application's own headers reach the
browser. Keycloak, Vaultwarden and Matomo were measured directly and behind
each profile on 2026-10-18; the three office servers were not measured, and
the proxy keeps setting for them what their own Docker middleware set before.

| Stack | The proxy stops setting | The proxy still sets | The application sends (measured) |
|---|---|---|---|
| `core/keycloak` | `nosniff`, the frame header (which the stack had stripped) | HSTS base, `Permissions-Policy` (`header-permissions`) | HSTS, `nosniff`, `no-referrer`, a CSP, `SAMEORIGIN` plus a CSP `frame-ancestors` on the console and no frame header on the two pages it frames |
| `apps/vaultwarden` | `nosniff`, `same-origin` referrer, the eight-directive Permissions-Policy, the report-only CSP, the frame header (stripped) | HSTS base | `nosniff`, `SAMEORIGIN` on the vault and none on the 2FA connector pages, `same-origin`, a 23-directive Permissions-Policy, an enforcing CSP |
| `business/matomo` | `strict-origin-when-cross-origin` referrer, the report-only CSP, the frame header (stripped) | HSTS base, `nosniff`, `Permissions-Policy` (two blocks) | an enforcing CSP, `sameorigin` per endpoint — `deny` on the reporting UI, none on the Widgetize endpoints — and `same-origin` |
| `apps/collabora`, `apps/onlyoffice`, `apps/euro-office` | `X-XSS-Protection` (obsolete; browsers ignore it); the explicit `X-Forwarded-Host` request header, which Traefik sets from the request on its own | HSTS base, `nosniff` (`header-nosniff`), the stack's `frame-ancestors` CSP (`<project>-csp@docker`), `X-Forwarded-Proto` to the backend | not measured |

**The three `strip-xfo` middlewares are gone.** They deleted the frame header
the chain set — and with it the application's own. Now the profile sets none
on these routers, so Keycloak's per-page, Vaultwarden's per-route and Matomo's
per-endpoint value reaches the browser: the behaviour the stacks' comments
asked for, and tighter than before, when no frame header arrived at all.

listmonk (`frame-self`) and Nextcloud (`frame-self`) keep `SAMEORIGIN`; every
other `headers-standard` router keeps or gains `DENY`.

### 1.4 TLS

A router with `tls=true` takes the file provider's `default` option, never the
entrypoint's (measured 2026-10-18); `default` is built from
`TLS_DEFAULT_OPTION` in `core/traefik/.env`, `tls-standard` as shipped. **115
routers drop their `tls.options` label** and take that option. On a
deployment that keeps `tls-standard`, they serve the handshake they served
with `tls-aplus`: the same minimum version, ciphers and curves under a new
name. On a deployment whose `core/traefik/.env` names another profile, they
now follow it — before the cut their label pinned them to `tls-aplus` whatever
the deployment chose. A change of `TLS_DEFAULT_OPTION` takes effect on a
recreate of the Traefik container, not on a reload (measured).

Thirteen stacks and the dashboard keep a named option, each a documented
exception; the reason stands above the variable in the stack's `.env.example`.

| Stack | Option | Reason |
|---|---|---|
| `apps/vaultwarden` | `tls-strict` | TLS 1.3 only for a password manager |
| `core/jumpserver`, `core/warpgate` | `tls-strict` | a PAM / bastion console takes the strictest profile |
| `core/dockhand`, `core/orion-belt`, `core/portainer`, `core/shellhub` | `tls-strict` | no reason recorded before the cut; kept as it was, to verify on a host |
| `apps/shlink` | `tls-compatible` | a short link is followed by whatever client it is pasted into |
| `apps/nextcloud`, `apps/whoami`, `apps/wordpress`, `business/openproject`, `business/vikunja` | `tls-compatible` | no reason recorded before the cut; kept as it was, to verify on a host and then drop |
| `core/traefik` dashboard | `TRAEFIK_DASHBOARD_TLS_OPTION`, `tls-strict` | a system route may be stricter than the deployment standard |

Two routers of one stack that name different options for one host name are a
conflict Traefik resolves by serving `default` to both; CI refuses it
(`tls-conflict`) and `overview.sh --host` repeats the check across stacks with
the live `.env` files.

### 1.5 Threat enforcement

66 routers carried `${APP_TRAEFIK_THREAT}` in their label; every shipped
`.env.example` left it empty. The slot is gone: `CROWDSEC_BOUNCER_ENABLED=true`
places `threat-crowdsec@file` on the `websecure` entrypoint in front of every
router, `CROWDSEC_APPSEC_ENABLED=true` the inspecting variant instead. For a
deployment that had named the bouncer on some routers, this is a change in
both directions: with the switch on, every router is behind the bouncer, with
it off, none is — exemptions are CrowdSec AllowLists, never a label. The
migration script prints one line per stack that had the bouncer on. After a
render that switches the bouncer off, the Traefik container has to be
recreated at once: until then the running entrypoint list names a middleware
the dynamic configuration no longer defines, and every router is disabled.

### 1.6 Compression

`compress` is one definition, on the entrypoint, for every router, with exact
`excludedContentTypes` (`application/octet-stream` and `image/png` measured as
wasted work, jpeg, webp, avif, gif, zip, gzip, mp4, mpeg and woff2 by type).
Streams are not buffered: `text/event-stream` stays compressible and events
arrive as sent, a websocket upgrade is untouched (measured 2026-10-18).

**11 routers are compressed for the first time**: the three office servers and
the eight Seafile side routers, which carried no chain. Collabora's document
traffic is a websocket and unaffected; a document download from OnlyOffice or
Euro-Office is a `application/vnd.openxmlformats-…` body and is now
compressed above 1024 bytes — not measured; if it costs more CPU than it
saves, the type belongs in the exclusion list in `model.yml`, one place.

### 1.7 The auth position

129 routers carry `auth-none@file`: an explicit "no gate", where before the
position did not exist. `apps/paperless-gpt` and `monitoring/scrutiny` carry
their own basicAuth, provider-qualified (`${COMPOSE_PROJECT_NAME}-auth@docker`),
as before. `apps/paperless-ngx` names `ADMIN_TRAEFIK_AUTH=auth-authentik@file`
for its optional, commented-out `-admin` router. No router gained or lost a
gate.

## 2. Special cases, per stack

| Stack | What is particular | Evidence |
|---|---|---|
| `core/keycloak` | `headers-application-owned` + `header-permissions` before the profile; `strip-xfo` gone | measured 2026-10-18 |
| `apps/vaultwarden` | `headers-application-owned`, no block; `strip-xfo` gone; `tls-strict` kept | measured 2026-10-18 |
| `business/matomo` | `headers-application-owned` + `header-nosniff` + `header-permissions` before the profile, `forwarded-proto-https` after the four; `strip-xfo` and the `-headers` request middleware gone (the explicit `X-Forwarded-Host` with it; Traefik sets it from the request) | measured 2026-10-18 |
| `business/listmonk` | `frame-self` before `headers-standard` — the campaign preview renders in an iframe | documented |
| `apps/nextcloud` | `limit-sync`; `frame-self` before `headers-standard`; `tls-compatible` kept without a recorded reason | sync measured; headers not measured |
| `apps/whoami` | `limit-strict`; `csp-self-only` before the profile — the enforcing policy of `sec-5`, same string; `tls-compatible` kept without a recorded reason | documented |
| `apps/collabora`, `apps/onlyoffice`, `apps/euro-office` | `limit-none` as before; `headers-application-owned` with `header-nosniff` and the stack's `-csp@docker` (`frame-ancestors`) before the profile; `forwarded-proto-https` after the four; `-proto` and `-headers` gone — with them the explicit `X-Forwarded-Host`, which Traefik sets from the request — and `X-XSS-Protection` gone | not measured |
| `apps/seafile`, `apps/seafile-pro` | main router `limit-sync`; the four side routers `SIDE_TRAEFIK_LIMIT=limit-none` and the stack's headers profile; `seadoc-strip@docker` after the four on `-seadoc` | side routers assumed, see 1.3 |
| `core/authentik` | `-static` router `STATIC_TRAEFIK_LIMIT=limit-none` (no counter, as `sec-1` had none) and the portal's headers | documented |
| `apps/paperless-ngx` | `forwarded-proto-https` after the four; the commented `-admin` router reads `ADMIN_TRAEFIK_AUTH`; the `-headers` request middleware gone (the explicit `X-Forwarded-Host` with it; Traefik sets it from the request) | documented (bugfix 2026-05-03) |
| `apps/paperless-gpt`, `monitoring/scrutiny` | `APP_TRAEFIK_AUTH=${COMPOSE_PROJECT_NAME}-auth@docker` — the stack's basicAuth | unchanged |
| `business/vikunja` | `-sso-redirect@docker` after the four; `tls-compatible` kept without a recorded reason | unchanged |
| `apps/ghost` | the ActivityPub overlay's `-ap` router: the four positions, `forwarded-proto-https` after them (bugfix 2026-05-02) | documented |
| `apps/shlink` | three routers, two with their own access variable; `tls-compatible` kept with its reason | documented |
| `apps/agentgateway`, `monitoring/ntfy` | the `-ui` router keeps its own access variable; the rest the stack's | unchanged |
| `apps/dependency-track` | the `-api` router on its own host name, the stack's four values | unchanged |
| `business/twenty`, `apps/windmill` | `limit-extra-large`, both behind a closed policy (`access-vpn`, `access-blocked`) | measured |
| `core/traefik` dashboard | `access-vpn`, `limit-strict`, `headers-standard`, `auth-none`; loses `includeSubDomains`/`preload` like the `sec-3` tier; names `tls-strict` | documented |

## 3. Every router, before and after

Access, rate limit and TLS read "before → after"; the headers column names
only what changes between the proxy's set before and after (`proxy` means the
proxy sets it, `application's own` means the application's header reaches the
browser). `default` is the file provider's option from `TLS_DEFAULT_OPTION`.
The last column lists the model's blocks, the stack's own `@docker` middlewares
that stay, and a gate other than `auth-none`.

| Stack | Router | Access | Rate limit (avg/s / burst) | Headers — what changes | TLS option | Blocks, gate |
|---|---|---|---|---|---|---|
| `core/authelia` | `authelia` | acc-public → access-public | 125/200 → 125/500 | CSP report-only: proxy → none; HSTS: max-age+includeSubDomains+preload → max-age; Vary: proxy → none | tls-aplus → default | — |
| `core/authentik` | `authentik` | acc-public → access-public | 125/200 → 125/500 | CSP report-only: proxy → none; HSTS: max-age+includeSubDomains+preload → max-age; Vary: proxy → none | tls-aplus → default | — |
| `core/authentik` | `authentik-static` | acc-public → access-public | none → none | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `core/dockhand` | `dockhand` | acc-tailscale → access-vpn | 125/500 → 125/500 | CSP report-only: proxy → none; HSTS: max-age+includeSubDomains+preload → max-age; Vary: proxy → none | tls-modern → tls-strict | — |
| `core/headscale` | `headscale` | acc-local → access-lan | 125/200 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `core/infisical` | `infisical` | acc-tailscale → access-vpn | 125/500 → 125/500 | CSP report-only: proxy → none; HSTS: max-age+includeSubDomains+preload → max-age; Vary: proxy → none | tls-aplus → default | — |
| `core/jumpserver` | `jumpserver` | acc-tailscale → access-vpn | 125/200 → 125/500 | CSP report-only: proxy → none; HSTS: max-age+includeSubDomains+preload → max-age; Vary: proxy → none | tls-modern → tls-strict | — |
| `core/keycloak` | `keycloak` | acc-tailscale → access-vpn | 125/500 → 125/500 | Permissions-Policy: none → proxy; frame: none (stripped by the stack) → application's own (per page); nosniff: proxy → application's own | tls-aplus → default | header-permissions |
| `core/orion-belt` | `orion-belt` | acc-tailscale → access-vpn | 125/200 → 125/500 | CSP report-only: proxy → none; HSTS: max-age+includeSubDomains+preload → max-age; Vary: proxy → none | tls-modern → tls-strict | — |
| `core/portainer` | `portainer` | acc-tailscale → access-vpn | 20/40 → 20/40 | CSP report-only: proxy → none; HSTS: max-age+includeSubDomains+preload → max-age; Vary: proxy → none | tls-modern → tls-strict | — |
| `core/shellhub` | `shellhub` | acc-tailscale → access-vpn | 125/200 → 125/500 | CSP report-only: proxy → none; HSTS: max-age+includeSubDomains+preload → max-age; Vary: proxy → none | tls-modern → tls-strict | — |
| `core/warpgate` | `warpgate` | acc-tailscale → access-vpn | 125/200 → 125/500 | CSP report-only: proxy → none; HSTS: max-age+includeSubDomains+preload → max-age; Vary: proxy → none | tls-modern → tls-strict | — |
| `core/zot` | `zot` | acc-tailscale → access-vpn | 125/200 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `apps/_reference` | `reference` | acc-public → access-public | 125/200 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `apps/adminer` | `adminer` | acc-tailscale → access-vpn | 20/40 → 20/40 | CSP report-only: proxy → none; HSTS: max-age+includeSubDomains+preload → max-age; Vary: proxy → none | tls-aplus → default | — |
| `apps/agentgateway` | `agentgateway` | acc-private → access-lan-vpn | 125/200 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `apps/agentgateway` | `agentgateway-ui` | acc-private → access-lan-vpn | 125/200 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `apps/bookstack` | `bookstack` | acc-public → access-public | 125/200 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `apps/caldiy` | `caldiy` | acc-public → access-public | 125/200 → 125/500 | CSP report-only: proxy → none; HSTS: max-age+includeSubDomains+preload → max-age; Vary: proxy → none | tls-aplus → default | — |
| `apps/calnode` | `calnode` | acc-tailscale → access-vpn | 125/200 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `apps/calrs` | `calrs` | acc-tailscale → access-vpn | 125/200 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `apps/ciso-assistant` | `ciso-assistant-api` | acc-tailscale → access-vpn | 125/500 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `apps/ciso-assistant` | `ciso-assistant` | acc-tailscale → access-vpn | 125/500 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `apps/collabora` | `collabora` | acc-public → access-public | none → none | X-XSS-Protection: proxy → none | tls-aplus → default | header-nosniff, forwarded-proto-https, collabora-csp@docker |
| `apps/dashy` | `dashy` | acc-tailscale → access-vpn | 125/200 → 125/500 | CSP report-only: proxy → none; HSTS: max-age+includeSubDomains+preload → max-age; Vary: proxy → none | tls-aplus → default | — |
| `apps/defectdojo` | `defectdojo` | acc-tailscale → access-vpn | 125/200 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `apps/dependency-track` | `dependency-track-api` | acc-tailscale → access-vpn | 125/200 → 125/500 | CSP report-only: proxy → none; HSTS: max-age+includeSubDomains+preload → max-age; Vary: proxy → none | tls-aplus → default | — |
| `apps/dependency-track` | `dependency-track` | acc-tailscale → access-vpn | 125/200 → 125/500 | CSP report-only: proxy → none; HSTS: max-age+includeSubDomains+preload → max-age; Vary: proxy → none | tls-aplus → default | — |
| `apps/dfir-iris` | `dfir-iris` | acc-tailscale → access-vpn | 125/200 → 125/500 | CSP report-only: proxy → none; HSTS: max-age+includeSubDomains+preload → max-age; Vary: proxy → none | tls-aplus → default | — |
| `apps/dify` | `dify-api` | acc-private → access-lan-vpn | 125/500 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `apps/dify` | `dify-web` | acc-private → access-lan-vpn | 125/500 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `apps/docling-serve` | `docling-serve` | acc-private → access-lan-vpn | 125/200 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `apps/easyappointments` | `easyappointments` | acc-public → access-public | 125/200 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `apps/euro-office` | `euro-office` | acc-public → access-public | none → none | X-XSS-Protection: proxy → none | tls-aplus → default | header-nosniff, forwarded-proto-https, euro-office-csp@docker |
| `apps/ghost` | `ghost-ap` | acc-public → access-public | 125/200 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | forwarded-proto-https |
| `apps/ghost` | `ghost` | acc-public → access-public | 125/200 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `apps/greenmail` | `greenmail` | acc-private → access-lan-vpn | 125/200 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `apps/heimdall` | `heimdall` | acc-tailscale → access-vpn | 125/200 → 125/500 | CSP report-only: proxy → none; HSTS: max-age+includeSubDomains+preload → max-age; Vary: proxy → none | tls-aplus → default | — |
| `apps/hemmelig` | `hemmelig` | acc-public → access-public | 125/200 → 125/500 | CSP report-only: proxy → none; HSTS: max-age+includeSubDomains+preload → max-age; Vary: proxy → none | tls-aplus → default | — |
| `apps/heyform` | `heyform` | acc-tailscale → access-vpn | 125/200 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `apps/homarr` | `homarr` | acc-tailscale → access-vpn | 125/200 → 125/500 | CSP report-only: proxy → none; HSTS: max-age+includeSubDomains+preload → max-age; Vary: proxy → none | tls-aplus → default | — |
| `apps/homepage` | `homepage` | acc-tailscale → access-vpn | 125/200 → 125/500 | CSP report-only: proxy → none; HSTS: max-age+includeSubDomains+preload → max-age; Vary: proxy → none | tls-aplus → default | — |
| `apps/httpbin` | `httpbin` | acc-tailscale → access-vpn | 125/200 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `apps/immich` | `immich` | acc-public → access-public | 125/500 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `apps/it-tools` | `it-tools` | acc-tailscale → access-vpn | 125/200 → 125/500 | CSP report-only: proxy → none; HSTS: max-age+includeSubDomains+preload → max-age; Vary: proxy → none | tls-aplus → default | — |
| `apps/librephotos` | `librephotos` | acc-public → access-public | 125/200 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `apps/litellm` | `litellm` | acc-private → access-lan-vpn | 125/200 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `apps/lycheeorg` | `lychee` | acc-public → access-public | 125/200 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `apps/mailpit` | `mailpit` | acc-tailscale → access-vpn | 125/200 → 125/500 | CSP report-only: proxy → none; HSTS: max-age+includeSubDomains+preload → max-age; Vary: proxy → none | tls-aplus → default | — |
| `apps/mailserver-jeboehm` | `mailserver-jeboehm` | acc-tailscale → access-vpn | 125/200 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `apps/monicahq` | `monica` | acc-tailscale → access-vpn | 125/200 → 125/500 | CSP report-only: proxy → none; HSTS: max-age+includeSubDomains+preload → max-age; Vary: proxy → none | tls-aplus → default | — |
| `apps/n8n` | `n8n` | acc-tailscale → access-vpn | 125/500 → 125/500 | CSP report-only: proxy → none; HSTS: max-age+includeSubDomains+preload → max-age; Vary: proxy → none | tls-aplus → default | — |
| `apps/nextcloud` | `nextcloud` | acc-private → access-lan-vpn | 1000/1000 → 1000/1000 | CSP report-only: proxy → none; HSTS: max-age+includeSubDomains+preload → max-age; Vary: proxy → none; referrer: same-origin → strict-origin-when-cross-origin | tls-basic → tls-compatible | frame-self |
| `apps/nocodb` | `nocodb` | acc-tailscale → access-vpn | 125/500 → 125/500 | CSP report-only: proxy → none; HSTS: max-age+includeSubDomains+preload → max-age; Vary: proxy → none | tls-aplus → default | — |
| `apps/obot` | `obot` | acc-tailscale → access-vpn | 125/200 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `apps/ollama` | `ollama` | acc-private → access-lan-vpn | 125/200 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `apps/onlyoffice` | `onlyoffice` | acc-public → access-public | none → none | X-XSS-Protection: proxy → none | tls-aplus → default | header-nosniff, forwarded-proto-https, onlyoffice-csp@docker |
| `apps/open-webui` | `open-webui` | acc-private → access-lan-vpn | 125/500 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `apps/opnform` | `opnform` | acc-public → access-public | 125/200 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `apps/paperless-gpt` | `paperless-gpt` | acc-tailscale → access-vpn | 125/200 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | paperless-gpt-auth@docker |
| `apps/paperless-ngx` | `paperless` | acc-tailscale → access-vpn | 125/200 → 125/500 | CSP report-only: proxy → none; HSTS: max-age+includeSubDomains+preload → max-age; Vary: proxy → none | tls-aplus → default | forwarded-proto-https |
| `apps/photoprism` | `photoprism` | acc-public → access-public | 125/200 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `apps/photoview` | `photoview` | acc-public → access-public | 125/200 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `apps/privatebin` | `privatebin` | acc-public → access-public | 125/200 → 125/500 | CSP report-only: proxy → none; HSTS: max-age+includeSubDomains+preload → max-age; Vary: proxy → none | tls-aplus → default | — |
| `apps/qdrant` | `qdrant` | acc-private → access-lan-vpn | 125/200 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `apps/seafile` | `seafile-notification` | acc-private → access-lan-vpn | none → none | HSTS: none → max-age; Permissions-Policy: none → proxy; frame: none → DENY; nosniff: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `apps/seafile` | `seafile-seadoc-ws` | acc-private → access-lan-vpn | none → none | HSTS: none → max-age; Permissions-Policy: none → proxy; frame: none → DENY; nosniff: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `apps/seafile` | `seafile-seadoc` | acc-private → access-lan-vpn | none → none | HSTS: none → max-age; Permissions-Policy: none → proxy; frame: none → DENY; nosniff: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | seadoc-strip@docker |
| `apps/seafile` | `seafile` | acc-private → access-lan-vpn | 1000/1000 → 1000/1000 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `apps/seafile` | `seafile-thumbnail` | acc-private → access-lan-vpn | none → none | HSTS: none → max-age; Permissions-Policy: none → proxy; frame: none → DENY; nosniff: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `apps/seafile-pro` | `seafile-pro-notification` | acc-private → access-lan-vpn | none → none | HSTS: none → max-age; Permissions-Policy: none → proxy; frame: none → DENY; nosniff: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `apps/seafile-pro` | `seafile-pro-seadoc-ws` | acc-private → access-lan-vpn | none → none | HSTS: none → max-age; Permissions-Policy: none → proxy; frame: none → DENY; nosniff: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `apps/seafile-pro` | `seafile-pro-seadoc` | acc-private → access-lan-vpn | none → none | HSTS: none → max-age; Permissions-Policy: none → proxy; frame: none → DENY; nosniff: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | seadoc-strip@docker |
| `apps/seafile-pro` | `seafile-pro` | acc-private → access-lan-vpn | 1000/1000 → 1000/1000 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `apps/seafile-pro` | `seafile-pro-thumbnail` | acc-private → access-lan-vpn | none → none | HSTS: none → max-age; Permissions-Policy: none → proxy; frame: none → DENY; nosniff: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `apps/shlink` | `shlink-api` | acc-tailscale → access-vpn | 125/200 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-basic → tls-compatible | — |
| `apps/shlink` | `shlink` | acc-private → access-lan-vpn | 125/200 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-basic → tls-compatible | — |
| `apps/shlink` | `shlink-client` | acc-tailscale → access-vpn | 125/200 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-basic → tls-compatible | — |
| `apps/stalwart` | `stalwart` | acc-tailscale → access-vpn | 125/200 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `apps/threat-dragon` | `threat-dragon` | acc-tailscale → access-vpn | 125/200 → 125/500 | CSP report-only: proxy → none; HSTS: max-age+includeSubDomains+preload → max-age; Vary: proxy → none | tls-aplus → default | — |
| `apps/tymeslot` | `tymeslot` | acc-tailscale → access-vpn | 125/200 → 125/500 | CSP report-only: proxy → none; HSTS: max-age+includeSubDomains+preload → max-age; Vary: proxy → none | tls-aplus → default | — |
| `apps/unifi` | `unifi` | acc-tailscale → access-vpn | 125/200 → 125/500 | CSP report-only: proxy → none; HSTS: max-age+includeSubDomains+preload → max-age; Vary: proxy → none | tls-aplus → default | — |
| `apps/vaultwarden` | `vaultwarden` | acc-tailscale → access-vpn | 125/200 → 125/500 | CSP report-only: proxy → none; HSTS: max-age+includeSubDomains+preload → max-age; Permissions-Policy: proxy → application's own (23 directives); Vary: proxy → none; frame: none (stripped by the stack) → application's own (SAMEORIGIN; none on the 2FA connector pages); nosniff: proxy → application's own; referrer: same-origin → application's own (same-origin) | tls-modern → tls-strict | — |
| `apps/vllm` | `vllm` | acc-private → access-lan-vpn | 125/200 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `apps/whoami` | `whoami` | acc-tailscale → access-vpn | 20/40 → 20/40 | CSP report-only: proxy → none; HSTS: max-age+includeSubDomains+preload → max-age; Vary: proxy → none | tls-basic → tls-compatible | csp-self-only |
| `apps/wikijs` | `wikijs` | acc-tailscale → access-vpn | 125/200 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `apps/windmill` | `windmill` | acc-deny → access-blocked | 125/1000 → 125/1000 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `apps/wordpress` | `wordpress` | acc-public → access-public | 125/200 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-basic → tls-compatible | — |
| `apps/yopass` | `yopass` | acc-public → access-public | 125/200 → 125/500 | CSP report-only: proxy → none; HSTS: max-age+includeSubDomains+preload → max-age; Vary: proxy → none | tls-aplus → default | — |
| `business/akaunting` | `akaunting` | acc-tailscale → access-vpn | 125/200 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `business/chatwoot` | `chatwoot` | acc-tailscale → access-vpn | 125/200 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `business/documenso` | `documenso` | acc-public → access-public | 125/200 → 125/500 | CSP report-only: proxy → none; HSTS: max-age+includeSubDomains+preload → max-age; Vary: proxy → none | tls-aplus → default | — |
| `business/dolibarr` | `dolibarr` | acc-tailscale → access-vpn | 125/200 → 125/500 | CSP report-only: proxy → none; HSTS: max-age+includeSubDomains+preload → max-age; Vary: proxy → none | tls-aplus → default | — |
| `business/erpnext` | `erpnext` | acc-tailscale → access-vpn | 125/200 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `business/erpnext` | `erpnext-socketio` | acc-tailscale → access-vpn | 125/200 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `business/facturascripts` | `facturascripts` | acc-tailscale → access-vpn | 125/200 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `business/invoiceninja` | `invoiceninja` | acc-tailscale → access-vpn | 125/200 → 125/500 | CSP report-only: proxy → none; HSTS: max-age+includeSubDomains+preload → max-age; Vary: proxy → none | tls-aplus → default | — |
| `business/kimai` | `kimai` | acc-tailscale → access-vpn | 125/200 → 125/500 | CSP report-only: proxy → none; HSTS: max-age+includeSubDomains+preload → max-age; Vary: proxy → none | tls-aplus → default | — |
| `business/leantime` | `leantime` | acc-tailscale → access-vpn | 125/200 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `business/listmonk` | `listmonk` | acc-public → access-public | 125/200 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | frame-self |
| `business/matomo` | `matomo` | acc-public → access-public | 125/200 → 125/500 | CSP report-only: proxy → none; HSTS: max-age+includeSubDomains+preload → max-age; Vary: proxy → none; frame: none (stripped by the stack) → application's own (per endpoint); referrer: strict-origin-when-cross-origin → application's own (same-origin) | tls-aplus → default | header-nosniff, header-permissions, forwarded-proto-https |
| `business/openproject` | `openproject` | acc-tailscale → access-vpn | 125/200 → 125/500 | CSP report-only: proxy → none; HSTS: max-age+includeSubDomains+preload → max-age; Vary: proxy → none | tls-basic → tls-compatible | — |
| `business/opensign` | `opensign-api` | acc-public → access-public | 125/500 → 125/500 | CSP report-only: proxy → none; HSTS: max-age+includeSubDomains+preload → max-age; Vary: proxy → none | tls-aplus → default | — |
| `business/opensign` | `opensign-ui` | acc-public → access-public | 125/500 → 125/500 | CSP report-only: proxy → none; HSTS: max-age+includeSubDomains+preload → max-age; Vary: proxy → none | tls-aplus → default | — |
| `business/plane` | `plane` | acc-tailscale → access-vpn | 125/200 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `business/plausible` | `plausible` | acc-tailscale → access-vpn | 125/200 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `business/solidinvoice` | `solidinvoice` | acc-tailscale → access-vpn | 125/200 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `business/twenty` | `twenty` | acc-tailscale → access-vpn | 125/1000 → 125/1000 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `business/vikunja` | `vikunja` | acc-tailscale → access-vpn | 125/200 → 125/500 | CSP report-only: proxy → none; HSTS: max-age+includeSubDomains+preload → max-age; Vary: proxy → none | tls-basic → tls-compatible | vikunja-sso-redirect@docker |
| `business/zammad` | `zammad` | acc-public → access-public | 125/200 → 125/500 | CSP report-only: proxy → none; HSTS: max-age+includeSubDomains+preload → max-age; Vary: proxy → none | tls-aplus → default | — |
| `monitoring/beszel` | `beszel` | acc-tailscale → access-vpn | 125/200 → 125/500 | CSP report-only: proxy → none; HSTS: max-age+includeSubDomains+preload → max-age; Vary: proxy → none | tls-aplus → default | — |
| `monitoring/changedetection` | `changedetection` | acc-tailscale → access-vpn | 125/200 → 125/500 | CSP report-only: proxy → none; HSTS: max-age+includeSubDomains+preload → max-age; Vary: proxy → none | tls-aplus → default | — |
| `monitoring/checkmate` | `checkmate` | acc-tailscale → access-vpn | 125/200 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `monitoring/ciao` | `ciao` | acc-tailscale → access-vpn | 125/200 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `monitoring/gatus` | `gatus` | acc-tailscale → access-vpn | 125/200 → 125/500 | CSP report-only: proxy → none; HSTS: max-age+includeSubDomains+preload → max-age; Vary: proxy → none | tls-aplus → default | — |
| `monitoring/gotify` | `gotify` | acc-tailscale → access-vpn | 125/200 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `monitoring/grafana-prometheus` | `grafana` | acc-tailscale → access-vpn | 125/200 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `monitoring/healthchecks` | `healthchecks` | acc-tailscale → access-vpn | 125/200 → 125/500 | CSP report-only: proxy → none; HSTS: max-age+includeSubDomains+preload → max-age; Vary: proxy → none | tls-aplus → default | — |
| `monitoring/langfuse` | `langfuse` | acc-private → access-lan-vpn | 125/200 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `monitoring/ntfy` | `ntfy` | acc-public → access-public | 20/40 → 20/40 | CSP report-only: proxy → none; HSTS: max-age+includeSubDomains+preload → max-age; Vary: proxy → none | tls-aplus → default | — |
| `monitoring/ntfy` | `ntfy-ui` | acc-tailscale → access-vpn | 20/40 → 20/40 | CSP report-only: proxy → none; HSTS: max-age+includeSubDomains+preload → max-age; Vary: proxy → none | tls-aplus → default | — |
| `monitoring/scrutiny` | `scrutiny` | acc-tailscale → access-vpn | 125/200 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | scrutiny-auth@docker |
| `monitoring/uptime-kuma` | `uptime-kuma` | acc-tailscale → access-vpn | 125/200 → 125/500 | CSP report-only: proxy → none; HSTS: max-age+includeSubDomains+preload → max-age; Vary: proxy → none | tls-aplus → default | — |
| `monitoring/zabbix` | `zabbix` | acc-tailscale → access-vpn | 125/200 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `backup/kopia` | `kopia` | acc-tailscale → access-vpn | 125/200 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `backup/rclone-web` | `rclone-web` | acc-tailscale → access-vpn | 125/200 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `backup/rclone-web` | `rclone-web-api` | acc-tailscale → access-vpn | 125/200 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `backup/urbackup` | `urbackup` | acc-tailscale → access-vpn | 125/200 → 125/500 | CSP report-only: proxy → none; HSTS: max-age+includeSubDomains+preload → max-age; Vary: proxy → none | tls-aplus → default | — |
| `development/static-site` | `static-site` | acc-public → access-public | 125/200 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `development/web-api` | `web-api` | acc-public → access-public | 125/200 → 125/500 | Permissions-Policy: none → proxy; referrer: none → strict-origin-when-cross-origin | tls-aplus → default | — |
| `core/traefik` | `traefik-dashboard` | acc-tailscale → access-vpn | 20/40 → 20/40 | CSP report-only: proxy → none; HSTS: max-age+includeSubDomains+preload → max-age; Vary: proxy → none | tls-modern → tls-strict (named) | — |

## 4. Moving an installation

No production change happens under this document. The order for a host, to
be run from its own migration plan:

1. **Inventory.** Which stacks run; every `.env` next to a `docker-compose.yml`;
   hand edits in `core/traefik/config/`; the release the host runs
   (`./scripts/overview.sh`).
2. **Dry run.** `scripts/migrate-traefik-env.sh --all` prints every change and,
   per stack, every consequence that is not a rename — the bucket, the HSTS
   extension, a frame or CSP block that now lives in the compose file, the
   bouncer that moves to the switch. Read all of it. A value the script does
   not know stops it before anything is written.
3. **Backup.** The host's blueprint directory, `core/traefik/config/`, every
   `.env` (the script writes `.env.pre-model` beside each when it writes).
4. **Write.** `scripts/migrate-traefik-env.sh --write --all`; then in
   `core/traefik`: `bash ops/scripts/render.sh` — which removes the three
   retired files from `config/dynamic` and says when the container has to be
   recreated — and `bash ops/scripts/validate.sh`. The script does not set
   `TRAEFIK_FORWARDED_PROXY` in `core/traefik/.env`, and `render.sh` refuses an
   installation from before the model until it is set: `cloudflare` where
   Cloudflare proxies the public records, `none` otherwise.
5. **Recreate.** `docker compose up -d --force-recreate` in `core/traefik`,
   then `docker compose up -d` in every stack. Routers answer nothing between
   the Traefik recreate and the last stack recreate.
6. **After.** `./scripts/overview.sh` shows no old name and no empty position;
   `./scripts/overview.sh --host` shows no TLS conflict; `curl -sI` per route
   against the record taken before; one first load per interface with its
   `429` count.

Abort on: a router reported disabled after its recreate; a header missing
that section 1 does not name as removed; a `429` on a reference first load; a
certificate not served; the bouncer refusing the operator's own address.
Rollback is the reverse order from the backup — stacks, Traefik, `config/`,
`.env` — to the tagged release before the model, which stays installable for
a host that is not migrated yet.

Run once on 2026-10-30, from v0.9.4 on a disposable installation behind a
Cloudflare Tunnel with Traefik, CrowdSec and one application: no abort
condition was met; the application's headers changed as sections 1.2 and 1.3
name; routes, access policies, the redirect to HTTPS, the certificate, the
tunnel and a CrowdSec decision behaved as before. It does not cover section 5.

## 5. Not verified on a host

- Every value marked "assumed" or "not measured" above: the office servers'
  own headers, Nextcloud's own headers, the Seafile side routers under
  `headers-standard`, compression of office document bodies.
- The `429` count on a first load per public stack under the bucket of 500 —
  no interface has been measured against 500 in this repository's networks
  except through the former `rl-spa`.
- The six TLS exceptions without a recorded reason, and whether the deployment
  standard serves their clients.
- The window between render and recreate when the bouncer is switched off,
  and the entrypoint list on a running Traefik.
- The thirteen host checks of Phase 3 (`core/traefik/README.md`, "Behind
  Cloudflare", "Not verified on a host") — unchanged by the cut.
