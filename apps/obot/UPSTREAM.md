# Upstream Reference

## Source

- **Image:** https://github.com/obot-platform/obot/pkgs/container/obot
- **GitHub:** https://github.com/obot-platform/obot
- **Docs:** https://docs.obot.ai
- **License:** MIT
- **Use restrictions:** none — https://github.com/obot-platform/obot/blob/main/LICENSE · checked 2026-09-23
- **Edition gating:** none found — the repository is MIT throughout and names no paid tier — https://github.com/obot-platform/obot/blob/main/LICENSE · checked 2026-09-23
- **Commercial model:** no paid edition — https://github.com/obot-platform/obot · checked 2026-09-23
- **Decision facts checked:** 2026-09-23
- **Origin:** US · Obot AI, Inc · non-EU
- **Domain:** AI and local AI
- **Role:** MCP gateway and agent platform — catalogues MCP servers, runs the hosted ones as containers, with an LLM gateway in front
- **Based on version:** `v0.26.0`

## Project maturity

1 037 stars, pushed 2026-09-22, release v0.26.0 on 2026-09-17. Moving fast: the
image registry holds over 2 000 tags, and the minor version has gone from 0.7 to
0.26 in the time this repository has existed. Treat an upgrade as a change, not
a refresh.

## What we use

- `ghcr.io/obot-platform/obot:v0.26.0`, one container.
- `postgres:18.6-alpine`, which **replaces the PostgreSQL the image bundles**.
- `tecnativa/docker-socket-proxy:v0.5.0` between obot and the Docker daemon.

## What we changed and why

| Change | Reason |
|--------|--------|
| A socket proxy instead of `/var/run/docker.sock` on the application | Upstream's own `docker run` mounts the raw socket. The proxy denies exec, swarm, configs and secrets. It does not make the access safe — see the README section on that |
| An external PostgreSQL through `OBOT_SERVER_DSN` | Setting the DSN is what stops `run.sh` starting the bundled PostgreSQL, whose user and password are `obot`/`obot` baked into the image, on the same container as the application |
| `OBOT_SERVER_ENABLE_AUTHENTICATION=true` | **Upstream's default is off.** Without it obot serves everything to whoever reaches the port |
| `OBOT_BOOTSTRAP_TOKEN` from a Docker Secret | Left unset, obot generates one and prints it into the container log, where it stays |
| `user: "1000:1000"` | The image declares `USER 0`. With the DSN set it never needs root — verified below |
| `OBOT_SERVER_DISABLE_UPDATE_CHECK=true` | Upstream checks for new releases on its own |
| `APP_TAG=v0.26.0` | Upstream's documented command uses `:latest` |
| PostgreSQL on `internal: true` | Upstream has no second service to isolate |
| `APP_TRAEFIK_ACCESS=acc-tailscale` | This stack can start containers on the host |

## Verified on the images (2026-09-23)

Not a host verification: this ran the stack's own files with a throwaway network
and no Traefik router. The socket proxy did reach the real Docker daemon.

- `ops/init.sh` → `docker compose up -d`: obot came up healthy against the
  external PostgreSQL, with `cap_drop: ALL` and `no-new-privileges`.
- **It runs as uid 1000.** The image declares `USER 0`; nothing needed it once
  `OBOT_SERVER_DSN` was set. With root *and* `cap_drop: ALL` it fails instead —
  `mkdir: can't create directory '/data/cache': Permission denied`, because
  dropping `DAC_OVERRIDE` takes away exactly what lets root ignore file
  permissions. Non-root with a correctly owned volume is the working
  combination, not the fallback.
- **The socket proxy carries the real traffic.** Its access log shows obot
  listing, stopping and deleting MCP server containers through it:
  `GET /v1.52/containers/json?all=1&filters=…`,
  `POST /v1.52/containers/…/stop`, `DELETE /v1.52/containers/…?force=1`.
  A read-only allow-list is not an option: `pkg/mcp/docker.go` calls
  `ContainerCreate`, `ContainerRemove`, `ImagePull` and `VolumeCreate`.
- **Authentication is enforced once switched on.** `/api/me`,
  `/api/mcpcatalogs`, `/api/users` and `/api/agents` all answer `401
  unauthorized` without credentials; the bootstrap token as a bearer token
  returns the `bootstrap` user with the `owner` and `admin` groups, and a wrong
  token is refused.
- **The image ships no HTTP client** — no curl, no wget, and busybox is built
  without the wget applet. The health check opens the socket in bash instead.
  The endpoint is `/api/healthz`; `/healthz` and `/health` are 404.
- `client.FromEnv` in `pkg/mcp/docker.go` is why `DOCKER_HOST` is all it takes
  to point obot at the proxy.
- Idle with no MCP server hosted: obot 153 MiB anonymous, PostgreSQL 15 MiB
  plus 204 MiB page cache, the proxy 25 MiB.
- A restart came back healthy.

What a host run still has to establish: the route through `core/traefik`, an
authentication provider configured beyond the bootstrap user, actually hosting
an MCP server end to end, what the containers obot creates are allowed to do,
and a restore from the volumes.

## What reaches the network on its own

`OBOT_SERVER_DISABLE_UPDATE_CHECK` closes the update check. Four content feeds
remain, all on GitHub, all fetched at start:

| Setting | Default |
|---|---|
| `OBOT_SERVER_DEFAULT_MCPCATALOG_PATH` | `github.com/obot-platform/mcp-catalog` |
| `OBOT_SERVER_DEFAULT_SYSTEM_MCPCATALOG_PATH` | `github.com/obot-platform/system-mcp-catalog` |
| `--default-skill-repo-url` | `github.com/obot-platform/skills` |
| `--default-hosted-agents-catalog-url` | `github.com/obot-platform/hosted-agents-catalog` |

They are what the catalogue is made of rather than telemetry, and each can be
pointed at your own repository. Nothing about the installation is sent.

Upstream's defaults are on the careful side where it matters most:
`--disallow-localhost-mcp`, `--disallow-private-ipmcp` and
`--disallow-link-local-mcp` all default to **true**, so a hosted MCP server
cannot reach this host's own services unless that is changed.

## Upgrade checklist

1. Read the release notes — https://github.com/obot-platform/obot/releases,
   and expect behaviour changes at this release cadence
2. Raise `APP_TAG` in `.env` and in `.env.local.example`
3. `docker compose pull && docker compose up -d`
4. `docker compose logs obot-app` — no fatal errors; the health check green
5. Sign in and confirm the MCP servers you host still start
6. Record the result in `Last verified` once it ran behind `core/traefik`

## Diff against upstream

```bash
# Upstream's documented command — raw socket, :latest, bundled PostgreSQL
curl -s https://raw.githubusercontent.com/obot-platform/obot/main/README.md | grep -A12 'docker run'

# What the entrypoint does with OBOT_SERVER_DSN, and every server flag
docker run --rm --entrypoint sh ghcr.io/obot-platform/obot:v0.26.0 -c 'cat "$(command -v run.sh)"'
docker run --rm --entrypoint obot ghcr.io/obot-platform/obot:v0.26.0 server --help
```
