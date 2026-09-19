# Decisions

Architecture and governance decisions with their reasoning, newest first. The full
rationale for structural decisions lives in [`../docs/architecture.md`](../docs/architecture.md);
this file is the index and covers decisions that have no other home.

---

## 2026-09 · Personal data on the public site

**Status: direction, not yet a decision.** Summary in [`../ROADMAP.md`](../ROADMAP.md#a-public-repository-should-not-carry-personal-data); the full reasoning is here.

The legal notice and the privacy statement hold a name, a postal address and an
e-mail. The repository is public and meant to be forked, so those values travel
with every copy.

The case to prevent is not someone taking them deliberately. It is the fork
that builds and goes live without anyone looking — and then a stranger's site
carries this author's imprint, and the people who read it write to **him** about
a site he has nothing to do with. Nobody had to act in bad faith for that to
happen.

Beyond the nuisance, a template that anyone can fork and build ought to be free
of its author's identity by construction. Keeping personal data out of a
public, copyable artefact is both the cleaner engineering answer and the correct
one under data-protection law.

**Direction, not yet a decision.** Encrypt the pages that carry personal data,
commit the ciphertext, and ship a placeholder in their place. What is secret is
the key, not the file: the repository holds a blob anyone can copy and nobody
can read, and a fork inherits a template that visibly asks for its own details.
It still builds on the first try, because the placeholder is a valid page.

`age` looks like the right size: one binary, no keyring, no web of trust, no
expiry, and a key pair that is two lines of text. SOPS earns its place when
single fields inside a YAML stay readable, which is not the case here — whole
files are encrypted, so it would be one layer over the same age. A repository
secret alone will not do either: a secret holds a value, so the imprint would
become an unversioned blob in a form field instead of a file with a history and
a diff.

Two key holders, both able to decrypt:

| Where | Holds |
|---|---|
| GitHub Actions secret | the key the deploy uses, decrypting into the runner's own workspace |
| a password manager | the same key for local editing, alongside the SSH keys already kept there |

An offline backup recipient belongs in the recipients file as well, so a lost
laptop does not take the imprint with it.

**Scope: everything personal, not only the two legal pages.** A fork inherits
the name and address in the legal notice, the contact address in
`security.txt`, the domain in `astro.config.mjs`, and the repository URLs in
the footer and the reference lists. Encrypting the imprint alone would still
leave a stranger's site pointing at this one.

**A fork builds, with the fields empty.** The placeholder is a valid page that
visibly asks for its own details, so nobody has to fix anything before the
first build succeeds.

That works for prose. It does not work for every value: the site URL feeds the
canonical tags and the sitemap, and an empty one produces a broken build rather
than an obvious gap. Values the build needs get a neutral placeholder —
`example.com` and the repository's own URL — while name, address and e-mail go
empty. The distinction is between a field a reader should notice is blank and a
value the build cannot do without.

**One data module rather than encrypted pages.** The values live in a single
module the pages and the config import. `site.ts` is committed and holds the
placeholders; `site.local.ts` is decrypted, gitignored, and wins when present.
That is a better shape than encrypting the markdown: one file to encrypt, one
import to resolve, and nothing in the working tree that a fork could mistake
for its own.

It also dissolves most of the trap. Decrypting over a committed placeholder
invites a thoughtless `git add` that puts real values back into a history that
keeps them; a gitignored file cannot be added by accident. A pre-commit hook
guarding against a forced add is then a belt on top of braces rather than the
only thing standing between the repository and a permanent mistake.

Locally the key never reaches the filesystem, because process substitution
hands `age` a descriptor instead of a path:

    age -d -i <(op read "op://Private/age-signing-key/notesPlain") \
        -o site/src/data/site.local.ts secrets/site.age

The runner needs the same care for the opposite reason: writing the key to a
file and deleting it afterwards leaves a window, however short, so the key
should reach `age` on a descriptor there too.

This concerns the site. The rule that no secret-management tooling belongs in
the blueprint itself stands: no stack gains a dependency, and none of this is
offered to an operator as a way to hold their own credentials.

---

## 2026-09 · Optional watchdogs for the Docker daemon and Traefik, bounded and opt-in

A read-only host-resilience evaluation found that `restart: unless-stopped` and
container healthchecks already cover a crashed process, but nothing acts on a
service that is running and unhealthy — Traefik included — or on the Docker
daemon's API hanging while the process stays alive. `docker inspect --format
'{{.State.OOMKilled}} {{.RestartCount}}'` in `docs/resource-measurement.md` was
already a manual command, never automated.

`willfarrell/autoheal`, the common general-purpose answer, was already rejected
once in this repository — `business/openproject/docker-compose.yml` omits it
because it needs a direct `docker.sock` mount, which containers here do not get.
A host-installed script run by systemd as root is a different trust boundary and
does not need that exception; it has the access an administrator already has.

Two independent scripts, `core/host-watchdog/docker-daemon-watchdog.sh` and
`core/traefik/ops/scripts/traefik-watchdog.sh`, each follow the same bounded
model: N consecutive confirmed failures → one recovery attempt → re-verify →
report and stop retrying if it did not hold. Neither installs by default,
neither is required by anything else, and either can be enabled alone. Both
report to a Healthchecks check on every run — the same dead-man's-switch
pattern `backup/borgmatic` already uses — so the watchdog itself going silent
is caught independently of whatever it watches.

Restarting Traefik on sustained unhealthy status is accepted specifically
because it holds no state — a wrong restart costs seconds of routing, not
data. This is not a general auto-heal policy: a stateful service reported
unhealthy should still alert a person, not restart itself, and the README
says so explicitly.

Neither script has run on a live host. The systemd hardening blocks mirror
`backup/borgmatic.service.example`'s pattern as a documented starting point,
not a verified one — matching this repository's own standard for anything
new: configured, not yet exercised.

---

## 2026-09-19 · Dify and Langfuse keep their real component count

Dify is ten services and Langfuse six, and none was collapsed: the worker, plugin
daemon, sandbox and SSRF proxy are what makes Dify's chat, knowledge-base and code
paths work, and Langfuse v4's ClickHouse, Redis and MinIO are all in its read and
write path. Where a component is optional upstream it was left out and named in
`UPSTREAM.md`: nginx and certbot (Traefik replaces them), workflow collaboration
and the 1.17 Agent runtime (backend, local sandbox, second proxy).

Dify's vector store is pgvector, not Weaviate and not the repository's own Qdrant:
Dify supports several, and no stack here embeds another. Langfuse sits in
`monitoring/` because it receives traces, and nothing else in the repository sends
to it or depends on it.

Exceptions were measured, not assumed. The plugin daemon ships as root but runs as
uid 1001, read-only, with installs verified. The sandbox needs five capabilities
(each removal broke a code run; a sixth was not needed). Squid stays root with five
capabilities. Langfuse's web service needs a 2 GB limit and a raised Node heap or it
loops at start, and both Node services bind to the container's hostname address, not
loopback, so their healthchecks call `$(hostname)`. Dify's licence and Open WebUI's
are classed source-available in the sovereignty report.

## 2026-09-19 · The AI gateways and chat UI are independent stacks

`apps/litellm`, `apps/open-webui` and `apps/agentgateway` were added without a
dependency between them or on the foundation stacks. Each takes its backend as
configuration (an OpenAI-compatible URL) and ships pointing at an Ollama address
that only resolves if the operator has one; the READMEs say so instead of wiring
a shared network.

Three secrets findings shaped the stacks. LiteLLM and Open WebUI have no `_FILE`
variants, so each carries an `entrypoint.sh` that exports Docker Secrets;
agentgateway's image is distroless and has no shell, so its client key is stored
in the config only as a SHA-256 hash and its UI login is an htpasswd file mounted
as a secret. Open WebUI runs as an unprivileged uid though its image defaults to
root, and creates its administrator from the environment because upstream
otherwise makes the first registrant the administrator. agentgateway's default
binds metrics to all interfaces; the template pins them to loopback.

Open WebUI's licence is BSD-3-Clause with a branding-preservation clause, so the
sovereignty report classes it as source-available rather than OSI.

## 2026-09-18 · The AI foundation exists; vLLM is documented as unverified on GPU

The 2026-09 position that AI & Local AI stays latent was conditional: it waited
on a deployment somebody needs. That need was declared, and `apps/ollama`,
`apps/vllm` and `apps/qdrant` landed together. `docs/architecture.md` now says
deploying and hardening AI services is this repository's job and the
engineering above them is not; `ROADMAP.md`'s out-of-scope entry narrowed to
match. The earlier decision below stays as the record of why the absence was
reasoned.

Ollama and vLLM are both kept although both serve models — the repository
carries alternatives deliberately — because they serve different deployments.

Two decisions about evidence. vLLM's CUDA image is 8.7 GB and needs a GPU, and
the test host had neither the disk nor the hardware. The stack was therefore
validated on the CPU build of the same release — real inference, the
authentication behaviour, the Traefik path allowlist, the hardening flags — and
says in its README and `UPSTREAM.md` that the CUDA image has not run and that
its non-root and read-only settings are a first-run hypothesis for it, not a
result. And the authentication limits are properties to design around, not to
hide: Ollama has none, vLLM's key covers `/v1` only (`/invocations` runs
inference without it), so vLLM's router forwards `/v1/` only and both READMEs
state that peers on `proxy-public` reach everything.

## 2026-09-18 · Windmill runs without job sandboxing rather than with privileged workers

Upstream's default Windmill worker is `privileged: true`, for PID-namespace
isolation of job code. The repository baseline has no exception path for
privileged containers, so the stack does not use it. NSJAIL, upstream's
unprivileged alternative, was tried with `cap_add: SYS_ADMIN`,
`seccomp=unconfined` and `apparmor=unconfined` and still failed on a `mount()`
call; whether that is specific to the nested-virtualisation test host is not
established. The stack therefore ships with no per-job isolation beyond the
worker container's own boundary (non-root, all capabilities dropped,
read-only root filesystem, `no-new-privileges`), and says so in the stack's
README and `UPSTREAM.md` instead of implying a sandbox.

Two smaller consequences. Workers join a per-stack `app-egress` network — the
pattern `apps/nextcloud` and `business/invoiceninja` already use — because
runtime and dependency downloads fail on `app-internal` alone. And a fresh
Windmill carries a published superadmin password, so the router defaults to
`acc-deny` until `ops/bootstrap-admin.sh` has replaced it. The first
reproducible retest is on a bare-metal host, where NSJAIL may work.

## 2026-09-18 · A blueprint entry needs an independently operated service, not just a container

Clarified while evaluating OCRmyPDF for `apps/`. Functional overlap with an
existing stack is not a reason to exclude a tool — this repository already
carries multiple alternatives per category deliberately (dashboards, photo
galleries, scheduling) and continues to. The separate, narrower test is
whether a tool is something to deploy, harden and operate as its own service
at all: a pure CLI utility or job that upstream itself runs as one container
per invocation does not become more of a service by wrapping it in Compose.

`apps/docling-serve` passes this test — an API with its own healthcheck,
authentication and multiple plausible independent callers. OCRmyPDF does not:
upstream's own documentation describes its Docker image as ephemeral, "one
OCR job and terminates, just like a command line program... as opposed to the
more conventional case, where a Docker container runs as a server." No
`apps/ocrmypdf` entry was created, and none is planned as a substitute — the
need this would have filled was never established as real, so there is
nothing to replace it with. Recorded in `ROADMAP.md` → "Out of scope here" so
the absence is not silently re-proposed later.

Tika, Gotenberg and ClamAV were explicitly held out of this batch by the same
correction that sharpened the criterion above — an earlier plan had scoped
standalone Tika and Gotenberg stacks into this batch alongside `docling-serve`,
before that plan was implemented. They remain embedded in Paperless-ngx /
optional in Seafile-Pro, unchanged, pending a later evaluation.

## 2026-09-18 · `development/` becomes a Supporting-tier domain

The Development / Custom Applications conceptual domain had no physical home:
its two real members, `business/vikunja` and `apps/caldiy`, sit under the
normal five categories, and `docs/standards/custom-application.md` stated that
a genuinely first-party application — source with no upstream — "stays absent
until a real application needs it." That precondition is now met: the need for
a reusable starting point across future first-party projects, not for one
specific named application, was declared real and current.

`development/` is not a sixth entry in the five-category access-pattern table.
The Directory Structure test asks how a running service reaches the system; a
deployment pattern that is never run from this repository has no access
pattern to test. It is a Supporting-tier directory instead, alongside `docs/`,
`scripts/ci/` and `site/` — checked by `scripts/ci/check-structure.py` anyway,
because unlike those three it holds real, buildable compose files. `ROOTS` in
that checker gained `development`, and `development/static-site` and
`development/web-api` were added to `EXCEPT_DIRS` for the same reason
`apps/_reference` is there: a template, not a versioned app, no `UPSTREAM.md`.

Two patterns exist: `development/static-site/` (a build step producing static
files, Astro and Vite/React recipes differing only in the build stage) and
`development/web-api/` (a generic backend, deliberately without a database —
one is added the way `apps/_reference` shows, only when a real application
needs one). Each is proven by a minimal fixture: a real `docker compose build
&& up`, hardened (`read_only`, `cap_drop: ALL`, non-root), reporting healthy.
The fixture proves the pattern's contract, not that a real project has been
through it — no project has yet been copied out of `development/` and
operated, and `custom-application.md` records that as a standing gap rather
than closing it.

`docs/architecture.md`'s "Development is a mission scope, not the local
test-stack mode" section is now "Development is a Supporting-tier domain, not
a sixth category", and `custom-application.md` gained this as a third shape
alongside the in-repo build layer and the external governed pipeline.

Third-party developer tooling (Mailpit, GreenMail, Adminer, IT-Tools, Whoami,
Windmill) is unaffected — it stays in `apps/` under the ordinary
categorisation test and is linked from `development/README.md`, which does not
become a stack listing.

## 2026-09 · v1.0.0 requires both the repository and the operator site

`v1.0.0` is not tagged until this repository *and* the SecDockBlue site meet
their criteria. The site being live is not sufficient — it has been live since
2026-07-31 and is not finished. The repository is the technical source of truth
and the site is how most people will meet it, so a stable technical release in
front of an unfinished public surface would promise something the project cannot
deliver.

This reverses a position the repository held. `ROADMAP.md` said Operator Site
work was "tied to no version", and `site/README.md` recorded that a v1.0.0
coupling had been decided and then abandoned. Both statements were about
**when the site would first publish**, which is settled and unchanged:
publishing is continuous, every push to `main` that touches `site/` deploys, and
no release schedules it. The new gate runs the other way and constrains the
**tag**, not the content. Both files now say so rather than leaving the
implication that the two are unrelated.

`ROADMAP.md`'s v1.0 section is the canonical home — it already owned the v1.0
criteria, and the File Map makes `ROADMAP.md` the owner of anything
forward-looking. Its ten repository bullets gained five site ones, and the
Release Chain in `docs/maintenance.md` gained a step so the release procedure
enforces the gate instead of leaving it as prose. Repository and site stay
separate products with separate structures; v1.0 is the one checkpoint they
share.

## 2026-09 · AI & Local AI stays latent; Document Processing has capabilities but no pipeline

Both were conceptual domains carried in `docs/architecture.md` with one bullet
each, and neither absence had a reason attached. AI & Local AI said only that no
stack exists; Document Processing said `apps/` "covers both halves", which read
as *already done* rather than as bounded. Read from this file alone, neither
would have looked like a decision. They are now reasoned at their owner, and
both appear in `ROADMAP.md`'s "Out of scope here".

**AI & Local AI.** The line is between running a service and doing the
engineering. Deploying and hardening a reusable AI service is in scope the
moment a real need exists, and it takes the ordinary categorisation test —
nothing about "AI" changes which directory it lands in. Model evaluation,
retrieval architecture and prompt design sit above that line and belong to a
different project. So the absence is not waiting on a decision; it is waiting on
a deployment somebody needs. A candidate catalogue assembled in advance would be
a list, not a capability. Machine learning already runs inside Immich and
PhotoPrism as a property of those applications, which is not a domain.

**Document Processing.** Described in three parts rather than two, because
e-signature was missing from the previous account: archive and ingest
(`apps/paperless-ngx`), browser editing (the three editors in `apps/`), and
e-signature (`business/documenso`, `business/opensign`). Tika and Gotenberg are
Paperless-ngx's own converters, not shared services, which is why they have no
stack. What does not exist is a general pipeline from an arbitrary document
through extraction and layout recognition to a structured result — and a pipeline
is defined by the document it handles and the output someone needs, so building
one before a real case exists would produce a chain of tools with no test for
whether it works.

Neither gets a directory, a stack, or a placeholder.

## 2026-09 · The custom-application path is named from the two builds that already exist

`README.md` promised patterns for "applications you build yourself" while the
same paragraph said no reference pattern existed, and
`docs/architecture.md` said none was planned. Both were written without
noticing that two stacks here already build their own image, in two different
shapes: `business/vikunja` adds a layer to a published image because upstream
ships `FROM scratch`, and `apps/caldiy` consumes a reviewed release from a
governed fork. The pattern existed; it had never been named.

[`docs/standards/custom-application.md`](../docs/standards/custom-application.md)
is derived from those two. It owns one phase — source, build, image identity,
and what verifies the image — and its central claim is that every phase after
the image is unchanged and already owned elsewhere. Restating the downstream
standards would have created a second owner for facts that already have one.

**Only four rules are binding**, because only four are supported by evidence:
no secret material in any build stage or layer (already binding everywhere
else); the deployed image identity is explicit, reviewable and traceable, with
no floating references; provenance is recorded in the stack's `UPSTREAM.md`;
and everything after the image follows the existing standards unchanged.

Practices that appear in **one** of the two shapes are recorded as what that
stack does and explicitly **not** as requirements: `<app>-local:` image naming,
a `build:` block in the local Compose file, an explicit `USER` in the final
stage, digest-pinning every `FROM`, the `build --pull` upgrade shape, and
universal digest pinning of the deployed image. Two instances are not a
pattern, and this closure task was not the place to promote good engineering
practice to repository-wide policy. Note in particular that the two shapes do
**not** agree on digest pinning — vikunja pins a tag and digest pair, caldiy
accepts a reviewed tag — so "immutable" is not the shared rule; explicit,
reviewable and traceable is.

Gaps are documented rather than closed: locally built images are not CVE
scanned (Trivy cannot pull them), no checker reads a Dockerfile, Renovate
cannot see a base pin behind a build arg, and `business/vikunja`'s tag and
digest have **already drifted apart** unnoticed — which is the concrete reason
the pin rule exists. The drift itself is left as found; correcting it needs a
registry lookup and is a pin decision, not an architecture one.

No ROADMAP item was created, consistent with the mission-scope decision below:
the absence of one is deliberate, not an oversight. No directory, no framework
sample, and no stand-in `Dockerfile` in `apps/_reference` — the template states
its boundary and points at the standard instead.

What remains absent is a **first-party** application: source with no upstream at
all. Both real cases wrap third-party software, so that shape is unproven, and
the mission's residual now sits in a reasoned absence rather than a false claim.

## 2026-09 · `core/` is defined by scope, not dependency; `whoami` moves to `apps/`

`core/` held five different definitions across two canonical files, three of
which were false of real membership: "Infrastructure every other service
depends on" and "Infrastructure shared by everything" and "(always needed)"
are all untrue of Authentik, Keycloak, CrowdSec, Infisical and the four
Docker-management tools, every one of which is optional. The test question
was the only accurate one, and its enumeration had no slot for secrets, so
`core/infisical` fitted none of the five.

All five now state one definition: `core/` holds capabilities whose scope is
the installation rather than one stack — control of Docker, the host or other
containers, and shared network, TLS, identity, DNS, security or secrets.
**Scope decides, not dependency.** Optionality does not disqualify a
capability, and two members may be alternatives to each other. The
"Core Services and Their Roles" table read as exhaustive while explaining 4
of 12 members, and one of its rows was not a directory at all; it is now
grouped by role and accounts for every member.

This came out of classifying the whole operator/helper/fixture cohort
together — whoami, mailpit, adminer, it-tools, acme-certs and the four Docker
management components — rather than judging any one of them alone. **No new
top-level category is justified.** The five categories model access patterns
coherently once `core/` is corrected. What that cohort shares is lifecycle and
audience, not access pattern, and the repository already expresses that
without a directory: `apps/README.md`'s "Developer & admin tools" grouping and
the status model.

`core/whoami` is therefore now `apps/whoami`. It failed the `core/` test
before any edit — nothing depends on it, it manages nothing, it is not
identity, certificates, DNS, WAF or secrets — and its access pattern is the
`apps/` one: `proxy-public`, Traefik-routed, `read_only`, `cap_drop: ALL`, no
socket, no database, no secrets, no state. It joins adminer, it-tools and
mailpit, which are already there. The argument for keeping it — that core's
own acceptance procedures gate on it — is an argument from purpose, which is
the axis the 2026-04 `business/` decision rejected. Compose and security
configuration are unchanged; only the directory and the paths naming it moved.

`acme-certs` was examined in the same pass and **stays in `core/`** on the
merits: certificates are an installation-scoped capability, and it is the
second implementation of that capability for the devices that never pass
through Traefik. It also cannot pass the `apps/` test — no router, no Traefik
label, no UI, no users; it runs `crond` and writes certificate files at host
level. Its planned extraction to a separate repository is a maintenance
decision and does not bear on where it belongs while it is here.

Known and deliberate imprecision: no directory test asks about lifecycle, so
"deploy temporarily, then disable" is not what places whoami — `apps/` is.
The `apps/` test was not widened to describe throwaway fixtures; a lifecycle
claim belongs to `docs/standards/status-model.md` if it ever earns one.

## 2026-09 · Swap-policy coverage completed; `no-swap-policy` is a FAIL

Every production service (150/150, 61 stacks) now states `memswap_limit`,
mechanically set equal to its own `memory` value — the documented default from
`compose-structure.md`, which needs no measurement. `scripts/ci/check-structure.py`
promotes `no-swap-policy` from `WARN` to `FAIL`, matching `no-resources`: it now
guards the property rather than reporting a migration.

**What this is not.** The compose files changed; no running container did. Per
`compose-structure.md` → "What is written here is not what is running," a limit
takes effect only when a container is recreated, not on restart and not on a
daemon restart. Live-host rollout is deliberately out of scope here — it happens
per stack, on a running host, chosen by the operator, the same way the v0.10.0
measurement pass already does. Nothing here claims otherwise.

**What stays open.** The *value* is still derived, not measured, for the same
services `cpus` already flags — v0.10.0 turns a peak into a limit; this decision
only closes the question of whether a swap policy is stated at all. The one
service using a variable instead of a literal (`backup/urbackup`) ties
`memswap_limit` to the same `${APP_MEM_LIMIT}` its `memory` already uses, rather
than a new variable — the two move together by construction, not by convention.

`docs/resource-measurement.md`'s "one-shot containers get no limit" line was
wrong on inspection — `core/authentik`'s `init-perms` (a chown, exits in under a
second) already carried one before this change, and setting one costs nothing.
Corrected: one-shot containers get sized limits like everything else, not an
exemption.

## 2026-09 · The document editors move from `core/` to `apps/`

`core/onlyoffice`, `core/euro-office` and `core/collabora` are now
`apps/onlyoffice`, `apps/euro-office` and `apps/collabora`. This resolves the
open decision recorded at `state.md` → "What belongs in `core/`": the
`core/` test in `docs/architecture.md` (breaks the deployment, controls
Docker, or is shared identity, certificates, DNS or WAF) was never met —
nothing else breaks without a document editor, and a homelab user benefits
from one exactly as a company does, which is the `apps/` test.

Compose, security configuration and every consuming stack's integration
(JWT secret, allowed origins, network path) are unchanged — only the
directory and the paths that name it moved. The website already treated
these as applications before this move; the repository now matches.

## 2026-09 · The mission covers custom applications; physical layout, conceptual domain and navigation stay three separate questions

The mission now covers two kinds of software: existing self-hosted open-source
projects, and applications someone builds themselves, both through the same
deploy → secure → operate → recover model. Full rationale, the layer
distinction and what stays out of scope: `docs/architecture.md` →
"Physical layout, conceptual domains and navigation are three different
layers."

**Why now.** Two review passes in a row conflated "how does a reader group
this" with "which directory does this belong in" — the same mistake the
2026-04 access-pattern decision (below) already corrected once for
`business/`.

## 2026-08 · Host CrowdSec enforcement is scoped to the public interface

The firewall bouncer runs in nftables `set-only` mode and maintains only the IPv4 and
IPv6 blacklist sets. This repository owns the DROP rule, attached to `hook forward` with
an explicit ingress-interface match on the public interface. There is no generic INPUT
chain, and no rule can match the management interface.

The alternative — the package's default managed mode — installs a source-address chain at
`hook input` with no interface restriction. That shape removed administrative access when
a legitimate detection banned an administrator's own VPN address, and it filtered no
proxy traffic at all, because published container ports are DNAT'd and traverse `FORWARD`
rather than `INPUT`. It carried the failure mode without the benefit.

Rejected: relying on an allowlist for the management plane. An allowlist is data and can
be wrong — the previous design trusted `safe_range`, which is not a configuration key in
the installed package and was silently ignored while validation reported success. A LAPI
AllowList for the VPN ranges is kept as defence in depth; the interface match is the
guarantee, because it is topology rather than data.

Rejected: `nft flush ruleset` or whole-snapshot restore as a rollback. Docker and the VPN
daemon rewrite host netfilter state continuously, so recovery names only CrowdSec's own
units and tables.

Deferred: the scoped enforcement is designed, not runtime-accepted. The acceptance
sequence and what is verified today live in `core/crowdsec/docs/firewall-bouncer.md`; the
incident evidence is in `docs/bugfixes/crowdsec-firewall-bouncer-2026-08-28.md`.

## 2026-08 · CrowdSec gets a dedicated core-to-core network

The engine joins `crowdsec-security` and no longer joins `proxy-public`. The network
is an ordinary IPv4 bridge, declared by `core/traefik` and joined by `core/crowdsec`
with `external: true`. Traefik and the engine are the intended members; application
stacks stay on `proxy-public` and never attach.

`proxy-public` is the network every routed application joins, and the CrowdSec LAPI,
AppSec and Prometheus ports answered all of them. Authentication already bounded what
that reach was good for — a bouncer key reads decisions and can neither create nor
delete one, and AppSec returns 401 without a valid remediation key — so this is
control-plane segmentation rather than the closing of an exploit. It also returns the
deployment to the upstream expectation that the AppSec component answers the reverse
proxy and nothing else.

Rejected: leaving the engine on `proxy-public`, which keeps the unauthenticated
metrics and pprof endpoints on port 6060 reachable from every application container.
Rejected: `internal: true` plus a separate egress network — it denies a route neither
member uses, and closed membership already bounds reachability.

Deferred: extending the shared-external-network identity check to this network. It
carries two members named in this repository, so the ambiguity that rule prevents
cannot arise. Revisit if an independent participant is ever added. Deferred also: what
becomes of the Prometheus endpoint on 6060, since the v0.8.0 monitoring milestone
wants to scrape it and that decision belongs there.

AppSec keeps `listen_addr: 0.0.0.0:7422` and the LAPI keeps its `127.0.0.1` host
publication for the host-firewall remediation bouncer. Neither is an oversight: the bind cannot
be loopback across containers, and the host publication is a mechanism no container
reaches.

## 2026-08 · Binary controls and values have separate owners

`security-baseline.md` owns the controls that are on or off: `no-new-privileges`,
`cap_drop`, secrets through Docker Secrets or `_FILE`, socket access, network
isolation. `compose-structure.md` owns every rule that carries a number, together
with the derivation that produces it.

Resource limits were defined in both. `security-baseline.md` held a profile table
with fixed `memory`, `cpus` and `pids` values and called the block optional;
`compose-structure.md` held a role table with the same limits, their basis, and
called it required. Neither file appeared in the File Map for this fact, so the two
versions had no defined relationship and drifted apart on whether a CPU limit is set
by default.

The split follows what each file can answer. A binary control is met or it is not,
and a checker decides it. A value has a derivation behind it and a failure mode when
it is set too low, which is the treatment the deriving text already carries.

This applies beyond the resource block: a rule that carries a number belongs in
`compose-structure.md`.

## 2026-08 · Memory and pids bound the host, CPU does not

An unbounded memory leak runs until the kernel OOM-killer fires, and the process it
selects is not necessarily the one that allocated. A fork bomb exhausts the global
pid space, after which the host starts no further process, including a login shell.
`memory` and `pids` are set on every service for that reason.

A CPU limit addresses a different failure. Under contention the scheduler distributes
cycles, so a container spinning on the CPU makes other containers slow rather than
unavailable. `cpus` is therefore not part of the baseline.

Two dozen services carry one anyway, with the values of the profile table that was
removed — a derivation, not a measurement. `compose-structure.md` admits that state
explicitly and requires the compose file to declare it beside the value, so a reader
can tell a derived ceiling from a measured one. v0.10.0 resolves it per service.

`security-baseline.md` stated that `deploy.resources` "caps memory and CPU so a
single container cannot exhaust the host under load or during a memory leak". That
holds for memory and not for CPU, and it was the reasoning behind the `cpus` column
in its profile table. Both were removed with the section.

## 2026-08 · The Traefik service port stays a literal

`traefik-labels.md` states that the container-internal port is hardcoded per app,
because it is a property of the image rather than of the deployment. 39 of 51 label
lines used `${APP_INTERNAL_PORT}` instead, including `apps/_reference`, and the
variable was defined in no standard.

The tree was brought to the standard rather than the reverse. `APP_INTERNAL_PORT` is
removed from every compose file, from the four healthchecks that read it, and from
every `.env.example`. Changing the value moves the label away from the port the image
listens on, so it breaks routing instead of relocating it.

## 2026-08 · No review gate on `main`

Branch protection on `main` requires seven status checks and no approving review.
With a single maintainer, a required review is satisfied by the author approving
their own pull request, which records an approval that nobody performed. The status
checks are the part of the gate that reports a result.

`CHANGELOG.md` recorded five checks and one approving review. That was not the live
configuration.

## 2026-07 · Two troubleshooting documents, one entry point

`TROUBLESHOOTING.md` is the symptom index and the place to start: what you
observe, its cause, its fix, including app-specific traps. `docs/standards/troubleshooting.md`
is the method — which layer is broken, and the commands that interrogate each one.
Both were catalogues without a stated relationship; neither is merged, because the
deep links from Traefik, CrowdSec and the IPv6 documentation already follow that
split. Owners are in the File Map.

## 2026-07 · Register follows the section purpose, not the repository

The neutral-language rule was written for German drafts and its scope over the
English documentation was never stated. Resolved at `writing-style.md`: imperative
and direct address where the reader performs steps, declarative and neutral where
they establish what is true. No repository-wide language rule overrides a section
contract.

## 2026-07 · Backup agent runs on the host

A containerised backup agent needs `/:/host:ro` or `--privileged` to reach other
stacks' data — which makes it a container able to read every secret in the
deployment. The security baseline already treats the Portainer Agent's host mount as
its one documented deviation of that kind.

Database consistency still reaches into containers: Borgmatic's `container:` option
(2.0.8+) resolves the address through Docker and dumps without published ports.

**Open:** this conflicts with the portability design goal in `architecture.md`
("no host-specific assumptions beyond Debian + Docker"). Needs to be recorded there
as an explicit exception, or revisited — carried in `state.md` as the open decision
on the host-installed agent.

## 2026-07 · Backup covers two directions

`backup/` covers the host outward (Borgmatic) and the operator's own devices inward
(UrBackup). They solve different problems; neither replaces the other. Kopia stays
a named alternative for operators wanting a UI or object storage.

## 2026-07 · One status model, two axes

Public status (what an operator can rely on) and internal status (what the
maintainer has established) are separate axes with a defined mapping. The ten
baseline-aligned criteria are the single gate between them. Full definition in
[`../docs/standards/status-model.md`](../docs/standards/status-model.md).

**Reason:** three status systems previously ran in parallel with no derivation
between them, so drift was structural rather than accidental.

## 2026-07 · LIFECYCLE.md is generated

Derived from the owning files by `scripts/ci/lifecycle-report.py`, never hand-edited.
The previous hand-maintained version covered 6 of 54 stacks, was three months stale,
and claimed backup documentation that no stack had.

## 2026-07 · One canonical app template

`apps/_reference/` is the only template — runnable, not a paper skeleton. The former
`docs/templates/` was folded into it.

## 2026-06 · IPv6 dual-stack is opt-in

`proxy-public` stays IPv4-only by default so existing installations are unaffected;
`network-dual-stack.yml` enables IPv4+IPv6. Tailscale ingress needs it to preserve
real client IPs. See `core/traefik/docs/ipv6-dual-stack.md`.

## 2026-04 · Five top-level categories, split by access pattern

Not by audience. `monitoring/` and `backup/` are top-level rather than under `apps/`
because they reach across service boundaries and need broader permissions.
Established in v0.2.0 as the Structure Stable Baseline — forks can rely on it.

## 2026-04 · Choice-matrix instead of defaults

Where several tools compete, multiple options are included and the operator picks by
preference. Applies to dashboards, photo galleries, wikis, form builders, uptime
monitoring. Documented per category README.

**Narrow exception:** for deduplicating backup tools one is recommended, because two
repositories mean two retention policies and two restore rehearsals — a real
operational cost that does not exist for monitoring tools covering different axes.

## 2026-09 · The CrowdSec reverse-proxy integration is switched in `.env`, never by editing a template

**Decision.** `CROWDSEC_BOUNCER_ENABLED` in `core/traefik/.env` is the only way the
bouncer plugin and the `crowdsec-basic` / `crowdsec-appsec` middlewares reach a
rendered configuration. `render.sh` emits the plugin block between two markers in
`traefik.yml.tmpl` and renders `dynamic/crowdsec.yml.tmpl` when the switch is
`true`; with `false` it strips the block and removes the rendered middleware file.
The plugin version is `CROWDSEC_BOUNCER_PLUGIN_VERSION`, the key
`CROWDSEC_BOUNCER_KEY`; `validate.sh` refuses the switch without a key or with a
version that is not a release tag, and refuses a `config/` that disagrees with
`.env` in either direction.

**Why.** The previous flow had the operator uncomment blocks in two tracked
templates. A checkout restored the comments, and the next render silently wrote a
configuration without the plugin and without the middlewares while the running
container kept both — a host was found in exactly that state on 2026-09-13,
templates pristine, rendered files enabled, plugin at a version the template no
longer named. State that is meant to differ per host belongs in `.env`; a tracked
file cannot hold it.

**Consequences.** `render.sh` refuses to render over a `config/` that carries the
integration while `.env` does not declare the switch, so the drifted host is
stopped rather than silently downgraded; the README carries the migration. The CI
gate no longer greps templates for commented blocks — it renders `core/traefik`
with the shipped `.env.example`, then with the switch on and off, and judges each
result. Switching off while routers still name the middleware disables those
routers; the README says to detach first.

## 2026-09 · Swap is bounded per service, and the host reserve is an invariant without a mechanism

A memory limit does not bound what a container takes from the host. With
`memswap_limit` unset Docker grants as much swap again as the memory limit —
confirmed against the running daemon, where an unset value renders `MemorySwap` at
twice `Memory`. A container inside its cap can therefore page a host into
unusability and never be killed, because the container OOM-killer fires only when
memory and the swap allowance are both exhausted.

So every service with a memory limit states a swap policy. The mechanism is fixed
and the value is not: equal to `memory` means no swap and is the default choice;
above it is a deliberate, justified amount. Unset is no longer acceptable, because
the amount is then accidental. `memswap_limit` does not conflict with a `deploy:`
block, unlike `pids_limit`. `compose-structure.md` owns the values as it owns every
number; `security-baseline.md` owns the binary requirement.

`no-resources` becomes a FAIL in `check-structure.py`. Every service in the tree
already carries both limits, so the rule now guards the property rather than
reporting drift toward it. The swap rule lands as a WARN counted per compose file —
making it a FAIL today would fail seventy stacks to prove a policy exists, and one
line per file keeps the report readable while v0.10.0 calibrates the values.

**The host reserve is approved as an invariant and not as a mechanism.** Workload
pressure must not consume what management and recovery need, and Foundation/Host owns
that. The candidate — a separate cgroup hierarchy for container workloads plus memory
protection on the slice holding management services — is documented, not installed:
it has never been rehearsed under real pressure, and an untested protection is an
assumption. `docs/architecture.md` carries what a rehearsal has to establish.

`live-restore` joins the reference daemon configuration. It removes one avoidable
restart storm — the one a Docker package update causes — and it is documented for
what it is: no help across a reboot, none across a major daemon version, and no
substitute for per-service limits.

## 2026-09 · Capabilities, with one reference implementation each

The blueprint is a set of capabilities — Foundation, Reverse Proxy, Identity & Access,
Threat Detection & Remediation, Web Application Security, Network Security — and each has
at most one product that this repository actually configures and tests. The capability
answers whether a deployment needs the function; the product is replaceable. Both
questions were previously answered by naming a product.

`docs/architecture.md` owns the model: the capability table, the Foundation boundary, the
exposure classification, the state-ownership rule and the application contract. Stack
READMEs stay product documentation. The directory split by access pattern is unchanged —
the capability model is a layer above it, not a replacement for it.

Three states are kept apart: **implemented** (configured and exercised here),
**documented alternative** (described so a fork can choose it, not maintained here) and
**evaluation candidate** (no claim of support). Current: Traefik, Authentik and CrowdSec
implemented; CrowdSec AppSec the current Web Application Security reference with Coraza +
OWASP CRS a documented alternative — mature engine, but the Traefik open-source
integration is not mature enough to adopt; Suricata an evaluation candidate for passive
network IDS, not implemented and not baseline. SIEM, XDR and SOC platforms are out of
scope: different operating model, and a secure Docker host does not need one.

**An application does not intrinsically require Traefik.** It requires the reverse-proxy
capability when served over a network, and most stacks ship a local compose file that uses
no proxy at all. The concrete integration vocabulary stays Traefik-specific
(`APP_TRAEFIK_*`, `acc-tailscale`) because the implementation genuinely is — renaming
waits for a second implementation that creates the need.

## 2026-09 · CrowdSec has a Core and two independent remediation points

"Phase 1 / 2 / 3" is retired from current documentation. It implied an order that the
repository's own text contradicted: the two enforcement components are peers, and neither
depends on the other.

    Core  →  Reverse-Proxy Remediation
          →  Host-Firewall Remediation

Core detects, decides and serves decisions over the LAPI. **Core alone blocks nothing** —
that sentence belongs early in every CrowdSec entry document, because a detector with no
remediation attached is a detector.

Which remediation applies follows from exposure, not from a sequence: a public HTTP
application behind the proxy is covered by reverse-proxy remediation without any host
firewall work; a service terminating on the host and reachable publicly is the case
host-firewall remediation exists for. Both may run together, at different enforcement
points, and that remains a choice.

The verified host-firewall work is reclassified, not revised: ingress scoping, structural
management-plane exclusion, the FORWARD path, set-only ownership, the prepare/cleanup
lifecycle, the readiness gate, fail-open, the range limitation and the rollback and reboot
models all stand unchanged under Host-Firewall Remediation. Historical records keep the
old numbering — it is accurate for the architecture of their time.

## 2026-09 · The dashboard follows the certificate strategy, like every router

The Traefik dashboard router carried `tls.certResolver` unconditionally, so a
wildcard deployment issued a second certificate for its dashboard hostname and
published that name in Certificate Transparency — the exact outcome the wildcard
path exists to avoid. No rationale for the exception existed anywhere; the
configuration could not express the consistent alternative, because `validate.sh`
required the variable to be non-empty.

The dashboard now follows the selected strategy: empty resolver under a covering
wildcard, its own resolver otherwise. Coverage is checked as the actual
relationship between `TRAEFIK_DASHBOARD_HOST` and `ACME_WILDCARD_DOMAIN`, not as
"a wildcard is configured somewhere" — the two are independent free-form
variables, and `*.example.com` matches exactly one label. An explicit resolver
under a covering wildcard stays supported and warns, because refusing it would
fail validation on every existing installation over a privacy preference rather
than a fault.

Migration is forward-looking only. Traefik loads every certificate in `acme.json`
at startup regardless of router references and renews it on expiry alone, and it
documents no way to retire a single stored certificate. An existing dashboard
certificate therefore keeps being served and renewed, and a published hostname
stays in the append-only logs.

**How this was found matters for how the next report is read.** External field
feedback reported an HTTP-01 deployment silently receiving Traefik's default
certificate and proposed enabling `certresolver` across the Compose files. That
proposal was declined: the operator had chosen a documented alternative path and
skipped its documented requirement, and the commented label is what makes the
wildcard path work. Investigating the claim is what surfaced the real defect,
one the report never mentioned — in the dashboard, not the applications.
Evidence to investigate, not a specification to implement.

## 2026-08 · Host-firewall remediation stays scoped, and ships without range enforcement

Host CrowdSec enforcement keeps its shape: `hook forward`, priority `filter - 10`,
an explicit ingress-interface match on the public interface, no generic INPUT
chain. The interface match is the management-plane guarantee; the LAPI AllowList
for the VPN ranges is defence in depth behind it.

The blueprint owns both nftables tables, **both** blacklist sets and the scoped
chains. The bouncer owns set membership and nothing else. Both sets are created
deliberately even though this bouncer version can auto-create the IPv4 one, so no
per-family special case survives into operation and "state is ready" stays a
single predicate.

The set schema is `flags timeout` for both families. **`flags interval` must not
be used.** nftables supports it and represents CIDR correctly, but the installed
bouncer cannot populate an interval set — the commits fail and the sets stay
empty, which is worse than the problem it would solve.

The consequence is accepted rather than worked around: host-firewall remediation enforces
**individual source-IP decisions**, IPv4 and IPv6. Range decisions degrade to
their network address at this layer. That is a coverage limit and not a lockout
risk — it blocks less than intended, never more, and cannot reach the management
plane. Proceeding on individual-IP enforcement does not wait for range support,
and no unverified future package is planned around.

## 2026-08 · Artefacts stand alone; the test environment is evidence, not specification

Every file is written for whoever opens it, and states the final result and the
facts needed to use, operate or verify it. The route taken — experiments, the
test host, rejected alternatives, how it differs from another file — is working
context and stays out. A `docker-compose.local.yml` says how to run it, and
nothing else.

The environment this repository is developed and tested on is evidence about the
software, never part of its specification. No requirement, dependency, default,
deployment assumption or documentation obligation follows from it alone. The
test host runs every stack behind one proxy; a reader takes one stack. The
working unit for repository-facing docs: an instruction has to be true for
someone running exactly one stack.

## 2026-08 · A local test stack per stack, where one means anything

`docker-compose.local.yml` beside the production file, publishing on
`127.0.0.1` with plain credentials, so an application can be tried without a
proxy, DNS or certificate. Shape and header in
`docs/standards/compose-structure.md`; the Local column in `LIFECYCLE.md` is
generated, so the coverage figure cannot drift.

Stacks that show nothing run alone have none — a reverse proxy, an agent
reporting to a central instance, something needing host networking, a client for
another stack's data. A reasoned absence is the outcome, not a gap.

## 2026-04 · Hub-and-spoke networking per app

`proxy-public` shared and external; `app-internal` per app with `internal: true`.
Databases never join the public network and never publish a host port.

## 2026-04 · Config in git, secrets and data never

The compose file and `.env.example` are the portable artifact. `.env`, `.secrets/`
and `volumes/` stay on the host.

## 2026-04 · Security-first with documented exceptions

Hardening is the default; relaxing a control requires a written, per-app exception.
Deviations are never silent.
