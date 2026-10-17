# Phase 3 review — `TRAEFIK_FORWARDED_PROXY` (branch `feature/cloudflare-mode`)

**Date:** 2026-10-17 · **Scope:** `origin/dev..feature/cloudflare-mode` (commits `2a69603`,
`6864c45`; 16 files) · **Kind:** independent technical review, read-only. Nothing in this
document was applied; every correction is a proposal. Host verifications stay open.

## 1. Scope and method

Reviewed in the order the brief gave: the trust boundaries of the client address in both
modes; `render.sh` and `validate.sh`; `scripts/host-files.sh` and the manifest; the tests;
the documentation claims. Each claim was checked against one of these sources, all read
at the versions the blueprint pins or names:

| Source | What was read |
|---|---|
| Traefik `v3.7` | `pkg/middlewares/forwardedheaders/forwarded_header.go`, `pkg/middlewares/accesslog/logger.go`, `pkg/ip/strategy.go`, `pkg/middlewares/extractor.go`, `pkg/middlewares/ipallowlist/ip_allowlist.go`, `pkg/middlewares/ratelimiter/rate_limiter.go`, `pkg/config/dynamic/middlewares.go` |
| Bouncer plugin `v1.7.1` | `README.md`, `bouncer.go`, `pkg/ip/ip.go`, `pkg/configuration/configuration.go`, `examples/behind-proxy/README.md` |
| CrowdSec hub (`master`) | `parsers/s01-parse/crowdsecurity/traefik-logs.yaml` |
| Cloudflare documentation | HTTP request headers; Pseudo IPv4; rate-limiting rules (availability); request header modification rules (restrictions); managed transforms |
| This repository | the diff, `core/crowdsec/docs/firewall-bouncer.md`, `core/traefik/docs/ipv6-dual-stack.md`, `docs/standards/host-files.md`, `.ai/decisions.md`, the audit |

Executed, in a scratch copy outside the repository, never on a host:

- `python3 -m unittest discover -s scripts/ci -p 'test_traefik_*.py'` (Python 3.12,
  PyYAML, GNU envsubst): **50 tests, OK**. `test_host_files.py`: 14 tests, OK.
  `check-links.py`: 375 files, 0 broken. `check-prose.py`: 0 blocking.
- Both modes rendered into a temporary directory; the generated YAML and the nft file
  inspected raw (section 2).
- `scripts/host-files.sh render | check | install-commands | diff` for `core/traefik`
  against a scratch `HOST_FILES_PREFIX` in `none` mode (finding 2).
- The drift guard exercised with a changed ranges file, an empty value, an upper-case
  value and an exported environment variable (finding 6).
- The rendered nft defines parsed, together with a forward-hook rule that uses them, by
  `nft -c` (nftables 1.0.9 in a local Alpine container with `NET_ADMIN`): **rc 0**.

Line numbers below refer to the branch tip `6864c45`; upstream line numbers to the
files as fetched on 2026-10-17.

## 2. What was verified and holds

**The entrypoint, both modes.** With an empty `trustedIPs` list Traefik builds no checker
(`forwarded_header.go:87`), `isTrustedIP` then returns false for every sender
(`:133-138`), and `ServeHTTP` deletes the set `XHeadersSet` — the `X-Forwarded-*`
headers and `X-Real-Ip` (`:39-48`, `:117-119`). `X-Real-Ip` is set from the connection
only when it is empty afterwards (`:144-145`); `X-Forwarded-For` is joined, never
appended to, before the middlewares (`:179`). So in `none` mode every layer sees the
connecting address, and in `cloudflare` mode a request from a listed range keeps what
Cloudflare sent. The rendered `none` list is `trustedIPs: &cloudflareTrustedIPs` followed
by `[]` on the next line, which PyYAML and Traefik read as an empty list; the
`cloudflare` list carries the 22 ranges of the file on both entrypoints (the anchor is
reused). The inserted bouncer block sits at ten and twelve spaces under
`plugin.bouncer` and parses as part of it.

**Access policies and rate limits.** `ipAllowList` and `rateLimit` use
`RemoteAddrStrategy` unless an `ipStrategy` is set (`middlewares.go`, `IPStrategy.Get`;
`extractor.go:30-36`); the templates set none, and the test asserts that in both modes.
Behind Cloudflare the closed policies therefore refuse the edge and the limits count per
edge address, as documented. The claim that a header-reading strategy "leaves a direct
client with no address" holds for `ipAllowList`: Traefik's `PoolStrategy` returns an
empty string when the header is absent (`strategy.go:74-92`) and `IsAuthorized("")`
refuses (`ip_allowlist.go:75-78`). For `rateLimit` the consequence is one shared bucket,
not an error (`extractor.go:46-48` returns no error; `rate_limiter.go:134-138` fails only
on an error) — see note 13.

**Cloudflare's side.** `x-real-ip` from a client is stripped by Cloudflare when no Worker
is involved, and Transform Rules cannot modify the value of any visitor-address header
(`x-real-ip`, `x-forwarded-for`, `true-client-ip`, `cf-connecting-ip`): the CHANGELOG's
"Cloudflare's own rules cannot set `X-Real-Ip`" holds, and `X-Real-Ip` = edge at the
application holds. Rate-limiting rules: 1 on Free, 2 on Pro — holds. `X-Forwarded-For`:
Cloudflare appends the connecting client behind any value the client sent — holds.

**CrowdSec detection.** The hub's Traefik parser derives `source_ip` from
`TrimSpace(Split(ClientHost, ',')[-1])` in the JSON branch (`traefik-logs.yaml:32-34,
75-76`), so a forged first entry does not reach a scenario. The access-log field itself is
different — note 8.

**The ranges.** `ops/cloudflare-ips.txt` carries both families; the offline checker
accepts it; the weekly workflow compares it with cloudflare.com. The nft output is valid
`define` syntax with prefix sets and parses together with a forward-hook rule.

**The guard and the agreement checks** do what the tests say in the cases the tests
cover; what they miss is finding 6.

## 3. Findings

Severity: **blocker** — must change before merge; **should-fix** — change before the
mode is recommended to anyone, may follow in the same PR or the next; **note** — for
the record.

### F1 · blocker — in `cloudflare` mode the bouncer compares a header any sender may set

**Claim under review.** Five places state that the bouncer compares `CF-Connecting-IP`
"only when the request arrives from a Cloudflare address" / "from those ranges only":
`core/traefik/README.md:635`, `docs/standards/traefik-security.md:79`,
`core/crowdsec/README.md:112-117`, `CHANGELOG.md:13`, the template comment
`crowdsec.yml.tmpl:32-37`, `render.sh:105-108`, `.env.example:113-116`.

**Evidence.** The plugin never gates on the connecting address. `GetRemoteIP`
(`pkg/ip/ip.go:119-129`) calls `getIP`, which reads the configured header, splits it on
commas and returns the last entry that is not in `forwardedHeadersTrustedIPs`
(`:96-116`); the connecting address is used only when that yields nothing. The pool built
from `forwardedHeadersTrustedIPs` (`bouncer.go:145`) is consulted solely to skip entries
inside the header value. `NewChecker` with an empty list returns a non-nil checker
(`ip.go:23-25`), so even the default configuration reads the header whenever it is
present. Traefik deletes only its own header set at the entrypoint
(`forwarded_header.go:39-48`); `CF-Connecting-IP` is not in it and reaches the
middleware from every sender unchanged.

**Consequence.** With `forwardedHeadersCustomName: CF-Connecting-IP` rendered
(`render.sh:138`), any request that does not come through Cloudflare's proxy — a LAN or
VPN client, a direct Internet client while the origin firewall is absent or placed on the
wrong hook (F3), a Worker (F4) — chooses the address the bouncer compares by sending
`CF-Connecting-IP: <anything>`. A banned direct client sends an unbanned address and
passes. The D3 condition "No client-supplied address header taken on trust"
(`.ai/decisions.md:83-84`) is not met in this mode.

**Proposed correction.** Do not set `forwardedHeadersCustomName`; keep
`forwardedHeadersTrustedIPs`. With the plugin default `X-Forwarded-For`
(`configuration.go:171`) the gating is done by Traefik's entrypoint, which deletes the
header from every untrusted sender: a direct client is compared by its connection, and a
request from a Cloudflare range yields the client Cloudflare appended last (`ip.go:105-112`
walks from the right; a forged first entry is never reached). Behaviour for WARP or other
Cloudflare-egress clients is unchanged (note 14). Then correct the sentence in the seven
places above to: "compares the last `X-Forwarded-For` entry outside the trusted ranges;
the entrypoint deletes that header from every sender outside them, so a direct client is
compared by its connection". Add a test that the rendered middlewares carry no
`forwardedHeadersCustomName`. If `CF-Connecting-IP` is kept on purpose, the documentation
must say that it is unsanitised and that the origin firewall is the only control, and
F3 becomes a blocker.

### F2 · blocker — `scripts/host-files.sh check` fails on every `none`-mode host

**Evidence.** `read_manifest` tolerates an absent `config/host/` source
(`host-files.sh:84-89`) and `render_stack` skips it (`:114-117`), but `check_stack` does
not: an entry whose rendered copy is missing reports `not rendered` and counts as a
problem (`:199-202`, `:182`). Run in a scratch copy with the manifest line
(`host-files.manifest:9`) and `TRAEFIK_FORWARDED_PROXY=none`:

```text
  not rendered   traefik: config/host/cloudflare-ranges.nft -> /etc/nftables.d/cloudflare-ranges.nft  (run: scripts/host-files.sh render traefik)
  2 host file(s) need attention.
check rc=1
```

`none` is the default and the migration target for every installation without
Cloudflare (`CHANGELOG.md:40`), so `check` and `./scripts/overview.sh --host` exit 1 on
them permanently, and the suggested command does not produce the file. Two smaller
consequences: `install-commands` prints a `sudo install` line for the non-existent file
(`:299-300`), and `diff` for that target says "not rendered — run: … render" (`:275`).
No test covers `check` for `core/traefik`; `test_host_files.py` renders the shipped
manifests only.

**Proposed correction.** In `check_stack`, before the "not rendered" branch, treat a
`config/host/` source that does not exist as a state that is not a problem — for example
`not rendered by the stack` for an optional entry, reported but not counted (the standard's
table needs that row). `install_commands` and `diff_file` skip or explain such an entry
the same way. Add a test: render `core/traefik` with the switch at `none`, run `check`
against a prefix, expect exit 0 and the new state. Update `docs/standards/host-files.md`
for the convention (note 11).

### F3 · should-fix — the origin-firewall instruction does not say where the rule goes, and "reload nftables" collides with the repository's own rule

**Claims.** `README.md:658-673`: "a host firewall rule admits 80 and 443 from those sets
and from the VPN and LAN ranges, and from nowhere else … render, reinstall, reload
nftables". The nft file's comment says the same (`render.sh:159-161`). The target is
`/etc/nftables.d/cloudflare-ranges.nft` (`host-files.manifest:9`).

**Evidence.** Traefik's ports are published by Docker (`docker-compose.yml:105-108`).
The repository's own firewall document states, host-verified, that published ports never
traverse `input` and that enforcement belongs on `hook forward`
(`core/crowdsec/docs/firewall-bouncer.md:123-146`, verification table `:842`). A reader
who writes the obvious `input` rule filters nothing and believes the origin is closed —
the exact trap that document exists to prevent, and the trap on which F1's residual risk
rests. Further: the same document forbids `nft flush ruleset` and whole-ruleset
restores twice (`:323-324`, `:577-580`) because Docker and the VPN own live state, yet
"reload nftables" on Debian means `systemctl restart nftables`, which runs
`/etc/nftables.conf` starting with `flush ruleset`. And `/etc/nftables.d/` is not
included by the shipped Debian configuration; a `define` is only visible inside the
`nft -f` run that includes it, so the README has to show the include and the rule that
uses the symbols. Direct HTTP/3 clients (UDP 443, published at `:108`) are not mentioned.

**Proposed correction.** In "Protect the origin": state the hook (`forward`, priority
before Docker's, with the ingress-interface match as in `firewall-bouncer.md:225-235`),
show one complete example — a dedicated table that includes the defines, admits TCP 80
and 443 from `$cloudflare_v4` / `$cloudflare_v6` and the VPN/LAN interfaces, UDP 443 for
direct clients, and drops the rest on the public interface — and the reload as
`nft -f` of that table's file (beginning with `destroy table …` or `flush table …`),
never a ruleset flush. Cross-reference the firewall document's section. Alternative worth
considering: render a named set (`type ipv4_addr; flags interval`) instead of defines,
which can be replaced atomically without reloading anything else.

### F4 · should-fix — the trust boundary in `cloudflare` mode is "Cloudflare's network", not "my zone", and the README does not say so

**Evidence.** Cloudflare's header reference states, for Worker subrequests to an origin
that is not a Cloudflare customer zone: "the Worker script controls the client IP
headers: both `CF-Connecting-IP` and `x-real-ip` can be altered by the Worker". Such a
request leaves a published Cloudflare range, passes the origin firewall of F3, is trusted
by the entrypoint, and arrives with a chosen `CF-Connecting-IP` (compared by the bouncer
under the current rendering, F1) and a chosen `X-Real-Ip` (read by Vaultwarden's
`IP_HEADER` in `none` mode and logged). A second tenant pointing a zone of their own at the
origin address also arrives from the ranges; Cloudflare then sets the headers honestly,
but that tenant's zone carries none of the operator's edge rules — including the
rate-limiting rule the README moves to the edge (`README.md:637`), while the origin counts
per edge address. What a tenant can do with the `Host` header and routing depends on
Cloudflare features that cannot be verified from the repository. The README names
Authenticated Origin Pulls as "the stronger form … not shipped here yet"
(`README.md:670-673`) without saying what it is stronger against.

**Proposed correction.** One paragraph under "Protect the origin": the ranges admit
anything that leaves Cloudflare's edge, Workers and other zones included; Cloudflare's
documentation says a Worker chooses `CF-Connecting-IP` and `x-real-ip` towards such an
origin; what bounds trust to this zone is Authenticated Origin Pulls (a `clientAuth` TLS
option on the public routers) or a Tunnel, neither shipped; until then the per-client
limit at the edge is advisory and the bouncer's address is as good as the firewall plus F1.
Record the AOP template as the Phase 3 follow-up it is.

### F5 · should-fix — IPv6 between Cloudflare and the origin is not addressed, and on an IPv4-only `proxy-public` it defeats the mode

**Evidence.** `proxy-public` is IPv4-only by default (`docker-compose.yml:144-152`);
the repository documents that an IPv6 connection to a published port then reaches Traefik
from the Docker gateway address (`core/traefik/README.md:97`,
`docs/ipv6-dual-stack.md`, "The three traffic paths"). Cloudflare connects to an origin
over IPv6 whenever the origin record is an `AAAA`. In that case, in `cloudflare` mode:
the gateway is not in the trusted ranges, so the entrypoint deletes Cloudflare's headers;
`ClientHost` and `X-Real-Ip` become the gateway; every rate limit shares one bucket; and
`acc-local` / `acc-private` **admit** the gateway, which lies in `172.16.0.0/12`
(audit RP4, issue #129) — so the README's "a request to such a host through Cloudflare
… is refused" (`README.md:636`) is false on that path, and a public visitor reaches a
LAN-only route. The bouncer, under the current rendering, still reads
`CF-Connecting-IP` because Traefik did not delete it (F1). "Behind Cloudflare" does not
mention IPv6 at all; D3's condition is "proof … over IPv4 and IPv6".

**Proposed correction.** Under "What Cloudflare has to be set to": either `proxy-public`
dual-stack (the overlay, `README.md:101-124`) or origin records `A`-only, stated as a
requirement with the consequence above; and the same sentence in the standard's IPv6 note
(`traefik-security.md:99`). The host proof for IPv6 stays open (section 4).

### F6 · should-fix — the drift guard is keyed on one value and goes blind when the file's first entry changes; two silent paths beside it

**Evidence.** `render.sh:98` takes the first range of the file and `:125` refuses only if
that exact quoted string is in `config/traefik.yml`; `validate.sh:150,300` uses the
same key. Exercised in a scratch copy:

| Case | Result |
|---|---|
| first range removed from the file, config stale, switch absent | refused — the new first range is also in the old list |
| a range inserted at the top of the file, config stale, switch absent | **rendered**: `trustedIPs` became `[]` without a word; `validate.sh` afterwards fails only through the `crowdsec.yml` check (`:319-321`), with the wrong message "`TRAEFIK_FORWARDED_PROXY=none` but …", and only when the bouncer is enabled |
| `TRAEFIK_FORWARDED_PROXY=` (empty) in `.env` over a trusting config | rendered as `none`, silently (`:116-117`: set-but-empty counts as declared) |
| variable exported in the caller's environment, absent from `.env` | rendered as `none`, silently (`.env` is sourced into the environment, `:15-17`) |
| `CLOUDFLARE` | accepted as `cloudflare` (normalisation works) |

Cloudflare adds ranges rarely, but the weekly workflow exists because it happens, and the
guard protects precisely the host that has not rendered for a long time. The two silent
paths are shared with the other switches and are noted for consistency.

**Proposed correction.** Key the guard and the agreement check on the shape, not a value:
the line after `trustedIPs: &cloudflareTrustedIPs` starts with `- "` (trusting) or is
`[]` (not). In `cloudflare` mode let `validate.sh` compare the rendered list with the
file (count or set equality) and say "the ranges file changed — run render.sh" when they
differ; the file exists so that a script can do this (`render.sh:73-76`). Treat an empty
value as undeclared, for all three switches, in one follow-up.

### F7 · should-fix — the audit and the decision record still describe the mechanism the branch found impossible

**Evidence.** `docs/audits/core-v1-readiness-2026-10-15.md:390-391` (Phase 3 paragraph)
and `:433` (D3 row), and `.ai/decisions.md:74-80`, say "the limits use
`requestHeaderName: X-Real-Ip` with a Cloudflare Transform Rule". The branch records in
`docs/maintenance-log.md:90` that Transform Rules cannot set `X-Real-Ip` (confirmed
against Cloudflare's documentation, section 2) and ships the limits on the connecting
address. The diff updates RP1 and RP2 (`:130-131`) but not these three places. All three
also cite `docs/traefik-middleware-proposal.md`, "verified against the Traefik source",
which is not in the tree.

**Proposed correction.** A dated addendum under D3 in `decisions.md` (the mechanism as
shipped, why the Transform Rule was dropped, where the per-client limit now lives) and
the same two sentences in the audit's D3 row and Phase 3 paragraph; replace the pointer
to the absent proposal document with the branch's own evidence or drop it.

### F8 · note — `ClientHost` is the whole `X-Forwarded-For` value, not the client

`README.md:634` says `ClientHost` is "the client Cloudflare appends". Traefik sets
`ClientHost` to the entire header string whenever the header exists
(`logger.go:273-277`); behind Cloudflare that is `client` or `forged, client`. Detection
is unaffected because the hub parser takes the last element (section 2), but any other
consumer of the access log — `grep`, a dashboard, the "read your address out of the
access log" step in `README.md:566-575` — sees the list. The audit's Phase 3 criterion
"`ClientHost` equal to the address the bouncer compared" (`:393-394`) should read "the
last element of `ClientHost`". Suggested wording for the table cell: "`ClientHost` =
the `X-Forwarded-For` value Cloudflare sent, whose last element is the client; the
CrowdSec parser uses that element".

### F9 · note — Pseudo IPv4 wording

`README.md:650-651`: "With it on, Cloudflare replaces `CF-Connecting-IP` and
`X-Forwarded-For`". Only the *Overwrite headers* setting does; *Add header* adds
`Cf-Pseudo-IPv4` and leaves both alone (Cloudflare, Pseudo IPv4 reference). "Off" is
still the right instruction; the sentence should name the setting it describes.

### F10 · note — in `none` mode three address headers pass through unsanitised

Traefik deletes `X-Forwarded-*` and `X-Real-Ip` only (`forwarded_header.go:39-48`).
`CF-Connecting-IP`, `True-Client-IP` and `Forwarded` (RFC 7239) reach the application
from any client in both modes. Nothing in the blueprint reads them in `none` mode, and
Vaultwarden is pointed at `CF-Connecting-IP` only for `cloudflare` mode
(`apps/vaultwarden/docker-compose.yml:120-125`, holds). Worth one sentence in the
standard's "Trusted Proxy Headers": an application configured to read one of these is on
its own in `none` mode. Optional hardening for `none` mode: a `headers` middleware with
`customRequestHeaders` setting those three to empty, on every chain — not possible per
sender in `cloudflare` mode, which is F1's point.

### F11 · note — the `config/host/` exemption is by path, not by requirement, and the standard does not know it

`host-files.sh:84-89` exempts any `config/host/` source from the existence check,
`required` or not. A `required` entry of that kind would pass `read_manifest`, be skipped
by `render`, and always report `not rendered` in `check` — so a missing required file is
not hidden, but the manifest check that `docs/standards/host-files.md` promises ("a
manifest that names a missing source … fails there", step 4) no longer holds for these
sources: a typo in the nft path would never be caught, by CI or on a host.
`docs/standards/host-files.md` is not touched by the diff; the convention (a source the
stack renders itself, under `config/host/`, present only in one mode) needs a sentence
in "The manifest" and a state in the table (F2). Consider restricting the exemption to
`optional` entries, or to names a stack declares.

### F12 · note — what the tests prove and what they do not

The eight tests cover the shape of D3's conditions: both modes on both entrypoints and
both middlewares, the nft defines, no `ipStrategy` / `sourceCriterion`, the refused value,
the guard (`test_rendered_trust_with_switch_absent_is_refused` fails if `render.sh:125`
is removed, and its `validate` half if `validate.sh:311-318` is), both stale directions
(`test_validate_catches_a_stale_render_in_both_directions` fails if `:301-305` or
`:311-318` is removed), and the bouncer switch off. Not covered: the `crowdsec.yml`
agreement checks alone (`:306-309`, `:319-321` — the first error wins, so removing them
changes nothing a test sees); the nft file's absence in `none` mode in `validate.sh` (not
checked at all; `render.sh:252` removes it and the test asserts the removal); F2; the
empty and upper-case values; and, by nature, the header semantics of F1 and F8, which
need a request. The changed case in `test_traefik_entrypoint.py:100-112` is correct:
the list equals the file only in `cloudflare` mode.

### F13 · note — the rate-limit alternative the README rules out is not ruled out by the source

`README.md:640-644` says a header-reading strategy leaves a direct client "with no
address at all". For `rateLimit`, `sourceCriterion.ipStrategy.excludedIPs: <the
ranges>` would give per-client buckets behind Cloudflare (walk from the right past the
ranges, `strategy.go:74-92`) and one shared bucket for every direct client (empty source,
no error, `extractor.go:46-48`). In `cloudflare` mode direct clients are LAN and VPN
only, so that shared bucket may be the better trade than per-edge buckets for the whole
Internet. Not a defect; a measurement for D2, which the audit already schedules after
Phase 3.

### F14 · note — clients whose address lies inside Cloudflare's ranges

WARP users and Cloudflare's own egress carry a source address inside the published
ranges. The plugin skips every header entry in the trusted pool and falls back to the
connecting address (`ip.go:105-116`, `:124`) — the edge — so a decision against such a
client is not enforced by the bouncer, and a decision the engine derives from the log
(the parser does not skip trusted ranges) names an address the host-firewall bouncer
would then drop for every visitor behind it. One sentence in the CrowdSec README's
"Behind Cloudflare" pointer; the firewall bouncer's allowlist is the mitigation.

### F15 · note — `render.sh` / `validate.sh` mechanics

Atomic `place` is used for the nft file (`render.sh:249`); `rm -f` for the other mode
(`:252`); every `grep` inside `if`/`&&` is safe under `set -e`; `head -1` after `grep`
under `pipefail` cannot SIGPIPE on a 36-line file. `validate.sh` does not check that the
nft file is absent in `none` mode (asymmetry with `:310`), nor that the rendered list
equals the file (F6). The rendered `none` list `[]` under an anchor is valid YAML. The
`.env.example` sentence "the CrowdSec bouncer compares the client Cloudflare names in
CF-Connecting-IP" (`:115-116`) carries F1.

## 4. Documentation claims, one line each

| Claim | Where | Verdict |
|---|---|---|
| `none` deletes every client's `X-Forwarded-*` and `X-Real-Ip`, connection is the client | README 625-627, standard 78, CHANGELOG 13 | holds (`forwarded_header.go:39-48,117-119`) |
| `cloudflare` trusts the file's ranges on both entrypoints | README 633 | holds (rendered, tested) |
| `ClientHost` = the client Cloudflare appends, also after a forged header | README 634 | holds for CrowdSec detection (parser `[-1]`); the field itself is the whole list — F8 |
| bouncer compares `CF-Connecting-IP` only from Cloudflare addresses | README 635, standard 79, crowdsec README 112-117, CHANGELOG 13, template 32-37 | **does not hold** — F1 |
| closed policies refuse a proxied request | README 636, standard 81-82 | holds over IPv4; false over IPv6 on IPv4-only `proxy-public` — F5 |
| rate limits per edge at origin; 1 rule Free, 2 Pro at the edge | README 637 | holds |
| application sees `X-Forwarded-For` = `client, edge`, `X-Real-Ip` = edge | README 638, standard 86-87 | holds (`x-real-ip` stripped by Cloudflare, set by Traefik from the connection, ReverseProxy appends the edge) |
| no single definition reads header for one sender and connection for another | README 640-644, CHANGELOG 13 | holds for `ipAllowList`; for `rateLimit` the alternative is a shared bucket — F13 |
| Pseudo IPv4 on replaces both headers | README 650-651 | imprecise — F9 |
| Transform Rules cannot set `X-Real-Ip` | CHANGELOG 13, maintenance-log 90 | holds |
| origin firewall "from the proxy and from nowhere else" | README 658-673, nft comment | incomplete — F3; trust bound — F4 |
| Vaultwarden `IP_HEADER` reads the edge; set `CF-Connecting-IP` | vaultwarden compose 120-125, README 677-679 | holds; the header is unsanitised for direct clients (F1/F10), so it depends on F3 |
| n8n and HeyForm need two hops | README 680-681 | holds (`N8N_PROXY_HOPS=1`, `TRUST_PROXY=1` today; two hops at the application behind Cloudflare) |
| migration guard refuses an undeclared trusting config | README 685-691, CHANGELOG 40 | holds for today's file; blind after an insertion at the top — F6 |
| "Eight tests" | CHANGELOG 13 | holds |
| D3 mechanism in audit and decisions | audit 390-391, 433; decisions 74-80 | stale — F7 |

## 5. Open — needs a host, kept open, never to be marked passed here

1. The address at every hop through Cloudflare, IPv4 and IPv6: `whoami` behind
   `acc-public`, the access log's `ClientHost` (last element), the bouncer's compared
   address (a manual decision answered `403`), Vaultwarden's lockout address.
2. A closed route refusing a proxied request over IPv4 **and** over IPv6, with
   `proxy-public` dual-stack and with it IPv4-only (F5).
3. Forged `CF-Connecting-IP` and `X-Forwarded-For` from a direct client in both modes,
   with the origin firewall of F3 in place and absent (F1).
4. A Worker subrequest and a second zone pointing at the origin (F4) — what arrives, what
   the bouncer compares, whether `Host` can be made to match a router.
5. The forward-hook rule from F3 on a running Docker host: Traefik unreachable from a
   non-Cloudflare address, reachable from the VPN, the CrowdSec tables intact after the
   reload.
6. `scripts/host-files.sh check` and `overview.sh --host` on a `none`-mode host after F2.
7. The parser version on the host carries the `[-1]` split (hub `master` was read; the
   installed collection is whatever `cscli hub update` last pulled).

Nothing in this review was run against a host, committed or pushed.

## 6. Corrections — added by the maintainer's session after the review, 2026-10-17

The review above is kept as written. Every finding below names the commit on
`feature/cloudflare-mode` that answers it, or why it is left; the host checks of
section 5 stay open and are listed in `core/traefik/README.md`, "Behind
Cloudflare", "Not verified on a host". A second independent review of the
security-relevant changes is due before merge.

| Finding | Status | Where |
|---|---|---|
| F1 | corrected — `forwardedHeadersCustomName` removed; the middlewares keep `X-Forwarded-For` with `forwardedHeadersTrustedIPs`; `validate.sh` refuses a rendered middleware naming a custom header; the seven text places say what the plugin does and what the entrypoint does; test `test_no_mode_names_a_custom_header_for_the_bouncer` and the assertion in `test_cloudflare_trusts_the_file_everywhere` | `2b1cda2` |
| F2 | corrected — `check` reports an optional `config/host/` source the stack did not render as `not produced`, not counted; `install-commands` and `diff` say the same; `read_manifest` exempts only `optional` sources under `config/host/`, a `required` one must exist (F11); four tests in `test_host_files.py`; the standard carries the state and the convention | `fdcbab1` |
| F3 | corrected — "Protect the origin" places the rule on the forward hook, shows one `inet` table with the include and the drop for TCP 80/443 and UDP 443 on the public interface, loaded by `nft -f`, never a ruleset flush, with the boot include; cross-reference to `firewall-bouncer.md`; the rule is marked as not run on a host. A named set instead of defines is left for the host proof | `a2a2432` |
| F4 | corrected — "What the mode cannot promise": Workers, other zones, WARP clients, Authenticated Origin Pulls and Tunnel not shipped; the edge rule called advisory against another zone | `a2a2432` |
| F5 | corrected — "IPv6 between Cloudflare and the origin": `A`-only records or a dual-stack `proxy-public`, with the consequence on the closed policies; the IPv6 section and the standard's IPv6 note say the same; not verified on a host | `a2a2432` |
| F6 | corrected — guard and agreement check keyed on the shape of the rendered list; an empty value counts as not set (this switch; the other two switches are a follow-up); `validate.sh` compares the rendered list with the ranges file and refuses a firewall file in `none` mode; tests for the inserted range, the empty value, the changed file and the stray file. The exported-variable path is shared with every switch and stays as noted | `2b1cda2` |
| F7 | corrected — the audit's D3 row and Phase 3 paragraph, and a dated addendum under D3 in `.ai/decisions.md`; the proposal document is named with its unmerged branch | `a2a2432` |
| F8 | corrected — README table and the audit's Phase 3 criterion say "last element of `ClientHost`" | `a2a2432` |
| F9 | corrected — the Pseudo IPv4 sentence names *Overwrite headers* and *Add header* | `a2a2432` |
| F10 | corrected — one paragraph in the standard: an application reading `CF-Connecting-IP`, `True-Client-IP` or `Forwarded` is on its own in both modes; the `headers` middleware hardening is left open | `a2a2432` |
| F11 | corrected with F2 | `fdcbab1` |
| F12 | the uncovered checks named there are now covered by the F6 tests where they concern the switch; the header semantics stay a host matter | `2b1cda2` |
| F13 | recorded in the README as a measurement for D2, not settled | `a2a2432` |
| F14 | recorded in the README ("What the mode cannot promise"), the CrowdSec README and the template comment | `a2a2432` |
| F15 | the asymmetry is closed (F6); `.env.example` corrected with F1 | `2b1cda2` |
