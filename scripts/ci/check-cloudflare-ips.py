#!/usr/bin/env python3
"""
Trusted proxy ranges for secure-docker-blueprint — are they ranges, and are
they Cloudflare's current ones?

`core/traefik/ops/cloudflare-ips.txt` is the list of senders whose forwarded
headers the Traefik entrypoints trust. A range missing from it means Cloudflare
traffic from that edge arrives without a trusted client address; a range that
is not Cloudflare's means a stranger's forwarded headers are trusted. The file
is kept by hand, so two things are checked:

  offline   every entry parses as an IPv4 or IPv6 network, none is repeated,
            both families are present — runs in CI on every pull request
  --online  the entries equal the sets published at
            https://www.cloudflare.com/ips-v4 and /ips-v6 — runs on a schedule,
            because a network call has no place in the deterministic gates

Usage:
  python3 scripts/ci/check-cloudflare-ips.py [--online] [--file PATH] [github-summary-path]

Exit 1 on any finding, or when the published lists cannot be fetched.
"""

import argparse
import ipaddress
import sys
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_FILE = Path("core/traefik/ops/cloudflare-ips.txt")
SOURCES = {
    4: "https://www.cloudflare.com/ips-v4",
    6: "https://www.cloudflare.com/ips-v6",
}


def read_ranges(path: Path) -> tuple[list[str], list[str]]:
    """Entries of the file in order, and the problems found with them."""
    entries: list[str] = []
    problems: list[str] = []
    seen: set[str] = set()
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        text = raw.split("#", 1)[0].strip()
        if not text:
            continue
        try:
            net = ipaddress.ip_network(text, strict=True)
        except ValueError as exc:
            problems.append(f"line {line_no}: '{text}' is not a network: {exc}")
            continue
        key = str(net)
        if key in seen:
            problems.append(f"line {line_no}: '{text}' is listed twice")
        seen.add(key)
        entries.append(key)
    families = {ipaddress.ip_network(e).version for e in entries}
    for family in (4, 6):
        if family not in families:
            problems.append(f"no IPv{family} range — Cloudflare publishes both families")
    return entries, problems


def fetch(url: str) -> set[str]:
    # The endpoint answers 403 to urllib's default User-Agent; a named one is served.
    req = urllib.request.Request(url, headers={"User-Agent": "secure-docker-blueprint/check-cloudflare-ips"})
    with urllib.request.urlopen(req, timeout=20) as resp:  # noqa: S310 — fixed https URLs
        body = resp.read().decode("utf-8")
    return {str(ipaddress.ip_network(line.strip())) for line in body.splitlines() if line.strip()}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--online", action="store_true", help="compare with the published lists")
    parser.add_argument("--file", type=Path, default=DEFAULT_FILE)
    parser.add_argument("summary", nargs="?", help="GitHub step summary path")
    args = parser.parse_args(argv)

    if not args.file.is_file():
        print(f"ERROR: {args.file} not found")
        return 1

    entries, problems = read_ranges(args.file)
    lines = [f"{len(entries)} ranges in {args.file}"]
    for p in problems:
        lines.append(f"  FAIL  {p}")

    if args.online and not problems:
        for family, url in SOURCES.items():
            try:
                published = fetch(url)
            except (urllib.error.URLError, ValueError, OSError) as exc:
                lines.append(f"  FAIL  could not fetch {url}: {exc}")
                problems.append(url)
                continue
            ours = {e for e in entries if ipaddress.ip_network(e).version == family}
            missing = sorted(published - ours, key=ipaddress.ip_network)
            extra = sorted(ours - published, key=ipaddress.ip_network)
            if missing:
                lines.append(f"  FAIL  published but not in the file (IPv{family}): {', '.join(missing)}")
                problems.extend(missing)
            if extra:
                lines.append(f"  FAIL  in the file but no longer published (IPv{family}): {', '.join(extra)}")
                problems.extend(extra)
            if not missing and not extra:
                lines.append(f"  ok    IPv{family}: {len(ours)} ranges equal the published list")

    if not problems:
        lines.append("  ok    every entry is a network, none repeated, both families present")

    text = "\n".join(lines)
    print(text)
    if args.summary:
        with open(args.summary, "a", encoding="utf-8") as fh:
            fh.write("## Cloudflare trusted ranges\n\n```text\n" + text + "\n```\n")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
