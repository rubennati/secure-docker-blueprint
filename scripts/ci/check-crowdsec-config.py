#!/usr/bin/env python3
"""CrowdSec remediation configuration: default-off, and keyed by file when enabled.

Two properties, both decided by rendering configuration and parsing the result
rather than by matching comment text. A commented-out block and an absent block
are the same thing to a YAML parser, which is exactly the question being asked.

**Default-off** (`--templates`, run in CI). The blueprint ships CrowdSec
detection available and HTTP remediation supported, but attached to nothing.
Since the switch, the templates *contain* the plugin block and the middleware
definitions as live YAML — `render.sh` emits them only when
`CROWDSEC_BOUNCER_ENABLED=true` in `.env`. So the gate renders `core/traefik`
twice into a scratch copy: with the shipped `.env.example` as it is, which must
yield no plugin and no `crowdsec-*` middleware; and with the switch on and a
placeholder key file, which must yield the plugin and both middlewares keyed.
Then it switches off again over the enabled render and checks that both halves
are gone. That exercises the mechanism itself, not just the shipped default.

**Keyed by file when enabled** (`--rendered DIR`, run by
`ops/scripts/validate.sh`). Every rendered CrowdSec middleware names the key
file (`crowdsecLapiKeyFile`) and carries no key itself (`crowdsecLapiKey`).
`config/dynamic` stays readable for Traefik as a whole, so a key inside it is
readable by every account on the host; `crowdsec-bouncer.yml` mounts the key as
a Docker secret at the path the middlewares name, and `--templates` holds the
two together. Checked only when a CrowdSec middleware is actually present in
the rendered dynamic configuration — the default-off blueprint renders and
validates without a key.

No key value is ever read into a message: this reports only where the key comes
from. The placeholder the `--templates` mode writes is a literal string in this
file and no secret.

Run:
    python3 scripts/ci/check-crowdsec-config.py --templates
    python3 scripts/ci/check-crowdsec-config.py --rendered core/traefik/config
"""
import argparse
import shutil
import subprocess
import sys
import tempfile
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
# Traefik plugin and differ only in whether AppSec inspection is switched on;
# render.sh places one of them on the websecure entrypoint. (A configuration
# rendered before the middleware model named them crowdsec-basic and
# crowdsec-appsec; the rendered check keys on the plugin block, not the name.)
CROWDSEC_MIDDLEWARES = ("threat-crowdsec", "threat-crowdsec-appsec")

TRAEFIK = Path("core/traefik")
SWITCH = "CROWDSEC_BOUNCER_ENABLED"
# The key file: on the host, as a Docker secret in the overlay, and the path the
# middlewares name (ops/scripts/bouncer-key.sh carries the same three).
KEY_FILE = Path(".secrets/crowdsec_bouncer_key.txt")
KEY_OVERLAY = "crowdsec-bouncer.yml"
KEY_SECRET = "crowdsec_bouncer_key"
KEY_TARGET = f"/run/secrets/{KEY_SECRET}"


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


def key_file_of(doc, name: str) -> tuple[str, bool]:
    """(the key file the named middleware names, whether it carries a key itself)."""
    plugin = ((doc.get("http") or {}).get("middlewares") or {}).get(name, {}).get("plugin") or {}
    path, inline = "", False
    for config in plugin.values():
        if isinstance(config, dict):
            key = config.get("crowdsecLapiKey")
            inline = inline or (isinstance(key, str) and bool(key.strip()))
            named = config.get("crowdsecLapiKeyFile")
            if isinstance(named, str) and named.strip():
                path = named.strip()
    return path, inline


def overlay_mounts(root: Path) -> str:
    """Where crowdsec-bouncer.yml mounts the key for Traefik, or why it does not."""
    path = root / TRAEFIK / KEY_OVERLAY
    if not path.exists():
        return f"{KEY_OVERLAY} is missing"
    doc = load(path) or {}
    service = (doc.get("services") or {}).get("traefik") or {}
    if KEY_SECRET not in (service.get("secrets") or []):
        return f"{KEY_OVERLAY} does not give the traefik service the secret {KEY_SECRET}"
    source = ((doc.get("secrets") or {}).get(KEY_SECRET) or {}).get("file")
    if source not in (str(KEY_FILE), f"./{KEY_FILE}"):
        return f"{KEY_OVERLAY} reads {KEY_SECRET} from {source!r}, expected ./{KEY_FILE}"
    return KEY_TARGET


def render_into(scratch: Path, root: Path, overrides: dict) -> Path:
    """Render core/traefik into `scratch` with .env.example plus `overrides`.

    The scratch copy holds ops/, a .env and a placeholder key file; render.sh
    writes config/ next to them. The live deployment's .env, .secrets/ and
    config/ are never read or written.
    """
    if not (scratch / "ops").exists():
        shutil.copytree(root / TRAEFIK / "ops", scratch / "ops")
        key = scratch / KEY_FILE
        key.parent.mkdir(parents=True, exist_ok=True)
        key.write_text("ci-placeholder-not-a-secret", encoding="utf-8")
        key.chmod(0o644)  # a runner is not root: readable for Traefik through "other"
    lines = []
    for line in (root / TRAEFIK / ".env.example").read_text(encoding="utf-8").splitlines():
        key = line.split("=", 1)[0] if "=" in line and not line.startswith("#") else None
        if key in overrides:
            continue
        lines.append(line)
    for key, value in overrides.items():
        lines.append(f'{key}="{value}"')
    (scratch / ".env").write_text("\n".join(lines) + "\n", encoding="utf-8")
    result = subprocess.run(
        ["bash", str(scratch / "ops" / "scripts" / "render.sh")],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise SystemExit(
            f"FAIL  render.sh exited {result.returncode} with {overrides or 'the shipped .env.example'}:\n"
            + result.stdout + result.stderr
        )
    return scratch / "config"


def rendered_state(config: Path) -> tuple[list, dict]:
    """Plugins declared in traefik.yml, and {file: [crowdsec middlewares]} under dynamic/."""
    plugins = declared_plugins(load(config / "traefik.yml"))
    middlewares = {}
    for path in sorted((config / "dynamic").glob("*.yml")):
        found = crowdsec_middlewares(load(path))
        if found:
            middlewares[path.name] = found
    return plugins, middlewares


def compose_file_with_overlay(root: Path) -> str:
    """The shipped COMPOSE_FILE with the key overlay added, as the README sets it."""
    for line in (root / TRAEFIK / ".env.example").read_text(encoding="utf-8").splitlines():
        if line.startswith("COMPOSE_FILE="):
            return f"{line.split('=', 1)[1]}:{KEY_OVERLAY}"
    return ""


def check_templates(root: Path) -> int:
    """The shipped blueprint renders no CrowdSec remediation; the switch renders it keyed."""
    failures = []
    scratch = Path(tempfile.mkdtemp(prefix="crowdsec-switch-"))
    try:
        # 1. As shipped: .env.example untouched. The switch it carries is false.
        plugins, middlewares = rendered_state(render_into(scratch, root, {}))
        if plugins:
            failures.append(f"shipped .env.example renders plugin(s) {', '.join(plugins)} — the blueprint ships default-off")
        if middlewares:
            failures.append(f"shipped .env.example renders plugin middleware(s) {middlewares} — nothing may be enabled by default")
        if (scratch / "config" / "dynamic" / "crowdsec.yml").exists():
            failures.append("shipped .env.example leaves config/dynamic/crowdsec.yml behind")

        # 2. Switch on, with the overlay and a placeholder key file: both halves,
        #    keyed by the file the overlay mounts.
        on = {SWITCH: "true", "COMPOSE_FILE": compose_file_with_overlay(root)}
        config = render_into(scratch, root, on)
        plugins, middlewares = rendered_state(config)
        if plugins != ["bouncer"]:
            failures.append(f"{SWITCH}=true renders plugins {plugins}, expected ['bouncer']")
        names = sorted(n for found in middlewares.values() for n in found)
        if names != sorted(CROWDSEC_MIDDLEWARES):
            failures.append(f"{SWITCH}=true renders middlewares {names}, expected {sorted(CROWDSEC_MIDDLEWARES)}")
        if list(middlewares) != ["crowdsec.yml"]:
            failures.append(f"{SWITCH}=true defines the middlewares in {list(middlewares)}, expected crowdsec.yml only")
        doc = load(config / "dynamic" / "crowdsec.yml") if (config / "dynamic" / "crowdsec.yml").exists() else {}
        mounted = overlay_mounts(root)
        if mounted != KEY_TARGET:
            failures.append(mounted)
        for name in CROWDSEC_MIDDLEWARES:
            if not doc:
                continue
            path, inline = key_file_of(doc, name)
            if inline:
                failures.append(f"{SWITCH}=true renders '{name}' with the key in the file — crowdsecLapiKey")
            if path != KEY_TARGET:
                failures.append(f"{SWITCH}=true renders '{name}' with key file {path or '(none)'}, expected {KEY_TARGET}")

        # 3. Switch off again over the enabled render: both halves removed.
        plugins, middlewares = rendered_state(render_into(scratch, root, {SWITCH: "false"}))
        if plugins or middlewares:
            failures.append(f"{SWITCH}=false over an enabled render leaves plugins {plugins} / middlewares {middlewares}")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    for line in failures:
        print(f"  🔴 FAIL  crowdsec-switch  {line}")
    if failures:
        print(f"\n❌ {len(failures)} failure(s) — CrowdSec must ship default-off and follow the switch")
        return 1
    print("✅ CrowdSec ships default-off  ·  switch on renders plugin + middlewares keyed by the mounted file  ·  switch off removes both")
    return 0


def check_rendered(config_dir: Path) -> int:
    """A CrowdSec middleware that is actually rendered names the key file, and holds no key."""
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
            key_file, inline = key_file_of(doc, name)
            if inline:
                failures.append(
                    f"{path.name}: middleware '{name}' carries the bouncer key itself "
                    "(crowdsecLapiKey), readable by every account on this host — it was "
                    f"rendered before the key moved to {KEY_FILE}. Put the key there and "
                    "run render.sh (core/traefik/README.md, 'How to enable')"
                )
            elif not key_file:
                failures.append(
                    f"{path.name}: middleware '{name}' is enabled but names no key file "
                    "(crowdsecLapiKeyFile) — run render.sh"
                )

    for line in failures:
        print(f"ERROR: {line}")
    if failures:
        return 1
    if checked:
        print(f"OK: CrowdSec middleware(s) keyed by a file: {', '.join(checked)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--templates", action="store_true",
                       help="render core/traefik with the shipped .env.example, then with the switch on and off, and assert each state")
    group.add_argument("--rendered", metavar="DIR",
                       help="assert rendered CrowdSec middlewares name the key file and carry no key")
    args = parser.parse_args()

    if args.templates:
        return check_templates(Path("."))
    return check_rendered(Path(args.rendered))


if __name__ == "__main__":
    sys.exit(main())
