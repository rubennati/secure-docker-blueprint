# IPv4-only vs. Dual-Stack Networking

Why the Traefik public network sometimes needs IPv6, how to set it up for a
new deployment, and how to migrate an existing IPv4-only install safely.

For the security middleware system (access policies, TLS, headers), see
[Traefik Security Architecture](../../../docs/standards/traefik-security.md).
For the general network model (`proxy-public` / `app-internal`), see
[Networking](../../../docs/standards/networking.md).

---

## Why this exists

This blueprint has two public-facing access paths into Traefik:

1. **Public** — Browser → Cloudflare → Traefik → Docker app
2. **Internal** — Tailnet client → Tailscale / MagicDNS / Split-DNS → Traefik → Docker app

These two paths recover the real client IP through **completely different
mechanisms**, and conflating them is the root of the failure this document
exists to prevent:

| Path | How the real client IP reaches Traefik |
|------|----------------------------------------|
| Cloudflare | Cloudflare terminates the original connection and proxies to Traefik. The real client IP travels in the `X-Forwarded-For` header. Traefik only trusts that header from Cloudflare's own edge IPs (`forwardedHeaders.trustedIPs` in `traefik.yml`) — this is an **application-layer (HTTP header) mechanism**. |
| Tailscale | The tailnet client connects to Traefik **directly** — there is no intermediate proxy rewriting headers. The real client IP is whatever Docker hands Traefik as the TCP peer address — this is a **network-layer (source IP) mechanism**. There is no header to trust or fall back on. |

Because Tailscale always gives a client an IPv6 address
(`fd7a:115c:a1e0::/48`) in addition to its IPv4 CGNAT address
(`100.64.0.0/10`), the network-layer mechanism only works for IPv6 clients
if the **Docker network Traefik's public-facing container sits on can carry
an IPv6 source address end to end**. If that network is IPv4-only, the
IPv6 source IP is lost before Traefik ever sees it — no header exists to
recover it from, unlike the Cloudflare path.

This is why the public Traefik network needs IPv6 specifically to preserve
real client IPs for Tailscale, while Cloudflare's real-IP handling is
unaffected by the network's IP family — it depends on
`forwardedHeaders.trustedIPs`, not on the network.

### The three traffic paths

```
PUBLIC PATH (Cloudflare)                     INTERNAL PATH (Tailscale)
─────────────────────────                    ─────────────────────────
Browser (any IP)                              Tailnet client (100.x.x.x / fd7a:...)
   │ HTTPS                                       │ HTTPS — direct, no proxy hop
   ▼                                              ▼
Cloudflare edge                               Tailscale / MagicDNS / Split-DNS
   │ proxied; sets X-Forwarded-For to the         │ resolves the hostname straight
   │ real client IP. TCP peer seen by             │ to Traefik's Tailscale or LAN
   │ Traefik is Cloudflare's own edge IP.         │ address — no header rewriting.
   ▼                                              ▼
┌───────────────────────────────────────────────────────────────────────┐
│ Traefik (core/traefik) — proxy-public network                         │
│  · Cloudflare path: forwardedHeaders.trustedIPs (traefik.yml) recovers│
│    the real client IP from X-Forwarded-For — works regardless of      │
│    whether proxy-public is IPv4-only or dual-stack.                   │
│  · Tailscale path: ClientHost IS the real Tailscale IP already — IF   │
│    the network can carry it end to end. IPv6 clients need IPv6 on     │
│    proxy-public, or the source IP is lost before Traefik sees it.     │
└───────────────────────────────────────────────────────────────────────┘
   │ proxy-public                                 │ proxy-public
   ▼                                               ▼
┌───────────────────────────────────────────────────────────────────────┐
│ Docker app — web-facing service: proxy-public + app-internal          │
└───────────────────────────────────────────────────────────────────────┘
   │ app-internal (internal: true)
   ▼
┌───────────────────────────────────────────────────────────────────────┐
│ DB · Redis · workers — app-internal only. IPv4-only is fine here:     │
│ nothing outside the Docker host ever connects to these directly.      │
└───────────────────────────────────────────────────────────────────────┘
```

**The rule this gives us:** the public Traefik ingress network
(`proxy-public`) is the only network that needs IPv6, and only because of
the Tailscale path. Internal `app-internal` networks (DB, Redis, workers)
stay IPv4-only — see [Why internal networks don't need IPv6](#why-internal-networks-dont-need-ipv6).

---

## The failure mode this prevents

This is the production issue that motivated this document, debugged on a
Linux host running Traefik v3.6 in Docker.

**Symptom:** Tailscale clients connecting over IPv6 got `HTTP 403` from
Traefik's `acc-tailscale` middleware, while the same clients worked fine
over IPv4.

```bash
curl -4 https://auth.example.com/   # → 100.116.181.16  → HTTP/2 302 (ok)
curl -6 https://auth.example.com/   # → fd7a:115c:a1e0::9e32:b510 → HTTP/2 403 (blocked)
```

**Root cause — in order:**

1. The Docker public network (`proxy-public`) was created IPv4-only:
   `EnableIPv6=false`, subnet `172.19.0.0/16`, gateway `172.19.0.1`.
2. The Docker daemon was still listening on IPv6 host ports (`[::]:80`,
   `[::]:443`) — this is normal; the daemon listens on both families by
   default regardless of any single network's IPv6 setting.
3. With the default `userland-proxy: true`, Docker's `docker-proxy`
   process bridges those IPv6 host-port connections into the IPv4-only
   container network using a userland relay — not a kernel NAT rule. The
   relay terminates the IPv6 connection and opens a **new** IPv4
   connection to the container, **sourced from the Docker bridge gateway
   address**, not the original client.
4. Traefik therefore sees `ClientHost=172.19.0.1` (the gateway) for every
   IPv6 client, instead of the real Tailscale IPv6 address.
5. `acc-tailscale`'s `ipAllowList` only allows `100.64.0.0/10` and
   `fd7a:115c:a1e0::/48` — `172.19.0.1` matches neither → `403`.

```
Tailscale IPv6 client
  → fd7a:115c:a1e0::...:443 on the host
  → Docker published port → docker-proxy (userland relay)
  → IPv4-only Docker bridge (source IP rewritten to the gateway)
  → Traefik sees ClientHost=172.19.0.1
  → acc-tailscale ipAllowList: no match
  → HTTP 403
```

**The fix** is the combination documented below: enable IPv6 at the
Docker daemon level, disable `userland-proxy` (so Docker uses kernel
`ip6tables` DNAT instead of the lossy userland relay), and give
`proxy-public` an actual IPv6 subnet so the container has a real IPv6
address to be the NAT target. All three together — any one alone is not
sufficient:

- IPv6 daemon support without a dual-stack network: the container still
  has no IPv6 address to route to.
- A dual-stack network without disabling `userland-proxy`: the userland
  relay still terminates the connection and re-sources it from the
  gateway, even though the container could now carry a real IPv6 address.
- Disabling `userland-proxy` without daemon IPv6 support: `ip6tables`
  rules cannot DNAT into a network that has no IPv6 addresses to target —
  the connection simply fails instead of silently using the wrong IP.

After the fix:

```bash
curl -6 https://auth.example.com/   # → fd7a:115c:a1e0::9e32:b510 → HTTP/2 302 (ok)
```

And `whoami` (see [core/whoami](../../whoami/)) shows the real address in
both the proxy headers and its own view of the connection:

```
X-Forwarded-For: fd7a:115c:a1e0::9e32:b510
X-Real-Ip: fd7a:115c:a1e0::9e32:b510
```

---

## Why not `network_mode: host`

Putting Traefik on `network_mode: host` would also "fix" this — the
container would see the host's real network stack directly, no Docker
bridge translation involved at all. It is not the primary recommendation
in this blueprint, for reasons specific to how this repo is built:

- **It breaks the Docker provider's network-scoped discovery model.**
  Traefik's docker provider (`providers.docker.network` in
  `traefik.yml.tmpl`) resolves backends by joining the same bridge network
  as the target container. Host networking removes Traefik from
  `proxy-public` entirely, which breaks routing to every app unless every
  app is *also* moved to host networking — cascading the exception across
  the whole blueprint.
- **It bypasses every container-level network isolation control** this
  blueprint relies on (`docs/standards/security-baseline.md` —
  `app-internal` networks, `internal: true`, the socket-proxy network).
  Traefik would share the host's network namespace, not a scoped bridge.
- **It is already a documented, narrow exception for a different
  reason.** `core/dnsmasq` uses `network_mode: host` because a DNS server
  must receive broadcast/multicast queries the Docker bridge does not
  forward — a constraint specific to UDP/53, not HTTP routing. Adding
  Traefik to that exception list would be a structural change to the
  blueprint's network model, not a targeted fix for this bug. The CI
  baseline checker (`scripts/ci/check-baseline.py`) treats
  `network_mode: host` as a reviewed exception requiring `reason` /
  `alternatives` / `risk` fields precisely because it should stay rare.

Host networking is mentioned here only as a fallback for operators who
have a specific reason to bypass Docker's bridge networking entirely
(e.g. running Traefik directly on a host that already terminates IPv6
correctly some other way). It is not what this blueprint sets up by
default, and the rest of this document does not assume it.

---

## Why internal networks don't need IPv6

`app-internal` networks (databases, Redis, workers) are not reachable from
outside the Docker host under any of the three paths described above —
they have no Traefik router, no published port, and (where `internal:
true` is set) no route to the internet at all. Nothing external ever
connects to them directly, so there is no client source IP to preserve in
the first place. Making every internal network dual-stack would add
operational surface (more daemon/network configuration to get right) for
zero security or functionality benefit. Per
[Networking](../../../docs/standards/networking.md), `app-internal` stays
exactly as it is today — IPv4-only, `internal: true` where appropriate.

---

## Why `172.19.0.1/32` in `ipAllowList` is a workaround, not a fix

A tempting quick patch when you first see `ClientHost=172.19.0.1` getting
blocked is to add `172.19.0.1/32` to `acc-tailscale`'s `ipAllowList` and
move on. Resist this — it does not fix anything, it just stops the
specific symptom from showing up as a 403:

- **It collapses every IPv6 client into one identity.** Every Tailscale
  IPv6 peer hitting the broken path looks identical to Traefik —
  `172.19.0.1`, the Docker gateway. The allowlist can no longer
  distinguish between "a legitimate tailnet member" and "anything that
  can reach the gateway address," which defeats the entire point of an
  IP-based access policy.
- **It silently widens access beyond Tailscale.** `172.19.0.1` is the
  gateway address for *any* container on that bridge network, not just
  the path from Tailscale. Allowlisting it permits traffic from that
  shared identity in general, not specifically "real Tailscale clients
  whose IPv6 got mangled."
- **It breaks CrowdSec decisions for the same reason** — see
  [CrowdSec and real client IPs](#crowdsec-and-real-client-ips) below.
- **It hides the actual defect.** The real problem — IPv6 source IPs
  being silently discarded — remains. The allowlist entry just stops it
  from being visible as a 403, which makes it more likely to resurface
  somewhere CrowdSec, audit logs, or per-user access policies depend on
  an accurate client IP later.

The correct fix is restoring real source IPs end to end (this document),
not widening the allowlist to tolerate their absence.

---

## Docker daemon prerequisites

Three daemon-level settings, applied together, on the Docker host. This
changes `/etc/docker/daemon.json` and requires a daemon restart — **plan a
maintenance window**: restarting the Docker daemon affects every
container on the host, not just Traefik.

### 1. Back up the current config

```bash
# If the file exists, back it up first. If it doesn't exist yet, Docker
# is running on defaults and there is nothing to back up.
test -f /etc/docker/daemon.json && \
  sudo cp /etc/docker/daemon.json /etc/docker/daemon.json.bak-"$(date +%Y%m%d)" \
  || echo "No existing daemon.json — will create a new one"
```

### 2. Apply the new config

Merge these three keys into the existing file — keep whatever logging
options (or other settings) are already present:

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "ipv6": true,
  "ip6tables": true,
  "userland-proxy": false
}
```

What each setting does:

| Setting | Effect |
|---|---|
| `ipv6: true` | Required groundwork for IPv6 networking at the daemon level. (Exact scope has evolved across Docker Engine versions — treat it as a prerequisite flag, not a fine-grained switch.) |
| `ip6tables: true` | Docker manages `ip6tables` NAT/filter rules for IPv6, the same way `iptables: true` already does for IPv4 by default. Without this, published IPv6 ports are not actually forwarded even on a dual-stack network. |
| `userland-proxy: false` | Disables the `docker-proxy` userland relay for **all** published ports (IPv4 and IPv6). Docker uses kernel-level `iptables`/`ip6tables` DNAT instead, which preserves the real source IP. This is the setting that directly fixes the `ClientHost=172.19.0.1` symptom — but only once `proxy-public` actually has an IPv6 subnet to DNAT into (see below). |

Validate the JSON before restarting (a syntax error here can prevent the
daemon from starting at all):

```bash
sudo python3 -m json.tool /etc/docker/daemon.json
# or: jq . /etc/docker/daemon.json
```

### 3. Restart and verify

```bash
sudo systemctl restart docker

# Daemon came back up and is healthy
sudo systemctl status docker --no-pager
docker info >/dev/null && echo "daemon reachable"

# Every container that was running should have restarted automatically
# (restart: unless-stopped) — spot check:
docker ps --format "table {{.Names}}\t{{.Status}}"
```

### Rollback

```bash
sudo cp /etc/docker/daemon.json.bak-<date> /etc/docker/daemon.json
sudo systemctl restart docker
docker ps --format "table {{.Names}}\t{{.Status}}"
```

If `userland-proxy` is reverted to its default while a dual-stack
`proxy-public` network still exists, Docker falls back to the userland
relay for the *published host ports*. The network itself stays
dual-stack — containers keep their IPv6 addresses — but **this
reintroduces the original symptom**: the userland relay loses the real
source IP for published-port connections regardless of whether the
target network is dual-stack, so `ClientHost` goes back to showing a
Docker-internal address instead of the real Tailscale IP. Reverting
`userland-proxy` is therefore not a partial/safe middle ground — treat
the three daemon settings as applied together or not at all. To fully
roll back to the original IPv4-only state, also remove the dual-stack
network (see [Rollback](#8-rollback) in the migration guide).

---

## Choosing a ULA prefix

Dual-stack `proxy-public` needs an explicit IPv6 subnet — Docker has no
default IPv6 address pool to auto-assign from the way it does for IPv4.
Use a **Unique Local Address (ULA)** prefix (`fc00::/7`, same family as
the `fc00::/7` range already used by `acc-local`/`acc-private` in
`access.yml`), not a public/global IPv6 allocation you don't own.

`fd00:dead:beef:30::/64` (used as the example throughout this repo) is a
**placeholder** — every production deployment should generate and
document its own random prefix, the same way you would not reuse someone
else's RFC1918 range on purpose:

```bash
# Generate a random 40-bit ULA global ID (RFC 4193 §3.2.2) and format it
# as an fd00:.../64 prefix:
printf 'fd%s\n' "$(openssl rand -hex 5 | sed -E 's/(.{4})(.{4})(.{2})/\1:\2:\3/')"
# Example output: fd3a:9f1c:7e::  → use as fd3a:9f1c:7e00::/64 (pick a
# consistent /64 boundary) — or use https://www.unique-local-ipv6.com/
```

Record the prefix you chose somewhere durable (this repo's convention:
the per-deployment `.env`, which is already gitignored and host-specific).

---

## Quick setup — new deployment (dual-stack from day one)

Recommended default for new installs: modern servers increasingly have
IPv6, and Tailscale always hands out an IPv6 address regardless. Starting
dual-stack avoids a later migration.

```bash
cd core/traefik
cp .env.example .env
# Edit .env: uncomment and set
#   PUBLIC_NETWORK_SUBNET_V4=172.30.0.0/16
#   PUBLIC_NETWORK_SUBNET_V6=<your own ULA prefix>/64

# Complete the Docker daemon prerequisites above FIRST.

bash ops/scripts/render.sh
docker compose -f docker-compose.yml -f network-dual-stack.yml up -d

# Verify it actually applied — EnableIPv6 must be true, and IPAM.Config
# must list both subnets. This overlay only CREATES a dual-stack network;
# if proxy-public already existed, Compose silently reuses it as-is and
# does NOT error — always check this rather than assuming success:
docker network inspect "$(grep ^PUBLIC_NETWORK= .env | cut -d= -f2)" \
  --format 'EnableIPv6={{.EnableIPv6}}'
docker network inspect "$(grep ^PUBLIC_NETWORK= .env | cut -d= -f2)" \
  --format '{{json .IPAM.Config}}'
```

Everything else (apps, security middleware, TLS) works exactly as in the
IPv4-only setup — `proxy-public` is still just `proxy-public`, attached
via `external: true` the same way in every app's `docker-compose.yml`.

---

## Migration guide — existing IPv4-only deployment

Do not edit the live `proxy-public` network in place. Docker cannot add
IPv6 to a network that already exists without recreating it, which means
detaching and reattaching every container on it. Instead: stand up a new
dual-stack network under a new name, prove it works, then cut over.

### 1. Capture current state

```bash
mkdir -p /tmp/traefik-migration
docker network inspect proxy-public > /tmp/traefik-migration/proxy-public-before.json
docker ps --filter network=proxy-public --format '{{.Names}}' \
  > /tmp/traefik-migration/containers-before.txt
cat /tmp/traefik-migration/containers-before.txt
```

> **Before sharing any of this output (issue, chat, support request):**
> see [Secret redaction](#secret-redaction-when-sharing-debug-output) —
> `docker compose config` resolves and prints `.env` values, including
> tokens.

### 2. Complete the Docker daemon prerequisites

See [Docker daemon prerequisites](#docker-daemon-prerequisites) above.
Do this before creating the new network.

### 3. Create the new dual-stack network

```bash
docker network create \
  --driver bridge \
  --ipv6 \
  --subnet 172.30.0.0/16 \
  --subnet <your-ULA-prefix>::/64 \
  --opt com.docker.network.bridge.name=br-proxy-v6 \
  proxy-public-v6

docker network inspect proxy-public-v6 --format '{{json .IPAM.Config}}'
```

### 4. Attach a test service (whoami) and verify

`core/whoami/docker-compose.yml` references the network by the literal
name `proxy-public` (`networks: proxy-public: external: true`) — it has
no `PUBLIC_NETWORK`-style variable to redirect, so do not try to retarget
it via `.env`. Connect the already-running container to the new network
directly instead:

```bash
cd core/whoami
docker compose up -d   # if not already running, on the original proxy-public
docker network connect proxy-public-v6 "$(grep ^CONTAINER_NAME_APP= .env | cut -d= -f2)"
docker inspect "$(grep ^CONTAINER_NAME_APP= .env | cut -d= -f2)" \
  --format '{{range .NetworkSettings.Networks}}{{.IPAddress}} {{.GlobalIPv6Address}}{{end}}'
```

Both an IPv4 and a global/ULA IPv6 address should be present (whoami is
now on both networks at once — this is expected and fine for testing).

This step is for direct inspection of whoami's own connection only —
it is **not** what makes the IPv6 fix testable. What actually determines
whether Tailscale IPv6 ingress preserves the real client IP is whether
**Traefik itself** is on the dual-stack network (step 5), since that's
what controls the published host ports IPv6 clients connect to. Once
Traefik sets `X-Forwarded-For`/`X-Real-Ip` correctly, whoami reports the
real client IP in its response regardless of which network whoami itself
is on.

### 5. Attach Traefik and the backends you're migrating

```bash
cd core/traefik
docker network connect proxy-public-v6 "$(grep ^TRAEFIK_CONTAINER_NAME= .env | cut -d= -f2)"
# Repeat for each app you're migrating, e.g.:
docker network connect proxy-public-v6 authentik-server
```

Traefik's docker provider re-discovers containers automatically — no
restart needed for routing. (The static `network:` setting in
`traefik.yml` selects which network Traefik uses when a container is on
more than one — see `providers.docker.network`.)

### 6. Test before touching anything else

```bash
curl -4 -v https://whoami.example.com/
curl -6 -v https://whoami.example.com/

# Tail Traefik's access log while testing — look at ClientHost
# (see the troubleshooting access-log table for what "good" looks like)
docker exec "$(grep ^TRAEFIK_CONTAINER_NAME= .env | cut -d= -f2)" \
  tail -f /var/log/traefik/access.log
```

Confirm `whoami`'s response shows the real Tailscale IPv6 address in
`X-Forwarded-For` / `X-Real-Ip`, not a `172.x` Docker gateway address.

### 7. Cut over

Only after step 6 passes for every test target:

```bash
# Point the deployment at the new network as the primary public network
cd core/traefik
# Edit .env: PUBLIC_NETWORK=proxy-public-v6 (or rename at the Docker
# level if you'd rather keep using the name "proxy-public")
bash ops/scripts/render.sh
docker compose up -d --force-recreate

# Re-point every app's .env (TRAEFIK_NETWORK / network name it joins)
# and recreate each one:
docker compose up -d --force-recreate   # run inside each app directory
```

Decommission the old IPv4-only network only once nothing references it:

```bash
docker network inspect proxy-public --format '{{range .Containers}}{{.Name}} {{end}}'
# Empty output → safe to remove
docker network rm proxy-public
```

### 8. Rollback

If anything goes wrong before full cutover, the old `proxy-public`
network and every container still on it are untouched — nothing was
removed yet, so rollback is simply: don't continue. To fully revert a
completed cutover:

```bash
# Reconnect Traefik (and migrated apps) to the original IPv4-only network
cd core/traefik
docker network connect proxy-public "$(grep ^TRAEFIK_CONTAINER_NAME= .env | cut -d= -f2)"

# Edit .env back to PUBLIC_NETWORK=proxy-public, re-render, recreate
bash ops/scripts/render.sh
docker compose up -d --force-recreate

# Remove the dual-stack network once nothing references it
docker network rm proxy-public-v6

# Revert the Docker daemon prerequisites — see Rollback under
# "Docker daemon prerequisites" above
```

---

## CrowdSec and real client IPs

CrowdSec's Traefik bouncer and its scenario engine both work from the
client IP Traefik records — bans, rate-based scenarios, and geo-blocking
decisions are all keyed on it. If Traefik sees `172.19.0.1` instead of
the real Tailscale IPv6 address:

- A ban decision for one abusive client bans the shared gateway identity
  — either over-blocking (every Tailscale IPv6 user behind that address)
  or under-blocking (the real source rotates behind the same logged IP,
  so per-client thresholds never trigger correctly).
- Geo-blocking and reputation scenarios become meaningless for that
  traffic — `172.19.0.1` has no real-world geography or reputation.

After the fix in this document, `X-Forwarded-For` and Traefik's access
log (`type: traefik` source in
[`core/crowdsec/config/acquis.yaml`](../../crowdsec/config/acquis.yaml))
contain the real client IP again, and CrowdSec decisions apply to the
actual source. No CrowdSec-side configuration changes are needed — it
already reads whatever IP Traefik logs. See
[CrowdSec Operations Runbook](../../crowdsec/docs/runbook.md) for
day-to-day bouncer operations.

---

## Secret redaction when sharing debug output

`docker compose config` resolves every `${VAR}` against the live `.env`
and prints the result — including `CF_DNS_API_TOKEN` and any other
secret-shaped variable. Migration and troubleshooting both lean on this
command; redact before pasting output anywhere (an issue, chat, a support
request):

```bash
docker compose config | sed -E 's/(CF_DNS_API_TOKEN: ).*/\1***REDACTED***/'
```

Extend the pattern for any other sensitive variable in the same way
(`'(VAR_NAME: ).*/\1***REDACTED***/'`, one `-e` per variable, or chain
`sed` expressions). This is the same constraint the `docs/bugfixes/`
entries and CI's `gitleaks` job already guard against — `docker compose
config` is just a place it can resurface if pasted unredacted.

---

## Verification command reference

Full troubleshooting command set (network inspection, port bindings,
`docker-proxy` process check, access-log field interpretation) lives in
[`docs/standards/troubleshooting.md`](../../../docs/standards/troubleshooting.md)
— "Layer 5: Access Control (IP Allow Lists)" and the IPv4/IPv6
verification commands there, so it stays in one place rather than
duplicated across documents.

---

## Related docs

- [Traefik README](../README.md) — setup, security levels, CrowdSec bouncer integration
- [Traefik Security Architecture](../../../docs/standards/traefik-security.md) — access policies, trusted proxy headers, TLS profiles
- [Networking](../../../docs/standards/networking.md) — `proxy-public` / `app-internal` model
- [Troubleshooting](../../../docs/standards/troubleshooting.md) — full command reference, access-log interpretation
- [Bugfix snapshot](../../../docs/bugfixes/traefik-ipv6-dualstack-2026-06-19.md) — the original incident this document generalizes from
