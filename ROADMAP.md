# Roadmap

Planning overview. See [current evidence and shipped work](#current-evidence-and-shipped-work) for status sources.

What remains to be built, what blocks it, and what proves it finished. Shipped
work belongs to [`CHANGELOG.md`](CHANGELOG.md), per-stack status to the generated
[`LIFECYCLE.md`](LIFECYCLE.md), and per-category detail to the `README.md` in each
top-level directory. What the stabilization programme established, and what is
still open with the evidence behind it, is in
[`docs/v1-readiness-audit.md`](docs/v1-readiness-audit.md); actionable work is in
GitHub Issues. This file holds direction only.

---

## Direction

Pre-1.0 tags are set when a natural milestone is reached, not on a fixed cadence.
The single criterion for v1.0 is: **could someone fork this and run it without
needing my mental model?**

Current verification belongs to [`LIFECYCLE.md`](LIFECYCLE.md), which compares
current pins with recorded test versions. A release's successful host run does
not verify image pins changed afterwards. Work that remains is listed below.

### v1.0 — Complete and hand-off ready

**v1.0.0 is not tagged until both surfaces are ready — this repository and the
[SecDockBlue](https://secdockblue.rubennati.at) operator site.** The site has been
live since 2026-07-31; being live is not being finished. They stay separate
products with separate structures, and v1.0 is the one checkpoint they share.

Open in this repository:

- **Verification depth.** Every app verified at least once on a clean install, and
  no stack left at `scaffolded` without a documented reason. Most stacks are
  `scaffolded` today — [`LIFECYCLE.md`](LIFECYCLE.md) has the count. A state rises
  only on evidence, so this is measured in host sessions, not in editing.
- **Traefik middlewares, checked against the applications on a host.** The
  names and the structure are settled by the middleware model of v0.9.5: four
  positions on every router, defined once. What is not established is how the
  applications behave under it — the headers the office servers and Nextcloud
  set themselves, the `429` count of a first load under the bucket of 500, the
  TLS exceptions without a recorded reason. The list is section 5 of
  [`core/traefik/docs/middleware-model-migration.md`](core/traefik/docs/middleware-model-migration.md#5-not-verified-on-a-host);
  it is measured in host sessions, not in editing.
- **Trusted proxies narrowed to the Traefik hop.** An application behind its own
  nginx has to trust the proxy that sets `X-Forwarded-For` and `X-Forwarded-Proto`,
  and only that proxy. `business/invoiceninja` ships `TRUSTED_PROXIES` with the
  ranges measured on the step 8 lab host — Docker's default pools — as an interim
  value, not a standard: it trusts every container Docker can address.
  `apps/nextcloud`'s `NC_TRUSTED_PROXIES` asks for the edge network's subnet, which
  Docker assigns per host and anew when the network is recreated. The target
  (decision of 2026-11-04): `core/traefik` creates each edge network on a subnet
  the operator chooses, so the value is known and stays. A subnet is the same
  boundary as Traefik's own address only while the edge network holds Traefik and
  the stack's front container alone; an overlay that adds a member
  (`apps/nextcloud/office.yml` puts Nextcloud's nginx on the office server's edge
  network) or the shared `proxy-public` widens it, so the work decides whether the
  trust names the subnet or a fixed Traefik address in it. Not implemented; it is
  measured on a host before it replaces the interim value.

Decision pending, with a possible impact on v1.0 — the site's personal data:
see [A public repository should not carry personal data](#a-public-repository-should-not-carry-personal-data).

Open on the operator site:

- **Every shipped stack is discoverable.** A reader can find any application by
  name and by the problem it solves, and the catalogue is checked against the
  repository so it cannot silently fall behind again.
- **The reader path holds end to end** — someone arriving at any page can reach
  what they need next, and the navigation names subjects that match what is there.
- **Where alternatives need comparing, the site compares them** — by what each
  does differently, without ranking, and no product page defines itself through
  another product.
- **The security and operations material is complete for what the repository actually does**, with the layers it leaves to the operator stated rather than implied.
- **Every public claim agrees with the repository**, and a gap named there is a
  gap named here. Sections that exist are finished; a capability with no guide is
  named as having none rather than carried as a placeholder.

Site work does not otherwise wait for a version — see
[Continuous](#continuous--not-tied-to-a-version).

### v0.10.0 — Measured resource limits

Every production service carries a memory, PID and swap ceiling, and states a
healthcheck or why it has none; `python3 scripts/ci/check-structure.py` fails on
any that does not. What remains is the values: the ceilings in place are derived
by rule, generously, and several compose files say so. Turning them into measured
values needs a running install per stack — the procedure is
[`docs/resource-measurement.md`](docs/resource-measurement.md), the target values
and the derivation rule are in
[`docs/standards/compose-structure.md`](docs/standards/compose-structure.md).

**Done when** the stacks presented as verified have limits based on measurements
from real installations rather than on the derivation rule. The verification
states are defined in the [status model](docs/standards/status-model.md).

---

## Continuous — not tied to a version

**App testing runs in parallel to everything above.** When there is bandwidth,
pick a `scaffolded` app, run the App Chain, record the verified version. This
blocks and triggers no release. The bar rises with the repository: an app
verified today must meet the current baseline-aligned criteria in
[`docs/maintenance.md`](docs/maintenance.md).

- Verified before the standards moved and worth a second run: Vaultwarden,
  WordPress, Nextcloud, Seafile / Seafile Pro, Invoice Ninja.
- Pinned to a new major in a dependency sweep and not yet run anywhere —
  [`LIFECYCLE.md`](LIFECYCLE.md) carries the pin beside the version last verified,
  and `lifecycle-report.py --check` warns `pin-drifted` where the two differ.
- Never started on a host: UrBackup, `apps/vllm`, and the security-tooling,
  PAM/bastion and secret-sharing stacks added in v0.9.1.

**Cal.diY hardening** ([`apps/caldiy/docs/hardening-plan.md`](apps/caldiy/docs/hardening-plan.md))
runs on its own track. Phase 0 and Phase 1 configuration has landed; the Phase 0
acceptance checks are open and Phases 2 and 3 have not started.

**Operator site work** — content, structure and review — is continuous, and each
push to `main` that touches `site/` publishes. What is written there is public the
moment it lands, which is why the content gate sits in front of it.

---

## A public repository should not carry personal data

The site's legal notice and privacy statement hold a name, a postal address and an
e-mail; `security.txt`, `astro.config.mjs` and the footer carry the domain and
repository URLs. The repository is public and meant to be forked, so those values
travel with every copy — and a fork that builds and goes live unnoticed publishes
this author's imprint on a stranger's site.

**Direction, not yet a decision:** the personal values live in one gitignored
module (`site.local.ts`, decrypted from a committed `age`-encrypted file) that
overrides a committed placeholder module (`site.ts`), so a fork builds on the
first try with the fields empty and nothing personal in the tree. Values the build
cannot do without get a neutral placeholder (`example.com`, the repository's own
URL); name, address and e-mail go empty. The reasoning, the key-holder layout and
the local and CI decrypt commands are recorded in
[`.ai/decisions.md`](.ai/decisions.md) under *2026-09 · Personal data on the
public site*. The rule that no secret-management tooling belongs in the blueprint
itself stands: this concerns the site only.

---

## On hold — after v1.0 or not yet needed

**New applications are on hold while the v1.0 items above are open.** Discuss a
proposed exception before implementing a new stack. Improvements, security fixes,
verification and documentation for existing stacks remain welcome.
The [candidate](#added--the-held-candidates) and [mail-server](#added--mail-servers)
additions below record past exceptions; they do not lift the hold.

Concepts with no timeline, picked up app by app as they are re-verified:

- **Configuration tiers** — Minimum, Advanced and Expert layers per app.
- **App evaluation criteria** — stack size, security features, release cadence and
  privacy posture as factual per-app metadata. Open: where it lives without
  becoming a maintenance burden.
- **Deploy script** — `./deploy.sh <server> core/traefik apps/nextcloud`, rsync of
  the selected directories to a server.
- **Alternative container runtimes** — Podman, Docker Swarm, K3s.
- **MCP connectors** — the blueprint defines the pattern; individual servers live
  in their own repositories.
- **Network IDS — Suricata. Not a stack yet: two questions still need a disposable
  host.** A passive IDS sees packets, flows and protocol anomalies that log-driven
  detection cannot, and two of the four open questions now have answers. On one
  Docker host the physical interface carries TLS to Traefik, so inspecting payloads
  means capturing the Docker bridges — which carry the plaintext traffic between
  Traefik and each application, cookies and form data included. And
  `crowdsecurity/suricata` bans a source on a single severity-1 alert, so the alerts
  reach CrowdSec without that scenario or not at all. The two that remain — the cost
  under deep packet inspection and the false-positive load — cannot be measured on a
  host carrying live services, which is what adding the stack would require next.
  Passive only when it comes: inline IPS drops traffic when the engine is down, the
  failure mode this blueprint avoids elsewhere.

---

## Out of scope here

- SIEM, XDR and SOC platforms (Wazuh and comparable) — a different operating model:
  agents, central collection and someone to read the output. A secure Docker host
  does not require one.
- `core/acme-certs/` — being extracted to its own repository. The blueprint stub
  remains `scaffolded` and is no longer actively maintained here.
- Paperless-mcp — will live in its own repository once built.
- The engineering above an AI deployment — model evaluation, retrieval
  architecture, prompt design. `apps/ollama`, `apps/vllm`, `apps/qdrant`, `apps/litellm`,
  `apps/open-webui`, `apps/agentgateway`, `apps/dify` and `monitoring/langfuse` deploy and
  harden the services; choosing models and judging retrieval is a different
  project. See [`docs/architecture.md`](docs/architecture.md#ai--local-ai-is-deployment-not-engineering).
- A general, orchestrated document-processing pipeline. `apps/docling-serve`
  provides document understanding for AI/RAG pipelines, consumed directly by
  whatever calls its API; building the orchestration before a real case needs it
  would produce an untestable chain. See
  [`docs/architecture.md`](docs/architecture.md#document-processing-has-the-capabilities-and-one-standalone-service).
- OCRmyPDF as a standalone stack. Upstream ships its image as ephemeral — one
  container per job, exiting like a command-line program. A CLI/job tool with no
  independently operated service gets no blueprint entry.
- The products evaluated on 2026-09-22 and not added — each is named with its reason
  in [`docs/audits/candidate-evaluation-2026-09-22.md`](docs/audits/candidate-evaluation-2026-09-22.md#decided-on-2026-09-22).
- The mail servers evaluated on 2026-10-03 and not added — each is named with its
  reason in [`docs/audits/candidate-evaluation-2026-10-03.md`](docs/audits/candidate-evaluation-2026-10-03.md#decided-on-2026-10-03).

---

## Current evidence and shipped work

- **Verification at current pins:** [`LIFECYCLE.md`](LIFECYCLE.md). Historical
  test results do not carry forward automatically after a pin change.
- **Shipped changes:** [`CHANGELOG.md`](CHANGELOG.md). The v0.9.7 record includes
  the ingress host run and the later image updates; those updates left many
  stacks awaiting verification at their new pins.
- **Version-update history:** the [2026-10-31 inventory and batch plan](docs/audits/upstream-version-inventory-2026-10-31.md)
  describes the starting point. The later sweep is recorded in the v0.9.7
  changelog and each stack's `UPSTREAM.md`; the old batch table is not a current
  backlog. New version work starts from the actual pins and current upstream
  evidence, following the [Version Chain](docs/maintenance.md#version-chain).
- **Active follow-ups:** [GitHub Issues](https://github.com/rubennati/secure-docker-blueprint/issues)
  and [the remaining local task list](.ai/tasks.md). Detailed historical findings
  remain in the [v1 readiness audit](docs/v1-readiness-audit.md).

### Added — the held candidates

**Historical decision, September 2026.** The candidate rounds were exceptions to
the application hold, not a change to the v1.0 goals. The September 22 candidates
were narrowed to open-source products, and sixteen stacks were added by September
24, each initially `scaffolded`. The [September 21](docs/audits/candidate-evaluation-2026-09-21.md)
and [September 22](docs/audits/candidate-evaluation-2026-09-22.md) evaluations
retain the product-by-product evidence; the [decision record](.ai/decisions.md)
explains the exceptions. Verification at current pins belongs to the backlog
above and `LIFECYCLE.md`.

Two candidates represented capabilities rather than applications:

- **Coraza — use the capability already present.** CrowdSec's AppSec engine uses
  Coraza. Its optional OWASP Core Rule Set is installed through the hub
  collections `crowdsecurity/crs` and `crowdsecurity/crs-inband`; it does not need
  a second standalone WAF stack. At the September 24 evaluation, the community
  Traefik integration was experimental and lacked a maintainer, while the native
  integration belonged to commercial Traefik Hub. That was the reason to document
  the existing capability instead of adding another implementation. The
  [AppSec guide](core/crowdsec/docs/appsec.md) owns installation and the reasons
  the CRS is not enabled by default; the evaluation's upstream observations are
  historical, not a fresh support assessment.
- **Suricata — questions still needing a disposable host.** The unanswered load
  and false-positive questions remain [on hold above](#on-hold--after-v10-or-not-yet-needed),
  along with the network visibility and failure-mode reasoning.

Each category README owns its planned products: [apps](apps/README.md),
[business](business/README.md), [monitoring](monitoring/README.md),
[backup](backup/README.md) and [core](core/README.md).

### Added — mail servers

**Historical decision, October 3, 2026.** [Stalwart](apps/stalwart/),
[docker-mailserver](apps/docker-mailserver/) and
[mailserver-jeboehm](apps/mailserver-jeboehm/) were added as a third exception to
the hold, each initially `scaffolded`, with mail ports published through an opt-in
overlay. The v1.0 requirements stayed the same.

At that evaluation Mailu met the selection requirements but was held until a
release carried the recorded security fix. The
[evaluation](docs/audits/candidate-evaluation-2026-10-03.md) owns that reason and
the other candidates not added; a new evaluation needs current upstream evidence.
The [decision record](.ai/decisions.md) preserves why the exception was made.
Verification at current pins belongs to `LIFECYCLE.md` and the backlog above.
