# Phase 3 — re-review of 63ce76d: does the migration guard hold against what the releases rendered? (2026-10-17)

Third review of the Phase 3 branch (`feature/cloudflare-mode`, PR #238), limited to
one commit: `63ce76d` — *the migration guard skips comment lines*. It answers finding 1
(blocker) of the second review, which found `rendered_trusts_ranges` reading the
comment line `# Cloudflare IPv4` of every released template as "trusts nobody". This
review asks one question: with that commit, is the guard right about the files the
releases actually produced — not about a fixture, but about `config/traefik.yml` as
each release's own `render.sh` wrote it?

**Verdict: holds, with notes.** Every configuration a release from v0.8.4 to v0.9.4
rendered is refused by the current `render.sh` with the switch absent and with it
empty, with the message the guard promises, with the file untouched. The current
`validate.sh` refuses the same files; on installations from before v0.9.3 it names a
missing dynamic file first and the switch only after that file is supplied (note 1).
With `TRAEFIK_FORWARDED_PROXY=cloudflare`, the release's 22 hard-coded ranges equal
today's `ops/cloudflare-ips.txt`, and `validate.sh` fails only for the two reasons a
pre-switch installation must fail: the bouncer middlewares carry no trusted-proxy list,
or the firewall file does not exist — each saying "run render.sh". One should-fix
(finding 2) concerns a shape no release rendered and only a hand edit produces.

Binding rules of this review: read-only. No host was contacted, nothing was deployed,
nothing was committed or pushed, no file in the repository was changed apart from this
document. Corrections are proposed, not applied. What only a host can prove is listed
at the end and stays open; nothing here is production-verified.

## Scope and method

Environment: macOS, GNU bash 3.2.57 as `/usr/bin/env bash` resolves it, BSD `awk`
version 20200816, GNU `envsubst` (gettext-runtime 1.0) from Homebrew, Python 3.12.15
with PyYAML 6.0.3 in the review venv. The worktree is
`claude/laughing-rubin-b87881`, HEAD `880e921`, which contains `63ce76d`.

1. **Per tag, the release's own render.** For each of v0.8.4, v0.9.0, v0.9.1, v0.9.2,
   v0.9.3 and v0.9.4, `git archive <tag> core/traefik` was unpacked into a scratch
   directory, the tag's `.env.example` was copied to `.env` with
   `CROWDSEC_BOUNCER_ENABLED` set once to `true` (with a key) and once to `false`, and
   the tag's own `ops/scripts/render.sh` was run. That is not a re-enactment: it is the
   script that release shipped, over the template that release shipped. The result is
   `config/traefik.yml` with the hard-coded list, and `config/dynamic/crowdsec.yml`
   where the switch was on.
2. **The current scripts over that output.** The current branch's `core/traefik` was
   copied to a scratch directory, its `config/` replaced by the release's, and the
   current `render.sh` run with the switch absent (A) and empty (B); the current
   `validate.sh` with the switch absent (C), empty (D), `cloudflare` (E) and `none`
   (G). The `.env` for these runs is the test suite's `VALID_ENV` without the switch;
   the validate runs were repeated with a release-like `.env` (per-domain dashboard
   resolver, no wildcard domain) because `VALID_ENV` sets `ACME_WILDCARD_DOMAIN`, which
   demands a file no release host without a wildcard has. SHA-256 of
   `config/traefik.yml` was taken before and after every run, and `config/` was
   checked for temporary files.
3. **The previous guard over the same files (F).** `render.sh` as of `2b1cda2` was
   placed into a copy of the same tree and run with the switch absent, to see the
   blocker as it was.
4. **Shapes.** Both awk functions, copied verbatim from `validate.sh` (the one in
   `render.sh` is the same text), were fed twenty hand-written shapes.
5. **Fixture.** `RELEASED_BLOCK` was compared byte for byte with the block of the
   v0.9.4 template, and the two release-shape tests were run against a scratch copy
   carrying the `2b1cda2` scripts, then the `63ce76d` scripts.
6. **Tests.** `python3 -m unittest discover -s scripts/ci -p 'test_traefik_*.py'` on
   the worktree.

Every scratch directory lives outside the repository; `git status` on the worktree is
clean apart from this file.

## What the six tags are

The six tags share one template, one `render.sh` and one `crowdsec.yml.tmpl`:

| Tag | Date | `traefik.yml.tmpl` blob | `render.sh` blob | `.env.example` blob |
|---|---|---|---|---|
| v0.8.4 | 2026-09-15 | `8b2dcbe` | `dbd20ab` | `c546d03` |
| v0.9.0 | 2026-09-18 | `8b2dcbe` | `dbd20ab` | `c546d03` |
| v0.9.1 | 2026-09-20 | `8b2dcbe` | `dbd20ab` | `c546d03` |
| v0.9.2 | 2026-09-22 | `8b2dcbe` | `dbd20ab` | `c546d03` |
| v0.9.3 | 2026-09-24 | `8b2dcbe` | `dbd20ab` | `aa4d483` |
| v0.9.4 | 2026-10-04 | `8b2dcbe` | `dbd20ab` | `aa4d483` |

The `.env.example` change at v0.9.3 adds `TRAEFIK_MEMORY`, which `traefik.yml.tmpl`
does not use. Consequently the rendered `config/traefik.yml` is byte-identical across
all six tags for a given bouncer setting: SHA-256 `c943ff0e…` with the plugin block,
`45c0647f…` without. The forwardedHeaders block (template lines 40–65 at v0.9.4) is
the same bytes at every tag, and `# Cloudflare IPv4` has been on the line after
`trustedIPs:` since commit `386e8bf` (2026-06-19) — so v0.8.0 to v0.8.3, outside the
task's range, carry the same shape (their templates were checked with the function
directly: "trusts" on each). What a copied-directory host from any 0.8.x or 0.9.x
release holds is therefore one shape, as far as the repository's own output goes.

## Results per tag

Columns: the release's own render (plugin block present, `crowdsec.yml` present); A =
current `render.sh`, switch absent; B = switch empty; C = current `validate.sh`, switch
absent; D = switch empty; E = switch `cloudflare`; F = `render.sh` as of `2b1cda2`,
switch absent. "refused, named" means exit 1 and the message contains
`TRAEFIK_FORWARDED_PROXY is not` (render) or `not set in .env` (validate), with
`config/traefik.yml` unchanged and no temporary file left. "list = file" is the
rendered list compared with `ops/cloudflare-ips.txt` the way `validate.sh` line 327
compares it.

### v0.8.4

| Run | Bouncer on | Bouncer off |
|---|---|---|
| Release render | rc 0, plugin block, `crowdsec.yml` present | rc 0, no plugin block, no `crowdsec.yml` |
| A render, absent | refused, named, unchanged | refused, named, unchanged |
| B render, empty | refused, named, unchanged | refused, named, unchanged |
| C validate, absent | refused: `Missing config/dynamic/servers-transports.yml (run render.sh)`; with that file supplied: refused, named | same |
| D validate, empty | same as C | same as C |
| E validate, cloudflare | list = file (22 = 22); refused: `crowdsec.yml carries no trusted-proxy list — run render.sh` (after the missing file is supplied) | list = file; refused: `Missing config/host/cloudflare-ranges.nft (run render.sh)` |
| F 2b1cda2, absent | rc 0, silent, list now `[]` | rc 0, silent, list now `[]` |

### v0.9.0

| Run | Bouncer on | Bouncer off |
|---|---|---|
| Release render | rc 0, plugin block, `crowdsec.yml` present | rc 0, no plugin block, no `crowdsec.yml` |
| A render, absent | refused, named, unchanged | refused, named, unchanged |
| B render, empty | refused, named, unchanged | refused, named, unchanged |
| C validate, absent | refused: missing `servers-transports.yml`; with it supplied: refused, named | same |
| D validate, empty | same as C | same as C |
| E validate, cloudflare | list = file; refused: `crowdsec.yml carries no trusted-proxy list` | list = file; refused: missing `cloudflare-ranges.nft` |
| F 2b1cda2, absent | rc 0, silent, list now `[]` | rc 0, silent, list now `[]` |

### v0.9.1

| Run | Bouncer on | Bouncer off |
|---|---|---|
| Release render | rc 0, plugin block, `crowdsec.yml` present | rc 0, no plugin block, no `crowdsec.yml` |
| A render, absent | refused, named, unchanged | refused, named, unchanged |
| B render, empty | refused, named, unchanged | refused, named, unchanged |
| C validate, absent | refused: missing `servers-transports.yml`; with it supplied: refused, named | same |
| D validate, empty | same as C | same as C |
| E validate, cloudflare | list = file; refused: `crowdsec.yml carries no trusted-proxy list` | list = file; refused: missing `cloudflare-ranges.nft` |
| F 2b1cda2, absent | rc 0, silent, list now `[]` | rc 0, silent, list now `[]` |

### v0.9.2

| Run | Bouncer on | Bouncer off |
|---|---|---|
| Release render | rc 0, plugin block, `crowdsec.yml` present | rc 0, no plugin block, no `crowdsec.yml` |
| A render, absent | refused, named, unchanged | refused, named, unchanged |
| B render, empty | refused, named, unchanged | refused, named, unchanged |
| C validate, absent | refused: missing `servers-transports.yml`; with it supplied: refused, named | same |
| D validate, empty | same as C | same as C |
| E validate, cloudflare | list = file; refused: `crowdsec.yml carries no trusted-proxy list` | list = file; refused: missing `cloudflare-ranges.nft` |
| F 2b1cda2, absent | rc 0, silent, list now `[]` | rc 0, silent, list now `[]` |

### v0.9.3

| Run | Bouncer on | Bouncer off |
|---|---|---|
| Release render | rc 0, plugin block, `crowdsec.yml` present, `servers-transports.yml` present | rc 0, no plugin block, no `crowdsec.yml` |
| A render, absent | refused, named, unchanged | refused, named, unchanged |
| B render, empty | refused, named, unchanged | refused, named, unchanged |
| C validate, absent | refused, named | refused, named |
| D validate, empty | refused, named | refused, named |
| E validate, cloudflare | list = file; refused: `crowdsec.yml carries no trusted-proxy list` | list = file; refused: missing `cloudflare-ranges.nft` |
| F 2b1cda2, absent | rc 0, silent, list now `[]` | rc 0, silent, list now `[]` |

### v0.9.4

| Run | Bouncer on | Bouncer off |
|---|---|---|
| Release render | rc 0, plugin block, `crowdsec.yml` present, `servers-transports.yml` present | rc 0, no plugin block, no `crowdsec.yml` |
| A render, absent | refused, named, unchanged | refused, named, unchanged |
| B render, empty | refused, named, unchanged | refused, named, unchanged |
| C validate, absent | refused, named | refused, named |
| D validate, empty | refused, named | refused, named |
| E validate, cloudflare | list = file; refused: `crowdsec.yml carries no trusted-proxy list` | list = file; refused: missing `cloudflare-ranges.nft` |
| F 2b1cda2, absent | rc 0, silent, list now `[]` | rc 0, silent, list now `[]` |

The refusal text of run A, identical on every tag:

```text
ERROR: config/traefik.yml trusts Cloudflare's ranges, but TRAEFIK_FORWARDED_PROXY is not
       set in .env. Rendering now would trust no sender — an installation behind
       Cloudflare's proxy would then see edge addresses everywhere, and CrowdSec would
       ban them.

       Records proxied by Cloudflare (orange cloud):  TRAEFIK_FORWARDED_PROXY=cloudflare
       No Cloudflare proxy in front of this host:     TRAEFIK_FORWARDED_PROXY=none
       Then run render.sh again. See core/traefik/README.md, 'Behind Cloudflare'.
```

Run F, the guard before `63ce76d`, on the same file: `Rendering static config...`,
`-> trusted proxy ranges: none (TRAEFIK_FORWARDED_PROXY=none)`, exit 0, and the web
entrypoint's list is `[]` afterwards — the blocker of the second review, reproduced on
every tag's own output, in both bouncer settings.

Run G (`validate.sh` with `TRAEFIK_FORWARDED_PROXY=none` over the release file) refuses
on every tag with `TRAEFIK_FORWARDED_PROXY=none but config/traefik.yml still trusts
Cloudflare's ranges — run render.sh`, and `render.sh` with `none` declared then renders
the empty list — the documented migration for a host without Cloudflare.

The list comparison: the release's 22 hard-coded ranges (15 IPv4, 7 IPv6) are exactly
the 22 entries of today's `ops/cloudflare-ips.txt`; `rendered_ranges` reads all 22 of
them through the `# Cloudflare IPv6` line, so a host that sets `cloudflare` and renders
will not see the "ranges file changed" error on the first validation after the render.

## Shapes the two functions were given

`rendered_trusts_ranges` is at `core/traefik/ops/scripts/render.sh:106` and
`core/traefik/ops/scripts/validate.sh:156`; `rendered_ranges` at `validate.sh:162`.
The key rule is `/^[[:space:]]*trustedIPs:[^*]*$/` (any `trustedIPs:` line without a
`*`, which excludes the alias line); once armed, comment and blank lines are skipped and
the first other line decides: a dash followed by a space means trusts, anything else
means nobody.

| Shape | Can it occur? | `rendered_trusts_ranges` | `rendered_ranges` | Right? |
|---|---|---|---|---|
| Released block, `# Cloudflare IPv4` after the key, `# Cloudflare IPv6` inside | every release v0.8.0–v0.9.4 | trusts | all entries | yes |
| Current `none` render: `[]` on the line after the key | every render in `none` mode | nobody | none | yes |
| Tabs for indentation | no render; a hand edit Traefik's YAML parser would reject anyway | trusts | all entries | yes |
| CRLF line endings, trusting list | no render; a hand edit from a Windows editor | trusts | entries with a trailing CR | guard yes; comparison fails, see finding 4 |
| CRLF, `[]` | same | nobody | none | yes |
| Comment with deeper indentation inside the list | no render; hand edit | trusts | all entries | yes |
| Trailing comment on a range line | no render; hand edit | trusts | entry with the comment appended | guard yes; comparison fails, finding 4 |
| Inline flow list `trustedIPs: ["a", "b"]` | no render; hand edit | nobody | none | **no** — finding 2 |
| Anchored flow list `trustedIPs: &x ["a"]` | same | nobody | none | **no** — finding 2 |
| `[]` with a comment line before it | no render; hand edit | nobody | none | yes |
| `trustedIPs: []` on the key line | no render; hand edit | nobody | none | yes |
| `proxyProtocol.trustedIPs` trusting, before `forwardedHeaders` with `[]` | no template today; `docs/audits/candidate-evaluation-2026-10-03.md:355` names PROXY protocol as an open option for mail | trusts (reads the wrong list) | the proxyProtocol entries | wrong list, safe direction — finding 3 |
| `proxyProtocol.trustedIPs: []` before a trusting `forwardedHeaders` | same | nobody | none | **no** — finding 3 |
| `websecure` before `web`, alias on websecure | no render (web is first); hand reorder | trusts | all entries | yes — the alias line is excluded by `[^*]*` |
| `websecure` first with its own `[]`, `web` trusting, no anchor | no render; two hand edits at once | nobody | none | no — finding 5 |
| No `trustedIPs:` key at all | no render | nobody | none | yes |
| Key with trailing spaces | hand edit | trusts | all entries | yes |
| Unquoted or single-quoted entries | hand edit | trusts | entries, single quotes kept | guard yes; comparison fails, finding 4 |
| `-` followed by a tab instead of a space | hand edit; valid YAML | nobody | none | **no** — finding 5 |
| The key only inside a comment block, real key with `[]` | hand edit | nobody | none | yes |
| Key is the last line of the file | truncated file | trusts | none | safe direction: refuses, finding 6 |
| Entry is a nested mapping `- ip: …` | hand edit, not a Traefik shape | trusts | `ip: …` | refuses; harmless |
| Sibling key right after `trustedIPs:` (null value) | hand edit | nobody | none | yes |
| Two families separated by a blank line | hand edit | trusts | all entries | yes |

The function is right on every shape this repository ever rendered, in both modes, and
on every hand edit that keeps the block-list style. It is wrong on four shapes, all of
which require an operator to rewrite the rendered block in a different YAML style;
three of the four answer "nobody" for a list that trusts, which is the silent direction.

## Findings

### 1. note — `validate.sh` names a missing dynamic file before it names the switch

Evidence: `core/traefik/ops/scripts/validate.sh:272-277` demands
`servers-transports.yml` (first rendered at v0.9.3) and, with `ACME_WILDCARD_DOMAIN`
set, `acme-wildcard.yml`; the trusted-sender block is at lines 315–343. On a
`config/` from v0.8.4–v0.9.2 the first message is `Missing
config/dynamic/servers-transports.yml (run render.sh)`, exit 1; the switch is named
only once that file exists (runs C and D above). The advice leads to `render.sh`, which
refuses with the full message, so the chain holds and nothing is rendered — but the
operator reads two errors in sequence, the first of which does not say why the second
will happen.

Proposed correction (not applied): move the undeclared-switch refusal (validate.sh
lines 338–343, the `-z "${proxy_declared}"` branch) ahead of the file-existence checks
at lines 272–277, or run `rendered_trusts_ranges` once at the top of the "Runtime
files" block and refuse there when the switch is undeclared. The comparison with the
ranges file and the crowdsec/nft checks can stay where they are.

### 2. should-fix — an inline flow list is read as "trusts nobody"

Evidence: shapes 7 and 7b above. `trustedIPs: ["173.245.48.0/20", "2400:cb00::/32"]`
matches the key rule (no `*` on the line), the next line is the entrypoint's `http:`
key, which is neither a comment nor a dash-space entry, so the function answers
nobody; `rendered_ranges` prints nothing. With the switch absent, `render.sh` then
renders `none` over a trusting file without a word — the failure mode the guard exists
for. With `cloudflare` declared, `validate.sh` says `config/traefik.yml trusts no
Cloudflare range — run render.sh`, which at least leads to a re-render.

Can it occur? No release and no render of this branch writes flow style; the template
says "edit the file or the switch, never this block". An operator would have to replace
the 22-line block by hand. Likelihood is low; the consequence is the silent one, and
`validate.sh` already claims to catch hand edits of a neighbouring kind
(`forwardedHeadersCustomName`, tested by `test_no_mode_names_a_custom_header_for_the_bouncer`).

Proposed correction (not applied): in the key rule, look at what follows the colon.
If the rest of the line contains `[` followed by anything other than whitespace and
`]`, answer trusts at once; if it is exactly `[]`, answer nobody at once; otherwise arm
as today. `rendered_ranges` can either split the flow entries on commas or, simpler and
safer, `validate.sh` can refuse a flow list as "not a shape render.sh writes — run
render.sh", since the comparison with the ranges file only has to hold for rendered
files. Add the two flow shapes to `test_traefik_forwarded_proxy.py` next to
`released_shape()`.

### 3. note — the key rule is not tied to `forwardedHeaders`

Evidence: shapes 9 and 9b. The first `trustedIPs:` line in the file decides, whatever
its parent. A `proxyProtocol.trustedIPs` list on an entrypoint that comes before `web`,
or above `forwardedHeaders` inside `web`, is read instead of the forwarded-headers
list. Trusting proxyProtocol with empty forwardedHeaders answers trusts (refuses; safe);
empty proxyProtocol with trusting forwardedHeaders answers nobody (silent).

Can it occur? Not from any template in the repository's history, and `web` is the
first entrypoint in every one of them. The mail-server evaluation
(`docs/audits/candidate-evaluation-2026-10-03.md:355`) keeps "routed by Traefik through
TCP entrypoints with PROXY protocol" as an open option, so a future template could add
such an entrypoint — and if it is added above `web`, the guard reads the wrong list
with no test to notice.

Proposed correction (not applied): arm only when the previous non-comment line is
`forwardedHeaders:` (keep the last line in a variable and test it in the key rule), or
reset on any `proxyProtocol:` line. A test with a `proxyProtocol` block before
`forwardedHeaders` would pin it.

### 4. note — hand-edited entries make the ranges comparison misdiagnose

Evidence: shapes 4, 6 and 13. A trailing comment on a range line, a single-quoted
entry, or CRLF line endings leave `rendered_ranges` printing `173.245.48.0/20  # edge`,
`'2400:cb00::/32'` or `173.245.48.0/20\r`. `rendered_trusts_ranges` is right in each
case, so the migration guard holds; but in `cloudflare` mode `validate.sh:327` compares
those strings with the file and reports `the ranges file changed since the last render —
run render.sh`. The action is right (a render rewrites the block), the diagnosis is
wrong (the file did not change).

Can it occur? Only by hand: `render.sh` writes LF, double quotes and no trailing
comments. Proposed correction (not applied): in `rendered_ranges`, strip `#.*`, both
quote characters and `\r` before printing, and reword the message to "the list in
config/traefik.yml differs from ops/cloudflare-ips.txt".

### 5. note — two more hand-edit shapes answer "nobody"

Evidence: shape 14 (`-` followed by a tab: valid YAML, the dash-space test needs a
space) and shape 10b (`websecure` written first with its own `[]` and `web` trusting,
no anchor). Both need an operator to depart from the rendered file in a way nobody has
a reason to. Proposed correction (not applied): `-[[:space:]]` instead of dash-space in
both functions; shape 10b is covered by the correction of finding 3 only partially (it
would still read the first `forwardedHeaders` list) and is not worth more than this
line.

### 6. note — a file that ends on the key answers "trusts"

Evidence: shape 16. With `trustedIPs:` as the last line, the loop never reaches a
deciding line; `END` sees `t` set and the function exits 0. `render.sh` with the switch
absent then refuses, and with `none` declared renders a complete file. The safe
direction; no change proposed.

### 7. note — the fixture and the revert test

`RELEASED_BLOCK` (`scripts/ci/test_traefik_forwarded_proxy.py:155-181`) is byte-equal to
lines 40–65 of `core/traefik/ops/templates/traefik.yml.tmpl` at v0.9.4 (SHA-256 of both
`2d758a2b9d03ece8…`), occurs exactly once in that template, and is contained in the
template at every tag from v0.8.4 to v0.9.3 as well. In a scratch copy of
`scripts/ci` and `core/traefik/ops` carrying the `2b1cda2` versions of `render.sh` and
`validate.sh`, `test_guard_holds_against_a_configuration_rendered_by_a_release` fails
with `0 == 0 : rendered over a release's trusting config without a declared mode` and
`test_validate_reads_the_whole_list_of_a_release_shape` fails with
`TRAEFIK_FORWARDED_PROXY=cloudflare but config/traefik.yml trusts no Cloudflare range`;
with the `63ce76d` scripts in the same copy both pass. The tag test
(`test_released_block_matches_the_tagged_template_when_git_has_the_tag`) is a substring
check, which is what it claims to be.

One observation, no finding: `released_shape()` splices the released block into a file
the current template rendered, so the surrounding comments are the branch's, not the
release's. The guard does not read them, and this review ran the actual release output
in addition, so nothing is lost — but a fixture of the whole v0.9.4 render would make
the test independent of that argument.

### 8. note — the range of releases

The second review wrote v0.9.0–v0.9.4; the commit message writes v0.8.4–v0.9.4. Git
shows the same template blob `8b2dcbe` at all six tags, and the comment line present
since `386e8bf` (2026-06-19), so v0.8.0–v0.8.3 carry it too. The commit message is
right and, if anything, understates: every tagged release of this repository rendered
the shape the previous guard misread.

## Tests

`python3 -m unittest discover -s scripts/ci -p 'test_traefik_*.py'` on the worktree:
`Ran 59 tests in 26.787s — OK` (Python 3.12.15, PyYAML 6.0.3, GNU envsubst). The test
run leaves the worktree clean. This document passes markdownlint-cli2 v0.18.1 with the
repository's `.markdownlint-cli2.jsonc`, `scripts/ci/check-links.py` (0 broken) and
`scripts/ci/check-prose.py` (0 blocking).

## Verdict on 63ce76d

**Holds, with notes.** The correction does what its message says: both readers skip
comment lines, the guard refuses every configuration a release produced, in both bouncer
settings, with the switch absent and with it empty, leaving the file untouched; the list
comparison reads the whole released list; the fixture is the released bytes and the test
that carries it fails against the previous guard. Findings 1 and 3–8 are notes on
ordering, on shapes that only a hand edit produces, and on the record. Finding 2 is a
should-fix because its failure mode is the silent one, even though no file this
repository ever wrote has that shape.

## What only a host can prove — open

1. **The installed file of a real pre-switch host.** This review ran the releases'
   own `render.sh` over the releases' own templates. A production host predates v0.9.2
   and is a copied directory, not a checkout; its `config/traefik.yml` may have been
   rendered from a tree between two tags, or edited by hand since. The guard's answer
   on that file — and the full `render.sh` refusal on that host, with the host's own
   `.env` — is the verification README item 10 (`core/traefik/README.md:821`) names,
   and it stays open. It must be read from the host before any render there.
2. **The host's awk.** This review ran BSD awk 20200816. Debian and Ubuntu hosts run
   mawk or gawk; the expressions are POSIX ERE with bracket classes and should behave
   the same, but the function has not been executed by the awk that will execute it.
   One run of `bash ops/scripts/validate.sh` on the host, before any change, settles it.
3. **The `cloudflare` path end to end.** After the operator sets the switch and
   renders, `validate.sh` must pass on the host (this review shows what it refuses
   before that render and why), and the running Traefik must see client addresses
   from Cloudflare — the seven items already open in the second review are untouched.

None of these is marked passed here, and nothing in this document is
production-verified.

## Corrections — added by the maintainer's session after the review, 2026-10-17

The review above is kept as written. One commit on `feature/cloudflare-mode` answers
the findings below; the host items stay open.

| Finding | Status | Where |
|---|---|---|
| 1 (note) | corrected — `validate.sh` refuses the undeclared switch over a trusting list before it names any missing dynamic file; test `test_validate_names_the_switch_before_a_missing_file` | `e5b1178` |
| 2 (should-fix) | corrected — a flow list on the key line is read: `["…"]` trusts, `[]` nobody, in both readers; `rendered_ranges` splits it; test `test_a_flow_list_written_by_hand_is_read_like_the_block_list` (trusting flow list refused without the switch and valid with `cloudflare`; empty flow list is the `none` shape) | `e5b1178` |
| 3 (note) | corrected — the key counts only when the previous non-comment line is `forwardedHeaders:`; test `test_only_the_key_under_forwarded_headers_counts` (a `proxyProtocol` list above it, in both directions) | `e5b1178` |
| 4 (note) | corrected — `rendered_ranges` strips a trailing comment, both quote characters and a carriage return; the message reads "the list in config/traefik.yml differs from ops/cloudflare-ips.txt"; test `test_hand_edited_entries_are_compared_by_value` | `e5b1178` |
| 5 (note) | corrected for the tab — `-[[:space:]]` in both readers; the two-entrypoint reorder without an anchor is left, as the review suggests | `e5b1178` |
| 6 (note) | no change — the safe direction | — |
| 7 (note) | no change; the observation that a whole-render fixture would make the test independent of the splice is left open for a later pass | — |
| 8 (note) | recorded — every tagged release from v0.8.0 to v0.9.4 rendered the shape | — |

What only a host can prove, items 1–3 above, is unchanged by this commit: the installed
file of a real pre-switch host, the host's awk, the `cloudflare` path end to end.
