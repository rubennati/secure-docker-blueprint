# Test and infrastructure plan — a temporary public test server for Phase 3 proofs and Phase 4 architecture questions (2026-10-18)

**Status: plan, deferred by the maintainer on 2026-10-18 — kept for the host proofs that remain open. No server exists, nothing was
provisioned, no token was created, no system was touched.** The plan says what
a temporary Hetzner Cloud server with Debian 13, public IPv4 and IPv6, a test
subdomain with wildcard DNS and Cloudflare in front would be used for, how it
would be built reproducibly, what each test measures, what counts as passed,
what it costs, how secrets are handled, how results are kept and how the whole
thing is torn down. It also says which tests do **not** need that server and
can run locally first.

Inputs: the thirteen open host checks of Phase 3
(`docs/reviews/phase-3-*.md`, `core/traefik/README.md` "Not verified on a
host"), the thirteen open proofs of the architecture review
(`traefik-architecture-review-2026-10-17.md`, section 10), the Phase 2 host
verification plan (`docs/host-verification-phase-2.md`, whose shape — rules,
prerequisites, cases with expected and observed, results "not run" until run —
this plan reuses), and the stack inventory of the architecture review.

## 1. Rules

- The server is temporary and isolated: no production data, no production
  domain, no existing system is changed. It is destroyed at the end, and the
  destruction is recorded.
- Two phases on the same server, in this order: **A — the blueprint as it is**
  (the `dev` state that ships Phase 3, by tag), then **B — the new model as a
  lab-only prototype** (hand-written Traefik configuration and labels on the
  test server, nothing changed in the repository). B compares against A's
  record. B is not an implementation of Phase 4; it answers the architecture
  questions so that the implementation can be decided.
- Every test has a written expectation before it runs; the observed value is
  recorded beside it; a test that is not run stays "not run".
- Access to the server is the maintainer's: SSH from the maintainer's
  addresses only, and the maintainer runs or watches every step. Nothing in
  this plan authorises an AI session to open an SSH connection; the plan is
  written so that the maintainer can run it, or hand single read-only
  commands to a session with explicit approval.

## 2. What needs a public server, and what does not

| Question | Local (throwaway containers on the maintainer's machine) | Public server | Why |
|---|---|---|---|
| Entrypoint-level middlewares: `@file` references, the CrowdSec plugin, request/response order with router middlewares | **yes, first** | re-run as a check | pure Traefik semantics; a local CrowdSec container serves the LAPI |
| TLS: entrypoint standard, inheritance on Docker routers, router overrides, the two default mechanisms | **yes, first** | re-run with real certificates | handshake behaviour is independent of the certificate; the public server adds DNS-01 and real client tools |
| Compression on normal responses, SSE, chunked, websocket, downloads, buffering and latency | **yes, first** | re-run on real applications | synthetic backends measure buffering exactly; real applications confirm |
| HSTS floor with per-router extensions, the alternatives | **yes, first** | confirm on real host names | header semantics only |
| Migration guard on the released list shape; migration script on fixtures | **yes, done for the fixture** | the real installed file of a pre-switch host (Phase 3 check 10–12) — needs a **production** host's file, not this server | the test server never ran a release; it can only simulate |
| Client address at every hop through Cloudflare, IPv4 and IPv6 (Phase 3 checks 1, 2, 13) | no | **yes** | needs a proxied public name and Cloudflare's edge |
| Forged `CF-Connecting-IP` / `X-Forwarded-For` from a direct client, with and without the origin firewall (check 3) | partly (direct client semantics) | **yes** | the origin-firewall part needs a real public interface |
| Worker subrequest, second zone pointing at the origin (check 4) | no | **yes** | needs two Cloudflare zones or a Worker |
| Forward-hook nftables table on a running Docker host (check 5) | no | **yes** | needs a host kernel, Docker's chains and a public interface |
| `host-files.sh check` and `overview.sh --host` on a `none` host (check 6) | partly (scratch prefix) | **yes** | the real `/etc` paths |
| Parser version carrying the last-element split (check 7) | no | **yes** | the installed hub collection |
| Direct IPv6 client to the published 443 on an IPv4-only `proxy-public`, docker-proxy relay path (check 8) | no | **yes** | needs a global IPv6 address on the host |
| WARP client's arriving address (check 9) | no | **yes** | needs a WARP client on a workstation and a public origin |
| Host awk running the guard (check 12) | no (BSD awk here) | **yes** — Debian's mawk | one command |
| DNS-01, single host names and wildcard certificates | no | **yes** | needs the zone and Cloudflare's API |
| Rate limits: `429` count on real first loads, sync clients, under 125/200 and 125/500 | partly (synthetic) | **yes** | the real interfaces and the real sync clients |
| Header ownership of the eight candidate applications without the proxy | **yes, mostly** (run the application locally, `curl -sI` the container) | confirm through the proxy | the application's headers do not depend on the host |
| Authentik forward-auth flows, OIDC, admin path | partly | **yes** | real browser flows need public, certificate-bearing names |
| CrowdSec firewall bouncer, nftables set-only mode, AppSec false positives on uploads | no | **yes** | kernel, real traffic |
| Dual-stack `proxy-public` and the overlay, `userland-proxy: false` | partly | **yes** | the daemon's IPv6 NAT and the host's IPv6 |

The local group is therefore the whole of the architecture review's proofs 1–4
and the fixture half of 12; the server group is every Phase 3 host check except
10–12 (which need a production host's file), plus DNS-01, real first loads,
real clients, Authentik flows, CrowdSec at the host and the IPv6 paths.
**Recommendation: run the local group first** (one to two days, no cost, no
risk), carry its results into the architecture review, and only then build the
server — its programme shrinks to what truly needs it, and the prototype for
Phase B is already known to work in principle.

## 3. The test infrastructure

### 3.1 Components

| Component | Purpose | Spec |
|---|---|---|
| **Test server** | the origin: Docker, the blueprint, the host firewall | Hetzner Cloud, Debian 13, **8 vCPU, 16 GB RAM, ≥160 GB disk** (a CPX41-class shared or a CCX23-class dedicated instance; see 6); primary IPv4 and a primary IPv6 `/64`; Hetzner Cloud Firewall: 22 from the maintainer's addresses only, 80 and 443 open, everything else closed; a Hetzner snapshot after the base install |
| **Client vantage point** | a direct client outside the origin: forged headers, IPv6-only access, `hey`/`k6` load, curl from a second public address | a second, small Hetzner instance (2 vCPU, 4 GB) with IPv4 and IPv6, in another location; destroyed with the server |
| **Workstation** | browser flows (Authentik, admin paths, first loads with DevTools), the WARP client, the Tailscale client, `testssl.sh`, result capture | the maintainer's machine |
| **DNS and Cloudflare** | the test zone | a test subdomain delegated to a Cloudflare zone — either a dedicated zone (`<something>-lab.<tld>`, recommended: nothing in it is real) or a subdomain of an existing zone with its own records; `*.lab.<zone>` wildcard A/AAAA plus the single names the tests need; proxied (orange) for the public names, DNS-only for the VPN-only names; one Cloudflare rate-limiting rule by IP on the public names; Pseudo IPv4 off |
| **VPN** | the VPN path (`access-vpn`, `acc-tailscale`) | Tailscale with an ephemeral auth key for the server and the workstation, or the repository's `core/headscale` on the test server — Tailscale is simpler for a one-week lab |
| **Second Cloudflare zone or Worker** | Phase 3 check 4 | a second zone on the same account pointing a name at the origin address; a Worker with a subrequest to the origin |
| **CrowdSec** | both remediation points | `core/crowdsec` as shipped; the host firewall bouncer per `core/crowdsec/docs/firewall-bouncer.md` |
| **Representative applications** | section 5 | from the repository, unchanged in Phase A |

### 3.2 Reproducible build

Everything the build needs lives in one directory, versioned once the plan is
approved (proposed: `docs/lab/phase-4/` or `scripts/lab/` — decided then, not
here):

1. `cloud-init.yaml` — Debian 13: Docker from Docker's repository (pinned
   version), `nftables`, `curl`, `git`, `jq`, the maintainer's SSH public key,
   SSH password login off, unattended upgrades off for the week (reproducible
   state), the Hetzner firewall as the only inbound rule set at first.
2. `provision.sh` — `hcloud` CLI calls: create the two servers from the
   cloud-init, attach the firewall, print the addresses; **run by the
   maintainer**, with the Hetzner token in the shell environment for that run
   only (section 7).
3. `dns.sh` — the Cloudflare records for the zone from one list (wildcard,
   single names, proxied flags), applied with the zone-scoped token; idempotent
   and reversible (`dns.sh teardown`).
4. `phase-a.sh` — on the server: clone the repository at the tag, deploy
   `core/traefik` (`TRAEFIK_FORWARDED_PROXY=none` first, `cloudflare` second),
   `core/crowdsec`, `core/authentik`, the applications of section 5 with their
   `.env` from a lab `.env` set (test passwords, lab names, `example.com`
   replaced by the lab zone — generated, never committed).
5. `phase-b/` — the lab-only prototype of the new model: a Traefik static and
   dynamic configuration written by hand from the architecture review
   (entrypoint middlewares, TLS at the entrypoint, the four positions, the
   header blocks), and the label sets for the same applications; applied on
   the server in place of Phase A's `core/traefik/config/` and labels, **never
   through the repository's templates**.
6. `verify-lab.sh` — the readable half, modelled on `scripts/verify-phase-2.sh`:
   one line per check, PASS / FAIL / SKIP with the reason, reads state only.
7. `capture.sh` — collects the record: `curl -sI` per route, the access log
   lines of each test, `openssl s_client` outputs, the `429` counts, the
   nftables rulesets, the rendered configuration — into a timestamped results
   directory, synced to the workstation after every session.

A fresh server built from 1–4 reaches the same Phase A state; the Hetzner
snapshot after step 1 shortens a rebuild.

### 3.3 Order of execution and decision points

| Step | Content | Decision after |
|---|---|---|
| 0 | the local group (section 2) on the maintainer's machine | results into the architecture review; does Phase B's prototype work in principle? |
| 1 | provision, DNS, VPN; base checks (SSH only from the maintainer, firewall, IPv6 reachable) | go for Phase A |
| 2 | Phase A, `none` mode: core, CrowdSec, Authentik, applications; the whole test programme that does not need Cloudflare | record A1 |
| 3 | Phase A, `cloudflare` mode: switch, render, recreate; the Cloudflare programme; origin firewall; Worker and second zone | record A2 — the Phase 3 host checks closed or failed |
| 4 | Phase B prototype in `none` mode, same applications: order, TLS, compression, HSTS, headers, limits | record B1, diff against A1 |
| 5 | Phase B prototype in `cloudflare` mode | record B2, diff against A2 |
| 6 | results written up (section 8), teardown (section 9) | the architecture review updated; the implementation decision |

Each step ends with the capture of 3.2 (7) and a short written state before the
next begins; a step that fails its abort criteria (section 9.3) stops the
programme until the cause is understood.

## 4. The test programme

Each case names its phase (A, B or both), its mode (`none`, `cloudflare` or
both), where it runs (L local first, S server), the method, the expectation
and the success criterion. "Record" means the capture of 3.2 (7).

### T1 — the Phase 3 host checks

| Case | Check | Where | Method | Expected | Pass |
|---|---|---|---|---|---|
| T1.1 | address at every hop (checks 1, 13) | S, A+B, `cloudflare` | `whoami` behind `acc-public`/`access-public` from the vantage point and the workstation over IPv4 and IPv6; the access log's `ClientHost`; a manual CrowdSec decision on the client address | `X-Forwarded-For` = `client, edge`, `X-Real-Ip` = edge, `ClientHost` whole header with the client last; the decision answers `403` | all four observed as expected over both families |
| T1.2 | closed route refuses a proxied request (check 2) | S, A+B, `cloudflare` | a VPN-only name proxied by Cloudflare on purpose, over IPv4 and IPv6, with `proxy-public` IPv4-only and then dual-stack | refused over IPv4; **over IPv6 on IPv4-only, admitted as the gateway** (the documented defect), refused on dual-stack | the documented behaviour reproduced; dual-stack refuses |
| T1.3 | forged headers from a direct client (check 3) | L then S, A+B, both modes | from the vantage point: `curl -H 'X-Forwarded-For: 203.0.113.9' -H 'CF-Connecting-IP: 203.0.113.9'` against the origin address, with the origin firewall absent and present | `none`: both deleted/ignored, the bouncer compares the connection; `cloudflare` without firewall: the request reaches Traefik, XFF deleted, bouncer compares the connection; with firewall: dropped | no forged value reaches a middleware or the log in any case |
| T1.4 | Worker and second zone (check 4) | S, A, `cloudflare` | a Worker fetching the origin with a chosen `CF-Connecting-IP`; a second zone's name pointed at the origin | the Worker's chosen header arrives; the second zone's request passes the firewall and carries that zone's `X-Forwarded-For`; `Host` decides the router | the boundary documented in the README observed, nothing worse |
| T1.5 | forward-hook table (check 5) | S, A+B, `cloudflare` | install the README's table; from the vantage point `curl` the origin address directly; from the VPN; CrowdSec tables before and after `nft -f` | direct refused, VPN served, CrowdSec tables intact, Traefik reachable through Cloudflare | all four |
| T1.6 | host-files check on a `none` host (check 6) | S, A | `scripts/host-files.sh check core/traefik`, `overview.sh --host` | exit 0, the nft entry `not produced` | as expected |
| T1.7 | parser split (check 7) | S, A | `cscli hub list`, the parser file's `source_ip` expression | `[-1]` present | present |
| T1.8 | direct IPv6 client on IPv4-only `proxy-public` (check 8) | S, A+B | from the vantage point over IPv6 to the origin's AAAA, with the forward table installed; then with the dual-stack overlay and `userland-proxy: false` | IPv4-only: served, arrives as the gateway, `acc-local` admits (the defect); dual-stack: filtered by the table, correct address | both states observed as documented |
| T1.9 | WARP client's address (check 9) | S, A, `cloudflare` | the workstation with WARP on, `curl` the proxied name; the access log | the address and whether it lies in the published ranges — unknown today | recorded either way; README sentence corrected if needed |
| T1.10 | migration guard on a real pre-switch file (checks 10–12) | **production host only** | not on this server — the server never ran v0.9.x; a v0.9.4 render on this server is a fixture, which the third review already did | — | stays open after this programme unless a production host's file is read |

### T2 — TLS and certificates

| Case | Where | Method | Expected | Pass |
|---|---|---|---|---|
| T2.1 DNS-01 single names | S, A | `cloudflare-dns` resolver, one name per router; `openssl s_client -servername`; certificate chain | a valid certificate per name, from the staging CA first, then production | staging then production issued, chain valid |
| T2.2 DNS-01 wildcard | S, A | `ACME_WILDCARD_DOMAIN=lab.<zone>`; the dashboard covered; a name outside the wildcard | wildcard served on every `*.lab` name, the outside name refused or self-signed as documented | as documented in the certificate-strategy section |
| T2.3 the three profiles today | L then S, A | `testssl.sh` / `openssl s_client` per profile on routers set to `tls-basic`, `tls-aplus`, `tls-modern` | minimum versions and cipher sets as in `tls-profiles.yml` | match |
| T2.4 entrypoint standard and inheritance | L first, S, B | `entryPoints.websecure.http.tls.options: tls-standard@file`; a Docker router without `tls.options`; one with `tls-strict@file` | the first negotiates `tls-standard`, the second TLS 1.3 only | match |
| T2.5 the two default mechanisms | L first, S, B | the file provider's `tls.options.default` set to a different minimum than the entrypoint option; a router without options | which one wins is recorded; then the loser removed and the test repeated | one mechanism remains, documented |
| T2.6 the six `tls-basic` stacks | S, A | Nextcloud's mobile and desktop clients, WordPress, Vikunja, OpenProject, Shlink, whoami against `tls-aplus` | all connect — or the client that cannot is named | each stack's reason recorded or the value changed to standard in B |

### T3 — headers

| Case | Where | Method | Expected | Pass |
|---|---|---|---|---|
| T3.1 the eight candidates without the proxy | L first, S | `curl -sI` the application container directly: Keycloak, Nextcloud, Vaultwarden, Matomo, Collabora, OnlyOffice, EuroOffice, listmonk — on the pages that matter (console, login, preview, 3p-cookie page) | the set each sends, per page | the record exists for all eight; the block granularity of the review decided from it |
| T3.2 every route through the proxy, Phase A | S, A | `curl -sI` per route per mode | the chain's set; the `strip-xfo` trio's effective frame header | the record exists for every route (the "before" of the migration) |
| T3.3 every route through the proxy, Phase B | S, B | the same | `headers-standard` on bare applications; `application-owned` plus blocks on the eight; HSTS on every route from the entrypoint | the diff against T3.2 is exactly the expected set of the architecture review's section 6 |
| T3.4 response order | L first, S, B | two `headers` middlewares setting the same custom header at the entrypoint and on the router; `frame-self` before `headers-standard`; `hsts-include-subdomains` on a router | the entrypoint's value wins; `frame-self` wins over `DENY`; the router's HSTS extension **loses** to the entrypoint's floor (the predicted defect) | observed; feeds T4 |
| T3.5 a dashboard embedding a target | S, A+B | Dashy framing a Nextcloud or whoami page; the target with a `frame-ancestors` naming the dashboard's origin | the widget renders only with the target's block | observed |

### T4 — HSTS floor with per-router extensions (the alternatives)

Precision 4: no premature choice between a deployment switch and a router slot.
The lab compares every technically possible shape:

| Alternative | Shape | What to observe | Consequence if it holds |
|---|---|---|---|
| H1 | `hsts-base` at the entrypoint; `includeSubDomains`/`preload` by a deployment switch on the same block | one HSTS value for every host; the apex case means the whole deployment switches | simplest; wrong for a deployment that mixes an apex site with subdomains |
| H2 | HSTS inside router position 3: every profile carries it, `headers-none` means "HSTS only"; `hsts-include-subdomains` as a router block before the profile | the router block wins over the profile (response order); a router with `headers-none` still sends HSTS | per-router extension possible; `headers-none` is no longer "nothing", which the standard must say |
| H3 | `hsts-base` at the entrypoint **and** the extension block at the router, with the entrypoint block told not to overwrite — Traefik's `headers` has no "set if absent"; test whether `customResponseHeaders` with the full STS value behaves differently from `stsSeconds` | whether any configuration lets the router's longer value survive | expected not to hold; recorded as the reason H3 is excluded |
| H4 | a second entrypoint (`websecure-apex`) with its own HSTS list, the apex router attached to it | the apex router alone carries `includeSubDomains`; everything else unchanged | works by construction; costs a second port or SNI routing — heavy for one router |
| H5 | HSTS set by the application for the apex case, the entrypoint block absent on … | not possible per router (H3) | excluded with H3 |

Expected: H1 and H2 work, H3 does not, H4 works at a cost. The lab records
each, and the architecture review then decides between H1 and H2 with the
measured facts — not here.

### T5 — middleware order, entrypoint middlewares, CrowdSec

| Case | Where | Method | Expected | Pass |
|---|---|---|---|---|
| T5.1 entrypoint list accepts `@file` and the plugin | L first, S, B | `entryPoints.websecure.http.middlewares: [threat-crowdsec@file, hsts-base@file, compress@file]` with CrowdSec's LAPI running | Traefik starts, no error in the log, the dashboard shows the middlewares on every router | observed |
| T5.2 request order | L first, S, B | `addPrefix` at the entrypoint and on the router, `whoami` shows the path | `/router/entrypoint/…` — the entrypoint ran first | observed |
| T5.3 a banned address on every router | S, A+B | `cscli decisions add` for the vantage point; requests to a router with middlewares, one without, the dashboard, the ACME bootstrap router | `403` everywhere in B; in A only where the router carries the bouncer | observed |
| T5.4 AppSec | S, A+B | AppSec on; uploads to Nextcloud, Seafile, Paperless; a webhook to n8n; a federation request to Ghost | which are blocked (false positives) and which AppSec rule fires | the exemption list for the CrowdSec side exists |
| T5.5 the host firewall bouncer | S, A | set-only mode as documented; a decision; the vantage point's packets | dropped before Docker; the Traefik bouncer never sees them | observed |

### T6 — rate limits

| Case | Where | Method | Expected | Pass |
|---|---|---|---|---|
| T6.1 first loads, Phase A | S, A | headless Chrome (`chrome --headless --dump-dom` with `--log-net-log`, or the DevTools HAR) on every application of section 5, five loads, cache cleared; count `429` | the measured numbers reproduced under `rl-soft`, `rl-spa`, `rl-spa-xl` | numbers recorded |
| T6.2 first loads, Phase B | S, B | the same under `limit-standard` 125/500 and `limit-extra-large` | zero `429` for every interface under 500; Twenty/Windmill under 1000 | zero |
| T6.3 sync clients | S, A+B | Nextcloud desktop client and Seafile client syncing 5 000 small files; `429` count | zero under `rl-sync`/`limit-sync`; `429` under `limit-standard` (the documented reason for the variant) | observed |
| T6.4 a strict router | S, A+B | Portainer's first load under `rl-hard`/`limit-strict` | fits (issue #37) | fits |
| T6.5 the sustained rate | S, B | `hey -q 200 -z 30s` from the vantage point against a public route | `429` after the bucket, at 125/s thereafter; CrowdSec's `http-crawl` scenario bans the address within its window | both observed — the division of labour between counter and CrowdSec recorded |

### T7 — API, websocket, SSE, downloads, sync

| Case | Where | Method | Expected | Pass |
|---|---|---|---|---|
| T7.1 compression on normal responses | L first, S, B | JSON > 1 KiB with `Accept-Encoding: gzip` | `Content-Encoding: gzip` | observed |
| T7.2 SSE and chunked streaming | L first, S, B | a synthetic backend emitting one event per second; then Open WebUI with Ollama (a small model) streaming a reply; timestamps per chunk at the client, direct versus through Traefik | no added latency beyond the network; no batching; `text/event-stream` either excluded or passed uncompressed and unbuffered | per-chunk delay through the proxy ≤ 50 ms above direct |
| T7.3 websocket | L first, S, B | a synthetic echo; then Seadoc (`/socket.io/`) editing a document and ERPNext's socket.io | upgrade succeeds, echo round-trip unchanged, compression untouched | observed |
| T7.4 downloads | S, A+B | a 1 GiB file from Nextcloud and Seafile; throughput and `Content-Encoding` | binary content not compressed (or excluded), throughput within 10 % of direct | observed |
| T7.5 pre-compressed assets | L first, S, B | a backend sending `Content-Encoding: gzip` | untouched | observed |
| T7.6 API routers | S, A+B | CISO Assistant `/api`, Shlink `/rest`, Dependency-Track's API host with their clients | the UI's limit does not break the client; the own-policy routers refuse from the wrong address | observed |

### T8 — Cloudflare versus direct, IPv4/IPv6, Docker network, nftables

Covered by T1.1–T1.5, T1.8, T2 and T5.5; additionally:

| Case | Where | Method | Expected | Pass |
|---|---|---|---|---|
| T8.1 switching modes on a running host | S, A | `none` → `cloudflare` → `none`: render, recreate, `validate.sh`, the guard | the documented migration path works both ways; the guard refuses an undeclared switch over the rendered list | observed |
| T8.2 the ranges file changed | S, A | add a range, `validate.sh` | "list differs — run render.sh" | observed |
| T8.3 dual-stack overlay | S, A+B | `network-dual-stack.yml`, `userland-proxy: false`, `ip6tables: true`; the Tailscale IPv6 client path; T1.8 again | the real client address over IPv6 everywhere | observed |

### T9 — Authentik

| Case | Where | Method | Expected | Pass |
|---|---|---|---|---|
| T9.1 forward-auth on a whole router | S, A+B | Dashy behind `auth-authentik`; browser login; API call without a session | redirect to the portal, then served; the API call `401`/redirect | observed |
| T9.2 admin path | S, A+B | Paperless-ngx `-admin` router at priority 100 | `/admin` gated, the rest open | observed |
| T9.3 OIDC inside an application | S, A | Vikunja with Authentik as provider | the SSO redirect middleware and the login work | observed |
| T9.4 the gate's position | S, B | `auth-authentik` in position 4 after `limit-strict` | a flood against the admin path is counted before the portal is asked (`429` before any redirect) | observed |

## 5. Representative applications

Chosen so that every requirement class of the inventory has one measured
representative, within 16 GB:

| Stack | Represents | Phase A value today | Phase B expectation |
|---|---|---|---|
| `apps/whoami` | public, static, CSP, the hop test | `acc-public`, `sec-5`, `tls-basic` | `limit-strict`, `headers-standard` + `csp-self-only` |
| `apps/nextcloud` | sync clients, own headers, mobile, downloads, `tls-basic` | `sec-3e-sync`, `tls-basic` | `limit-sync`, `application-owned` + blocks |
| `apps/seafile` | overlays, four secondary routers, websocket, sync, downloads | `sec-2-sync` | per router, 3.9 of the review |
| `core/keycloak` | the measured frame case, `strip-xfo` | `sec-2-spa` + `strip-xfo` | `application-owned` |
| `business/listmonk` | frames its own pages | `sec-2e` | `headers-standard` + `frame-self` |
| `apps/windmill` | whole first load, closed access | `acc-deny` → `acc-tailscale`, `sec-2-spa-xl` | `limit-extra-large` |
| `apps/paperless-ngx` | admin path behind the gate, mobile, proto header | `sec-2` + `-headers` | the gate in position 4 |
| `apps/open-webui` + `apps/ollama` (small model) | SSE streaming, measured first load | `sec-2-spa` | `limit-standard`, compression against streaming |
| `apps/dashy` | a dashboard embedding others | `sec-3` | `frame-ancestors` on the target |
| `apps/shlink` | API router with its own policy, `tls-basic` with a reason | three routers | own policy kept |
| `core/portainer` | strict limit, `tls-modern` | `sec-4`, `tls-modern` | `limit-strict`, `tls-strict` exception |
| `core/authentik` | the gate; its own `-static` router | `sec-1` literal | `limit-none` on static |
| `core/crowdsec` | both remediation points, AppSec | as shipped | at the entrypoint |

Not included, by weight or lack of a distinct requirement: ERPNext (websocket
covered by Seadoc), Twenty (covered by Windmill's class), the office servers
(headers covered by T3.1 locally), Dependency-Track (API host covered by
Shlink's shape), Immich (mobile covered by Nextcloud). Any of them can be added
for one test and removed.

## 6. Resources, time, cost

| Item | Estimate |
|---|---|
| Test server | 8 vCPU, 16 GB, 160–240 GB; Hetzner CPX41-class (shared AMD) or CCX23-class (dedicated) — the dedicated class gives steadier first-load timings; price per the Hetzner list at order time, in the order of €1–2 per day |
| Vantage point | 2 vCPU, 4 GB; well under €1 per day |
| Traffic | the 1 GiB download tests and syncs stay far inside the included volume |
| Cloudflare | the free plan suffices (one rate-limiting rule; Workers free tier for T1.4); a second zone needs a second domain or a free subdomain delegation |
| Tailscale | free tier |
| Time | step 0 local: 1–2 days; step 1: half a day; step 2 (Phase A `none`): 1 day; step 3 (`cloudflare`): 1 day; steps 4–5 (Phase B): 1–2 days; step 6: half a day — **5 to 7 working days**, the server alive for about two weeks with margin |
| Total cost | in the order of €20–40 for two weeks of both instances; a snapshot while paused costs cents per day |

## 7. Tokens and secrets

| Secret | Scope | Handling |
|---|---|---|
| Hetzner Cloud API token | one project created for the lab, read/write | created by the maintainer in the Hetzner console, stored in 1Password, exported into the shell only for `provision.sh` and the teardown; **deleted with the project** |
| Cloudflare API token | zone-scoped: `Zone:DNS:Edit` on the lab zone only (DNS-01 and `dns.sh`); a second token `Zone:Zone Settings:Edit` only if rules are set by script, otherwise by hand | created in the Cloudflare dashboard, stored in 1Password, written into the server's `core/traefik/.env` (gitignored) by the maintainer; revoked at teardown |
| Tailscale auth key | ephemeral, pre-authorised, tagged `lab` | expires by itself; devices removed at teardown |
| CrowdSec bouncer keys, Authentik secrets, application passwords | lab-only values generated on the server | never leave the server except inside the results archive, which is encrypted (section 8) |
| SSH key | the maintainer's existing key, or a lab key created for the week | the lab key deleted at teardown |

No token is pasted into a chat, a file in the repository, a commit, or an AI
session. A session that is given a single read-only command to run gets its
output, never the environment.

## 8. Results: capture and preservation

- Every session ends with `capture.sh`: the results directory
  (`results/<step>/<timestamp>/`) holds the `curl -sI` records, access-log
  excerpts, `openssl` outputs, HAR files or `429` counts, nftables rulesets,
  the rendered configuration, the `verify-lab.sh` output, and a `notes.md`
  written by the maintainer. It is synced to the workstation
  (`rsync` over the maintainer's SSH) and kept outside the repository.
- The write-up goes into the repository as `docs/reviews/host-verification-
  phase-3-4-<date>.md` in the Phase 2 plan's shape: case, expected, observed,
  pass/fail/not run, with the raw record's path; and the architecture review
  and the Phase 3 README section are updated from it — after the maintainer's
  review of the results, not before.
- The results archive is encrypted (`age` or 1Password document) because it
  contains lab credentials and real addresses; it is kept for as long as the
  write-up may need re-checking.

## 9. Teardown, abort criteria, what remains

### 9.1 Teardown checklist

1. `capture.sh` one last time; the archive synced and encrypted.
2. `dns.sh teardown` — every lab record removed; the proxied names gone from
   Cloudflare; rate-limiting rule, Worker and the second zone's record removed.
3. Tailscale devices removed; the auth key expired.
4. Both Hetzner servers deleted; the snapshot deleted; the Hetzner project
   deleted (which deletes its token).
5. Cloudflare tokens revoked; the lab SSH key removed from the maintainer's
   agent and 1Password.
6. A teardown record (date, what was deleted, by whom) appended to the
   write-up.

### 9.2 Reproducibility

The directory of 3.2 rebuilds the environment from nothing; the results
archive's `notes.md` names the exact image versions, the repository tag and
the Phase B prototype's files. A rebuild for one re-check should take under an
hour from the snapshot, two hours from scratch.

### 9.3 Abort criteria

A step stops when: a Phase A test contradicts the repository's documented
behaviour in a way that is not one of the known open defects (then the defect
is written up first); the server is reachable from anywhere but the maintainer
over 22; a token is found anywhere it should not be; the Phase B prototype
needs a change to the repository to work (then the finding goes to the
architecture review and the prototype stops); or the cost or time estimate is
exceeded by half.

### 9.4 What this programme leaves open

Phase 3 checks 10–12 need a **production** host's installed file; a
production host is also the only place where the migration script meets real
`.env` values. Both stay open until the maintainer provides that host or a
copy of its files.

## 10. What this plan does not do

It creates no server, no DNS record, no token; it changes no system and no file
in the repository; it is not an implementation plan for Phase 4; and it does
not decide between the HSTS alternatives, the header-block granularity or the
other open architecture questions — it produces the facts they need.
