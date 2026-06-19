# Traefik — Tailscale IPv6 blocked by IPv4-only Docker bridge — 2026-06-19

## Bug: Tailscale clients get 403 over IPv6, work fine over IPv4

**Symptom:** A tailnet client reaching an app through Traefik
(`acc-tailscale` middleware) got `HTTP 403` when its traffic happened to
go out over Tailscale's IPv6 address, while the same client worked
normally over IPv4.

```bash
curl -4 https://auth.example.com/   # → 100.116.181.16            → HTTP/2 302 (ok)
curl -6 https://auth.example.com/   # → fd7a:115c:a1e0::9e32:b510 → HTTP/2 403 (blocked)
```

**Affected blueprint:** `core/traefik/` (any app behind `acc-tailscale`
or `acc-private` is affected the same way — this is a network-layer
issue, not app-specific).

---

## Root cause

The Docker public network (`proxy-public`) was IPv4-only:

```text
Network: proxy-public
EnableIPv6=false
Subnet=172.19.0.0/16
Gateway=172.19.0.1
```

The Docker daemon still listens on IPv6 host ports regardless
(`[::]:80`, `[::]:443` — this is normal daemon behavior, independent of
any one network's IPv6 setting). With the default `userland-proxy:
true`, Docker's `docker-proxy` process bridges those IPv6 host-port
connections into the IPv4-only container network through a **userland
relay** — it terminates the inbound IPv6 connection and opens a new,
unrelated IPv4 connection to the container, sourced from the bridge
gateway address rather than the original client:

```text
docker-proxy -host-ip :: -host-port 443 -container-ip 172.19.x.x -container-port 443
```

Traefik therefore saw `ClientHost=172.19.0.1` (the gateway) for every
IPv6 client. `acc-tailscale`'s `ipAllowList`
(`100.64.0.0/10` + `fd7a:115c:a1e0::/48`) does not match `172.19.0.1` →
`403`.

```text
Tailscale IPv6 client
  → fd7a:115c:a1e0::...:443 on the host
  → Docker published port / docker-proxy
  → IPv4-only Docker bridge
  → Traefik sees ClientHost=172.19.0.1
  → Traefik ipAllowList blocks
  → HTTP 403
```

This is specific to the **Tailscale path**, which has no proxy in front
of it to recover a lost client IP from a header. The **Cloudflare path**
recovers the real client IP from `X-Forwarded-For` regardless of the
network's IP family — see "Cloudflare vs. Tailscale" in the doc linked
below. Cloudflare ingress was not affected by this bug.

---

## Fix applied

Three changes, all required together (see
[`core/traefik/docs/ipv6-dual-stack.md`](../../core/traefik/docs/ipv6-dual-stack.md)
for the full explanation of why each one alone is insufficient):

1. **Docker daemon prerequisites** — `ipv6: true`, `ip6tables: true`,
   `userland-proxy: false` in `/etc/docker/daemon.json` (existing logging
   options preserved). `userland-proxy: false` is what stops the lossy
   userland relay and makes Docker use kernel `ip6tables` DNAT instead,
   which preserves the real source IP.
2. **Dual-stack `proxy-public` network** — new opt-in overlay
   [`core/traefik/network-dual-stack.yml`](../../core/traefik/network-dual-stack.yml)
   adds `enable_ipv6: true` plus explicit IPv4 and IPv6 (ULA) subnets to
   the network already defined in `docker-compose.yml`. IPv4-only stays
   the default when the overlay is not applied — existing deployments are
   unaffected until they opt in.
3. **Cloudflare `forwardedHeaders.trustedIPs`** — added to both
   entrypoints in `ops/templates/traefik.yml.tmpl` (was previously
   undocumented/unset — flagged as a gap in
   `docs/security-verification.md`, control #12). Unrelated to the
   Tailscale bug itself, but closes the equivalent gap on the Cloudflare
   path: without it, Traefik has no way to distinguish a real client IP
   forwarded by Cloudflare from one a client could spoof in its own
   request headers.

Example working dual-stack network (from the host where this was
debugged):

```bash
docker network create \
  --driver bridge \
  --ipv6 \
  --subnet 172.30.0.0/16 \
  --subnet fd00:dead:beef:30::/64 \
  --opt com.docker.network.bridge.name=br-proxy-v6 \
  proxy-public-v6
```

```text
Name=proxy-public-v6
Driver=bridge
EnableIPv6=true
IPAM=[
  {"Subnet":"172.30.0.0/16","Gateway":"172.30.0.1"},
  {"Subnet":"fd00:dead:beef:30::/64","Gateway":"fd00:dead:beef:30::1"}
]
```

Containers attached received both address families:

```text
whoami           IPv6=fd00:dead:beef:30::2
authentik-server  IPv6=fd00:dead:beef:30::3
traefik-core      IPv6=fd00:dead:beef:30::4
```

`fd00:dead:beef:30::/64` is the example used throughout this repo's
docs — production deployments should generate their own ULA prefix (see
"Choosing a ULA prefix" in the doc above), the same way they would not
reuse someone else's RFC1918 range on purpose.

---

## Verification commands

```bash
# Tailscale IPv4 — should already work before and after
curl -4 -v https://<app-domain>/

# Tailscale IPv6 — this is what was broken
curl -6 -v https://<app-domain>/

# Traefik access log — look at ClientHost
docker exec <traefik-container> tail -f /var/log/traefik/access.log
```

Access-log `ClientHost` interpretation:

| `ClientHost` value | Meaning |
|---|---|
| `100.x.x.x` | Tailscale IPv4 — real source IP, working as expected |
| `fd7a:115c:a1e0::...` | Tailscale IPv6 — real source IP, working as expected (this is what was missing before the fix) |
| `172.19.0.1` (or any Docker gateway address) | Source IP lost — the bug this document describes |
| Cloudflare edge IP in `ClientAddr`, real client IP in `ClientHost` | Cloudflare path working correctly via `forwardedHeaders.trustedIPs` |

`whoami` (see [`core/whoami`](../../core/whoami/)) is the recommended
target for this kind of check — it echoes `X-Forwarded-For` and
`X-Real-Ip` directly in the response body, no need to parse access logs
for a quick check:

```bash
curl -6 https://whoami.example.com/ | grep -iE "x-forwarded-for|x-real-ip"
# Before the fix: 172.19.0.1
# After the fix:  fd7a:115c:a1e0::9e32:b510
```

Full troubleshooting command set (network inspection, port bindings,
`docker-proxy` process check) — see
[`docs/standards/troubleshooting.md`](../standards/troubleshooting.md)
→ "Layer 5: Access Control".

---

## Why `172.19.0.1/32` in the allowlist is not the fix

It's tempting to just allowlist the gateway address once you spot the
pattern. This was deliberately **not** done — see "Why
`172.19.0.1/32` in `ipAllowList` is a workaround, not a fix" in
[`core/traefik/docs/ipv6-dual-stack.md`](../../core/traefik/docs/ipv6-dual-stack.md)
for the full reasoning. Short version: every IPv6 client behind the
broken path looks identical (the same gateway address), so the
allowlist stops being able to tell a real tailnet member apart from
anything else that can reach that address — and CrowdSec decisions keyed
on that same IP become meaningless for the same reason.

---

## Lesson

`network_mode: host` would also have "fixed" this (no Docker bridge
translation at all), but is not the blueprint's primary recommendation —
see "Why not `network_mode: host`" in the doc above. The actual fix
works within the existing Docker bridge networking model: the
combination of daemon-level IPv6 support, `userland-proxy: false`, and a
dual-stack network is what restores real source IPs, not bypassing
Docker's networking model entirely.

`app-internal` networks (databases, Redis, workers) are unaffected and
intentionally stay IPv4-only — nothing outside the Docker host connects
to them directly, so there is no client source IP to preserve there.
