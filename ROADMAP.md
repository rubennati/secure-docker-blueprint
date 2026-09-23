# Roadmap

Direction reviewed 2026-09-20.

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

**Latest tag: v0.9.2 — Stabilization and release readiness (2026-09-22).**
Eighteen stacks verified behind Traefik with TLS on a host, twelve new stacks,
and an image scan that fails on a CRITICAL finding it has not recorded. What has
and has not been established per stack is in [`LIFECYCLE.md`](LIFECYCLE.md).

### v0.10.0 — Measured resource limits

Every production service carries a memory, PID and swap ceiling, and states a
healthcheck or why it has none; `python3 scripts/ci/check-structure.py` fails on
any that does not. What remains is the values: the ceilings in place are derived
by rule, generously, and several compose files say so. Turning them into measured
values needs a running install per stack — the procedure is
[`docs/resource-measurement.md`](docs/resource-measurement.md), the target values
and the derivation rule are in
[`docs/standards/compose-structure.md`](docs/standards/compose-structure.md).

**Done when** every `✅` stack's limits come from a measurement on a real install
rather than from the derivation rule.

### v1.0 — Complete and hand-off ready

The criterion: someone else could fork this and deploy it without needing this
conversation.

**v1.0.0 is not tagged until both surfaces are ready — this repository and the
[SecDockBlue](https://secdockblue.rubennati.at) operator site.** The site has been
live since 2026-07-31; being live is not being finished. They stay separate
products with separate structures, and v1.0 is the one checkpoint they share.

Open in this repository:

- **Verification depth.** Every app verified at least once on a clean install, and
  no stack left at `scaffolded` without a documented reason. Most stacks are
  `scaffolded` today — [`LIFECYCLE.md`](LIFECYCLE.md) has the count. A state rises
  only on evidence, so this is measured in host sessions, not in editing.
- **Traefik labels and middlewares, checked against the applications.** The label
  pattern, the security chains and their names, the header and rate-limit blocks,
  and the CrowdSec and Authentik middlewares grew stack by stack; 99 stacks now
  route through Traefik. The review asks what each application needs to start
  without errors, keep the headers it sets itself and stay responsive under a
  working day's load. It may change names and structure or confirm them — before
  v1.0.0, because afterwards a renamed middleware disables the router of every
  deployment that names it. Inputs in [`.ai/state.md`](.ai/state.md) under *Open
  decisions*; what the proxy owns, what its limits are for and which questions
  the review has to answer are collected in
  [`docs/audits/reverse-proxy-limits-2026-09-23.md`](docs/audits/reverse-proxy-limits-2026-09-23.md).

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
  [`LIFECYCLE.md`](LIFECYCLE.md) marks each `pin-drifted` and carries the pin.
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

## Being added — the held candidates

The candidates this file held until 2026-09-22, and two proposed that day, are
narrowed to open-source products and added in batches, each its own pull request
and each stack landing `scaffolded`. It is a second deliberate exception to the hold below and changes
nothing v1.0 requires — reasoning in [`.ai/decisions.md`](.ai/decisions.md),
evidence and batch order in
[`docs/audits/candidate-evaluation-2026-09-22.md`](docs/audits/candidate-evaluation-2026-09-22.md).
Each category README owns what it still plans: [`apps/`](apps/README.md),
[`business/`](business/README.md), [`monitoring/`](monitoring/README.md),
[`backup/`](backup/README.md), [`core/`](core/README.md).

Two of them are capabilities rather than applications, and each needs a design
answer before its stack:

- **Network IDS — Suricata.** A passive IDS sees packets, flows and protocol
  anomalies that log-driven detection cannot. On one Docker host the physical
  interface carries TLS to Traefik; inspecting payloads means capturing the Docker
  bridges, which carry the plaintext traffic between Traefik and each application.
  CrowdSec's Suricata collection bans a source on a single severity-1 alert, so the
  alerts reach CrowdSec without that scenario or not at all. Open: which interfaces,
  the cost under deep packet inspection, and the false-positive load. Passive
  only — inline IPS drops traffic when the engine is down, the failure mode this
  blueprint avoids elsewhere.
- **Web application firewall — Coraza.** CrowdSec AppSec is the reference
  implementation; Coraza with the OWASP Core Rule Set is the documented
  alternative. The open-source Traefik plugin describes itself as experimental and
  in need of a maintainer, and Traefik's native Coraza integration is part of the
  commercial Traefik Hub. CrowdSec's AppSec engine is built on Coraza and offers the
  Core Rule Set as a collection, whose rule files are a 2022 pre-release. Running
  both inline is not the answer.

---

## On hold — after v1.0 or not yet needed

No application is added while the v1.0 items above are open. Two exceptions were
made: on 2026-09-21 twelve proposed products that publish a versioned image went in
as stacks so they can be tried, and on 2026-09-22 the candidates this section held
were narrowed and are being added — see
[Being added](#being-added--the-held-candidates). Both change nothing v1.0 requires;
reasoning in [`.ai/decisions.md`](.ai/decisions.md), evidence in the two evaluations
under [`docs/audits/`](docs/audits/).

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
