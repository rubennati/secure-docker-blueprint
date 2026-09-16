#!/usr/bin/env python3
"""
trivy-summarize.py — turn per-image Trivy JSON reports into one concise summary.

The image-CVE-scan job in trivy.yml runs `trivy image --format json` once per
discovered image, writing each report to its own file and recording any image
that failed to scan in a separate, plain-text failures list. Printing every
report's vulnerability table into the job log — as the previous shape did —
produces on the order of 98,000 log lines for the full image set, with no
running summary and no way to tell "not scanned" apart from "scanned clean"
without reading every entry. This script reads both inputs and writes the
summary GitHub renders on the job's own page, so the log stays short and the
report stays complete.

Full per-CVE detail is not discarded: it is exactly what the JSON reports this
script reads carry, and the workflow uploads that directory as a build
artifact. This script's job is the index into it, not a replacement for it.

Usage:
    trivy-summarize.py --results-dir DIR --failures-file FILE
                        --images-total N [--top N] [--out FILE]

`--results-dir` holds one `*.json` Trivy report per successfully scanned
image (the image reference is read from each report's own `ArtifactName`,
never inferred from the filename). `--failures-file` is a TSV of
`image<TAB>reason`, one line per image that did not scan — reason is
whatever Trivy itself reported, not a guess. `--images-total` is the count
`list-images.sh` discovered, independent of either file, so a bug that drops
an image silently is visible as an arithmetic mismatch rather than absorbed
into the numbers.
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

SEVERITIES = ("CRITICAL", "HIGH")


def load_reports(results_dir: Path) -> list[dict]:
    reports = []
    for path in sorted(results_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"::warning::{path}: not valid JSON, skipped ({exc})", file=sys.stderr)
            continue
        image = data.get("ArtifactName")
        if not image:
            print(f"::warning::{path}: no ArtifactName, skipped", file=sys.stderr)
            continue
        counts = Counter()
        cve_images: set[tuple[str, str]] = set()
        for result in data.get("Results") or []:
            for vuln in result.get("Vulnerabilities") or []:
                sev = vuln.get("Severity")
                if sev not in SEVERITIES:
                    continue
                counts[sev] += 1
                cve_id = vuln.get("VulnerabilityID")
                pkg = vuln.get("PkgName")
                if cve_id:
                    cve_images.add((cve_id, pkg or ""))
        reports.append({
            "image": image,
            "critical": counts["CRITICAL"],
            "high": counts["HIGH"],
            "cves": cve_images,
        })
    return reports


def load_failures(failures_file: Path) -> list[tuple[str, str]]:
    if not failures_file.exists():
        return []
    failures = []
    for line in failures_file.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parts = line.split("\t", 1)
        image = parts[0]
        reason = parts[1] if len(parts) > 1 else "(no reason recorded)"
        failures.append((image, reason))
    return failures


def render(reports: list[dict], failures: list[tuple[str, str]], images_total: int, top: int) -> str:
    scanned = len(reports)
    total_critical = sum(r["critical"] for r in reports)
    total_high = sum(r["high"] for r in reports)
    with_critical = [r for r in reports if r["critical"] > 0]

    lines = []
    lines.append("## Trivy image CVE scan")
    lines.append("")
    lines.append(f"Severity: {', '.join(SEVERITIES)} · `--ignore-unfixed` (a CVE with no")
    lines.append("published fix is excluded from every count here — that is not evidence it")
    lines.append("doesn't matter, only that no fix exists to act on yet).")
    lines.append("")
    lines.append("| | |")
    lines.append("|---|---|")
    lines.append(f"| Images discovered | {images_total} |")
    lines.append(f"| Images scanned | {scanned} |")
    lines.append(f"| Images not scanned | {len(failures)} |")
    lines.append(f"| CRITICAL findings (total) | {total_critical} |")
    lines.append(f"| HIGH findings (total) | {total_high} |")
    lines.append(f"| Images with at least one CRITICAL | {len(with_critical)} |")
    lines.append("")

    mismatch = images_total - scanned - len(failures)
    if mismatch != 0:
        lines.append(f"⚠️ **{abs(mismatch)} image(s) accounted for in neither list** — "
                      "discovery, scanning and failure tracking disagree; treat the "
                      "counts above as unreliable until this is investigated.")
        lines.append("")

    if failures:
        lines.append("### Not scanned")
        lines.append("")
        lines.append("Named explicitly, not folded into a clean result:")
        lines.append("")
        for image, reason in failures:
            lines.append(f"- `{image}` — {reason}")
        lines.append("")

    if with_critical:
        lines.append(f"### Top {min(top, len(with_critical))} images by CRITICAL findings")
        lines.append("")
        lines.append("| Image | CRITICAL | HIGH |")
        lines.append("|---|---|---|")
        ranked = sorted(reports, key=lambda r: (-r["critical"], -r["high"]))
        for r in ranked[:top]:
            if r["critical"] == 0:
                break
            lines.append(f"| `{r['image']}` | {r['critical']} | {r['high']} |")
        lines.append("")

    cve_to_images: dict[str, set[str]] = defaultdict(set)
    for r in reports:
        for cve_id, _pkg in r["cves"]:
            cve_to_images[cve_id].add(r["image"])
    repeated = sorted(
        ((cve, imgs) for cve, imgs in cve_to_images.items() if len(imgs) > 1),
        key=lambda kv: -len(kv[1]),
    )
    if repeated:
        lines.append(f"### Top {min(top, len(repeated))} CVEs repeated across the most images")
        lines.append("")
        lines.append("A CVE appearing in many images is usually one shared base-image or")
        lines.append("distro package, not many independent problems.")
        lines.append("")
        lines.append("| CVE | Images affected |")
        lines.append("|---|---|")
        for cve, imgs in repeated[:top]:
            lines.append(f"| [{cve}](https://avd.aquasec.com/nvd/{cve.lower()}) | {len(imgs)} |")
        lines.append("")

    lines.append("### Where to look further")
    lines.append("")
    lines.append("Full per-image, per-package findings (installed version, fixed version,")
    lines.append("title, references) are in the `trivy-image-scan-results` workflow")
    lines.append("artifact attached to this run — one JSON report per scanned image, in")
    lines.append("Trivy's own report format.")
    lines.append("")
    lines.append("Non-blocking: this job's exit code does not depend on any count above.")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--results-dir", required=True, type=Path)
    parser.add_argument("--failures-file", required=True, type=Path)
    parser.add_argument("--images-total", required=True, type=int)
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--out", type=Path, default=None,
                         help="Write the summary here in addition to stdout (e.g. $GITHUB_STEP_SUMMARY).")
    args = parser.parse_args()

    reports = load_reports(args.results_dir)
    failures = load_failures(args.failures_file)
    summary = render(reports, failures, args.images_total, args.top)

    print(summary)
    if args.out:
        with open(args.out, "a", encoding="utf-8") as fh:
            fh.write(summary + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
