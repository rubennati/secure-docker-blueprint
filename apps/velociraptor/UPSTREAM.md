# Upstream Reference

- **Last verified:** 2026-11-08 (0.77.3) — over IPv4: the server wrote its config, the GUI answered the admin (`401` for a wrong password) and the client frontend served its certificate, before and after `down`/`up`; the ports are published directly, no route (docs/labs/stack-refresh/2026-11-08-results.md)

## Source

- **Image:** https://github.com/Velocidex/velociraptor/pkgs/container/velociraptor-server
- **GitHub:** https://github.com/Velocidex/velociraptor
- **Docs:** https://docs.velociraptor.app
- **License:** AGPL-3.0 (GitHub's own license detector reports `NOASSERTION` for this repository; the actual `LICENSE` file at the repository root is the unmodified GNU AGPLv3 text, confirmed by reading it directly)
- **Decision facts checked:** not yet
- **Origin:** Originally Velocidex (Australia), acquired by Rapid7 (United States) in 2021, which maintains it today · non-EU
- **Domain:** Security operations
- **Role:** Endpoint forensics and threat hunting across a fleet, driven by queries
- **Verification snapshot:** 2026-09-19 — local Compose stack booted,
  hardening and secret injection exercised against a live container; no
  endpoint agent has been enrolled

## What we use

- `ghcr.io/velocidex/velociraptor-server:0.77.4` — the image tag omits the
  `v` prefix the Git release tag (`v0.77.4`) carries; a `v`-prefixed image
  tag does not exist

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

## Version notes

- Moved from `0.77.3` to `0.77.4` on 2026-11-23 (released 2026-11-23). The
  release's Security section lists six fixes without GHSA or CVE IDs (no
  advisory for 0.77.4 is published yet): a child org reads only the secrets
  shared with it, no longer the root org's; an impersonating artifact can only
  impersonate the user who created it; the filestore gRPC API requires
  `DATASTORE_ACCESS` and the `yarax`, `cache`, `memoize` and `process_tracker`
  plugins check permissions; file accessors verify path prefixes and the server
  rejects out-of-range values in client responses; the GUI HTML sanitizer's
  attribute matcher is tightened; PGP is removed (GO-2026-5932, the
  unmaintained `golang.org/x/crypto/openpgp`). All of them sit behind a GUI or
  API login or an enrolled client, so on this stack they reach only an
  authenticated user or a client this server enrolled. Breaking:
  `pk_encrypt()`, `pk_decrypt()`, `Server.Utils.CreateCollector` and the offline
  collector no longer accept PGP — use X509 or a password; collectors built with
  a PGP key must be rebuilt. `Windows.Events.FailedLogBeforeSuccess` is removed;
  hunts or notebooks that call it fail. This stack's files use neither. No
  datastore migration or configuration change is stated. The image is still
  amd64 only, but 0.77.4 is published as a manifest list with that one entry,
  so an arm64 machine no longer falls back to emulation on its own:
  `docker-compose.local.yml` names `platform: linux/amd64`. Upgraded on data
  from 0.77.3 (local file, amd64 under emulation): a reader user added under
  0.77.3 and the admin both logged in to the GUI API after the move, a wrong
  password answered `401`, the client frontend served its certificate. Source:
  https://github.com/Velocidex/velociraptor/releases/tag/v0.77.4,
  https://pkg.go.dev/vuln/GO-2026-5932.

- Moved to `0.77.3` on 2026-10-31 (released 2026-10-05).
  Upstream says the release addresses the CVEs of the 0.77.3 cycle without naming
  them on the release page; the advisory is
  https://docs.velociraptor.app/announcements/advisories/v0-77-3/, not reachable
  from the session that moved the pin. Changes that can matter: the backup
  artifacts `Server.Utils.BackupDirectory`, `BackupGCS` and `BackupS3` emit only
  `ClientId`, `FlowId` and derived fields; `enrollments_per_second: -1` now
  disables enrollment (this stack does not set it); the Prefetch
  `VolumeSerialNumber` offset moved. No datastore migration stated.

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
