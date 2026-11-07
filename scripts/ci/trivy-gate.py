#!/usr/bin/env python3
"""Report CRITICAL findings against the recorded exceptions; block on none of them.

The repository does not build the images it pins, so a finding is fixed by
moving the pin to an upstream release that no longer carries it. Where no such
release exists, the finding stays — and then it is an exception, recorded per
image in `.trivy-baseline.json` with the stacks that use the image, the reason
the pin cannot move and the risk of running it as it is.

A finding in an upstream image is information for whoever uses or updates the
stack, not a defect in this repository (DEC-079), so this script reports

- a CRITICAL finding that is not listed under its image's exception, and
- an image that stopped being scannable and is not acknowledged,

and exits 0 for both. It fails only on what the repository itself got wrong or
cannot vouch for: an exception without its stacks, reason, risk or findings —
the baseline is written by hand here — a report that could not be read, and an
image that discovery resolved and that left neither a report nor a failure.

There is no way to record what a scan found in bulk: an exception is a
judgement about one image, written by hand. `--prune` only removes what the
scan no longer finds — an entry for a finding that has gone is untidy, not
dangerous, so it is reported but never fails the gate.

  Keyed by repository, not by tag. `postgres:17.1` and `postgres:17.2` are the
  same upstream, and a pin bump should surface what is *new* rather than
  re-present everything.

Each stack named in an exception carries an "Open findings" section in its
README, and `lifecycle-report.py` marks it in LIFECYCLE.md, so whoever installs
the stack from the blueprint sees that it ships with known findings.

Usage:
  trivy-gate.py --results-dir DIR              # report; exit 1 only on own errors
  trivy-gate.py --results-dir DIR --prune      # drop findings the scan no longer finds
  trivy-gate.py --results-dir DIR --out FILE   # also write a GitHub summary

HIGH findings are counted by the summariser and by upstream-status.py, not
compared against exceptions here. The decision names CRITICAL as the line, and
a list that names everything is one nobody reads.
"""

import argparse
import json
import sys
from pathlib import Path

BASELINE = Path(".trivy-baseline.json")
SEVERITY = "CRITICAL"


def repository(image: str) -> str:
    """The image without its tag or digest.

    A colon also separates a registry from its port, so only a colon after the
    last `/` introduces a tag — `registry:5000/app` is a repository already.
    """
    base = image.split("@", 1)[0]
    head, sep, tail = base.rpartition(":")
    return head if sep and "/" not in tail else base


def findings(results_dir: Path) -> tuple[dict[str, set[str]], list[str]]:
    """{repository: {CVE, ...}} for CRITICAL findings, plus unreadable reports.

    A report that cannot be parsed is returned by name rather than skipped
    quietly: "could not be read" must never reach the gate as "found nothing".
    """
    found: dict[str, set[str]] = {}
    broken: list[str] = []
    for path in sorted(results_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            broken.append(path.name)
            continue
        image = data.get("ArtifactName")
        if not image:
            broken.append(path.name)
            continue
        for result in data.get("Results") or []:
            for vuln in result.get("Vulnerabilities") or []:
                if vuln.get("Severity") != SEVERITY:
                    continue
                cve = vuln.get("VulnerabilityID")
                if cve:
                    found.setdefault(repository(image), set()).add(cve)
    return found, broken


REQUIRED = ("stacks", "reason", "risk", "cves")


def load_baseline(path: Path) -> tuple[dict[str, dict], dict[str, str]]:
    """(exceptions keyed by repository, acknowledged unscannable repositories)."""
    if not path.is_file():
        return {}, {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return dict(data.get("exceptions") or {}), dict(data.get("unscanned") or {})


def accepted(exceptions: dict[str, dict]) -> dict[str, set[str]]:
    return {repo: set(entry.get("cves") or []) for repo, entry in exceptions.items()}


def incomplete(exceptions: dict[str, dict]) -> dict[str, list[str]]:
    """{repository: [missing fields]} — an exception must say who, why and what risk."""
    bad: dict[str, list[str]] = {}
    for repo, entry in exceptions.items():
        missing = [f for f in REQUIRED if not entry.get(f)]
        if missing:
            bad[repo] = missing
    return bad


def render_baseline(exceptions: dict[str, dict], unscanned: dict[str, str]) -> str:
    payload = {
        "_comment": (
            "CRITICAL findings that stay in a pinned image because no upstream release "
            "removes them yet. One entry per image repository, written by hand: the "
            "stacks that use it, why the pin cannot move, the risk, and the findings. "
            "Every other CRITICAL is reported by the scan (scripts/ci/trivy-gate.py). The goal "
            "is an empty list."
        ),
        "exceptions": {
            repo: {**{k: v for k, v in entry.items() if k != "cves"},
                   "cves": sorted(entry.get("cves") or [])}
            for repo, entry in sorted(exceptions.items())
        },
        # Repositories the scanner cannot reach, each with why. An unscanned image
        # contributes no findings, so one that is not listed here would silently
        # shrink what the scan covers — it is reported instead.
        "unscanned": dict(sorted(unscanned.items())),
    }
    return json.dumps(payload, indent=2, sort_keys=False, ensure_ascii=False) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-dir", required=True, type=Path)
    ap.add_argument("--baseline", type=Path, default=BASELINE)
    # An image that did not scan produces no report, so it contributes nothing to
    # the verdict. Left unsaid, "every CRITICAL is recorded" would quietly claim
    # cover it does not have — the same reason the summariser names these.
    ap.add_argument("--failures-file", type=Path,
                    help="TSV of images that did not scan, so the verdict states its reach")
    # Discovery, scanning and failure tracking must add up. An image in neither
    # list is a hole the other checks cannot see, because it leaves no trace.
    ap.add_argument("--images-total", type=int, default=0,
                    help="how many images discovery resolved; 0 skips the arithmetic")
    ap.add_argument("--prune", action="store_true",
                    help="remove recorded findings this scan no longer finds")
    # Appended, not written: trivy-summarize.py has already put the facts in the
    # step summary and the gate's verdict belongs under them, not over them.
    ap.add_argument("--out", type=Path, help="append a GitHub step summary here")
    args = ap.parse_args()

    if not args.results_dir.is_dir():
        print(f"error: {args.results_dir} is not a directory", file=sys.stderr)
        return 2

    found, broken = findings(args.results_dir)

    exceptions, acknowledged = load_baseline(args.baseline)
    known = accepted(exceptions)

    if args.prune:
        scanned_repos = set(found)
        for path in args.results_dir.glob("*.json"):
            try:
                image = json.loads(path.read_text(encoding="utf-8")).get("ArtifactName")
            except (OSError, json.JSONDecodeError):
                image = None
            if image:
                scanned_repos.add(repository(image))
        removed = 0
        for repo in list(exceptions):
            if repo not in scanned_repos:
                continue  # not scanned this time: nothing is known about it
            keep = sorted(known[repo] & found.get(repo, set()))
            removed += len(known[repo]) - len(keep)
            if keep:
                exceptions[repo]["cves"] = keep
            else:
                del exceptions[repo]
        args.baseline.write_text(render_baseline(exceptions, acknowledged), encoding="utf-8")
        print(f"  ✅ {args.baseline} pruned — {removed} finding(s) no longer found, "
              f"{len(exceptions)} exception(s) remain")
        return 0

    new = {repo: sorted(cves - known.get(repo, set())) for repo, cves in found.items()}
    new = {repo: cves for repo, cves in new.items() if cves}
    stale = {repo: sorted(cves - found.get(repo, set())) for repo, cves in known.items()}
    stale = {repo: cves for repo, cves in stale.items() if cves}

    total_found = sum(len(c) for c in found.values())
    total_new = sum(len(c) for c in new.values())
    scanned = len(list(args.results_dir.glob("*.json")))

    unscanned = []
    if args.failures_file and args.failures_file.is_file():
        for line in args.failures_file.read_text(encoding="utf-8").splitlines():
            if line.strip():
                unscanned.append(line.split("\t", 1)[0])

    lines = ["## Trivy CRITICAL findings", ""]
    lines.append(f"{total_found} CRITICAL finding(s) in this scan · "
                 f"{sum(len(c) for c in known.values())} recorded as exceptions · "
                 f"**{total_new} not recorded**")
    lines.append("")
    unexpected = [i for i in unscanned if repository(i) not in acknowledged]
    if unscanned:
        lines.append(f"This verdict covers the images that scanned. "
                     f"{len(unscanned)} did not, and nothing here speaks for them:")
        lines.append("")
        for image in unscanned:
            why = acknowledged.get(repository(image))
            lines.append(f"- `{image}`" + (f" — acknowledged: {why}" if why else
                                           " — **not acknowledged**"))
        lines.append("")
    unaccounted = 0
    if args.images_total:
        unaccounted = args.images_total - scanned - len(unscanned)
        if unaccounted:
            lines.append(f"⚠️ **{abs(unaccounted)} image(s) in neither list** — discovery "
                         "resolved them, and they produced neither a report nor a recorded "
                         "failure. Coverage cannot be established while that is true.")
            lines.append("")

    if unexpected:
        lines.append("### An image stopped being scannable")
        lines.append("")
        lines.append("An unscanned image contributes no findings, so the counts above "
                     "cover less than they did. Fix the access, or record it under "
                     "`unscanned` in `.trivy-baseline.json` with the reason. Reported, "
                     "not blocking.")
        lines.append("")
        lines += [f"- `{image}`" for image in unexpected]
        lines.append("")

    if broken:
        lines.append("⚠️ Reports that could not be read, named rather than counted as clean:")
        lines.append("")
        lines += [f"- `{name}`" for name in broken]
        lines.append("")

    bad = incomplete(exceptions)
    if bad:
        lines.append("### Exceptions without their reason")
        lines.append("")
        lines.append("An exception must name the stacks that use the image, why the pin "
                     "cannot move, the risk, and the findings.")
        lines.append("")
        for repo, missing in sorted(bad.items()):
            lines.append(f"- `{repo}` — missing: {', '.join(missing)}")
        lines.append("")

    if new:
        lines.append("### Not recorded")
        lines.append("")
        lines.append("Each is a CRITICAL with a published fix that the repository has not "
                     "yet accounted for. Raise the pin to an upstream release that "
                     "removes it. Only if none exists, list it under the image's "
                     "exception with the reason and the risk, and mark the stack's README. "
                     "Reported, not blocking.")
        lines.append("")
        for repo, cves in sorted(new.items()):
            lines.append(f"- `{repo}` — {', '.join(cves)}")
        lines.append("")

    if stale:
        lines.append("### Recorded but no longer found")
        lines.append("")
        lines.append("Remove them with `--prune`.")
        lines.append("")
        for repo, cves in sorted(stale.items()):
            lines.append(f"- `{repo}` — {', '.join(cves)}")
        lines.append("")

    summary = "\n".join(lines)
    if args.out:
        with args.out.open("a", encoding="utf-8") as fh:
            fh.write("\n" + summary + "\n")
    print(summary)

    if broken:
        print(f"  ❌ {len(broken)} report(s) unreadable — the gate cannot vouch for them")
        return 1
    if unaccounted:
        print(f"  ❌ {unaccounted} image(s) produced neither a report nor a failure — "
              "discovery and scanning disagree, so coverage cannot be established")
        return 1
    if bad:
        print(f"  ❌ {len(bad)} exception(s) without stacks, reason, risk or findings")
        return 1
    if unexpected:
        print(f"  ⚠️ {len(unexpected)} image(s) did not scan and are not acknowledged — "
              "reported, not blocking")
    if new:
        print(f"  ⚠️ {total_new} CRITICAL finding(s) not recorded — reported, not blocking")
        return 0
    if unscanned:
        print(f"  ✅ every CRITICAL finding is a recorded exception ({total_found}) — "
              f"across the images that scanned; {len(unscanned)} did not")
    else:
        print(f"  ✅ every CRITICAL finding is a recorded exception ({total_found})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
