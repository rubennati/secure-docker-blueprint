#!/usr/bin/env python3
"""CrowdSec remediation configuration: default-off, and keyed when enabled.

Two properties, both decided by parsing configuration rather than by matching
comment text. A commented-out block and an absent block are the same thing to a
YAML parser, which is exactly the question being asked.

**Default-off** (`--templates`, run in CI). The blueprint ships CrowdSec
detection available and HTTP remediation supported, but attached to nothing: the
Traefik plugin stays out of the static configuration and no `crowdsec-*`
middleware is defined. That is a deliberate default, and an operator enabling it
locally edits tracked template files — so the enablement is one `git add` away
from becoming the shipped default by accident. This gate is what stops that.

**Keyed when enabled** (`--rendered DIR`, run by `ops/scripts/validate.sh`).
`render.sh` runs `envsubst`, which turns an unset `CROWDSEC_BOUNCER_KEY` into an
empty string. The result is a bouncer that cannot authenticate, with no error at
render time. The key is required only when a CrowdSec middleware is actually
present in the rendered dynamic configuration — never unconditionally, because
the default-off blueprint must render and validate without one.

The key's value is never read into a message: this reports only whether one is
present.

Run:
    python3 scripts/ci/check-crowdsec-config.py --templates
    python3 scripts/ci/check-crowdsec-config.py --rendered core/traefik/config
"""

import argparse
import sys
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError:  # operator host, not a CI runner
    sys.exit(
        "ERROR: PyYAML is required to check the CrowdSec configuration.\n"
        "       Install it (pip install pyyaml, or apt install python3-yaml) and re-run.\n"
        "       This check is skipped for nobody: a CrowdSec middleware is enabled and\n"
        "       its bouncer key has not been verified."
    )

# Middlewares that carry CrowdSec remediation. Both are defined by the same
# Traefik plugin and differ only in whether AppSec inspection is switched on.
CROWDSEC_MIDDLEWARES = ("crowdsec-basic", "crowdsec-appsec")

STATIC_TEMPLATE = Path("core/traefik/ops/templates/traefik.yml.tmpl")
DYNAMIC_TEMPLATE = Path("core/traefik/ops/templates/dynamic/integrations.yml.tmpl")


def load(path: Path):
    """Parse a YAML document, tolerating the `${VAR}` placeholders in templates."""
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8", errors="replace"))
    except yaml.YAMLError as exc:
        raise SystemExit(f"FAIL  {path}: not parseable as YAML — {exc}")


def declared_plugins(doc) -> list:
    """Plugin names in Traefik's static `experimental.plugins` block."""
    if not isinstance(doc, dict):
        return []
    plugins = (doc.get("experimental") or {}).get("plugins")
    return sorted(plugins) if isinstance(plugins, dict) else []


def crowdsec_middlewares(doc) -> list:
    """Defined middleware names that carry a CrowdSec bouncer plugin block.

    Keyed on the plugin block rather than on the name, so a middleware renamed by
    an operator is still caught, and a same-named middleware that is not a
    bouncer is not.
    """
    if not isinstance(doc, dict):
        return []
    middlewares = (doc.get("http") or {}).get("middlewares")
    if not isinstance(middlewares, dict):
        return []
    found = []
    for name, body in middlewares.items():
        if not isinstance(body, dict):
            continue
        plugin = body.get("plugin")
        if isinstance(plugin, dict) and plugin:
            found.append(name)
    return sorted(found)


def bouncer_key_present(doc, name: str) -> bool:
    """Whether the named middleware carries a non-empty LAPI key."""
    plugin = ((doc.get("http") or {}).get("middlewares") or {}).get(name, {}).get("plugin") or {}
    for config in plugin.values():
        if isinstance(config, dict):
            key = config.get("crowdsecLapiKey")
            if isinstance(key, str) and key.strip():
                return True
    return False


def check_templates(root: Path) -> int:
    """The shipped blueprint defines no active CrowdSec remediation."""
    failures = []

    static = root / STATIC_TEMPLATE
    if static.exists():
        plugins = declared_plugins(load(static))
        if plugins:
            failures.append(
                f"{STATIC_TEMPLATE}: declares Traefik plugin(s) {', '.join(plugins)} — "
                "the blueprint ships with the plugin commented out; enabling it is an "
                "operator-local step, not repository state"
            )

    dynamic = root / DYNAMIC_TEMPLATE
    if dynamic.exists():
        active = crowdsec_middlewares(load(dynamic))
        if active:
            failures.append(
                f"{DYNAMIC_TEMPLATE}: defines plugin middleware(s) {', '.join(active)} — "
                "integrations ship fully commented out and no router attaches one"
            )

    for line in failures:
        print(f"  🔴 FAIL  crowdsec-default-off  {line}")
    if failures:
        print(f"\n❌ {len(failures)} failure(s) — CrowdSec must ship default-off")
        return 1
    print("✅ CrowdSec ships default-off  ·  no plugin declared  ·  no middleware defined")
    return 0


def check_rendered(config_dir: Path) -> int:
    """A CrowdSec middleware that is actually rendered must carry a key."""
    dynamic_dir = config_dir / "dynamic"
    if not dynamic_dir.is_dir():
        print(f"  no rendered dynamic config at {dynamic_dir} — nothing to check")
        return 0

    failures = []
    checked = []
    for path in sorted(dynamic_dir.glob("*.yml")):
        doc = load(path)
        for name in crowdsec_middlewares(doc):
            checked.append(f"{name} ({path.name})")
            if not bouncer_key_present(doc, name):
                failures.append(
                    f"{path.name}: middleware '{name}' is enabled but "
                    "crowdsecLapiKey is empty or missing — set CROWDSEC_BOUNCER_KEY "
                    "in core/traefik/.env and re-render "
                    "(generate one with: docker exec crowdsec cscli bouncers add traefik-bouncer)"
                )

    for line in failures:
        print(f"ERROR: {line}")
    if failures:
        return 1
    if checked:
        print(f"OK: CrowdSec middleware(s) with a key present: {', '.join(checked)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--templates", action="store_true",
                       help="assert the committed templates ship CrowdSec default-off")
    group.add_argument("--rendered", metavar="DIR",
                       help="assert rendered CrowdSec middlewares carry a bouncer key")
    args = parser.parse_args()

    if args.templates:
        return check_templates(Path("."))
    return check_rendered(Path(args.rendered))


if __name__ == "__main__":
    sys.exit(main())
