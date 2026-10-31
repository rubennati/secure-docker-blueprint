# Ingress architecture — audit, lab run and decisions (2026-10-31)

**Status: audit record, decided; nothing in it is implemented.** The decisions it led
to are DEC-075 to DEC-078 and an addendum to DEC-063 in
[`.ai/decisions.md`](../../.ai/decisions.md); the programme that implements them is
`.ai/tasks.md` §12. This record keeps what was examined, what was measured and what
stays open, so that no later step has to measure it again.

Scope: the whole ingress path — host firewall, Docker networking, Traefik, CrowdSec,
Cloudflare, the VPN, Authentik and the applications — judged for a realistic
installation of one, three or ten stacks, not for the catalogue of 109.

Evidence classes: **tree** — in a file of this repository at the stated line;
**source** — vendor documentation or source code read on GitHub, the vendor sites
being unreachable from the environment that ran the audit; **lab** — measured on
2026-10-31 in a throwaway Docker daemon (§4); **open** — neither, and named as such.
Names of the time before the middleware model are not used here.

---

## 1. What the tree does today

| Mechanism | State | Evidence |
|---|---|---|
| Published ports | Traefik on `TRAEFIK_BIND_V4` only; IPv6 only with `network-dual-stack.yml` (PR #272, v0.9.5). Nine stacks publish a port without a host address: `apps/unifi`, `apps/opencanary`, `core/teleport`, `core/shellhub`, `core/warpgate`, `core/jumpserver`, `core/orion-belt`, `core/step-ca`, `core/headscale` (opt-in `derp.yml`) | tree |
| `proxy-public` | one network for Traefik and every routed web container; IPv4-only unless the overlay is applied | tree |
| Access policies | `access-public`, `access-lan` (RFC 1918 + `fc00::/7`), `access-vpn` (the Tailscale ranges), `access-lan-vpn`, `access-blocked`; all evaluate the connecting address; catalogue defaults: 66 vpn, 26 public, 14 lan-vpn, 1 lan, 1 blocked | tree, `model.yml.tmpl:50–86` |
| Auth position | 106 of 109 stacks `auth-none@file`, 2 a stack-owned `basicAuth`; forward-auth switched off as shipped; nine stacks have no login of their own | tree |
| Header hygiene | `forwardedHeaders.trustedIPs` by sender, nothing from anyone else; no `trustForwardHeader`; `forwardedHeadersCustomName` refused | tree, source (Traefik v3.7 entrypoints and forwardAuth reference) |
| CrowdSec | detection from the access log; bouncer at the entrypoint, fail-open; host bouncer set-only with one rule per family on the public interface | tree |
| Host firewall | not standardised (`deployment-lifecycle.md:60`); a Cloudflare origin ruleset is rendered, never loaded on a host | tree |
| Management access | the VPN interface; a second path is not stated; two lockouts recorded | tree, `core/crowdsec/docs/firewall-bouncer.md:50–72`, `docs/bugfixes/crowdsec-firewall-bouncer-2026-08-28.md` |
| Threat model | none written; `SECURITY.md:78` names the IP allowlist, the headers and the rate limit as the layers of a request path | tree |

---

## 2. Findings

**F1 — Network origin is used as authorisation.** For 106 routes the access policy is
the only control before the application's own login, and for nine applications
without a login it is the only control at all. The policy evaluates an address Docker
hands it, and the four security findings since June (the gateway bug of 2026-06-19,
the hairpin misreading of the bouncer test, the relay path past the origin ruleset,
PR #272) were all cases of that address being wrong. Vendor and standards guidance
agree: OWASP's authentication cheat sheet lists IP addresses as risk signals, "not as
substitutes for authentication"; Cloudflare rates an IP allowlist at the origin
"moderately secure, vulnerable to IP spoofing"; NIST SP 800-207 grants "no implicit
trust … based solely on … network location" (source; the NIST text by search excerpt
only).

**F2 — `access-lan` admits more than a LAN.** RFC 1918 contains every Docker subnet,
and `fc00::/7` contains Tailscale's `fd7a:115c:a1e0::/48`: a tailnet client over IPv6
passes a LAN-only policy (tree, `traefik-security.md:66`), and a compromised container
on any network Traefik joins passes it for another stack's host name (lab, T2c). A
LAN with a global prefix, the common case with provider delegation, is not admitted at
all.

**F3 — The shared network has no isolation between its members.** Containers on one
bridge network reach each other's ports; Docker isolates networks from one another
(source: `docker/docs` bridge driver; lab T1). On `proxy-public` a compromised web
container reaches every other backend without a router position, and can set
`X-Forwarded-For` or `X-authentik-username` on that direct path — Authentik's own
integration notes ask that clients cannot set those headers and that the backend is
not directly reachable (source). With one stack this is moot; with three it is a
blog reaching a password manager's container.

**F4 — The published ports land on a network nobody chose.** Docker maps a
multi-network container's published ports to its gateway endpoint, which Compose
orders alphabetically: `crowdsec-security` before `public`. Traefik's 80 and 443 are
DNAT'd to its `crowdsec-security` address on every installation shaped like the
shipped Compose file; a hairpin or published-port client appears as that network's
gateway (lab, T3, T7a). `gw_priority` on `public` moves the endpoint (lab, T7b). The
family check of PR #272 reads `networks.public.enable_ipv6`; which endpoint Docker
chooses for an IPv6 port is open.

**F5 — Exposure is not modelled.** The blueprint knows who may reach a router and not
who reaches the host. Docker: "publishing container ports is insecure by default …
available … to the outside world"; `ufw` rules are bypassed (source). With IPv6 and no
NAT, a host behind a home router is reachable on its global prefix as soon as a port is
published on `[::]`.

**F6 — The identity layer exists and is not the default.** Forward-auth is built,
fails closed (Traefik answers 500 when the outpost is unreachable — source,
`pkg/middlewares/auth/forward.go`) and deletes every client copy of its response
headers (source, lab T4b); no stack uses it by default, and a route with `auth-none`
passes `X-authentik-username` from the client (lab, T4c).

**F7 — Exceptions stand in for a recovery path.** A `safe_range` that was never a
configuration key, an allowlist for administrator devices, a gateway admission —
each either did nothing or opened a path. No management path independent of the VPN
is stated; Tailscale's own documentation asks for an alternate login before
`--force-reauth`, and a node key that expires ends every connection (source, search
excerpt).

**F8 — Three operating modes multiply the matrix the host has to prove.** Each mode
needs a host run; the host is the scarcest resource (`.ai/state.md`, active
constraints); the test server of 2026-10-18 is deferred.

**What is sound and stays:** the four router positions and their measured values; the
header hygiene by sender and the Cloudflare switch with its guard; `app-internal`;
CrowdSec with two remediation points and the topological management-plane invariant;
the render-and-validate chain; rendered host files; PR #272.

---

## 3. Decisions taken (summary; the entries own the wording)

| Entry | Decision |
|---|---|
| DEC-075 | An edge network per installed stack is the default for a new installation; the shared `proxy-public` stays a documented choice. `proxy-public` carries the published ports, named by `gw_priority`. Host ingress is two bind variables, one per family; no network mode. IPv6-only means no public IPv4 ingress; no IPv4 egress is a prerequisite list (§3.4); an IPv6-only Docker network is out of scope. |
| DEC-076 | `access-trusted` and `access-trusted-vpn` admit declared ranges; empty admits nobody; a range containing the VPN range or a Docker subnet is refused. `access-lan*` is not shipped to a new installation. An `.env` without `TRUSTED_RANGES` renders v0.9.5's policies byte-identically. |
| DEC-077 | The auth position states a posture per stack — `app-login`, `public`, `basic`, `forward-auth`, `none`; `auth-none` means no additional proxy authentication; `none` needs a closed policy and a reason; no login layer is forced. |
| DEC-078 | Exposure is derived (`direct`, `proxied`, `private`) and shown, never equated with measured reachability; mandatory invariants are what the blueprint controls inside the host; the host firewall ruleset is rendered and recommended; optional layers are named with their residual risk, never counted as errors; management has two independent paths. |
| DEC-063, addendum | The goals stand; the three modes become bind decisions. |

### 3.1 Mandatory, recommended, optional

Mandatory — what the blueprint itself guarantees without any external firewall:
only Traefik is published, on named addresses, and every other published port names
its address; backends are never published; `app-internal` is isolated; no address
class is trusted; headers are sanitised by sender; forward-auth fails closed; the
management path does not run through Traefik or Docker and has a second,
ingress-independent route; the published-address state is verified before `--strict`
passes.

Recommended, with the residual risk named when absent: a host firewall ruleset
(indispensable where no upstream firewall exists and where Cloudflare fronts the
origin; it also carries the IPv6 anti-spoofing rule for the VPN range, which
Tailscale's Linux client installs for IPv4 only — source, `util/linuxfw`); CrowdSec
detection with the entrypoint bouncer; forward-auth for weak application logins.

Optional, each with its own risk: Cloudflare (not "protected" without the origin
ruleset and Authenticated Origin Pulls or a tunnel — source, Cloudflare's own
rating); the host bouncer; AppSec; declared LAN ranges; geo-blocking; Tailscale
grants; HTTP/3.

A simple port forward of 80 and 443 is sufficient for the Traefik path in every
profile while the mandatory invariants hold. Additional firewall rules are needed
for Cloudflare, for public SSH and for a host with no upstream firewall at all.

### 3.2 Threats, and what answers them after the decisions

| Threat | Answer |
|---|---|
| Compromised LAN client | reaches only declared ranges (`access-trusted`), meets the application's login or the gate the posture names |
| Compromised VPN device | has network access, device identity and usually the browser's sessions: no ingress mechanism stops it; least privilege (Tailscale grants, application roles) and detection bound the damage — stated as a limit |
| Direct origin access past Cloudflare | the origin ruleset plus AOP or a tunnel, or the installation is not called protected |
| Compromised container | reaches Traefik and its own `app-internal`, nothing else (edge network); on the shared network it reaches every backend, which the choice documents |
| Forged proxy headers | deleted at the entrypoint from every sender outside `trustedIPs`; forward-auth deletes its own header names (T4) |
| IPv6 bypass | closed for the gateway path (PR #272); `access-trusted` has no implicit ULA; the IPv6 endpoint of the published ports is open (F4) |
| Administrator lockout | two independent paths, identity by key, automation topologically off the management interface; rehearsed at every host acceptance |

### 3.3 Not changed, and why

`access-vpn` stays: the VPN range is a property of the host's tunnel interface, and
the IPv4 anti-spoofing rule of the client plus the host ruleset's IPv6 rule keep it
so. `app-internal` stays. `ipv6Subnet` on the rate limits is not adopted: Tailscale's
translated IPv6 addresses share one `/104` (source, `net/tsaddr`), so any subnet
grouping puts the whole tailnet in one bucket. Computed exclusion lists are not
adopted: a declared range is simpler and what is trusted is what was written.

### 3.4 IPv6-only — what a host without IPv4 egress would need

Reachability of the services an installation pulls from, as far as it could be
established (source; AAAA records could not be resolved from the audit environment
and are to be confirmed with `dig AAAA` on the target host):

| Service | IPv6 |
|---|---|
| Docker Hub (`registry-1.docker.io`) | yes, generally available since 2023-08 (vendor blog) — 210 of 277 image references |
| `ghcr.io`, `lscr.io` | no AAAA on the registry host (third-party survey 2025) — 54 image references |
| `github.com` and its content hosts | no AAAA (community discussion open) — the clone of this repository |
| `plugins.traefik.io` | Traefik v3.7 downloads plugins from here (source, `pkg/plugins`), AAAA not established |
| Let's Encrypt | API and validation over IPv6; with A and AAAA present, validation always prefers IPv6 and does not fall back on an HTTP error (vendor documentation) |
| Tailscale control plane | AAAA since 2021-08 (issue tracker); relays dual-stack |
| CrowdSec central API | IPv6 via its CDN (vendor blog); the hub's AAAA not established |

A host without IPv4 egress therefore needs NAT64/DNS64 or excludes the registries and
sources above. That is a host prerequisite, not a blueprint mode. A host without
public IPv4 ingress needs none of it.

---

## 4. The lab run

Throwaway daemon in the audit environment: Docker Engine 29.9.2, iptables firewall
backend, `userland-proxy: false`, cgroup v1, **IPv4 only** (the kernel had no IPv6);
Compose 5.6.1; Traefik 3.7.17 (`traefik:v3.7`); `traefik/whoami` 1.11.0. `core/traefik`
was used unchanged — Compose file, templates, `render.sh`, `validate.sh` — with an
`.env` from `.env.example`; lab additions were separate files under `config/dynamic/`
only (a wildcard certificate for the lab names, the mock forward-auth middleware, the
exclusion middleware of T8). Three stacks shaped like `apps/_reference`: a web
container on its own edge network and an internal network, a "database" (another
whoami) on the internal network only, the label `traefik.docker.network=<edge>` as
every routed stack carries. Routers: `a` public, `a2` blocked, `b` lan, `b2` lan-vpn
with the mock forward-auth, `c` vpn, `c2` public. Traefik joined `proxy-public` (the
`public` key, publishing 8080/8443), the socket-proxy and CrowdSec networks,
`edge-a`, `edge-b` and the mock's network; `edge-c` only in T6. The attacker was a
shell entered into the web container of stack A with `nsenter`, so its address was that
container's. The mock forward-auth was whoami, whose `/health` answers the code last
posted to it. No client outside the host existed; the external path is PR #272's.

| Test | Expected | Measured | Settled by |
|---|---|---|---|
| T1a–c · A → B's web container, B's database, Traefik's address on `edge-b` | no path | timeout for all three | source + lab |
| T1d · A → Traefik's address on `edge-a` (control) | reachable | reachable (TLS alert without SNI; 200 with it) | lab |
| T2a · A → Traefik on `edge-a`, host `a` (public) | 200 | 200, client = A's address | — |
| T2b · host `a2` (blocked) | 403 | 403 | source + lab |
| **T2c · host `b` (lan)** | **200 — a bypass** | **200**, client = A's address | source + lab |
| T2d · host `b2` (lan-vpn, mock 200) | 200 — a bypass | 200 | source + lab |
| T2e · host `c` (vpn) | 403 | 403 | source + lab |
| T2f · host `c2` (public, backend on `edge-c`, Traefik not there) | no backend | no answer within 5 s; no warning in Traefik's log | lab |
| T3a–c · A and a host process → the published port, host `b` | reachable; source = a gateway | 200; the client is the gateway of the gateway-endpoint network (`crowdsec-security`'s), not of A's | lab |
| T3d · host process → published port, host `c` (vpn) | 403 | 403 | lab |
| T4a · host `b2`, mock answers 401, A sends `X-authentik-username` | 401, backend not reached | 401, not reached | source + lab |
| T4b · mock answers 200, A sends `X-authentik-username` | header deleted at the backend | 0 such header lines at the backend | source (`forward.go`) + lab |
| T4c · host `a` (auth-none), A sends `X-authentik-username` | passes | passes | lab |
| T5a–b · forged `X-Forwarded-For` of a VPN address against `c`; against `a` | 403; backend sees A | 403; A's address | source + lab |
| T6a–d · `edge-c` added and removed at runtime | connect works live; Compose recreates | live `docker network connect`: 200 after 2 s; `compose up -d` with the network added: container recreated, 10 of 178 probes at 0.2 s failed, outage ≈ 1.9 s; live disconnect: `c2` unreachable, `a` unaffected | lab |
| **T7a · which endpoint carries the published ports** | open | **Traefik's address on `crowdsec-security`**, default route through its gateway — the first network in Compose order | lab |
| **T7b · `gw_priority: 100` on `public`** | the endpoint moves | DNAT and default route on `proxy-public`; Compose 5.6.1 accepts the key | lab |
| T8 · `access-lan-excl` = RFC 1918 minus every Docker subnet of the daemon (4 CIDRs), on `b` | A 403, host hairpin 403, rest unchanged | 403, 403; `a` 200, `b2` 200 | lab |
| T9 · user networks the default address pool holds | about 30 | 12 present + 20 more, then "all predefined address pools have been fully subnetted": **32** | lab |
| T10 · a container without `traefik.docker.network`, on `edge-c` and an internal network, six runs | random | 200, 200, 200, 200 and twice no answer (the internal network chosen); no log line | source (map iteration) + lab |
| T11 · the address Traefik dials a backend from | its address on the labelled network | `edge-b`'s | source + lab |

Mechanics behind the results: Engine 29 carries `-A DOCKER ! -i br-X -o br-X -j DROP`
per bridge and `-P FORWARD DROP` (chains `DOCKER-FORWARD`, `DOCKER-BRIDGE`,
`DOCKER-INTERNAL`, `DOCKER-USER`; the `DOCKER-ISOLATION-STAGE` chains of earlier
releases are gone); `-A POSTROUTING -s <edge subnet> ! -o br-edge -j MASQUERADE`
rewrites every packet that leaves an edge network for another interface to the
gateway of the network it enters.

Not measured here, and to be measured on a host: IPv6 in every test, above all the
endpoint Docker chooses for an IPv6 port (T7 over IPv6); a real LAN or tailnet client;
the nftables firewall backend; rootless Docker.

---

## 5. Open — what a host has to show before a release that changes a default

- A host with a global IPv6 address and a client outside it: exposure measured from
  outside, every policy per family, the IPv6 endpoint of the published ports, a tailnet
  client against `access-trusted`.
- Both existing shapes — IPv4-only and dual-stack — render byte-identically without a
  declaration, and migrate and roll back by their documented paths
  (`scripts/ci/test_traefik_render_identity.py` holds the first half mechanically).
- The migration of a real shared installation with three stacks to edge networks, and
  its rollback.
- Forward-auth with a real outpost; a `basicAuth` gate on an application without a
  login.
- The rendered host ruleset loaded on a host: management gates over both families as
  new connections, the CrowdSec tables intact, the IPv6 anti-spoofing rule effective.
- The second management path used once.

---

## 6. Sources

Vendor documentation and source read on GitHub on 2026-10-31: `docker/docs`
(`engine/network/drivers/bridge.md`, `port-publishing.md`, `firewall-iptables.md`,
`firewall-nftables.md`, `daemon/ipv6.md`, release notes 27–29); `traefik/traefik` at
v3.7 (`pkg/provider/docker/config.go`, `shared.go`, `pkg/middlewares/auth/forward.go`,
the entrypoint, ipAllowList, forwardAuth and TLS options references);
`cloudflare/cloudflare-docs` (protect your origin server, authenticated origin pulls,
tunnel, IPv6 compatibility, HTTP headers); `tailscale/tailscale` (`net/tsaddr`,
`util/linuxfw`, `ipn/ipnlocal/serve.go`); `crowdsecurity/crowdsec-docs` and the
`traefik-logs` parser; `goauthentik/authentik` docs; `OWASP/CheatSheetSeries`
(authentication); `docker/docker-bench-security` for the CIS Docker Benchmark v1.6.0
items 2.2, 2.16, 5.14. NIST SP 800-207, the Tailscale knowledge base and CISA were
reachable by search excerpt only and are marked so where cited.
