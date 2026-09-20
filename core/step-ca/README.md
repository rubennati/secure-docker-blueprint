# step-ca

Internal PKI: X.509 certificates, ACME, and optionally an SSH certificate
authority, for machines and services *inside* this installation. Not a
public-facing service.

## Public Web TLS vs. internal trust — read this first

```text
Public Web TLS  →  Traefik / ACME / a public CA (Let's Encrypt, etc.)
Internal trust, machine identity, SSH CA  →  step-ca
```

Nothing about this stack replaces Traefik's own ACME configuration for
public hostnames, and this stack does not sit behind Traefik — see
[Traefik / networking](#traefik--networking) for why. Use step-ca for
certificates *other services in this installation* trust each other with —
mTLS between internal APIs, short-lived SSH host/user certificates, a
private ACME endpoint for infrastructure that never needs a
publicly-trusted certificate.

## Root CA vs. intermediate CA

`step ca init` (the image's own first-start behavior) creates a two-tier
PKI: a root CA and an intermediate CA that actually signs end-entity
certificates day to day. This stack ships **two paths**, and the choice you
make on first start is not easily undone:

- **Simple path (this stack's default in `.env.example`)** — both tiers are
  generated inside this container. The root private key ends up in
  `./volumes/data/secrets/root_ca_key` and stays there. This means the host
  running this container is also, permanently, the host holding the root
  key — an accepted tradeoff for a small internal PKI, not a hardened one.
- **Hardened path** — generate the root CA on a separate, offline machine,
  hand this container only the root's *public* certificate plus one-time
  use of the private key to sign the intermediate, then delete the root
  private key from this host entirely. The running server never needs it
  again — every day-to-day certificate it issues is signed by the
  intermediate. Full commands in `.env.example`'s Secrets section.

**The root key should not be online any longer than it takes to sign the
intermediate.** Once the intermediate exists, keep the root offline
(air-gapped machine, offline encrypted backup) and only bring it back for
the rare case of re-issuing a compromised or expiring intermediate.

## Provisioners, ACME, and SSH CA

- A JWK **provisioner** (`admin` by default) is created automatically at
  init, authenticated with the same password shown once in the logs at
  first start (see Setup below) — this is what `step` CLI clients use to
  request a certificate.
- **ACME** (`STEPCA_ENABLE_ACME=true`, this stack's default) exposes a
  standard ACME directory at `/acme/acme/directory` — anything that speaks
  ACME (certbot, Traefik's own ACME client pointed at this CA instead of a
  public one, etc.) can request certificates from it the same way it would
  from Let's Encrypt.
- **SSH CA** (`STEPCA_ENABLE_SSH`, off by default) additionally issues
  short-lived SSH host and user certificates. Only enable this at first
  init if you have an actual SSH-certificate workflow ready to use it —
  adding it later needs re-initialization, not a config edit. See
  UPSTREAM.md.
- **OIDC provisioners** (logging into `step` via an external identity
  provider instead of a shared JWK password) can be added after init with
  `step ca provisioner add` — not configured by default, and Authentik or
  Keycloak would both work as the provider. A deliberate follow-on, not a
  default this stack makes for you.

## Traefik / networking

This stack does **not** join `proxy-public` and carries no Traefik labels.
An ACME client or a `step ca bootstrap` call needs to reach step-ca's own
TLS certificate directly — that is the whole point of the fingerprint it
prints at first start (see Setup). Terminating TLS at Traefik first would
substitute Traefik's own certificate for step-ca's, which breaks that trust
model rather than merely reorganizing it. The port is published directly
instead; see `.env.example` for binding it to a narrower interface than
every host address.

## Security model

- **CA key never in `environment:` or plain config** — the password
  protecting it is a Docker Secret, read once at container start via
  `--password-file`, exactly as upstream's own image expects.
- **`cap_drop: ALL`, one capability re-added** — the binary carries an
  embedded file capability (`CAP_NET_BIND_SERVICE`) from its own build
  process; without re-adding it, the container fails to even exec the
  binary. Verified against a live container. Already non-root (`USER
  step` baked into the image).
- **`read_only: true`** — verified against a live container: step-ca writes
  only inside `/home/step` (its own volume mount), so the rest of the root
  filesystem can stay read-only.
- **The admin provisioner password is shown exactly once**, in the
  container's own startup log, and shredded from disk immediately after —
  it is never written anywhere by this stack. Capture it from `docker
  compose logs` right after the very first start.

## Setup

```bash
cp .env.example .env
# Edit: STEPCA_NAME, STEPCA_DNS_NAMES, STEPCA_PORT

mkdir -p .secrets volumes/data
openssl rand -base64 32 | tr -d '\n' > .secrets/ca_password.txt

docker compose up -d
docker compose logs -f    # capture "Your CA administrative password is: ..." — shown once
```

Verify and fetch the CA's fingerprint (needed by every client that will
trust this CA):

```bash
docker exec ${CONTAINER_NAME_APP:-step-ca-app} step certificate fingerprint /home/step/certs/root_ca.crt
```

Bootstrap a client against it:

```bash
step ca bootstrap --ca-url https://<STEPCA_DNS_NAMES>:<STEPCA_PORT> --fingerprint <fingerprint-from-above>
```

## Backup

| | |
|---|---|
| **CA keys** | `./volumes/data/secrets/` — root and/or intermediate private keys. **This is the single most critical file this stack produces.** Losing it without a backup means every certificate this CA ever issued becomes unverifiable, and every service trusting this CA needs to be re-bootstrapped against a new one |
| **CA config** | `./volumes/data/config/ca.json` — provisioners, ACME/SSH settings. Meaningless without the matching keys above; a config restored alone describes a CA that no longer exists |
| **Database** | `./volumes/data/db/` — step-ca's own embedded revocation and provisioner-metadata store. Restoring keys without this loses revocation history, not trust itself |
| **Password** | `.secrets/ca_password.txt` — without it, the restored keys are encrypted and inert |

```yaml
files:
    - path: /srv/docker/core/step-ca/volumes/data
    - path: /srv/docker/core/step-ca/.secrets/ca_password.txt
```

**Restore order:** all of `volumes/data` and the password file together, as
one unit — partial restores (config without keys, or keys at a different
path than the config expects) produce a CA that starts but cannot serve
certificates, or serves them under a different identity than the one every
client already trusts. If the root key was deliberately removed from this
host after the hardened init path, it is **not** part of this backup and
must be restored separately from wherever it is actually kept offline.

## Try it locally

```bash
cp .env.local.example .env.local
mkdir -p volumes/local/data
openssl rand -base64 32 | tr -d '\n' > ca_password.local.txt
docker compose -f docker-compose.local.yml --env-file .env.local up -d
docker compose -f docker-compose.local.yml --env-file .env.local logs   # capture the admin password
curl -sk https://localhost:9000/health
docker compose -f docker-compose.local.yml --env-file .env.local down
```

## Verify on first deploy (Preview → Ready gate)

- [x] `docker compose config` clean; `docker compose up -d` — running, one capability re-added, `read_only: true` intact — **verified locally, 2026-09-19**
- [x] ACME directory answers and `/health` returns `{"status":"ok"}` (local stack, real hostname) — **verified locally, 2026-09-19**
- [ ] The production compose's healthcheck against a real, DNS-resolvable `STEPCA_DNS_NAMES` — see UPSTREAM.md's known limitation; the local test used `localhost`, which trivially resolves and is not representative
- [ ] The hardened offline-root init path, end to end
- [ ] An actual client bootstrap and certificate issuance (X.509 and, if enabled, SSH) against a real host

## Details

- [UPSTREAM.md](UPSTREAM.md) — source, upgrade checklist, deviations
