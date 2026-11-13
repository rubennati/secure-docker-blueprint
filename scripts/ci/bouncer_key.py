"""A placeholder CrowdSec bouncer key for a test that renders core/traefik with the switch on.

render.sh refuses CROWDSEC_BOUNCER_ENABLED=true without .secrets/crowdsec_bouncer_key.txt
that Traefik — root without capabilities — can read: as its owner (uid 0), through
group 0, or through "other". A test runner is neither root nor in group 0, so the
placeholder is readable through "other" by default; render.sh warns about that, which
is the expected output here. The value is a fixed string, no secret.
"""

from pathlib import Path

PLACEHOLDER = "test-key-not-a-secret"


def write(stack: Path, mode: int = 0o644, value: str = PLACEHOLDER) -> Path:
    """Write the key file under `stack` (a copy of core/traefik) with `mode`."""
    key = stack / ".secrets" / "crowdsec_bouncer_key.txt"
    key.parent.mkdir(parents=True, exist_ok=True)
    key.write_text(value, encoding="utf-8")
    key.chmod(mode)
    return key
