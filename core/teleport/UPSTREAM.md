# Upstream Reference

## Source

- **Upstream GitHub:** https://github.com/gravitational/teleport
- **Image registry:** `public.ecr.aws/gravitational/teleport-distroless` (Amazon ECR Public)
- **Docs:** https://goteleport.com/docs/
- **Self-host reference:** https://goteleport.com/docs/installation/single-machine/docker/
- **License:** AGPL-3.0 (source) / Commercial (Community Edition compiled
  binaries and container images, since Teleport 16) — see "Community
  Edition license" below, this is not a simple open-source license
- **Origin:** USA · Gravitational, Inc. · non-EU
- **Based on version:** `18.11.0`
- **Verification snapshot:** 2026-09-19 — clean start and hardening under full
  container isolation; no real client connection, no join token exercised

## Community Edition license — read before deploying this

Verified directly, because this materially affects who may run this image:

Since **Teleport 16** (2026), Community Edition's compiled binaries,
container images and AMIs are **no longer Apache-2.0** — they moved to a
commercial license with usage conditions:

- **Individuals:** unrestricted personal/hobby use.
- **Companies:** free only with **fewer than 100 employees and less than
  $10M annual recurring revenue**. Above either threshold, Teleport
  requires contacting sales for an Enterprise agreement.
- Client libraries and documentation remain Apache-2.0; a binary you
  compile from source yourself is AGPL-3.0.

For this repository's stated personal/self-hosted scope, Community Edition
is usable under the individual clause. A company deploying this compose
file has to independently confirm it stays under the size/revenue
threshold — this is not something a Docker image or compose file can
enforce or verify.

## What we use

- `public.ecr.aws/gravitational/teleport-distroless:18.11.0`, single
  container, `auth` and `proxy` roles combined — the realistic single-node
  shape for what this repository targets, not a production Teleport
  cluster's separated-role, HA topology
- The image's own embedded BoltDB backend (`dir` storage) for cluster
  state — no external database

## What we changed vs. upstream docs

| Change | Reason |
|--------|--------|
| No Traefik | Verified: a fresh config defaults to `proxy_listener_mode: multiplex` — the proxy port carries certificate-based mutual TLS for tsh/agent/kube/db clients as well as the browser UI. A TLS-terminating reverse proxy in front would break every non-browser client. See `docker-compose.yml`'s header. |
| `teleport debug readyz` as the healthcheck | Verified real subcommand and real behavior against a live container — not invented. The distroless image has no shell for a curl/wget-style check. |
| `cap_drop: ALL` + `read_only: true` + `no-new-privileges:true` | Verified together against a live container: started cleanly, both listeners bound, `debug readyz` reported ready |

## What was actually verified, and how

- `docker inspect` — confirmed entrypoint `dumb-init /usr/local/bin/teleport
  start -c /etc/teleport/teleport.yaml`, `User: "0"` (root, vendor default),
  and genuinely no shell (`docker run --entrypoint /bin/sh` fails: `no such
  file or directory`).
- `teleport configure --roles=proxy,auth` — generated a working
  `teleport.yaml` with `auth_service.listen_addr: 0.0.0.0:3025` and
  `proxy_listener_mode: multiplex`, no `web_listen_addr` override needed.
- Started the container against that config, unhardened: bound both
  listeners, `GET /webapi/ping` over HTTPS returned a valid cluster status
  document confirming `"edition":"community"`.
- Repeated under `cap_drop: ALL`, `read_only`, `no-new-privileges`: same
  clean start, `teleport debug readyz` returned `ready (PID:7)`, exit 0.
- **Not verified:** joining a node with a real token, an actual `tsh`
  session, the web UI login flow, any auth connector (local users only —
  OIDC/SAML are Enterprise-only, see README.md), a real ACME certificate,
  backup/restore, or behavior across a restart or upgrade.

## Upgrade checklist

1. Check https://goteleport.com/docs/upcoming-releases/ — Teleport ships
   one major version per year (August) with 24 months of support; confirm
   whether 18.x is still current or 19.x has since become current
2. Read the release notes for breaking config changes
3. Back up `./config` and `./volumes/data` before upgrading — the BoltDB
   backend holds the cluster CA; losing it invalidates every issued
   certificate
4. Bump `APP_TAG` in `.env`
5. `docker compose pull && docker compose up -d`
6. Confirm with `docker compose exec teleport /usr/local/bin/teleport debug readyz -c /etc/teleport/teleport.yaml`

## Known limitations

- **OIDC/SAML SSO confirmed Enterprise-only in Community Edition** —
  verified via multiple independent sources. Local users plus MFA is the
  only auth path this deployment can offer; see README.md's Security
  Model for what that means for Authentik/Keycloak integration.
- **Single-node only.** This is `auth` and `proxy` combined in one
  container with an embedded backend — realistic for what this repository
  targets, not a representation of a production Teleport cluster's
  separated-role, HA-backend topology.
- **License requires the operator's own judgment** — see "Community
  Edition license" above. Nothing in this repository can verify a
  deployment stays within the free-use thresholds.
- **Not yet run on a live host beyond a clean start.**
