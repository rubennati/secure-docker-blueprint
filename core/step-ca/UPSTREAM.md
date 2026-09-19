# Upstream Reference

## Source

- **Image:** https://hub.docker.com/r/smallstep/step-ca
- **GitHub:** https://github.com/smallstep/certificates
- **Docs:** https://smallstep.com/docs/step-ca/
- **License:** Apache-2.0
- **Origin:** United States · Smallstep Labs, Inc. · non-EU
- **Based on version:** `0.30.2`
- **Verification snapshot:** 2026-09-19 — local Compose stack booted, init
  sequence, ACME directory and healthcheck exercised against a live
  container; the production compose's healthcheck against a real
  DNS-resolvable hostname not yet exercised (see Known limitations)

## What we use

- `smallstep/step-ca:0.30.2` — single container, no database. step-ca's own
  embedded badger-backed store lives inside the persistent volume

## What we changed vs. upstream's own examples

| Change | Reason |
|--------|--------|
| `cap_add: [NET_BIND_SERVICE]` | Verified against a live container: the image's binary carries an embedded file capability from its own build (`setcap CAP_NET_BIND_SERVICE`, confirmed by reading upstream's Dockerfile). Under `cap_drop: ALL` with nothing re-added, the entrypoint's final `exec` fails with "Operation not permitted" even though the configured port (9000) is not itself privileged |
| `read_only: true` + `tmpfs: /tmp` | Verified against a live container: every write happens under `/home/step`, its own volume mount — the rest of the filesystem can be read-only. Not shown in any upstream example |
| No Traefik, direct port publish | ACME/`step ca bootstrap` clients need step-ca's own certificate directly for fingerprint-pinned trust to mean anything; a TLS-terminating reverse proxy would substitute its own certificate. See README.md#traefik--networking |
| `DOCKER_STEPCA_INIT_PASSWORD_FILE` via Docker Secret | Upstream's own quick-start examples pass this as a plain env var or an interactive prompt; this stack treats it as what it is — a credential |
| Documented offline-root init path | Upstream's `docker ca init` flags support providing an existing root (`--root`/`--key`/`--key-password-file`, surfaced as `DOCKER_STEPCA_INIT_ROOT_FILE` etc.) but its own quick-start guides default to generating both tiers in-container. This stack documents both paths explicitly rather than defaulting silently to the weaker one |

## What was actually verified, and how

- `docker inspect smallstep/step-ca:0.30.2` — confirmed `User: "step"`,
  entrypoint `/bin/bash /entrypoint.sh`, and the image's own baked-in
  `HEALTHCHECK` (`step ca health | grep '^ok'`).
- Read `docker/Dockerfile` and `docker/entrypoint.sh` directly from the
  `smallstep/certificates` repository (not assumed from documentation) to
  confirm: the `setcap` build step, the exact env-var-driven init sequence,
  that init is skipped entirely once `ca.json` exists, and that the
  provisioner password is `shred -u`'d after being printed once.
- Ran with `--cap-drop ALL` alone: init completed (root + intermediate
  generated correctly), but the final `exec` of the `step-ca` binary failed
  with `Operation not permitted`. Added `NET_BIND_SERVICE`: started cleanly,
  served HTTPS on `:9000`, answered the ACME directory and `/roots.pem`.
- Additionally ran the same configuration under `--read-only --tmpfs /tmp`:
  identical clean start — confirms the read-only claim above.
- Ran the actual production `docker-compose.yml` end to end with a real
  Docker Secret for the CA password: init, ACME directory, and TLS serving
  all confirmed working.
- Ran the local test stack (`docker-compose.local.yml`, hostname
  `localhost`): `GET /health` returned `{"status":"ok"}` and the container
  reported `healthy`.
- **Not verified:** an actual client bootstrap and certificate issuance
  (X.509 or SSH), the offline-root init path, OIDC provisioner setup, and
  behavior across a restart or upgrade.

## A real, DNS-dependent healthcheck limitation

The image's baked-in healthcheck (`step ca health`) resolves and connects
to the CA's **own configured hostname** (`STEPCA_DNS_NAMES`'s primary
entry) rather than `127.0.0.1` or `localhost`. Confirmed directly: the
local test stack (hostname `localhost`) reported `healthy` immediately,
while the production stack — configured with the placeholder
`ca.example.com`, which does not resolve anywhere in this test
environment — logged `dial tcp: lookup ca.example.com ...: no such host`
and stayed at `starting`/`unhealthy`. This is not a bug in this stack's
compose file; it is how `step ca health` is implemented upstream. On a real
deployment, `STEPCA_DNS_NAMES`'s primary hostname must actually resolve
from inside the container (via internal DNS, `/etc/hosts`, or similar) for
the healthcheck — and for ACME clients generally — to work at all.

## Upgrade checklist

1. Watch [step-ca releases](https://github.com/smallstep/certificates/releases)
2. Read the changelog — a CA is not a service to upgrade carelessly;
   check for any provisioner-config or ACME-behavior changes
3. Back up `./volumes/data` and `.secrets/ca_password.txt` together before
   upgrading — see README.md#backup
4. Bump `APP_TAG` in `.env`
5. `docker compose pull && docker compose up -d`
6. Confirm the healthcheck passes and a test certificate can still be
   issued

## Known limitations

- **The healthcheck depends on real DNS resolution for `STEPCA_DNS_NAMES`**
  — see above.
- **The simple init path leaves the root CA key on the same host as the
  running service** — see README.md#root-ca-vs-intermediate-ca.
- **SSH CA and OIDC provisioners are not exercised** — flags/commands
  documented, not run against a live client.
- **No client bootstrap or certificate issuance has been exercised.**
