# Domain — Verification

This is a configuration project: the CI pipeline is its test suite, and a real
deployment is its acceptance test. Neither substitutes for the other.

**Specs:** [`quality-gates.md`](../quality-gates.md) ·
[`docs/standards/ci.md`](../../docs/standards/ci.md) ·
[`docs/security-verification.md`](../../docs/security-verification.md)

## Three levels

| Level | Catches | Where |
|---|---|---|
| Static | structure, tags, plaintext secrets, exposed datastores, status contradictions | `scripts/ci/*.py`, locally and in CI |
| Compose | files that do not parse or resolve | `docker compose config` |
| Real | everything that matters | a clean install on a host |

## The bar for ✅

Ten criteria in `docs/maintenance.md`, of which three cannot be automated: a clean
install completed, the core function actually usable, and Traefik routing confirmed.
"The container is running" is not one of them.

## Evidence over exit codes

- A directory tree of correctly named empty files is a failure, not a restore.
- A backup job reporting success proves the job ran, not that the archive is usable.
- A dump command that errors while the run continues produces an archive that looks
  complete and contains nothing — make hooks fail loudly.

Verify the thing itself: a row count that can be sanity-checked, a page that loads, a
file whose content is what it should be.

## Verify before asserting

Never claim an image contains a tool, that a flag exists, or that a version is
current without checking. `docker inspect`, `docker run --rm <image> which …`, the
upstream documentation, the registry API. "I do not know, I will check" is a valid
answer; a wrong claim costs more than the check.
