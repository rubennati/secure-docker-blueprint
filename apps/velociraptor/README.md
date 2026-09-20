# Velociraptor

Endpoint DFIR and threat-hunting server: query, monitor and collect
forensic artifacts from a fleet of Windows, Linux and macOS endpoints using
VQL (Velociraptor Query Language), at scale and over time.

```text
Velociraptor Server
        │
        ├── Windows Clients
        ├── Linux Clients
        └── macOS Clients
```

**Only the server is Docker-based here.** Endpoint agents run natively on
the machines being monitored and are not part of this stack — deploying,
enrolling and updating them is a separate, per-platform task this stack's
scope does not cover.

## What security problem this solves

Ongoing, queryable visibility into a real fleet of endpoints during a
hunt or an active investigation — not a one-time forensic image, a live
channel to run VQL queries, deploy monitoring artifacts and pull back
specific evidence across however many endpoints are enrolled.

## When this is useful

- You are actively hunting or responding across more than a handful of
  endpoints and need a queryable, persistent channel to them
- You want monitoring artifacts (not just one-off collection) running
  continuously across a fleet

## When this is not useful

- A single machine, one-off forensic acquisition — a dedicated collection
  tool without a fleet server is simpler
- Case management and evidence organization — see
  [DFIR-IRIS](../dfir-iris/); Velociraptor collects, IRIS organizes what
  was collected

## Velociraptor is an operative platform, not an always-on convenience app

Deploying this server creates ongoing trust relationships with every
endpoint that enrolls against it. Losing or replacing its cryptographic
identity does not just lose data — it breaks every enrolled client's trust
in this server (see Backup, below, which is the single most important
section in this document). Do not stand this up casually; plan for who
operates it, how long endpoints stay enrolled, and how its state gets
backed up before the first client ever connects.

## Security model

- **No non-root user in the upstream image** (verified: root only,
  confirmed against a live container) — a documented deviation, the same
  class already carried for DFIR-IRIS's `app`/`worker` in this repository.
  `cap_drop: ALL` still applies and needs nothing re-added — verified,
  including under `read_only: true`.
- **No Traefik, for both ports** — see the compose file's Networking
  comment. The frontend port (8000) uses certificate-pinned trust between
  server and agents; a TLS-terminating proxy in front would substitute its
  own certificate and break exactly the trust model this server exists to
  provide. The GUI port (8889) terminates its own TLS too, and mixing a
  second, differently-trusted TLS layer in front of it adds complexity
  without a clear benefit here.
- **Outbound internet access required** — verified against a live
  container: on first start (and after an upgrade) the server downloads
  endpoint-agent binaries and default hunting artifacts it later serves to
  clients. This stack does not isolate it on an internal-only network the
  way most other stacks in this repository do by default.
- **Initial admin password** is a Docker Secret, used once at first init
  only — every later start reuses the existing config and ignores it,
  confirmed by reading the entrypoint script directly.

## Setup

```bash
cp .env.example .env
# Edit: VELOCIRAPTOR_HOSTNAME (baked into the server certificate — get this
# right before first start), VELOCIRAPTOR_GUI_BIND, VELOCIRAPTOR_FRONTEND_BIND

mkdir -p .secrets volumes/etc volumes/datastore
openssl rand -base64 24 | tr -d '\n' > .secrets/admin_password.txt

docker compose up -d
docker compose logs -f   # watch for "GUI is ready to handle TLS requests"
```

Visit `https://<VELOCIRAPTOR_GUI_BIND>:8889` and sign in as `admin` with
the password you generated.

## Enrolling an endpoint

Not covered here — endpoint agents run natively on the machines being
monitored (see the architecture diagram above). Once the server is up,
generate a client config or an enrollment package from the GUI (Server
Artifacts → generate a client MSI/deb/pkg, or push a `client.config.yaml`)
and follow Velociraptor's own per-platform agent documentation.

## Optional: OIDC / SSO

Velociraptor's GUI supports OIDC, Google, Azure AD, GitHub and SAML
authenticators natively, confirmed free in the open-source server — not
configured by default here. Adding one means editing the generated
`server.config.yaml`'s `GUI.authenticator` block directly (there is no
env-var path for this) and recreating the container, a deliberate
follow-on rather than a default this stack makes for you.

## Backup — read this before this holds any real client

**A restored database without the matching `server.config.yaml` is
useless, and a restored `server.config.yaml` without the matching
datastore is a working server with no history.** They are not independent
backups of independent things.

| | |
|---|---|
| **Cryptographic identity & config** | `./volumes/etc/server.config.yaml` — the CA, the server's own certificate and private key, every provisioned user and their credentials. **Losing this, or replacing it with a different one, breaks trust for every already-enrolled endpoint** — they were issued certificates trusting this exact server identity, and a new/restored-from-elsewhere config is a different identity as far as they're concerned, even with the same hostname |
| **Datastore** | `./volumes/datastore` — every collected artifact, hunt result, monitoring event and client record. This is the actual forensic value this server accumulates over time |
| **Admin password** | `.secrets/admin_password.txt` — relevant only for a from-scratch re-init; an existing, restored config already has its own provisioned users independent of this file |

```yaml
files:
    - path: /srv/docker/apps/velociraptor/volumes/etc
    - path: /srv/docker/apps/velociraptor/volumes/datastore
```

**Restore order:** `server.config.yaml` and the datastore together, as one
unit, before the container starts for the first time after a restore.
Never generate a fresh config over an existing datastore, and never point
an old datastore at a freshly-generated config — either combination looks
like it works and silently produces a server none of your existing
endpoints actually trust.

## Try it locally

```bash
cp .env.local.example .env.local   # fill ADMIN_PASSWORD
mkdir -p volumes/local/etc volumes/local/datastore
docker compose -f docker-compose.local.yml --env-file .env.local up -d
# https://localhost:8889
docker compose -f docker-compose.local.yml --env-file .env.local down
```

## Verify on first deploy (Preview → Ready gate)

- [x] `docker compose config` clean; `docker compose up -d` — healthy, zero `cap_add`, running under `read_only: true` — **verified locally, 2026-09-19**
- [x] Real Docker Secret picked up for the initial admin password; GUI and frontend both confirmed serving TLS on their respective ports — **verified locally, 2026-09-19**
- [ ] An actual endpoint agent enrolled and a VQL query run against it
- [ ] OIDC/SSO sign-in
- [ ] A restore rehearsal of `server.config.yaml` + datastore together, confirming an already-enrolled client still trusts the restored server

## Details

- [UPSTREAM.md](UPSTREAM.md) — source, upgrade checklist, deviations
