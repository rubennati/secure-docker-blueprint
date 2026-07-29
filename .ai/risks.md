# Risks

Known risks carried deliberately, with what would reduce them. Not a threat model
for deployments — that is `docs/security-verification.md`.

| Risk | Impact | Current mitigation | What would close it |
|---|---|---|---|
| **No restore evidence anywhere** | A backup that has never been restored may not be one. Applies to every stack. | Restore procedure written and rehearsable | v0.7.0 Block 2 — one performed, documented restore |
| **Nine major versions pinned but never started** | Paperless 3.x, WordPress 7.x, Immich 3.x and others are advertised at a version nobody has run. Paperless needs a search-index migration. | Flagged in `docs/maintenance.md`; status honest | Host session, Block 4 |
| **22 stacks with legacy verification stamps** | `Last checked:` predates the current format; the evidence behind ✅ is older than the claim | Reported as `legacy-stamp`, non-blocking | Per-app judgement during the host session |
| **Single maintainer** | No second reviewer; a mistaken decision has no second pair of eyes | CI gates catch mechanical errors; branch protection on `main` | Structural — accepted |
| **Author-maintained container images** | `uroni/urbackup-server` and the Cal.diY fork are not vendor-official releases | Digest-pinned; documented in each `UPSTREAM.md` | Re-pin on upgrade; watch upstream |
| **Rolling upstream tags** | Some projects publish no exact semver (`2.5.x`, `main`) | Digest pinning, re-resolved per upgrade | Upstream would have to change |
| **Services without resource limits** | An unbounded container can exhaust the host | Counted per service by the structure checker; the current figure is the v0.9.0 progress bar in `ROADMAP.md` | v0.9.0 — needs values measured on real installs, never guessed |
| **Trivy findings unassessed** | CRITICAL image findings exist and do not block | Weekly scan, results in the Security tab | One assessment pass, then raise `exit-code` |
| **Checker coverage assumptions** | Three blind spots surfaced in one day: split compose files, components without compose, a whole category missing from the checker roots | All three closed, and `scripts/ci/check-coverage.py` now fails CI on a content directory no checker enumerates — tested against both gap classes | Add it to the required set in branch protection |
