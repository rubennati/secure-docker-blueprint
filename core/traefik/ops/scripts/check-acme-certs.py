#!/usr/bin/env python3
"""Compare the certificates Traefik stores with the wildcards .env asks for.

    check-acme-certs.py ACME_JSON [DOMAIN...]

DOMAIN is each entry of ACME_WILDCARD_DOMAIN. Traefik loads every certificate in
acme.json and renews it on expiry alone, whether or not a router still asks for
it, so two states go unnoticed in its log:

- a wildcard certificate for a domain the list no longer names: it is still
  served and renewed, and nothing requests it once it is removed by hand;
- a certificate for a single hostname a listed wildcard already covers: every
  renewal publishes that hostname in Certificate Transparency logs again.

A listed domain without a certificate yet is reported as a note: Traefik
requests it after the next start, and an error shows in its log.

Only the domain names are read and printed; the keys in the file are not.
Exit 0 after the comparison (findings are warnings), 2 when the file cannot be
read or parsed — the comparison is then not done, and says so.
"""
import json
import sys


def covered(name, zone):
    """*.zone matches exactly one label below zone; the certificate also carries zone."""
    if name == zone:
        return True
    label, dot, rest = name.partition(".")
    return bool(dot) and rest == zone and bool(label) and label != "*"


def main(argv):
    path, zones = argv[1], argv[2:]
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except OSError as e:
        print(f"NOT VERIFIED: {path} could not be read ({e.strerror}) — stored certificates not compared")
        return 2
    except ValueError:
        print(f"NOT VERIFIED: {path} is not valid JSON — stored certificates not compared")
        return 2

    issued = set()
    findings = []
    for resolver, store in sorted((data or {}).items()):
        for cert in (store or {}).get("Certificates") or []:
            domain = cert.get("domain") or {}
            names = [n for n in [domain.get("main")] + list(domain.get("sans") or []) if n]
            wild = sorted(n[2:] for n in names if n.startswith("*."))
            if wild:
                for zone in wild:
                    issued.add(zone)
                    if zone not in zones:
                        findings.append(
                            f"WARNING: acme.json ({resolver}) holds a wildcard certificate for *.{zone}, which "
                            "ACME_WILDCARD_DOMAIN does not name. Traefik keeps serving and renewing it; add the "
                            "domain to the list if it is still in use, so a router requests it.")
                continue
            for name in names:
                zone = next((z for z in zones if covered(name, z)), None)
                if zone:
                    findings.append(
                        f"WARNING: acme.json ({resolver}) holds a certificate for {name}, which *.{zone} covers. "
                        "Each renewal publishes the hostname in Certificate Transparency logs again. Expected "
                        "only where a router names a certresolver on purpose; core/traefik/README.md, "
                        "'Migrating an existing wildcard deployment'.")
                    break

    for line in findings:
        print(line)
    for zone in zones:
        if zone not in issued:
            print(f"NOTE: acme.json holds no certificate for *.{zone} yet — Traefik requests it after the next "
                  "start; an ACME error for it shows in the Traefik log.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: check-acme-certs.py ACME_JSON [DOMAIN...]")
        sys.exit(1)
    sys.exit(main(sys.argv))
