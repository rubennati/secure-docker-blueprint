# Upstream Reference

## Source

- **Image:** https://github.com/juanfont/headscale/pkgs/container/headscale
- **GitHub:** https://github.com/juanfont/headscale
- **Docs:** https://headscale.net
- **License:** BSD-3-Clause
- **Use restrictions:** none — https://github.com/juanfont/headscale/blob/main/LICENSE · checked 2026-09-23
- **Edition gating:** none — one open-source implementation, no paid tier — https://github.com/juanfont/headscale · checked 2026-09-23
- **Commercial model:** no paid edition — https://github.com/juanfont/headscale · checked 2026-09-23
- **Decision facts checked:** 2026-09-23
- **Origin:** Community · juanfont, Kristoffer Dalby and contributors · no single jurisdiction
- **Domain:** Infrastructure
- **Role:** Self-hosted control server for Tailscale clients — node registry, keys and access policy for a tailnet you run
- **Based on version:** `v0.29.4`

Upstream states plainly that the project is **not associated with Tailscale
Inc.** The clients are Tailscale's; the control server is not.

## Project maturity

44 069 stars, pushed 2026-09-23, release v0.29.4 the same day. Still 0.x, and
upstream says so: the configuration format changes between minor releases — two
keys in upstream's own `config-example.yaml` are already deprecated or removed
in this version, see below.

## Why `core/`

The test in [`docs/architecture.md`](../../docs/architecture.md) asks whether a
stack provides a shared network, TLS, identity, DNS, security or secrets
capability **for the installation rather than for its own users**. headscale is
the control plane of a tailnet — the same axis `acc-tailscale` sits on. The
older planned list in `apps/README.md` predates that sharpened rule.

## What we use

- `ghcr.io/juanfont/headscale:v0.29.4`, one container, SQLite.
- `config/config.yaml`, trimmed from upstream's 478-line example to what this
  stack sets or deliberately keeps.
- `derp.yml`, an opt-in overlay for the embedded relay.

## What we changed and why

| Change | Reason |
|--------|--------|
| `listen_addr: 0.0.0.0:8080` | Upstream's example listens on `127.0.0.1`, which nothing outside the container can reach |
| `user: "1000:1000"` | The image declares uid 0 and does not need it — everything it writes is under `/var/lib/headscale` |
| `read_only: true` with a tmpfs for `/var/run/headscale` | The control socket is the only thing outside the volume |
| `disable_check_updates: true` | Upstream's default is `false`: headscale checks for its own updates on start |
| `derp.update_frequency: 24h` | Upstream polls Tailscale's relay map every 3 hours |
| `trusted_proxies` set to the Docker bridge range | Without it headscale logs Traefik's address as every client's |
| `metrics_listen_addr` and `grpc_listen_addr` on loopback | Neither is routed, and the metrics endpoint has no authentication |
| `logtail.enabled: false` stated rather than omitted | Upstream ships the key pointing at Tailscale's logging service |
| `APP_TRAEFIK_ACCESS=acc-local` | A blueprint ships closed. See README, "Letting clients in" |
| The embedded relay is an overlay, not a default | It needs a published UDP port, which is the one thing the base file avoids |

## Verified on the image (2026-09-23)

Not a host verification: a throwaway network, no Traefik router, no Tailscale
client.

- First start healthy as **uid 1000** under `read_only`, `cap_drop: ALL` and
  `no-new-privileges`. No permission errors, before or after a restart.
- **`HEADSCALE_`-prefixed environment variables override the configuration
  file.** Measured: with `HEADSCALE_DERP_SERVER_ENABLED=true` headscale creates
  `derp_server_private.key`, without it it does not. That is what lets the two
  per-installation values stay in `.env` and the overlay stay a single variable
  — no second config file, no render step.
- **Two keys in upstream's own `config-example.yaml` do not work on v0.29.4.**
  `ephemeral_node_inactivity_timeout` warns and is ignored (it is
  `node.ephemeral.inactivity_timeout` now); `randomize_client_port` is **fatal**
  — headscale refuses to start and points at the policy file instead. A
  `configtest` against the trimmed configuration passes clean.
- `headscale health` is the health check: the image is distroless and carries
  no shell, no `ls` and no HTTP client.
- The HTTP surface Traefik routes: `/health` 200, `/windows` and `/apple` 200
  (client setup pages), `/key` 400 without the parameters a client sends.
- **`--user` on `preauthkeys create` takes the numeric ID, not the name.** A
  name is rejected with `strconv.ParseUint: parsing "ops": invalid syntax`.
  `users list` gives the ID.
- **The overlay works.** With `derp.yml` the container comes up healthy, the
  DERP key is created, the log reads `stun server started`, and 3478/udp is
  published.
- **A raw STUN probe gets no answer, and that is correct.** The embedded DERP
  is not a generic STUN server: it answers Tailscale clients only. Upstream
  [#3379](https://github.com/juanfont/headscale/issues/3379) reports exactly
  this observation and is closed as working as intended — verification needs
  `tailscale debug derp <region>` from a real client, which is a host test.
- Idle: 13 MiB anonymous with no node registered.

What a host run still has to establish: the route through `core/traefik`, a
client actually joining with a pre-auth key, MagicDNS resolving, the embedded
relay carrying traffic for a client that cannot connect directly, OIDC sign-in,
and a restore from the volume.

## What reaches the network on its own

The update check is off. One outbound dependency remains and it is deliberate:

`derp.urls` points at `https://controlplane.tailscale.com/derpmap/default`,
upstream's default, refreshed on the interval in `update_frequency`. That map
is what two clients fall back to when they cannot reach each other directly.
Removing it without enabling the embedded relay leaves them with no fallback at
all, so the base file keeps it and the README says what it costs. `derp.yml`
sets `HEADSCALE_DERP_AUTO_UPDATE_ENABLED=false`, because with your own relay in
the map the fetch is no longer what clients depend on.

## Upgrade checklist

1. Read the release notes and the CHANGELOG's BREAKING section —
   https://github.com/juanfont/headscale/releases. At 0.x the configuration
   format is part of the release
2. Raise `APP_TAG` in `.env` and in `.env.local.example`
3. `docker compose run --rm headscale configtest` **before** `up -d` — that is
   where a removed key shows up
4. `docker compose pull && docker compose up -d`
5. `docker compose exec headscale /ko-app/headscale nodes list` — every node
   still registered
6. Record the result in `Last verified` once it ran behind `core/traefik`

## Diff against upstream

```bash
# Upstream's full annotated example, which this configuration is trimmed from
curl -s https://raw.githubusercontent.com/juanfont/headscale/main/config-example.yaml

# Every command, and what this version accepts
docker run --rm ghcr.io/juanfont/headscale:v0.29.4 --help
```
