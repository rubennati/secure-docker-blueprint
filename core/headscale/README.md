# headscale

A self-hosted control server for Tailscale clients: the node registry, the keys
and the access policy for a tailnet you run yourself, instead of one run for
you. Upstream: [juanfont/headscale](https://github.com/juanfont/headscale),
which states it is **not associated with Tailscale Inc.** — the clients are
theirs, the control server is not.

It sits in `core/` for the reason the category test gives: it provides a shared
network capability for the installation rather than for users of its own. That
is the same axis [`acc-tailscale`](../traefik/) already sits on — and if you run
this, it is the tailnet that policy means.

## Architecture

```text
Traefik ──http──→ headscale :8080     control plane: registry, keys, policy
                      │
                      └── volumes/lib   SQLite, the node key, the DERP key

Clients ───────────────────────────→ each other, directly where they can
        └── relayed where they cannot: Tailscale's relays, or your own
            (derp.yml, 3478/udp)
```

## Setup

```bash
cp .env.example .env            # host name, tailnet domain
ops/init.sh                     # the data directory
sudo chown -R 1000:1000 volumes/lib
docker compose up -d

docker compose exec headscale /ko-app/headscale users create ops
docker compose exec headscale /ko-app/headscale users list          # note the ID
docker compose exec headscale /ko-app/headscale preauthkeys create --user 1 --expiration 1h
```

`--user` takes the **numeric ID**, not the name — v0.29.4 rejects a name with
`strconv.ParseUint: parsing "ops": invalid syntax`.

On the client:

```bash
tailscale up --login-server https://headscale.example.com --authkey <the key>
```

There is no password and no first-run wizard: `volumes/lib/noise_private.key`
is generated on the first start and **is the tailnet's identity**. Back it up
off this host — without it every node has to be registered again.

## Letting clients in

This ships with `acc-local`: reachable from your LAN and nowhere else. That is
the blueprint's position, not the product's — a control server no client can
reach is a control server no client can join.

Opening it is a deliberate step, and `acc-public` is not the only way to take
it:

| Approach | When it fits |
|---|---|
| Stay on `acc-local` | Every node joins from your network. They keep working anywhere afterwards — only the *join* needs the server |
| An IP allow-list in front | You know the addresses nodes register from |
| An SSH tunnel for the join | One node, once, without changing the policy |
| `acc-public` | Nodes join from anywhere. headscale's own authentication carries it: a node needs a pre-auth key or an OIDC sign-in, and the endpoint is not a user interface |

`acc-tailscale` is the one value that cannot work here: this server would be
that tailnet's control plane.

Whichever you pick, the host name in `APP_TRAEFIK_HOST` is what every node is
told to come back to. Changing it later means re-registering them.

## The embedded relay (`derp.yml`)

Two Tailscale clients talk directly when they can. When NAT or a firewall stops
them, the traffic goes through a relay — DERP. By default that relay is
Tailscale's, from the map headscale fetches at
`controlplane.tailscale.com`.

```bash
docker compose -f docker-compose.yml -f derp.yml up -d
```

turns on headscale's own instead.

|  | Tailscale's relays (default) | Your own (`derp.yml`) |
|---|---|---|
| Traffic content | end-to-end encrypted, relay sees none of it | the same |
| Metadata | Tailscale's infrastructure sees which endpoints relay, when, how much | nobody outside your host |
| Host ports | none | **3478/udp published** — STUN is not HTTP, Traefik cannot route it |
| Dependency | reachable relays operated by someone else | yours to keep running |

**The published port is the whole cost, and it is a deployment decision.** A
blueprint cannot know what sits in front of your host, so the base file does not
open it and this file does not pretend the question is settled. What protects a
published UDP port — a firewall rule, an address restriction, whether CrowdSec
can see it at all — has not been worked through here.

## Security model

- **Closed by default.** `acc-local`; see above.
- **Non-root**, `read_only`, `cap_drop: ALL`, `no-new-privileges`. The image
  declares uid 0 and does not need it.
- **No credential of its own to leak.** Nodes authenticate with pre-auth keys
  you issue and can expire; there is no admin password in this stack.
- **Metrics and gRPC stay on loopback.** headscale's metrics endpoint has no
  authentication, and nothing routes to it.
- **`logtail` is off**, stated rather than omitted — upstream ships the key
  pointing at Tailscale's logging service.
- **Update checks off.** One outbound dependency remains by design, the relay
  map above.
- **OIDC is supported and not configured here.** `oidc.client_secret_path`
  reads a file, which is the shape a Docker Secret takes — the wiring is
  upstream's to document and untested here.

## Known limits

- **Nothing has joined this tailnet.** The control server runs, the CLI creates
  users and keys, the HTTP surface answers — but no Tailscale client has
  registered against it, MagicDNS has not resolved anything, and no traffic has
  been relayed.
- **The embedded relay is started, not exercised.** A raw STUN probe gets no
  answer and that is correct: the embedded DERP answers Tailscale clients only
  ([upstream #3379](https://github.com/juanfont/headscale/issues/3379), closed
  as working as intended). Verifying it needs `tailscale debug derp` from a real
  client.
- **SQLite, one instance.** Fine for a tailnet; not a high-availability design.
- **Configuration changes between minor releases.** Two keys in upstream's own
  example are already deprecated or fatal on this version. Run `configtest`
  before every upgrade — the checklist in `UPSTREAM.md` puts it before `up -d`.
- **`sec-2` is not measured.** Clients poll and hold long connections.
- **Nothing here has run behind this repository's Traefik yet.** The stack is
  `scaffolded`.

## Backup

| | |
|---|---|
| **The identity** | `./volumes/lib/noise_private.key` — the tailnet's key. Lose it and every node re-registers. Copy it somewhere this host cannot reach |
| **The registry** | `./volumes/lib/db.sqlite` — nodes, users, pre-auth keys, policy. Stop the container before copying, or the write-ahead log makes it a half-file |
| **The relay key** | `./volumes/lib/derp_server_private.key` — only with `derp.yml`. Regenerating it is harmless; clients pick up the new one |
| **Reproducible** | `config/config.yaml` is in git |

```yaml
# /etc/borgmatic/config.yaml
source_directories:
  - /srv/secure-docker-blueprint/core/headscale/volumes/lib
```

Restore: put `volumes/lib` back owned by `1000:1000` and start the container.
Nodes reconnect on their own as long as the noise key and the host name are the
ones they were registered against.
