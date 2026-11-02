# Host verification — ingress programme, step 8

The test plan for what steps 1–7 of the ingress programme changed and no test in
CI can establish: the endpoint Docker gives an IPv6 port, what the internet
reaches, how each access policy and auth gate behaves against real clients over
both address families, the host ruleset loaded on a host, and the migrations of
an existing installation. Every result below is **not run** until a row says
otherwise, with the date and the evidence beside it. The plan is written before
the host exists; it changes no host.

What it covers, by decision: DEC-063 (dual-stack default), DEC-075 (published
ports, edge networks, bindings), DEC-076 (`access-trusted`), DEC-077 (auth
posture), DEC-078 (exposure profile, host ruleset, management access). The
acceptance list it turns into rows is §5 of
[`docs/audits/ingress-architecture-2026-10-31.md`](audits/ingress-architecture-2026-10-31.md),
extended by the items step 7 left open (`.ai/tasks.md` §12).

A row that existing evidence already settles is marked **covered** with that
evidence and is not run again; only the rows left open are host work.

## Rules

- **A disposable host, never a production one.** Nothing here runs on a host
  that serves anyone. The host carries throwaway data and is reinstalled or
  discarded afterwards.
- **The administrative path is secured before anything can close it.** Before
  the host ruleset or any CrowdSec enforcement is loaded, the hoster's console
  (VNC or serial) has been opened once and found working, a second SSH session
  over the VPN is kept open for the whole session, and every ruleset load carries
  the five-minute way back of
  [`core/traefik/docs/host-firewall.md`](../core/traefik/docs/host-firewall.md).
- **Evidence on record is not repeated.** A lab measurement, a CI test or an
  earlier host run that still holds for the configuration under test settles
  its row (see "Evidence already on record"). It is run again only when the
  configuration it measured has changed in the point it measured.
- **Manual, every open row.** There is no verification script for this plan yet; each
  row names its commands. A row that only reads state says *read*; a row that
  changes the host says *manual*.
- **A family is verified only by its own probe.** An IPv4 result says nothing
  about IPv6. Where a row has a column per family, both are filled or the row is
  open.
- **A phase is verified only by its rows.** Record a failure as a failure, with
  the output. `ipv6-only` stays "not verified" until block O has its own run.
- **Evidence without secrets.** `docker compose config` prints `.env` values;
  redact before anything leaves the host. Addresses in evidence are written as
  roles (`OUT4`, `TS6`, …), not as the real values.

## Prerequisites

| | |
|---|---|
| Host H1 (dual-stack) | Debian 12 or 13, Docker Engine 27+ with Compose v2, nftables firewall backend or iptables-nft; `envsubst`, `curl`, `jq`, `nft`, `ss`; a public IPv4 **and a global IPv6** address; the hoster's console tested |
| Host H2 (IPv6-only, block O only) | the same, without public IPv4 ingress; NAT64/DNS64 or an IPv4 egress path decided beforehand (audit §3.4) |
| Daemon | `/etc/docker/daemon.json` as in [`ipv6-dual-stack.md`](../core/traefik/docs/ipv6-dual-stack.md), "Docker daemon prerequisites": `ipv6`, `ip6tables`, `userland-proxy: false` |
| Checkout | `git clone`, `git checkout dev` at the commit under test; `./scripts/overview.sh` states it. A second checkout of the tag `v0.9.5` for block B |
| DNS | one test zone with a wildcard, A and AAAA records on H1; ACME by DNS-01, or HTTP-01 with 80 reachable on both families |
| Clients | **OUT** — a machine off the VPN with IPv4 and IPv6 (`OUT4`, `OUT6`); **TS** — a tailnet device with its IPv4 and IPv6 tailnet address (`TS4`, `TS6`); **LAN** — a client on a private network H1 is attached to, its range declared in `TRUSTED_RANGES` (`LAN4`, and `LAN6` where that network carries IPv6) |
| Stacks | `core/traefik`, `core/crowdsec`, `core/authentik` (embedded outpost), `apps/whoami`, `apps/heimdall`, one `app-login` stack (e.g. `apps/vaultwarden`), three more routed stacks for block N; each `.env` from its example with test values, no real secret |
| Values in the shell | `export H1_V4=… H1_V6=… ZONE=…` — the test hosts are reached as `<name>.$ZONE` |

## Evidence already on record

| Evidence | What it settles | Rows | What it leaves open |
|---|---|---|---|
| Lab run of 2026-10-31, audit §4 (throwaway daemon, Engine 29, IPv4 only) | T1–T2: a shared network lets web containers reach each other, an edge network does not; T3d: a host process on the gateway is not trusted; T4a–T4b: forward-auth stops the request on a non-2xx answer and deletes forged identity headers; T5: a forged `X-Forwarded-For` is ignored; T6: Traefik's recreate costs about two seconds; T7b: `gw_priority` moves the IPv4 DNAT to `proxy-public` | N1, N3, G2, A7 and A9 for IPv4, E3 for IPv4 | everything over IPv6; a real outpost; a real LAN or tailnet client; the nftables backend |
| `scripts/ci/test_traefik_exposure.py` | the derivation of the profile; `nft -c` accepts every rendered ruleset; the exposure script against a stub fails on a port that must never answer; a marker for the profile is accepted, one for another profile refused | X2, X3; the syntax half of P4 | the ruleset loaded on a host; the measurement itself (X1) |
| `scripts/ci/test_traefik_model.py` | empty `TRUSTED_RANGES` admits nobody; unset is refused by render and validate | A6 | — |
| `scripts/ci/test_traefik_published_ports.py` | unset `TRAEFIK_BIND_V4` is refused; an empty `TRAEFIK_BIND_V6` publishes IPv4 only; both families render | B6 | the running state of the ports (E2) |
| `scripts/ci/test_traefik_render_identity.py` | a `v0.9.5` `.env` renders the same files apart from the decided differences, for IPv4-only and dual-stack | the configuration half of B | the published state on a host and the rollback (B1–B5) |
| `scripts/ci/check-structure.py` `port-no-host-address` | each of the nine stacks names its binding through a required `${*_BIND:?…}`, which Compose refuses unset | S1 | a stack reached over its binding (S2) |
| Host run of 2026-06-19 ([`docs/bugfixes/traefik-ipv6-dualstack-2026-06-19.md`](bugfixes/traefik-ipv6-dualstack-2026-06-19.md)) | a tailnet client over IPv6 is seen with its own address once `proxy-public` is dual-stack and `userland-proxy` is off | none for the current configuration | the publishing (step 7) and the endpoint selection (step 2) have changed since: E3, E5 and the TS6 columns of A stay open |
| Host run of 2026-10-30, DEC-065.6 (v0.9.4 behind a Cloudflare Tunnel, `middleware-model-migration.md` §4) | the middleware-model migration and its abort conditions | none | it predates the bindings of step 7 and the edge networks: B and N stay open |

One whoami router per policy carries the access tests. In `apps/whoami` a
router per policy is not shipped; create them as test-only labels in a
`docker-compose.override.yml` that is deleted afterwards, named
`w-public`, `w-trusted`, `w-vpn`, `w-trusted-vpn`, `w-blocked`.

## P — preflight

| ID | Test | How | Expected | Pass when |
|---|---|---|---|---|
| P1 | the checkout under test | read | `./scripts/overview.sh` names the commit; `git status` clean apart from `.env` files | commit recorded |
| P2 | validate → render → validate | read | in `core/traefik`: `bash ops/scripts/validate.sh` exits 0 — on a fresh checkout it reports the published-address checks `NOT VERIFIED: not rendered yet`; `bash ops/scripts/render.sh` exits 0; `bash ops/scripts/validate.sh --strict` names only the exposure marker, which X1 stores, and exits 1 until then | only the marker missing |
| P3 | the derived profile | read | `validate.sh` prints `Exposure profile: direct` for `TRAEFIK_BIND_V4=0.0.0.0`, `TRAEFIK_BIND_V6=[::]`, `TRAEFIK_FORWARDED_PROXY=none`; the layers list names what is absent | profile and layers as stated |
| P4 | the rendered ruleset parses on the host's own `nft` (syntax covered in CI) | read | `sudo nft -c -f core/traefik/config/host/ingress.nft` exits 0; nothing applied (`sudo nft list tables` unchanged) | 0, no new table |

## E — published ports and the IPv6 endpoint (DEC-063, DEC-075)

| ID | Test | How | Expected | Pass when |
|---|---|---|---|---|
| E1 | the public network is dual-stack | read | `docker network inspect proxy-public --format '{{.EnableIPv6}} {{json .IPAM.Config}}'` → `true`, both subnets | both families present |
| E2 | the published ports, per family | read | `docker port traefik` and `sudo ss -ltnp` list 80 and 443 on `0.0.0.0` and `[::]` and nothing else of Traefik; no docker-proxy process for them (`pgrep -a docker-proxy` empty) | as stated |
| E3 | the endpoint that carries the IPv6 ports (audit T7 over IPv6; IPv4 covered by lab T7b) | read | `docker inspect traefik --format '{{json .NetworkSettings.Networks}}'` shows the highest `GwPriority` on `proxy-public`; `sudo nft list ruleset \| grep -A2 'dport 443'` (or `ip6tables -t nat -S DOCKER`) shows the IPv6 DNAT to Traefik's address on `proxy-public`, not on `crowdsec-security` | IPv6 DNAT target on `proxy-public` |
| E4 | the client address survives, IPv4 | manual | from OUT: `curl -4 https://whoami.$ZONE/` against `w-public` → `X-Real-Ip` is `OUT4`; Traefik's access log carries `OUT4` as `ClientHost` | `OUT4`, never a gateway |
| E5 | the client address survives, IPv6 | manual | the same with `curl -6` → `X-Real-Ip` is `OUT6`, not the bridge gateway of any network | `OUT6`, never a gateway |
| E6 | the family check agrees with the running state | read | `validate.sh --strict` reports no `PENDING` and no `NOT VERIFIED` from `check-published-family.py` | clean |

## X — the exposure test from outside (DEC-078.3)

| ID | Test | How | Expected | Pass when |
|---|---|---|---|---|
| X1 | profile `direct` holds | manual, from OUT | `bash scripts/exposure-test.sh $H1_V4 direct` and the same with `$H1_V6` (or a name with both records): 80 and 443 answer on both families; 8080, 2375, 2376, 3306, 5432, 6379, 8025, 11434 closed; SSH reported; the marker stored in `core/traefik/config/exposure-verified`, after which `validate.sh --strict` exits 0 | exit 0, marker stored, `--strict` green |
| X2 | the test fails when it should | **covered** | `test_traefik_exposure.py`: a port that must never answer fails every profile, against a stub | not run again |
| X3 | the marker is accepted, another profile's refused | **covered** | `test_traefik_exposure.py`: the marker tests | not run again |
| X4 | profile `proxied` — where the installation uses it | manual | `TRAEFIK_FORWARDED_PROXY=cloudflare`, `cloudflare-ranges.nft` and `ingress.nft` loaded (block F); from OUT `exposure-test.sh <origin address> proxied` → 80/443 do not answer | exit 0 |

## A — access policies per family (DEC-076)

Each cell is the status code a `curl -sk -o /dev/null -w '%{http_code}'` from
that client receives on the router named in the row. Nothing ships with a
declared range: set `TRUSTED_RANGES` to the LAN range for this block and render.

| ID | Router | OUT4 | OUT6 | TS4 | TS6 | LAN4 | LAN6 |
|---|---|---|---|---|---|---|---|
| A1 | `w-public` (`access-public`) | 200 | 200 | 200 | 200 | 200 | 200 |
| A2 | `w-trusted` (`access-trusted`) | 403 | 403 | 403 | 403 | 200 | 200 |
| A3 | `w-vpn` (`access-vpn`) | 403 | 403 | 200 | 200 | 403 | 403 |
| A4 | `w-trusted-vpn` (`access-trusted-vpn`) | 403 | 403 | 200 | 200 | 200 | 200 |
| A5 | `w-blocked` (`access-blocked`) | 403 | 403 | 403 | 403 | 403 | 403 |

| ID | Test | How | Expected | Pass when |
|---|---|---|---|---|
| A6 | nothing trusted without a declaration | **covered** | `test_traefik_model.py`: empty admits nobody, unset refused | not run again |
| A7 | a forged header changes nothing, over IPv6 (IPv4 covered by lab T5) | manual | from OUT6: `curl -6 -H 'X-Forwarded-For: <a TS6 address>'` and `-H 'X-Real-Ip: …'` on `w-vpn` → 403; whoami behind `w-public` shows `OUT6`, not the forged value | 403, real address |
| A8 | the tailnet's IPv6 path into `access-trusted` | manual | from TS6 on `w-trusted` → 403: no implicit ULA, and the tailnet range is not trusted by being private | 403 |
| A9 | a host-local process over IPv6 (IPv4 covered by lab T3d) | manual | on H1: `curl --resolve 'w-vpn.$ZONE:443:[::1]'` → 403 | 403 |

## G — the auth posture on a host (DEC-077)

| ID | Posture | How | Expected | Pass when |
|---|---|---|---|---|
| G1 | `forward-auth`, real outpost | manual | `AUTHENTIK_FORWARD_AUTH_ENABLED=true`, a provider for whoami, its router on `auth-authentik@file`; `curl -sI` → 302 to the Authentik host; after browser login whoami shows `X-Authentik-Username` | 302, then the header |
| G2 | forward-auth stops a request and strips a forged identity | **covered** | lab T4a–T4b: Traefik's forwardAuth behaviour, independent of which outpost answers | not run again |
| G3 | forward-auth fails closed | manual | `docker stop authentik-server` → 5xx or 401/403, never 200; `docker start` → 302 | never 200 |
| G4 | `basic` on an application without a login | manual | `apps/heimdall` with `APP_BASIC_AUTH_USERS` set: no credentials → 401; wrong → 401; right → 200; the router carries `<project>-auth@docker` | 401, 401, 200 |
| G5 | `app-login` — where a stack uses it | manual | the chosen stack on `auth-none@file`: unauthenticated request reaches the application's own login page, no proxy gate in between | the application's login |
| G6 | `public` — where a stack uses it | manual | a public stack (`apps/whoami` on `w-public`) answers without any login | 200 |
| G7 | `none` behind a closed policy — where a stack uses it | manual | a stack stating `none` (e.g. `monitoring/gatus`) answers TS4/TS6 and refuses OUT4/OUT6 with 403 | as stated |

## F — the host ruleset loaded (DEC-078)

| ID | Test | How | Expected | Pass when |
|---|---|---|---|---|
| F1 | the state before | read | `sudo nft list tables` and `sudo nft list ruleset > before.nft` saved; the CrowdSec tables (`crowdsec`, `crowdsec6` or the bouncer's `inet` table) and Docker's and Tailscale's tables listed | saved |
| F2 | load with the way back | manual | the four commands of `host-firewall.md`, "Loading it", from a session over the VPN; the session survives; the way back cancelled | session alive, table `inet blueprint_ingress` present |
| F3 | the other tables untouched | read | `sudo nft list tables` = F1 plus `inet blueprint_ingress`; the CrowdSec set still holds its entries (`sudo nft list set …` count before and after); `cscli decisions list` unchanged | identical apart from the new table |
| F4 | management over IPv4, a new connection | manual | from TS: a **new** `ssh -4 <TS4 address of H1>` succeeds; from OUT `ssh -4 $H1_V4` times out | TS yes, OUT no |
| F5 | management over IPv6, a new connection | manual | from TS: a new `ssh -6 <TS6 address of H1>` succeeds; from OUT `ssh -6 $H1_V6` times out | TS yes, OUT no |
| F6 | the published ports are not affected | manual | X1 again from OUT → exit 0; E4 and E5 again | unchanged |
| F7 | the forward path is open | manual | `docker run --rm --network <a bridge network> curlimages/curl -4 -sI https://<an external host>` and the same with `-6` on a dual-stack network | both answer |
| F8 | the IPv6 anti-spoofing rule | manual | a neighbour on H1's LAN (or a container on a dual-stack bridge) sends a packet whose source lies in `TAILSCALE_CIDR_V6` to Traefik's published port; the counter of the drop rule in `sudo nft list chain inet blueprint_ingress forward` increases and no answer arrives; the same from TS6 over `tailscale0` passes | counter up, no answer; TS6 passes |
| F9 | it survives a reboot | manual | installed through the host's `nftables` include; after `sudo reboot` (console open): table present, F4 and F5 hold; `scripts/host-files.sh check core/traefik` → `identical` for `ingress.nft` | present, identical |

## M — the second management path (DEC-078)

| ID | Test | How | Expected | Pass when |
|---|---|---|---|---|
| M1 | the path used once | manual | from the hoster's console (not over the VPN): log in with the key-protected account or console password the hoster offers; run `sudo nft list tables` | a shell on the host |
| M2 | it works while the VPN is gone | manual | from the console: `sudo tailscale down`; F4 now fails; the console session still works; `sudo tailscale up` and F4 holds again | console independent of the VPN |

## N — a shared installation moved to edge networks (DEC-075)

Three routed stacks on `proxy-public` (`TRAEFIK_NETWORK=proxy-public`), called
S1, S2, S3 below.

| ID | Test | How | Expected | Pass when |
|---|---|---|---|---|
| N1 | the shared state lets web containers reach each other | **covered** | lab T1d, T2a–T2d | not run again |
| N2 | the move, stack by stack | manual | the four steps of [`edge-networks.md`](../core/traefik/docs/edge-networks.md), "Moving a shared installation", for S1, S2, S3; during each, a probe loop against the other two stacks (`curl` every 0.2 s) | the other stacks keep answering; the moved one returns after its recreate |
| N3 | isolation on edge networks | **covered** | lab T1a–T1c | not run again; N2's probes show each moved stack still served |
| N4 | the validator follows | read | `validate.sh --strict` exits 0; remove S3's network from `EDGE_NETWORKS` without moving S3 back → error naming the network | 0, then the error |
| N5 | the way back | manual | the same steps with `TRAEFIK_NETWORK=proxy-public` for all three; every stack served; `validate.sh --strict` exits 0 | as before N2 |

## B — the existing shapes, migrated and rolled back (step 7, DEC-075.3)

Starting point: a `core/traefik/.env` from `v0.9.5`, once in the IPv4-only shape
and once in the dual-stack shape, as `scripts/ci/test_traefik_render_identity.py`
builds them.

| ID | Test | How | Expected | Pass when |
|---|---|---|---|---|
| B1 | the published state before | read | on the `v0.9.5` checkout, running: `docker port traefik`, `sudo ss -ltnp \| grep -E ':(80\|443) '` saved | saved |
| B2 | the migration, dry run | read | `scripts/migrate-traefik-env.sh core/traefik` prints `TRAEFIK_BIND_V4=0.0.0.0`, in the dual-stack shape also `TRAEFIK_BIND_V6=[::]`, and the new `COMPOSE_FILE`; nothing written | the lines as stated |
| B3 | the migration, written | manual | `--write`; `.env.pre-model` beside the file; switch the checkout to the commit under test; render, `up -d` | `.pre-model` present, healthy |
| B4 | the exposure is preserved | read | B1 again: the same addresses and families as before; X1 from OUT unchanged | identical |
| B5 | the way back | manual | stop Traefik, restore `.env.pre-model` over `.env`, checkout `v0.9.5`, `up -d`; B1 again | identical to B1 |
| B6 | an unset binding is refused, an empty one publishes nothing | **covered** | `test_traefik_published_ports.py` | not run again |

**The criterion for this block.** The audit's acceptance item read "render
byte-identically without a declaration". After step 7 an unmigrated `.env` is
refused by design, so the item is judged as follows: after the documented
migration the exposure an installation had is preserved, unless a change of
behaviour was decided; the parts of the configuration no decision changed show
no unintended difference (the render-identity test, with its decided regions);
and the rollback is traceable — the `.pre-model` copy restores the earlier
state, and B5 shows it does.

## S — the nine stacks with a required binding (step 7)

`core/teleport` (`TELEPORT_BIND`), `core/step-ca` (`STEPCA_BIND`),
`core/jumpserver` (`JUMPSERVER_BIND`), `core/headscale` DERP overlay
(`APP_DERP_STUN_BIND`), `core/orion-belt` (`ORION_BIND`), `core/shellhub`
(`SHELLHUB_BIND`), `core/warpgate` (`WARPGATE_BIND`), `apps/unifi`
(`UNIFI_BIND`), `apps/opencanary` (`OPENCANARY_BIND`).

| ID | Test | How | Expected | Pass when |
|---|---|---|---|---|
| S1 | unset is refused | **covered** | `check-structure.py` `port-no-host-address` holds every stack to the required form, which Compose refuses unset | not run again |
| S2 | bound to the VPN address | manual, per stack installed | variable = H1's TS4 address; `up -d`; `ss -ltnup` shows the port on that address only; from TS the port answers, from OUT it does not | TS yes, OUT no |
| S3 | coverage | read | the list above with a result per stack; a stack not installed stays `not run` and is named in the release notes | every stack has a row |

## O — IPv6-only, its own run on H2 (DEC-063)

| ID | Test | How | Expected | Pass when |
|---|---|---|---|---|
| O1 | egress prerequisites | read | on H2: `dig AAAA` for `registry-1.docker.io`, `ghcr.io`, `lscr.io`, `github.com`, `plugins.traefik.io`, `acme-v02.api.letsencrypt.org`, `controlplane.tailscale.com`, `api.crowdsec.net`; for each without AAAA, the decided path (NAT64/DNS64 or excluded) recorded | every service has an answer or a path |
| O2 | the bindings | manual | `TRAEFIK_BIND_V4=` (empty), `TRAEFIK_BIND_V6=[::]`; render; E2 shows `[::]` only | no IPv4 port |
| O3 | a certificate over IPv6 | manual | ACME issues the test certificate; Traefik's log shows no IPv4 attempt failing | certificate present |
| O4 | ingress | manual | from OUT: `exposure-test.sh <H2 name> direct` → IPv6 answers, IPv4 `no-address`; E5 on H2 | exit 0, `OUT6` seen |
| O5 | images and plugins | manual | `docker compose pull` for `core/traefik`, `core/crowdsec`, `apps/whoami`; the CrowdSec plugin loads | all pulled, plugin loaded |

Until O1–O5 pass, `ipv6-only` stays "not verified" in `core/traefik/README.md`
and in DEC-063.

## Release gate

What the release that carries step 7's breaking change needs depends on the
configuration it claims. A **covered** row counts as passed.

**Always**, on H1: P, E, X1, A, G1, G3, G4, F1–F7, F9, M, N and B.

**Where the configuration uses it:**

- F8 — required where the IPv6 anti-spoofing protection is to be stated as
  active and verified. Without F8 the release notes say it is rendered and
  loaded, not verified.
- X4 — required only for an installation that uses the `proxied` profile.
- G5, G6, G7 — required only for the auth postures in use on the host under
  test.
- S2 — required for each of the nine stacks that is installed; one not
  installed is named as not run.

**Not blocking:** O. IPv6-only stays explicitly "not verified" in
`core/traefik/README.md` and DEC-063 until block O has its own run.

A required row not passed blocks the tag. An optional row not run is named in
the release notes and leaves that part of the decision's host verification
open.

## Results

| ID | Date | Host | Result | Evidence |
|---|---|---|---|---|
| P1 | 2026-11-01 | H1 | pass | commit under test recorded; `git status` clean apart from `.env` files |
| P2 | 2026-11-01 | H1 | pass, corrected | the first `validate.sh` on a fresh checkout stopped with `compose file not found`; corrected in `5296fc4`, then validate → render → `--strict` with only the marker open |
| P3 | 2026-11-01 | H1 | pass | `Exposure profile: direct`; host firewall, CrowdSec, forward-auth and management listed with their residual risk |
| P4 | 2026-11-01 | H1 | pass | `nft -c` exit 0, no output; `nft list tables` and the ruleset hash unchanged |
| E1 | 2026-11-01 | H1 | pass | `proxy-public`: IPv6 enabled, an IPv4 and a ULA subnet |
| E2 | 2026-11-01 | H1 | pass | 80, 443/tcp and 443/udp on `0.0.0.0` and `[::]`, held by `dockerd`; no `docker-proxy` |
| E3 | 2026-11-01 | H1 | pass | highest `GwPriority` (100) on `proxy-public`; the IPv6 DNAT for 80 and 443 targets Traefik's ULA address there |
| E4 | 2026-11-01 | H1 | pass | from OUT: `X-Real-Ip` and `X-Forwarded-For` = OUT4; access log `ClientHost` = OUT4 |
| E5 | 2026-11-01 | H1 | pass | from OUT: `X-Real-Ip` and `X-Forwarded-For` = OUT6, no gateway address |
| E6 | 2026-11-01 | H1 | pass | `validate.sh --strict` names only the exposure marker; nothing PENDING or NOT VERIFIED from the family check |
| X1 | 2026-11-01 | H1 | pass | with `8f19db3` from OUT, one run per address: 80 and 443 answer on IPv4 and on IPv6, 8080, 2375, 2376, 3306, 5432, 6379, 8025, 11434 closed on both; SSH answers on IPv4 (the operator's address is admitted upstream), not on IPv6. The first run, before `8f19db3`, reported every open port closed (curl exits 28 after a connect) |
| A1–A5 (OUT4, OUT6) | 2026-11-01 | H1 | pass | `w-public` 200/200; `w-trusted`, `w-vpn`, `w-trusted-vpn`, `w-blocked` 403/403 |
| A1–A5 (TS, LAN) | 2026-11-01 | H1 | not run | no VPN on the lab host by the operator's decision for this phase; no LAN client |
| A7 | 2026-11-01 | H1 | pass | from OUT6 with a forged `X-Forwarded-For`/`X-Real-Ip` (tailnet example): `w-vpn` 403; `w-public` shows OUT6 |
| A8 | 2026-11-01 | H1 | not run | needs a tailnet client |
| A9 | 2026-11-01 | H1 | deviation | `--resolve …:[::1]` on `w-vpn`: no connection (timeout), not 403 — `userland-proxy: false` does not forward IPv6 loopback (`ipv6-dual-stack.md`); over the host's global IPv6 address and over 127.0.0.1: 403 |
| G1 | 2026-11-02 | H1 | pass after correction | a proxy provider (forward auth, single application) on the embedded outpost, `w-fa` on `auth-authentik@file`: 302 to the Authentik host, the login (password and TOTP, scripted through the flow executor), the outpost callback; whoami shows `X-Authentik-Username`. Before the outpost's `authentik_host` was set the 302 pointed at `http://localhost/` |
| G3 | 2026-11-02 | H1 | pass | `authentik-server` stopped: 500 without and with a valid session, never 200; started: 302 again |
| G4 | 2026-11-01 | H1 | pass, host-local | Heimdall: no credentials 401, wrong 401, right 200; router carries `heimdall-auth@docker`; reached through a router admitting the host itself only (deviation, see report) |
| N2 | 2026-11-01 | H1 | fail | each Traefik recreate interrupted every stack for 6.5–7.3 s, not only the one moved; the moved stack returned after its healthcheck |
| N4 | 2026-11-01 | H1 | pass after correction | `--strict`: only the marker; a network dropped from `EDGE_NETWORKS` while Traefik still joined it passed with exit 0 — corrected in `0d33bad` |
| N5 | 2026-11-01 | H1 | pass | all three stacks served on `proxy-public` again; the moved-back stack is unreachable between step 1 and step 3 when the list is shortened first |
| B1–B5 (dual-stack) | 2026-11-01 | H1 | pass | migrated state identical to the v0.9.5 state apart from the decided `gw_priority`; rollback identical to B1 |
| B1–B5 (IPv4-only) | 2026-11-01 | H1 | pass | addresses and families identical; the DNAT moves from `crowdsec-security` to `proxy-public` (the decided change of step 2); rollback identical to B1 |
| M1 | 2026-11-01 | H1 | pass | the hoster's console used once with a break-glass account; `sudo` asked for its password |

The run report is [`labs/ingress/2026-11-01-results.md`](labs/ingress/2026-11-01-results.md).
