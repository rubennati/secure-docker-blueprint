# Upstream Reference

## Source

- **Image:** https://github.com/project-zot/zot/pkgs/container/zot
- **GitHub:** https://github.com/project-zot/zot
- **Docs:** https://zotregistry.dev
- **License:** Apache-2.0
- **Decision facts checked:** not yet
- **Origin:** Community project under the CNCF sandbox umbrella, no single company · no single jurisdiction
- **Domain:** Developer tools
- **Role:** OCI registry for your own build output
- **Based on version:** `v2.1.21`
- **Verification snapshot:** 2026-09-19 — local Compose stack booted,
  authentication and access-control policy exercised against a live
  container; not yet run behind a real Traefik host

## What we use

- `ghcr.io/project-zot/zot:v2.1.21` — the **full** build, not
  `zot-minimal`. Confirmed via the image's own startup log
  (`binary-type` reports `events-imagetrust-lint-metrics-mgmt-profile-scrub-search-sync-ui-userprefs`).
  The minimal build only implements the bare OCI Distribution Specification
  and has none of the UI, embedded CVE scanning, or image-trust extensions
  this stack documents
- No separate database — zot's own local BoltDB-backed metadata store lives
  inside `storage.rootDirectory`

## What we changed vs. upstream examples

| Change | Reason |
|--------|--------|
| `user: "1000:1000"` set explicitly | Verified against a live container: the image runs as root by default (`docker inspect` shows `User: "0"`) with no privilege-drop entrypoint of its own — nothing upstream sets a safe default, so this stack sets one |
| `cap_drop: ALL`, zero `cap_add` | Verified: starts cleanly with no capabilities re-added |
| htpasswd file referenced as a Docker Secret path (`/run/secrets/zot_htpasswd`) rather than a plain config mount | The file holds real bcrypt password hashes — this repository's secrets standard treats that as credential material, not configuration |
| `accessControl` with an explicit `adminPolicy` and empty default/repository policies | Upstream's own example configs (`config-openid.json`, etc.) grant broader default access for demonstration purposes. This stack starts deny-by-default with one named admin user |
| No healthcheck | Verified: the image has no shell and no HTTP client tool inside it — nothing can run a check from within the container |

## What was actually verified, and how

- `docker inspect ghcr.io/project-zot/zot:v2.1.21` — confirmed `User: "0"`,
  entrypoint `/usr/local/bin/zot-linux-amd64`, `Cmd: ["serve",
  "/etc/zot/config.json"]`, and no shell present (`docker run --entrypoint sh` fails with "executable file not found in $PATH").
- `zot-linux-amd64 --version` — confirmed the full build via the
  `binary-type` field in its own version log line.
- Ran under `--user 1000:1000 --cap-drop ALL --security-opt
  no-new-privileges:true --read-only --tmpfs /tmp` with a real htpasswd
  file: started cleanly, the embedded Trivy CVE database downloaded
  automatically on boot, and `GET /v2/` returned 401 unauthenticated and
  200 with the admin credential — the access-control policy is real, not
  assumed from the config schema.
- Ran the actual production `docker-compose.yml` (with a temporary port
  override for the test only) end to end with the same result.
- **Not verified:** an actual `docker push`/`docker pull` round trip, the
  embedded CVE scan actually flagging a known-vulnerable image, Cosign/
  Notation signature verification (`imagetrust`, not configured — see
  README.md), OIDC login, garbage collection actually reclaiming a deleted
  tag's blobs, and behavior across a restart or upgrade.

## Upgrade checklist

1. Watch [zot releases](https://github.com/project-zot/zot/releases)
2. Read the changelog — zot documents config-schema changes between
   versions (`distSpecVersion` and extension config shapes have moved
   before)
3. Back up `./volumes/registry`, `./config/config.json` and
   `.secrets/htpasswd` together before upgrading — see README.md#backup
4. Bump `APP_TAG` in `.env`
5. `docker compose pull && docker compose up -d`
6. Confirm `docker login` and a test push/pull still work

## Known limitations

- **No healthcheck possible** — see above.
- **Cosign/Notation signature verification is not configured** — the
  `imagetrust` extension needs its own key material, added deliberately.
  See README.md.
- **OIDC is not configured** — htpasswd only. See README.md.
- **Not yet run behind a real Traefik host, and no actual image push/pull
  has been exercised.**
