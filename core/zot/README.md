# zot

OCI-native container registry — a place for this installation's own build
output to live: a self-built image (the `business/vikunja` /
`apps/caldiy`-style pattern documented in
[`docs/standards/custom-application.md`](../../docs/standards/custom-application.md)),
or an artifact you deliberately mirror rather than pull fresh from Docker
Hub/GHCR every time.

## What this is not

Not a replacement for Docker Hub, GHCR or any other upstream image source —
every stack in this repository keeps pulling its published images from
wherever `UPSTREAM.md` says they come from. This registry is for images
*this installation* produces, not a cache or mirror of the internet.

Not Harbor. Harbor is a broader platform (its own RBAC UI, project
quotas, a bundled Trivy deployment, replication policies across many
registries) and would be a defensible choice too. zot was picked here for a
much smaller operating footprint: one static Go binary, no database, no
separate scanner container — Harbor being more full-featured is not a claim
that it is the better choice for every installation, only that it costs
more to run.

## Security model

- **Single admin user, deny-by-default.** `config/config.json`'s
  `accessControl` grants full read/write/delete only to the one user named
  in `adminPolicy`; every other repository policy is empty, so an
  unauthenticated or unlisted caller gets nothing. Add more users to
  `.secrets/htpasswd` and to the policy block deliberately, not by copying
  a permissive example config.
- **No cap_add, no root.** The image ships as a single distroless binary
  with no privilege-drop entrypoint of its own; `user:` fixes it to a
  non-root UID directly, and it starts cleanly under `cap_drop: ALL` +
  `read_only: true` with zero capabilities re-added. Verified against a
  live container.
- **CVE scanning is built in, not bolted on.** `config.json` enables the
  `search` extension's embedded Trivy vulnerability database — zot
  downloads and refreshes it itself (`ghcr.io/aquasecurity/trivy-db`) and
  scans stored images on that schedule. No separate Trivy container is
  needed for this stack's own registry content.
- **No healthcheck.** The image has no shell, no `curl`/`wget`/`nc`, and no
  health-check subcommand — there is nothing inside the container that can
  run a check. Confirmed against a live container, not assumed.

## Setup

```bash
cp .env.example .env
# Edit: APP_TRAEFIK_HOST

mkdir -p .secrets volumes/registry
sudo chown 1000:1000 volumes/registry

# Bcrypt htpasswd entry — this host has no htpasswd binary by default
docker run --rm httpd:2.4-alpine htpasswd -Bbn admin "$(openssl rand -base64 24)" \
  > .secrets/htpasswd
# Note the generated password before it scrolls out of your shell history

docker compose up -d
docker compose logs -f    # watch for "finished setting up ui routes"
```

Verify:

```bash
docker login registry.example.com -u admin
docker tag alpine:3 registry.example.com/test/alpine:3
docker push registry.example.com/test/alpine:3
```

## Signing and SBOM (Cosign / Notation)

zot's `imagetrust` extension can verify Cosign and Notation signatures on
push, but it needs its own signing keys/certificates configured — this
stack does not enable it out of the box (`config.json` leaves it absent, and
the startup log confirms: *"skip enabling the image trust routes as the
config prerequisites are not met"*). If you sign images as part of your
build pipeline, add the `imagetrust` block to `config/config.json` once you
have decided where the verification key material lives; that is a
deliberate follow-on decision, not a default this stack makes for you.

## Garbage collection

Enabled inline (`storage.gc: true`) — zot reclaims unreferenced blobs on its
own schedule (`gcInterval: 24h`, `gcDelay: 2h` grace period before an
unreferenced blob is actually removed) without needing the registry taken
offline.

## Optional: OIDC via Authentik or Keycloak

zot supports a generic OIDC provider block under `http.auth.openid.providers.oidc`
alongside htpasswd (both can be active at once). Not configured here —
adding it means registering an OIDC application in Authentik or Keycloak,
adding the resulting client credentials as a Docker Secret, and extending
`config/config.json`'s `auth` block. Left as a deliberate follow-on, the
same way Threat Dragon's Git-provider OAuth is optional rather than
default.

## Backup

| | |
|---|---|
| **Config** | `./config/config.json` — access policy and extension settings, not sensitive on its own |
| **Credentials** | `.secrets/htpasswd` — bcrypt hashes; losing it locks every user out, but it does not by itself expose any password |
| **State** | `./volumes/registry` — every stored image layer, manifest and tag. This is the registry; nothing else contains its content |
| **Reproducible** | Nothing meaningfully — an image pushed here may not exist anywhere else once the source it was built from has moved on |

```yaml
files:
    - path: /srv/docker/core/zot/volumes/registry
    - path: /srv/docker/core/zot/.secrets/htpasswd
    - path: /srv/docker/core/zot/config/config.json
```

**Restore order:** restore `config/config.json` and `.secrets/htpasswd`
together with `volumes/registry`, then start the container. Restoring the
registry storage without the matching htpasswd file leaves images intact
but nobody able to authenticate against them.

## Local testing (no Traefik)

```bash
cp .env.local.example .env.local
mkdir -p volumes/local/registry
sudo chown 1000:1000 volumes/local/registry
docker run --rm httpd:2.4-alpine htpasswd -Bbn admin localtest123 > htpasswd.local
docker compose -f docker-compose.local.yml --env-file .env.local up -d
curl -u admin:localtest123 http://localhost:8080/v2/
docker compose -f docker-compose.local.yml --env-file .env.local down
```

## Verify on first deploy (Preview → Ready gate)

- [x] `docker compose config` clean; `docker compose up -d` — running, zero `cap_add` — **verified locally, 2026-09-19**
- [x] Unauthenticated request to `/v2/` returns 401, admin credentials return 200 — **verified locally, 2026-09-19**
- [ ] An actual `docker push`/`docker pull` round trip through Traefik on a real host
- [ ] The embedded CVE scan actually flags a known-vulnerable test image
- [ ] TLS and the chosen `APP_TRAEFIK_SECURITY` chain confirmed against the real domain

## Details

- [UPSTREAM.md](UPSTREAM.md) — source, upgrade checklist, deviations
