# web-api pattern

> **Not a deployable service.** A reusable deployment shape for a generic
> backend — copy it, replace `fixture/` with the real project's source.

Covers source → build → production image → health → Traefik → security
baseline → operate/update/rebuild for a backend service. Deliberately has no
database, Redis, queue or worker — those are optional extensions, added the
same way [`apps/_reference`](../../apps/_reference/) shows, only when the real
application needs one.

## The fixture

[`fixture/`](fixture/) is the smallest working service that still proves the
whole contract: a TypeScript build step, a compiled image with no dev
dependencies, a `/healthz` endpoint, and a non-root runtime user. It has no
npm dependencies at runtime — a validation fixture for this deployment
contract, not a starting template for a real API's business logic.

## Adopting this pattern

An own application runs on a host as an own stack: the pattern becomes the root
of the project's own repository, and the host checks that repository out under
`custom/<name>`
([`deployment-lifecycle.md`](../../docs/standards/deployment-lifecycle.md#11--own-stacks-custom)).
There `scripts/stacks.sh` lists it with the Blueprint release it follows and
never removes it. `apps/` and `business/` hold the Blueprint's own stacks, the
ones a host takes from the Blueprint's releases — the place for this pattern
only when the stack becomes part of the Blueprint itself.

1. Copy `development/web-api/` into the project's repository.
2. Replace `fixture/` with the real project's source and its own `Dockerfile`
   — the two-stage shape (build, then a slim runtime with no dev tooling)
   stays; the language and framework do not have to.
3. Rename `COMPOSE_PROJECT_NAME` and `APP_TRAEFIK_HOST` in `.env.example`, and
   set `APP_PORT` to whatever the real service listens on.
   Add `<project>-edge`, the stack's own edge network that `TRAEFIK_NETWORK`
   names, to `EDGE_NETWORKS` in `core/traefik/.env`, then render and `up -d`
   there ([`edge-networks.md`](../../core/traefik/docs/edge-networks.md)).
   Traefik creates the network and joins it.
4. Rename the `app` service key in `docker-compose.yml` to `<project>-app`
   ([`naming-conventions.md`](../../docs/standards/naming-conventions.md#services-on-a-shared-external-network)).
   Compose publishes the key as a DNS name on the Traefik network. On the
   stack's own edge network only Traefik sees it; on the shared `proxy-public`
   every stack there does, and two stacks with the same key make the name
   ambiguous.
5. Give the README a line `**Blueprint:** vX.Y.Z`, the Blueprint release
   whose standards the stack follows.
6. Follow [`docs/standards/custom-application.md`](../../docs/standards/custom-application.md)
   for image identity, and [`docs/standards/new-app-checklist.md`](../../docs/standards/new-app-checklist.md)
   for `UPSTREAM.md`, backup documentation, and everything else a full stack
   carries that this pattern does not.

## Local deployment validation

```bash
cp .env.local.example .env.local
docker compose -f docker-compose.local.yml --env-file .env.local up -d --build
curl http://localhost:8082/healthz
docker compose -f docker-compose.local.yml --env-file .env.local down
```

The fixture has been built and run this way, with `read_only`, `cap_drop: ALL`
and `no-new-privileges` active, running as the non-root `node` user, and
reported `healthy`.

## Production deployment

With the stack's edge network in `EDGE_NETWORKS` (step 3 above):

```bash
cp .env.example .env
docker compose up -d --build
```

Traefik routing, TLS and the four middleware positions follow the same
`.env.example` variables as every other stack — see
[`docs/standards/traefik-security.md`](../../docs/standards/traefik-security.md).

## Update / rebuild

The image is rebuilt from source, not pulled. An own stack under `custom/`
takes a release of its own repository:

```bash
git fetch --tags
git checkout <tag>
docker compose build --pull
docker compose up -d
```

`APP_TAG` in `.env` is this pattern's own version — bump it when the source
changes in a way worth tagging, matching
[`docs/standards/custom-application.md`](../../docs/standards/custom-application.md#what-is-required).

## Adding a database, cache or queue

Not part of the base pattern. A real API that needs one adds it the way
[`apps/_reference`](../../apps/_reference/) shows:

- a `db` (or `redis`) service on a new `${COMPOSE_PROJECT_NAME}-internal`
  network, `internal: true`;
- the app service joins that network in addition to the Traefik network;
- the password reaches the container as a Docker Secret — native `_FILE`
  support where the image has it, an entrypoint wrapper where it does not
  (see [`security-baseline.md`](../../docs/standards/security-baseline.md));
- a `## Backup` section in the adopted project's own README.
