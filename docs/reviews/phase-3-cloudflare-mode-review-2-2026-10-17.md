# Phase 3 review 2 — the correction commits of `feature/cloudflare-mode`

**Date:** 2026-10-17 · **Scope:** the five commits after the first cut, `2b1cda2`,
`fdcbab1`, `a2a2432`, `90e790f`, `fbdff64` (`origin/dev..HEAD` minus `2a69603` and
`6864c45`, which the first review covered) · **Kind:** second independent technical
review, read-only. Nothing in this document was applied; every correction is a
proposal. No host was touched, nothing was committed or pushed, no file in the
repository was changed. Host verifications stay open and are never marked passed here.

## 1. Scope and method

The first review (`docs/reviews/phase-3-cloudflare-mode-review-2026-10-17.md`, sections
1–5) is taken as read. Its section 6 and 6.1 are the claims under review here: for
every row, does the named commit do what the row says, and is the three-way split
(corrected / held by a test / open on a host) accurate. The order of work: the
security-relevant commit `2b1cda2` against the Traefik and plugin sources;
the drift guard and `validate.sh`; `fdcbab1` and the tests; the documentation commit
`a2a2432` against nftables, Docker and Cloudflare's documentation; the review document
itself.

| Source | Version | What was read |
|---|---|---|
| Traefik | `v3.7.0` and `v3.7.15` — the blueprint pins the floating tag `traefik:v3.7` (`.env.example:20`); `v3.7.15` was the newest `v3.7.x` release on 2026-10-17 | `pkg/middlewares/forwardedheaders/forwarded_header.go` (identical at both tags save one comment), `pkg/proxy/httputil/proxy.go`, `pkg/server/server_entrypoint_tcp.go`, `pkg/server/server_entrypoint_tcp_http3.go`, `pkg/config/static/entrypoints.go` |
| Bouncer plugin | `v1.7.1` (`render.sh:44`) | `pkg/ip/ip.go`, `bouncer.go`, `pkg/configuration/configuration.go`, `README.md` |
| Cloudflare documentation | as served on 2026-10-17 (`index.md` of each page) | HTTP request headers; IPv6 compatibility; HTTP/3; Pseudo IPv4; Cloudflare IP addresses; Cloudflare One egress policies |
| nftables | 1.1.3 (Alpine 3.22 in a throwaway local container with `NET_ADMIN`, no host) | `nft -c -f` and `nft -f` of the README's table together with the rendered define file |
| This repository | branch tip `fbdff64`; `origin/dev`; tags `v0.9.0`–`v0.9.4` | the five diffs, `render.sh`, `validate.sh`, `scripts/host-files.sh`, the templates, `core/traefik/README.md`, `docs/standards/traefik-security.md`, `core/traefik/docs/ipv6-dual-stack.md`, `core/crowdsec/docs/firewall-bouncer.md`, the tests |

Executed, in a scratch directory outside the repository, never on a host:

- `python3 -m unittest discover -s scripts/ci -p 'test_traefik_*.py'` with Python
  3.12.15, PyYAML 6.0.3 and GNU envsubst: **55 tests, OK**. `test_host_files.py`:
  **18 tests, OK**. `check-links.py`: 376 files, 0 broken. `check-prose.py`: 0 blocking.
  (A first run under the machine's Python 3.9 failed on the missing PyYAML; that was
  the interpreter, not the code, and is recorded only so the number of runs is honest.)
- Both modes rendered with the bouncer on; `config/traefik.yml`,
  `config/dynamic/crowdsec.yml` and `config/host/cloudflare-ranges.nft` read raw;
  `validate.sh` run on both: `OK`, rc 0.
- The shape detection of `render.sh` / `validate.sh` run against: the two renders, the
  `origin/dev` template rendered, and the template at tag `v0.9.4` rendered
  (finding 1).
- The migration guard reproduced end to end against a `v0.9.4`-shaped configuration
  (finding 1).
- The README's nftables table parsed, applied, re-applied over itself and loaded in the
  boot shape (`flush ruleset` + `include`) in the container: rc 0 each time.

Line numbers refer to the branch tip `fbdff64`; upstream line numbers to the files as
fetched on 2026-10-17.

## 2. What was verified and holds

**Commit `2b1cda2`, the bouncer's address (F1).** The reasoning in the commit message,
the template comment (`crowdsec.yml.tmpl:32-46`) and the standard
(`traefik-security.md:81-92`) holds against both sources:

- Traefik's entrypoint handler is built in `server_entrypoint_tcp.go:633-646`:
  `forwardedheaders.NewXForwarded` wraps the request decorator and the handler
  switcher, so every router, middleware and plugin sits *inside* it. The HTTP/3 server
  reuses the HTTPS server's handler (`server_entrypoint_tcp_http3.go:63-66`), so a
  direct HTTP/3 client on UDP 443 is sanitised the same way.
- `ServeHTTP` (`forwarded_header.go:115-129`) deletes the managed set for any sender
  that is not trusted; with an empty `trustedIPs` list no checker is built (`:83-91`)
  and `isTrustedIP` is false for everyone (`:131-136`). The set (`XHeadersSet`,
  `:35-47`, with the underscore aliases through `isManagedXHeader`, `:53-66`) is the
  ten `X-Forwarded-*` names and `X-Real-Ip` — not `CF-Connecting-IP`,
  `True-Client-IP` or `Forwarded`.
- `rewrite` (`:138-184`) sets `X-Real-Ip` from the connection only when it is empty
  afterwards (`:142-144`) and *joins* the surviving `X-Forwarded-For` values
  (`:177-179`); it never appends the connecting address. The append happens in the
  reverse proxy's rewrite on the outgoing request (`proxy.go:67-82`), after the
  middleware chain, and `notAppendXForwardedFor` governs only that (`:124-126`,
  `proxy.go:39-50`). So the plugin sees the header exactly as the trusted sender sent
  it, and nothing at all from an untrusted one.
- The plugin reads one header, `forwardedHeadersCustomName`, default
  `X-Forwarded-For` (`configuration.go:171`), from any request
  (`bouncer.go:341`), walks it from the right and returns the first entry outside
  `forwardedHeadersTrustedIPs` (`ip.go:96-116`), falling back to the connection only
  when nothing is left (`:119-129`). `clientTrustedIPs` (default empty, `:173`) is
  consulted on the *compared* address (`bouncer.go:347-358`) and is not rendered (the
  test asserts it). The AppSec path uses the same address (`:488-492`). No other option
  reads a header.

Hence, with the rendered `forwardedHeadersTrustedIPs` = the 22 ranges and the default
header:

| Request | Header at the plugin | Compared address |
|---|---|---|
| direct client, forged `X-Forwarded-For` and/or `CF-Connecting-IP` | `X-Forwarded-For` deleted at the entrypoint; `CF-Connecting-IP` present but never read | the connection |
| from a Cloudflare range, client sent nothing | `client` (Cloudflare's header reference: identical to `CF-Connecting-IP`) | `client` |
| from a Cloudflare range, client sent a forged first entry | `forged, client` — Cloudflare appends behind it | `client` (rightmost entry outside the ranges) |
| from a Cloudflare range, two proxies before Cloudflare | `client, proxyA, proxyB` (Cloudflare's own example) | `proxyB`, the address that connected to Cloudflare — the one Cloudflare's edge rules saw too |
| sender inside the ranges, nothing sent | `edge-side address` only, skipped | the connection — the edge |
| sender inside the ranges, forged first entry `X` | `X, edge-side address` | `X` if it parses as an address; if it does not, `Contains` errors, the plugin treats it as not trusted, then the `clientTrustedIPs` check errors on it and the request is answered with a ban (`bouncer.go:347-351`, reason TECH) — fail closed, not a bypass |

The last two rows are the WARP residual the texts describe; whether WARP clients are
such senders is finding 3.

**The rendered files.** `none`: `trustedIPs: &cloudflareTrustedIPs` followed by `[]`
on both entrypoints (the anchor is reused), no `forwardedHeaders*` key in either
middleware, no nft file. `cloudflare`: the 22 entries on both entrypoints, both
middlewares carry `forwardedHeadersTrustedIPs` with the same 22 entries at ten and
twelve spaces, no `forwardedHeadersCustomName`, no `clientTrustedIPs`; the nft file
carries two `define`s with 15 and 7 members. `validate.sh`: `OK` in both modes.

**The guard's mechanics (F6, F15).** Both awk functions exit 0/1 only through their
own `exit`, so `set -e` and `pipefail` cannot abort `render.sh:142`,
`validate.sh:315` (an `&&` list) or `validate.sh:326` (a command substitution);
`[ -n … ] && proxy_declared=yes` is safe under `set -e` for the same reason. The alias
line `trustedIPs: *cloudflareTrustedIPs` on the second entrypoint is excluded by
`[^*]*$`, and awk exits at the first list anyway. There is no other `trustedIPs` key in
the template (no `proxyProtocol`). The list comparison (`validate.sh:326`) strips
comments, whitespace and order on the file side and quotes on the rendered side; a
range with a trailing comment, a duplicate and a reordered file all compare as the
renderer would write them. The empty value is treated as undeclared
(`render.sh:132-133`, `validate.sh:167-168`), and the test holds it. The exported
environment path (a value exported by the caller, absent from `.env`) still renders
silently; section 6 says so and that is accurate.

**Commit `fdcbab1` (F2, F11).** `read_manifest` exempts only an `optional` source
under `config/host/` from existing (`host-files.sh:84-92`); a `required` one anywhere
and an `optional` one elsewhere still fail there, so a wrong path is caught in CI.
`check_stack` reports the absent optional file as `not produced`, not counted, and
names an installed copy (`:197-206`); `diff_file` (`:290-293`) and
`install_commands` (`:312-315`) say the same. The standard carries the convention
(`host-files.md:53-58`) and the state (`:78`). The four tests cover each path. A
missing *required* file goes unnoticed nowhere.

**Commit `a2a2432`, what the documents claim and the sources support.**

| Claim | Where | Source | Verdict |
|---|---|---|---|
| a Worker towards a non-Cloudflare-customer origin controls `CF-Connecting-IP` and `x-real-ip`; AOP or Tunnel bind trust to the zone | README 726-734 | header reference, "CF-Connecting-IP in Worker subrequests" (lines 39-45) | holds, nearly verbatim |
| `x-real-ip` stripped when no Worker is involved | README 638, standard 86-87 | same page, line 47 | holds |
| Cloudflare appends the connecting address behind an existing `X-Forwarded-For` | README 634 | same page, lines 81-85 | holds |
| Pseudo IPv4: *Overwrite headers* replaces both headers, *Add header* adds `Cf-Pseudo-IPv4` | README 653-656 | Pseudo IPv4 page, lines 47-48 | holds |
| Cloudflare does not use UDP 443 towards an origin | README 709 | HTTP/3 page: "HTTP/3 connection to the origin is not yet supported" | holds today; Cloudflare's own word is "yet" |
| `172.64.0.0/13` is Cloudflare egress space inside the published list | README 735-736 ("Cloudflare's egress") | IP addresses page, line 94 | holds |
| WARP clients arrive from inside the published ranges | README 735, CrowdSec README 122, template 44-46 | Cloudflare One egress page | **not supported** — finding 3 |
| Cloudflare connects over IPv6 "whenever the record it resolves is an `AAAA`" | README 665-666 | IPv6 compatibility page | imprecise — finding 4 |
| published ports never traverse `input`; the rule belongs on `forward` | README 693-698 | `firewall-bouncer.md:123-146`, verified on a host there | holds for the DNAT path — but not for the docker-proxy path, finding 2 |
| the table is valid nftables; `destroy` needs 1.0.8; boot through an `include` from `/etc/nftables.conf` works | README 700-723 | `nft -c`/`nft -f` 1.1.3, boot shape loaded | holds (section 1); the semantics next to Docker's chains in finding 5 |
| the D3 record and the audit rows describe the mechanism as shipped and name the unmerged proposal branch | `.ai/decisions.md` addendum, audit 390-391 and 433 | the diff | holds; the addendum is dated and names the review |

## 3. Findings

Severity as in the first review: **blocker** — must change before merge; **should-fix**
— before the mode is recommended to anyone; **note** — for the record.

### 1 · blocker — the shape-keyed migration guard is blind to every configuration rendered from a release

**Claim under review.** Section 6, F6: "guard and agreement check keyed on the shape of
the rendered list"; README 754-760: "The refusal is keyed on the shape of the rendered
list, so it holds after the ranges file changes."

**Evidence.** `rendered_trusts_ranges` (`render.sh:103-108`, `validate.sh:155-160`)
finds the `trustedIPs:` line, skips blank lines, and lets the *first other line* decide:
a line beginning with `-` and a space means trusting, anything else means trusting nobody. The template that every
release shipped — the comment line `# Cloudflare IPv4` was introduced in `386e8bf`
(2026-06-19) and removed in `8fc8110` (2026-10-16), so tags `v0.9.0` through `v0.9.4`
all carry it — renders this:

```yaml
      trustedIPs: &cloudflareTrustedIPs
        # Cloudflare IPv4
        - "173.245.48.0/20"
```

The first non-blank line is a comment, so the function answers "trusting nobody".
Reproduced in a scratch directory: `config/traefik.yml` rendered from the `v0.9.4`
template, `config/dynamic/crowdsec.yml` as `v0.9.4` wrote it (no
`forwardedHeadersTrustedIPs`; the key did not exist before this branch), `.env`
without `TRAEFIK_FORWARDED_PROXY`:

```text
validate.sh  -> OK.                                                 rc 0
render.sh    -> " -> trusted proxy ranges: none (TRAEFIK_FORWARDED_PROXY=none)"   rc 0
             -> trustedIPs became [] on both entrypoints, without a word
```

The first cut's key — `grep -F '"173.245.48.0/20"'` — matches that file (1 hit). So
`2b1cda2` replaced a guard that was blind to a *future* insertion at the top of the
ranges file (F6) by one that is blind to every *past* rendering: the installations the
guard exists for (`render.sh:127-130`; CHANGELOG, the migration target). An
installation behind Cloudflare that pulls this branch and renders without first
editing `.env` loses the trust silently and CrowdSec bans the edge — the exact
outcome the guard describes. The test
`test_rendered_trust_with_switch_absent_is_refused` renders the trusting configuration
with the branch's own template, which has no comment line, so it cannot see this.

**Proposed correction.** In both awk functions skip comment lines the way blank lines
are skipped — `if ($0 ~ /^[[:space:]]*(#|$)/) next` in `rendered_trusts_ranges`, and
the same line in `rendered_ranges` so a comment between the two families (`# Cloudflare
IPv6`, which `v0.9.4` also has) does not end the list early. Checked here against all
five shapes: `none` → not trusting, `cloudflare` → trusting, `origin/dev` rendered →
trusting, `v0.9.4` rendered → trusting, the guard reproduction above → refused. Add a
test whose fixture is the released shape: render in `cloudflare` mode, insert
`# Cloudflare IPv4` (indented eight spaces) after the `trustedIPs:` line and `# Cloudflare
IPv6` (same indent) before the first IPv6 entry, drop the switch from `.env`, expect `render.sh` to
refuse with "TRAEFIK_FORWARDED_PROXY is not" and the list unchanged, and expect
`validate.sh` to refuse with "not set in .env". Until then section 6's F6 row and the
README sentence quoted above do not hold.

### 2 · should-fix — the origin-firewall table covers the forward path only; on the default network shape a direct IPv6 client reaches Traefik on the input path, as the Docker gateway, and `acc-local` admits it

**Claims under review.** README 677-724 ("Protect the origin": one table on the
forward hook; "VPN and LAN clients arrive on other interfaces and are not touched");
README 665-676 ("IPv6 between Cloudflare and the origin": `proxy-public` dual-stack
*or* `A` records only); section 6.1, F3 and F5 "corrected".

**Evidence.** The repository's own IPv6 document describes the path a published port
takes when the request's family is one the container network does not carry
(`ipv6-dual-stack.md:100-111`): the daemon listens on `[::]:80` and `[::]:443`
regardless of any network's setting; with the default `userland-proxy: true` the
`docker-proxy` process terminates the IPv6 connection on the host and opens a new IPv4
connection to the container, sourced from the bridge gateway. That connection is
delivered to the host, not forwarded: it traverses `input`, and the forward-hook table
never sees it. `firewall-bouncer.md:123-146` measured the DNAT path and is right about
it; it says nothing about the relay path. Consequences on a host with a global IPv6
address and an IPv4-only `proxy-public` — the default (`docker-compose.yml:144-152`)
and one of the two shapes the README allows — with the table installed exactly as
written: a direct IPv6 client to port 443 passes the firewall (no rule on its path),
bypasses Cloudflare, and arrives at Traefik as `172.x.x.x`, which is inside
`172.16.0.0/12`: `acc-local` and `acc-private` admit it (the README's own IPv6
paragraph says so for Cloudflare's edge; it is equally true for anyone), the bouncer
compares the gateway, every rate limit shares one bucket, and CrowdSec can neither
detect (the gateway is whitelisted, `ipv6-dual-stack.md:570-574`) nor ban it. The `A`-only
alternative bounds Cloudflare's path only; it does nothing for a direct client. The
`UDP 443` drop has the same gap on that path.

**Proposed correction.** In "Protect the origin", one paragraph: the table filters the
DNAT path; a published port reached over a family the container network does not
carry is relayed by `docker-proxy` and arrives on the host's input path, where the
table does nothing and the source Traefik sees is the gateway. Then one of: (a) the
dual-stack overlay with `userland-proxy: false` and `ip6tables: true`
(`ipv6-dual-stack.md`, the documented fix), after which the forward table covers both
families; or (b) a second chain in the same table on the `input` hook, same priority,
admitting TCP 80/443 on the public interface from `$cloudflare_v4`/`$cloudflare_v6` and
dropping the rest (on that path `ip6 saddr` is the real client, the relay has not run
yet) — a version of that chain parsed with `nft -c` here, rc 0. Say which shape the
`A`-only option needs ((b), or no global IPv6 on the host), and add to the host list: a
direct IPv6 client to the published port on an IPv4-only `proxy-public` with the table
installed. Until then F3 and F5 are documented, not corrected, and 6.1 should say so.

### 3 · should-fix — the WARP sentence promises more than Cloudflare's documentation supports

**Claims under review.** README 735-739: "A client whose own address lies inside the
ranges — Cloudflare WARP, Cloudflare's egress — is compared by the bouncer as the edge
… and could place an entry before it"; CrowdSec README 122; template
`crowdsec.yml.tmpl:44-46`; the first review's F14 made the same assumption.

**Evidence.** The plugin mechanism (skip every trusted entry, fall back to the
connection) holds from `ip.go:105-116`. Whether a WARP client is such a sender does
not: Cloudflare's egress-policies page states "Cloudflare does not publish Cloudflare
One Client egress IP ranges. Cloudflare One Client egress IPs are not listed at
Cloudflare's IP Ranges." Consumer WARP egress is not documented either way. What *is*
documented inside the list is `172.64.0.0/13` as public egress space (IP addresses
page, line 94). So the sentence names a residual for a client population the sources
do not place inside the ranges — and omits the other direction: a WARP client whose
egress address is *outside* the ranges is compared as that shared address, and a
decision against it is enforced against everyone behind the same egress.

**Proposed correction.** Reword in the three places: "a sender whose own address lies
inside the ranges — Cloudflare's own egress space `172.64.0.0/13` is one; Cloudflare
states that its Zero Trust client egress addresses are not in the published list, and
does not document consumer WARP either way — is compared as the edge and can place an
entry before it; a WARP client outside the ranges is compared as its shared egress
address, and a decision against it hits every client behind it." Add "the address a
WARP client arrives from" to the host list. Keep F14's record as an assumption, not a
fact.

### 4 · note — "whenever the record it resolves is an `AAAA`" is a preference in Cloudflare's words, not a rule

README 665-666 and the standard's IPv6 note. Cloudflare's IPv6 compatibility page: "For
proxied DNS records that have both an IPv6 and IPv4 origin address, Cloudflare will
prefer the IPv4 address when connecting to your origin server." So the connection is
IPv6 when only an `AAAA` exists, and *may* be IPv6 when both exist — a preference, not
a guarantee. The README's requirement (`A` only, or dual-stack) is the conservative
reading and stays right; the sentence should say "when only an `AAAA` exists, and
possibly when both do — Cloudflare documents a preference for IPv4, not a guarantee".

### 5 · note — what the table does next to Docker's chains, and the port it matches

The table parses and applies (section 1). Its semantics, reasoned from the nftables
model rather than measured: `priority filter - 20` places the chain before CrowdSec's
(`filter - 10`, `firewall-bouncer.md:227`) and before Docker's `FORWARD` (`filter`);
`drop` is final across base chains, `accept` ends this chain only and the packet still
traverses CrowdSec's and Docker's, so a Cloudflare address under a CrowdSec decision is
still dropped and Docker's own isolation rules still apply; `policy accept` leaves every
non-matching packet (other interfaces, other ports) to those chains. `ct original ip
saddr` equals `ip saddr` on this path — DNAT rewrites only the destination — and both
work; `ct original` is defensible, not necessary. One sentence the README lacks: on the
forward hook the destination port is the *container's* (80 and 443 after DNAT), so the
rule is right whatever `TRAEFIK_HTTP_PORT`/`TRAEFIK_HTTPS_PORT` publish, and "the
published web ports" should read "the container ports after DNAT". The boot advice
holds: Debian's `nftables.service` is ordered before `network-pre.target`, Docker after
`network-online.target`; `destroy table` on an absent table is a no-op, and `nft -f`
applies the file as one transaction, so the reload leaves no window without the table.

### 6 · note — `host-files.sh check` cannot tell "not produced because the mode does not need it" from "not produced because `render.sh` has not run since the switch was set"

`check_stack` (`host-files.sh:197-206`) has no notion of the mode: in `cloudflare`
mode before a render, the entry is reported `not produced … optional` and `check` exits
0. `validate.sh:335` catches that state ("Missing config/host/cloudflare-ranges.nft"),
so nothing is hidden from an operator who runs both; the standard could say in the
`not produced` row that `validate.sh` is the check that knows the mode.

### 7 · note — section 6's F12 row overstates what the new tests cover

Of the gaps F12 listed, the nft file's absence in `none` mode and the empty value are
now covered. Still uncovered: the two `crowdsec.yml` agreement checks on their own
(`validate.sh:331-334`, `:344-346` — the first error still wins, so removing them
changes nothing a test sees), the upper-case value, and now the released list shape
(finding 1). The header semantics stay a host matter, as the row says.

## 4. Verdict per commit

| Commit | Verdict | Why |
|---|---|---|
| `2b1cda2` — F1 part (custom header removed, trusted list kept, `validate.sh` refuses a custom header, texts) | **holds** | derived from both sources at the pinned versions (section 2); the rendered files and the tests say what the row says; the security effect is still not measured on a host |
| `2b1cda2` — F6 part (shape-keyed guard, empty value, list comparison, stray nft file) | **does not hold** | the shape detection is blind to every released rendering — finding 1; the empty value, the list comparison and the stray-file refusal hold |
| `fdcbab1` — F2, F11 | **holds** | section 2; finding 6 is a note |
| `a2a2432` — docs | **holds with notes** | F4, F7, F8, F9, F10, F13 hold against the sources; F3 and F5 are incomplete on the docker-proxy path — finding 2; the WARP sentence (F14) is not source-backed — finding 3; findings 4 and 5 are wording |
| `90e790f` — the review document with section 6 | **holds** | the commits named per row are the ones that carry the change; the rows' wording is accurate except where findings 1–3 say otherwise |
| `fbdff64` — section 6.1 | **holds with notes** | F1, F2, F4, F7 rows accurate. F3: "corrected" and "the table itself was not [parsed]" — parsed now (section 1), still not run on a host, and incomplete (finding 2). F5: "corrected" — the requirement does not close the direct IPv6 path (finding 2), and the mechanism sentence is imprecise (finding 4). F6: "corrected … none beyond those" — finding 1, and the exported-variable path that section 6 keeps open is missing from the third column. F14 is not in 6.1 at all and should be, as an assumption (finding 3) |

Nothing in the five commits may be called production-verified: F1's effect and the
origin firewall are derived from sources and parsed, not measured, which is what
section 6.1's closing sentence says and what this review confirms.

## 5. Open — needs a host, kept open, never to be marked passed here

The seven items of the first review's section 5 (listed again in the README,
766-787) stay open, plus:

- **Item 8.** A direct IPv6 client to the published 443 on an IPv4-only `proxy-public`
  with the README's table installed — what reaches Traefik, as which address, and what
  `acc-local` answers (finding 2); the same after the dual-stack overlay.
- **Item 9.** The address a WARP client arrives from, inside or outside the published
  ranges, and what the bouncer compares for it (finding 3).
- **Item 10.** The guard on a real pre-switch host — `render.sh` with the switch absent
  over the installed `config/traefik.yml` — after finding 1 is fixed and its test
  exists; the reproduction here used the `v0.9.4` template, not a host's file.

The exported-environment path of F6 is a design choice shared by the three switches and
stays as section 6 records it.

Nothing in this review was run against a host, committed or pushed.

## 6. Corrections after the review, 2026-10-17

The review above is kept as written, with one exception: three Markdown-lint
corrections before the first commit of this file (two code
spans that carried leading or trailing spaces, written as words instead; the host-list
items 8–10 as bullets, since an ordered list cannot start at 8) — formatting only, no
statement, finding or test result changed. The first review's section 6.1 is corrected
in the same commit as this document.

| Finding | Status | Where |
|---|---|---|
| 1 (blocker) | corrected — both awk functions skip comment lines; tests `test_guard_holds_against_a_configuration_rendered_by_a_release` (the v0.9.x shape: `# Cloudflare IPv4` after the key, `# Cloudflare IPv6` inside the list; `render.sh` and `validate.sh` refuse) and `test_validate_reads_the_whole_list_of_a_release_shape`; the README's migration sentence says what the first version got wrong. Open on a host: item 10 | `63ce76d` |
| 2 (should-fix) | documented, not closed — the README states the docker-proxy input path, that `A`-only bounds Cloudflare's path only, and the two ways out (dual-stack overlay with `userland-proxy: false` and `ip6tables: true`, or an input-hook chain from the same sets); the standard's IPv6 note points there. Neither way is shipped as a file or verified. Open on a host: item 8 | `ddca564` |
| 3 (should-fix) | corrected — the three places say what Cloudflare documents (`172.64.0.0/13` in the list; Zero Trust egress not in it; consumer WARP undocumented) and name the outside-the-ranges direction. Open on a host: item 9 | `ddca564`, template comment in `63ce76d` |
| 4 (note) | corrected — "when only an `AAAA` exists, possibly when both" in the README and the standard | `ddca564` |
| 5 (note) | corrected — the table's comment names the container ports after DNAT; the semantics next to Docker's chains stay as reasoned, unmeasured | `ddca564` |
| 6 (note) | corrected — the `not produced` row of the host-files standard says `validate.sh` is the check that knows the mode | `ddca564` |
| 7 (note) | the upper-case value is now tested; the two `crowdsec.yml` agreement checks on their own are still not covered in isolation — left open as the first review's F12 row records | `63ce76d` |
