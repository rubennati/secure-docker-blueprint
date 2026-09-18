# Custom applications

Where a deployable image comes from when this repository produces it rather than
pulls a published one — and what stays exactly the same once the image exists.

This document owns one phase. Everything after the image is unchanged and already
owned elsewhere, so nothing downstream is restated here. Two stacks in this
repository already build their own image, in two different shapes; both are cited
as the evidence they are, and nothing below was invented to fill a gap.

---

## What differs, and what does not

| Phase | Custom application | Owner |
|---|---|---|
| Source | exists — a Dockerfile here, or a codebase in its own repository | this document |
| Build | exists — the image is produced, not fetched | this document |
| Image identity | the identity has to be established rather than read off a vendor tag | this document |
| What verifies the image | differs by shape, and is partly unverified — see [What verifies this](#what-verifies-this-and-what-does-not) | this document |
| Configuration and secrets | unchanged | [`secrets.md`](secrets.md), [`env-structure.md`](env-structure.md) |
| Local execution | unchanged | [`compose-structure.md`](compose-structure.md) |
| Production deployment | unchanged | [`compose-structure.md`](compose-structure.md), [`networking.md`](networking.md), [`traefik-labels.md`](traefik-labels.md) |
| Security baseline | unchanged at service level | [`security-baseline.md`](security-baseline.md) |
| Operation | unchanged | the stack's own `README.md` and `UPSTREAM.md` |
| Recovery | unchanged for data | [`restore.md`](restore.md) |

That table is the point of this document. A custom application is not a different
kind of stack — it is the same stack with four extra phases in front of it.

---

## The shapes

Three exist here. They are not instances of one procedure; each answers the same
question — where does the deployable image come from — differently.

**In-repo build layer** — [`business/vikunja`](../../business/vikunja/). The source
is a `Dockerfile` in the stack directory, the stack's own Compose file builds it,
and the base is a published third-party image. It exists because the upstream image
is `FROM scratch`: no shell to inject secrets with, no `cat` to read them, no
`wget` for a healthcheck. The build adds the minimum and nothing else.

**External governed pipeline** — [`apps/caldiy`](../../apps/caldiy/). The source
lives in its own repository with its own review gate, that repository publishes
versioned images, and this repository consumes a tag or digest like any vendor
image. It exists because a live instance was compromised, so every upstream change
is now reviewed before it can reach a deployable image. Its branch contract and
governance documents are recorded in
[`apps/caldiy/UPSTREAM.md`](../../apps/caldiy/UPSTREAM.md).

**Reusable pattern, no concrete application yet** —
[`development/static-site/`](../../development/static-site/) and
[`development/web-api/`](../../development/web-api/). Both build a project's
own source into a hardened production image; neither has a real application
behind it. Adoption is by copying the pattern into `apps/` or `business/` under
the real project's name, not by reference — at that point the copy is one of
the two shapes above, most often the in-repo build layer, and this document's
rules apply to it the same way. Each pattern is proven by a minimal fixture —
a working build that produces a healthy container — which establishes that the
pattern's Dockerfile and Compose shape are correct. It does not establish that
any real, adopted project has gone through it yet; that evidence starts
accumulating the first time a project is actually copied out.

The shapes differ in where the build lives, which follows from what is being
built: a thin delta over a published image, a codebase with its own release
surface, or a starting point with no codebase yet. `business/vikunja` and
`apps/caldiy` are shaped the way their own history made necessary; the
`development/` patterns are shaped the way a reusable starting point has to be
— generic enough to copy, complete enough to prove the contract without
becoming a product of their own (see
[`development/README.md`](../../development/README.md)).

---

## What is required

Four rules. Each is either already binding elsewhere in this repository, or
evidenced by both shapes.

**No secret material in any build stage or image layer.** `ARG` values and
`--build-arg` are readable in image history, so they carry pins and nothing else.
Secrets reach the container at runtime as files, exactly as
[`secrets.md`](secrets.md) requires everywhere else. The build is a new surface for
that rule, not an exception to it.

**The deployed image identity is explicit, reviewable, and traceable to the source
or build that produced it.** Mutable floating references are not accepted — no
`latest`, no tag that moves. This is the level both shapes share; how each one
reaches it differs, and the difference is not a rule:

- `business/vikunja` pins its base image as a tag **and** digest pair, both held in
  `.env.example` and both passed to the build.
- `apps/caldiy` relies on the fork's governed release pipeline plus a reviewed
  release tag or digest — never `latest`.

A reviewed registry tag is not inherently immutable, so "immutable" is not the
shared requirement; explicit, reviewable and traceable is.

**Where the image comes from, and what gates it, is written down here** — in the
stack's [`UPSTREAM.md`](../../apps/_reference/UPSTREAM.md), which already owns
upstream facts. For an in-repo build that means the base image and why the build
exists. For an external pipeline it means the source repository, the branch that
publishes, and the governance documents by name. This repository records the
pointer; it does not duplicate a fork's process documents.

**Everything after the image follows the existing standards unchanged.** A stack
that builds its own image gets no relaxation of the baseline, the network model,
the secrets handling or the restore expectations.

---

## What this repository has not established

Real engineering practice appears in these stacks that is *not* a rule here. Each
of the following is what one case does, recorded so the next stack can copy it
deliberately — not a requirement, because one instance is not a pattern:

- **Digest-pinning the deployed image universally.** A plausible future
  requirement. Only one of the two shapes does it, and the other accepts a reviewed
  tag, so the evidence does not support making it binding.
- **`<app>-local:${APP_TAG}` as the name of a self-built image.** Vikunja only. The
  reasoning is sound — the name says the artifact is not in any registry — but it
  is one stack's convention.
- **A `build:` block in the local Compose file as well as production.** Vikunja
  only, and only because it has a local stack at all.
- **An explicit `USER` in the final stage.** Vikunja declares it so static analysis
  does not report an implicit root user, even though the base already runs as
  uid 1000. Good practice; unverifiable for the external shape, which builds
  elsewhere.
- **Digest-pinning every `FROM`.** Vikunja pins both of its base images. This is
  also the rule that would have caught the drift described below.
- **`build --pull` then `up -d` as the upgrade shape.** A factual consequence of
  having a build, not a policy — and it has to include re-resolving the pin.
- **Including build inputs in the recovery set.** A self-built image is in no
  registry, so a restored volume with nothing to rebuild from is not a complete
  restore. This is **not evidenced at all** — no restore rehearsal has ever involved
  a self-built image — so it is a gap in [`restore.md`](restore.md)'s coverage
  rather than a rule.

---

## What verifies this, and what does not

The honest coverage, including where it is worse than for a pulled image:

| Property | Verified by | Gap |
|---|---|---|
| Image CVEs | Trivy, for registry images only | **In-repo builds are not scanned.** `scripts/ci/list-images.sh` skips `*-local:*` because Trivy cannot pull a locally built image, so `vikunja-local` is the one production image in this repository with no CVE scan. The external shape has no such gap — its image is in a registry and is scanned. |
| Dockerfile contents | nothing | No checker reads a Dockerfile. An unpinned or `:latest` `FROM` passes CI silently; `check-structure.py`'s tag rules read Compose `image:` values only. Trivy's config scan touches it and is non-blocking. |
| Base image freshness | nothing | Renovate's custom managers match `.env.example`, and the `FROM` line resolves its tag from a build arg, so the base pin of the one in-repo build is watched by nothing. |
| Pin correctness | nothing | **This has already drifted unnoticed.** `business/vikunja/.env.example` carries `APP_TAG=2.6.0` alongside the digest that the `Dockerfile` pairs with its `2.3.0` default — the tag was bumped and the digest was not. Because `FROM` resolves by digest, the build labels an older base as the newer version. Nothing caught it, which is the concrete reason the pin rule above exists. |
| Image signing / provenance attestation | nothing | Not done anywhere in this repository, for any image. |
| External build governance | the fork's own review gate | Unverifiable from here. This repository can name `FORK_PROCESS.md`, `SECURITY_REVIEW.md`, `IMAGE_BUILD.md` and `RELEASE_PROCESS.md`; it cannot check that they were followed. |

Two further boundaries:

**Compose and env conventions have no build vocabulary yet.**
[`compose-structure.md`](compose-structure.md) says where a `build:` block goes and
nothing more; [`env-structure.md`](env-structure.md) has no digest convention, and
`APP_DIGEST` exists in exactly one `.env.example`.

**The baseline-aligned criteria were not extended.**
[`../maintenance.md`](../maintenance.md) requires an `UPSTREAM.md` naming an
upstream licence and a verified version. Both real cases satisfy that because both
have an upstream. A genuinely first-party application would have neither, and the
criteria still require both — this repository has no such stack to widen them for.

**No fully first-party application has been built or verified here.** The two
real stacks still wrap third-party software: one adds a layer to a published
image, the other governs a fork. `development/`'s patterns give source with no
upstream at all a shape to start from, established because the need for a
reusable starting point was real and current — but a pattern proven by its own
fixture is not the same evidence as a real project that went through it. No
project has been copied out of `development/` and operated yet, so this row
stays a gap until one has.
