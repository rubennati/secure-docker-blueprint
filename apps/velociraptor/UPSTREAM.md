# Upstream Reference

## Source

- **Image:** https://github.com/Velocidex/velociraptor/pkgs/container/velociraptor-server
- **GitHub:** https://github.com/Velocidex/velociraptor
- **Docs:** https://docs.velociraptor.app
- **License:** AGPL-3.0 (GitHub's own license detector reports `NOASSERTION` for this repository; the actual `LICENSE` file at the repository root is the unmodified GNU AGPLv3 text, confirmed by reading it directly)
- **Origin:** Originally Velocidex (Australia), acquired by Rapid7 (United States) in 2021, which maintains it today · non-EU
- **Based on version:** `0.77.2`
- **Verification snapshot:** 2026-09-19 — local Compose stack booted,
  hardening and secret injection exercised against a live container; no
  endpoint agent has been enrolled

## What we use

- `ghcr.io/velocidex/velociraptor-server:0.77.2` — the image tag omits the
  `v` prefix the Git release tag (`v0.77.2`) carries; verified directly,
  `v0.77.2` does not exist as an image tag

## Docker-based server support since 0.77 — verified, not assumed from the prompt

Confirmed by reading `Docker/README.md` and `Docker/compose.yaml` directly
from the `Velocidex/velociraptor` repository: an official, CI-published
Docker deployment path exists, generating a self-signed config and
starting the server with sensible defaults on first run. Upstream's own
`compose.yaml` pins `image: ghcr.io/velocidex/velociraptor-server:latest`
and ships a default admin password of literally `password` — both
corrected in this stack (a specific version tag, and a generated secret).

## What we changed vs. upstream's own compose

| Change | Reason |
|--------|--------|
| Pinned `0.77.2`, not `latest` | Upstream's own example uses `latest`; this repository never does |
| Initial admin password via Docker Secret, not a literal default | Upstream's own default is the literal string `password` |
| `cap_drop: ALL`, zero `cap_add`, `read_only: true` | Verified against a live container: the image has no non-root user and no privilege-drop entrypoint, but neither property actually needs a capability re-added — the cleanest hardening result across every stack checked in this batch |
| Custom entrypoint wrapper for the admin-password secret | Verified: no `_FILE` support, plain env var only, relevant only on first init |
| No Traefik | See README.md's Security model |
| Not on an `internal: true` network | Verified against a live container: the server downloads endpoint-agent binaries and default artifacts from the internet on first start and after an upgrade |
| TCP-only healthcheck (`nc -z`) | The GUI serves self-signed HTTPS by default, and the image's only HTTP client (busybox `wget`) has no flag to skip certificate verification — confirmed against a live container |

## What was actually verified, and how

- `docker inspect ghcr.io/velocidex/velociraptor-server:0.77.2` — confirmed
  `User: ""` (root), `Cmd: ["/bin/sh","/bin/entrypoint"]`, no `HEALTHCHECK`.
- Read `/bin/entrypoint` directly from a live container: confirmed the
  exact env-var-driven init sequence, that init is skipped once a config
  file exists, and that the admin password has no `_FILE` equivalent.
- Ran with `--cap-drop ALL` (no `cap_add` at all): started cleanly, GUI and
  frontend both came up on their TLS ports. Additionally ran under
  `--read-only --tmpfs /tmp`: identical clean start.
- **First hardening attempt failed** with the custom entrypoint wrapper:
  `exec /bin/entrypoint "$@"` failed with `Permission denied`. Traced to
  `/bin/entrypoint` not being independently executable — upstream's own
  image invokes it as `sh /bin/entrypoint`, not directly. Fixed by
  wrapping it the same way: `exec /bin/sh /bin/entrypoint "$@"`.
- Ran the actual production `docker-compose.yml` end to end with a real
  Docker Secret: `GUI is ready to handle TLS requests on
  https://localhost:8889/` and `Frontend is ready to handle client TLS
  requests at https://localhost:8000/` both logged, and both ports
  answered TLS connections (`307` from the GUI, `404` from the frontend —
  both expected: the frontend speaks Velociraptor's own client protocol,
  not a browsable API).
- Confirmed `nc -z` accepts the flags this image's busybox build supports,
  and that `wget` in this image genuinely has no certificate-bypass
  option, by reading its own `--help` output.
- **Not verified:** an actual endpoint agent enrolled, a VQL query
  executed, OIDC/SSO sign-in, and a restore rehearsal of the config +
  datastore pair.

## Upgrade checklist

1. Watch [Velociraptor releases](https://github.com/Velocidex/velociraptor/releases)
2. Read the changelog — this project ships frequently and artifact/VQL
   behavior can change between minor versions
3. Back up `./volumes/etc` and `./volumes/datastore` together before
   upgrading — see README.md#backup
4. Bump `APP_TAG` in `.env`
5. `docker compose pull && docker compose up -d`
6. Confirm the GUI is reachable and an existing enrolled client (if any)
   still checks in successfully after the upgrade

## Known limitations

- **No non-root user in the image** — see README.md's Security model.
- **Requires outbound internet access** — not isolated on an internal-only
  network, unlike most other stacks in this repository.
- **Healthcheck is TCP-only**, not a real application-level check — see
  above.
- **No endpoint agent, OIDC/SSO or restore rehearsal has been exercised.**
