# static-site pattern

> **Not a deployable service.** A reusable deployment shape for a static
> frontend — copy it, replace the recipe with the real project's source.

Covers a build step that produces static files, served by a hardened, non-root
nginx behind Traefik. No backend, no database, no secrets — the entire deployed
artifact is the built image.

## The two recipes

Astro and Vite/React both compile to plain static files, so one runtime stage
serves either. The recipes differ only in the build stage:

| Recipe | Build command | Output |
|---|---|---|
| [`recipes/astro/`](recipes/astro/) | `astro build` | `dist/` |
| [`recipes/vite-react/`](recipes/vite-react/) | `vite build` | `dist/` |

Each recipe's `Dockerfile` is complete and self-contained — copy the one that
matches the real project's framework, not the whole pattern. `docker-compose.yml`
builds `recipes/astro` by default; point `build.context` at the other recipe, or
at the adopted project's own root, to use it instead.

The fixtures under `recipes/` are the smallest working project each framework
needs to build — a validation fixture for this deployment contract, not a
starting template for a real site's content.

## Adopting this pattern

An own application runs on a host as an own stack: the pattern becomes the root
of the project's own repository, and the host checks that repository out under
`custom/<name>`
([`deployment-lifecycle.md`](../../docs/standards/deployment-lifecycle.md#11--own-stacks-custom)).
There `scripts/stacks.sh` lists it with the Blueprint release it follows and
never removes it. `apps/` and `business/` hold the Blueprint's own stacks, the
ones a host takes from the Blueprint's releases — the place for this pattern
only when the stack becomes part of the Blueprint itself.

1. Copy `development/static-site/` into the project's repository.
2. Replace the recipe under `build.context` with the real project's source, or
   keep one recipe and delete the other.
3. Rename `COMPOSE_PROJECT_NAME` and `APP_TRAEFIK_HOST` in `.env.example`.
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
curl http://localhost:8081/
docker compose -f docker-compose.local.yml --env-file .env.local down
```

Both recipes have been built and run this way, with `read_only`, `cap_drop:
ALL` and `no-new-privileges` active, and reported `healthy`.

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

## Adding state

A static site has none by design. A real project that needs a backend follows
the `web-api/` pattern instead, or adds a database the way
[`apps/_reference`](../../apps/_reference/) shows — `app-internal` network,
Docker Secrets, a `## Backup` section in the adopted project's own README.
