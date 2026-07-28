# Host session findings

What running the blueprint on a real host surfaced that reading it did not.

Each entry is written to become an issue: what was observed, why it matters, and
what would fix it. Nothing here is speculation — every item was measured on a
Debian 13 host with Docker 29.3.1 while working through
[`host-session-v0.7.0.md`](host-session-v0.7.0.md) and
[`host-session-v0.8.0.md`](host-session-v0.8.0.md).

**Session 1 — 2026-07-28.** Traefik brought up from a clean clone.

---

## What worked without a single correction

Worth recording as precisely as the defects, because "it does not work out of the
box" is the wrong conclusion to draw from a list of findings:

- Traefik started healthy on first `up -d` and stayed healthy.
- A wildcard certificate was issued via DNS-01 on the first attempt.
- Both entry points bound IPv4 and IPv6 without extra configuration.
- Routing, TLS profile and middleware chain applied correctly; the dashboard was
  reachable over the tailnet and refused from everywhere else.
- **The real client IP arrived intact on all four paths measured** — public IPv4,
  public IPv6, Tailscale IPv6, and a commercial VPN exit node over IPv6. This is
  the property everything else depends on.
- `validate.sh` and `render.sh` did exactly what they document, including the
  post-render validation pass.

---

## 1. Dual-stack is opt-in but effectively mandatory for Tailscale

**Observed.** `proxy-public` is IPv4-only by default. Enabling IPv6 needs three
separate manual steps: a Docker daemon change with a restart, two new subnet
variables in `.env`, and the `network-dual-stack.yml` overlay on every
`docker compose` invocation.

**Why it matters.** Tailscale gives every client an IPv6 address and connects
directly, so there is no forwarded header to fall back on. On an IPv4-only
network the source address is lost before Traefik sees it, and `acc-tailscale`
then denies the very clients it exists to admit. `core/traefik/docs/ipv6-dual-stack.md`
documents this precisely — but the default configuration is the one that breaks
it, and the failure looks like a permissions problem rather than a network one.

**Fix.** Either make dual-stack the default for new deployments, or make the
Traefik setup ask the question up front: *are any clients reaching this through
Tailscale?* → if yes, the overlay is not optional. A `📋` note in the README is
not enough; this one silently produces 403s.

## 2. Denied requests produce no access-log line

**Observed.** Measured directly: 36 log lines before a request blocked by
`acc-tailscale`, 36 after. Repeated across IPv4 and IPv6, with
`bufferingSize: 0` and a `200-599` status filter that includes 403.

**Why it matters.** CrowdSec parses this access log. Every probe against a
VPN-only endpoint is therefore invisible to it — an attacker can enumerate
`traefik.example.com` indefinitely without generating a single event. The
blueprint's two protective layers do not compose: whatever `ipAllowList` blocks,
CrowdSec never learns about.

**Fix.** Needs upstream verification first — whether Traefik can log
middleware-denied requests at all, or whether this belongs in CrowdSec as a
separate acquisition (for example the Traefik application log rather than the
access log). Until then it is a documented blind spot, and
`docs/standards/traefik-security.md` should say so.

## 3. `TRAEFIK_ACCESSLOG_BUFFER=100` delays detection without saving anything

**Observed.** The default buffers up to 100 entries in memory before writing.

**Why it matters.** The intent was to reduce disk writes, but buffering only
defers them — the same volume is written either way. What it does cost is
detection latency for anything reading the log, which is exactly CrowdSec's job.

**Fix.** Default to `0`. Disk-space protection is logrotate's job, not the
buffer's — see the next item.

## 4. Logrotate is a manual copy step that is easy to miss

**Observed.** `core/traefik/config/logrotate/traefik` ships with the repository
but only takes effect after being copied to `/etc/logrotate.d/` by hand, with the
deployment path edited in. Nothing in the setup path prompts for it, and nothing
detects that it was skipped.

**Why it matters.** Traefik writes access logs to a bind mount, which Docker's
own log rotation does not touch. Skipped, they grow until the disk is full — and
the fastest way there is the log flood a request flood produces.

**Fix.** Two parts. Make the setup surface the step, and add `maxsize` to the
rotation config so a flood rotates on size rather than waiting for the daily
run — `daily`/`rotate 7` alone does not bound a burst.

## 5. `apt install borgmatic` gives a version that cannot do what the repo needs

**Observed.** `docs/host-session-v0.7.0.md` says `sudo apt install borgmatic` and
in the same checklist requires **≥ 2.0.8**. Debian 13 ships **1.9.14**. Current
upstream is 2.1.6.

**Why it matters.** The `container:` database hook — the mechanism `backup/README.md`
builds its entire database-consistency story on — does not exist before 2.0.8.
Following the repository's own instruction produces a borgmatic that silently
cannot do the thing the architecture depends on.

**Fix.** Replace the install line with the upstream-recommended method (`uv tool
install borgmatic`, or pipx), and keep the version assertion immediately after it
so the check still fires.

## 6. The dnsmasq template invites edits it then destroys

**Observed.** `ops/templates/dnsmasq.conf.tmpl` supports three wildcard zones as
variables and carries the comment *"Add/remove zones as needed after rendering."*
A deployment with more than three zones must hand-edit the rendered file — and
the next `render.sh` overwrites it.

**Why it matters.** The instruction guarantees the data loss. It is not a
trade-off anyone chose; it reads as supported.

**Fix.** Either an arbitrary-length zone list driven from `.env`, or an include
directory the renderer never touches.

## 7. The dashboard requests its own certificate even in wildcard mode

**Observed.** With `ACME_WILDCARD_DOMAIN` set (Path A), two certificates were
issued: the wildcard, and a separate one for the dashboard host.

**Why it matters.** `.env.example` states the reason the certresolver label stays
commented out in app stacks: a per-domain certificate publishes the subdomain to
Certificate Transparency logs when a wildcard already covers it. The system
router does exactly that by default, so the repository's own privacy rationale is
undermined by its own default.

**Fix.** `TRAEFIK_DASHBOARD_CERT_RESOLVER` should be empty when
`ACME_WILDCARD_DOMAIN` is set, and `validate.sh` is the natural place to catch
the combination.

---

## Not repository defects

Recorded so they are not mistaken for them later:

- **Split-DNS pointed at the wrong host.** A wildcard zone resolved to a
  different machine's tailnet address, so the dashboard was unreachable before
  the record was corrected. Environment, not blueprint.
- **Browser DNS cache.** After the record was fixed, Chrome kept serving the old
  answer; an incognito window worked immediately. Worth a line in the operator
  documentation, because it presents identically to a broken access policy.

---

## The sequence that actually worked

Recorded step by step because the documented order is not quite this, and because
this is the raw material for both the operator documentation and the site. Real
hostnames and addresses are replaced with `example.com` throughout.

**Preconditions on the host:** Debian 13, Docker 29.3.1, Compose v5.1.1, a user in
the `docker` and `sudo` groups, ports 80 and 443 free.

1. **Clone into its own directory.** Not over an existing checkout — an old clone
   on the same machine will have stale configuration and a matching
   `COMPOSE_PROJECT_NAME`, which makes Compose adopt and recreate the *running*
   containers of the older deployment rather than starting beside them.
2. **Enable IPv6 in the Docker daemon before anything starts.** Requires a daemon
   restart, so doing it while nothing runs costs nothing and doing it later costs
   an outage of every stack.
3. **Fill `core/traefik/.env`** — domain, ACME email, DNS API token, and both
   `PUBLIC_NETWORK_SUBNET_*`. Generate the ULA prefix rather than copying the
   example; the repository ships the command for it.
4. **`bash ops/scripts/validate.sh`** → **`render.sh`** → **`validate.sh`** again.
   The second pass catches unresolved placeholders and is worth the ten seconds.
5. **Start with the overlay**, not without it:
   `docker compose -f docker-compose.yml -f network-dual-stack.yml up -d`.
6. **Verify before moving on**, in this order — each answers a different question:
   - `docker compose ps` — did it come up healthy
   - `docker network inspect proxy-public` — two subnets, so dual-stack is live
   - certificate present and covering the wildcard
   - `ss -tlnp` — listening on both `0.0.0.0` and `[::]`
   - **`core/whoami` with `acc-public`, then read `X-Real-Ip`** — this is the only
     step that proves the real client IP survives, and it must be repeated once
     per path: public IPv4, public IPv6, and through the VPN

   **Then close whoami again.** It echoes the container hostname, the internal
   container addresses and the ULA prefix — reconnaissance material for anyone
   who finds it. `acc-public` is correct for the duration of the measurement and
   wrong the minute after; the repository default is `acc-tailscale` for this
   reason. On the host used here, scanners were probing WordPress and debug paths
   within minutes of the first certificate being issued.

Step 6 is the one that cannot be skipped. Everything before it proves the
configuration parses; only this proves the deployment behaves.

## Testing capabilities available for later blocks

Noted so the plan can use them rather than working around them:

- **Tailnet access** to the host, so VPN-only policies can be exercised for real
  instead of inferred.
- **A browser with exit nodes in several countries.** This makes the geoblocking
  guidance in `core/crowdsec/docs/` testable end to end — country rules, the
  self-lockout trap, and whether an allowlist behaves as documented — rather than
  reviewed on paper. Worth scheduling deliberately when CrowdSec comes up.

## How this list gets resolved

Not every entry deserves a change, and deciding that during the session would
bias toward whatever was annoying at the time. The rule:

1. **During the session — record, do not fix.** Anything not blocking the next
   step gets written down and left alone. Fixing as you go loses the thread and
   makes the cause of the next failure ambiguous.
2. **After the session — one review pass over the whole list.** Per entry: is it a
   defect, a documentation gap, or an environment quirk that was mistaken for one?
3. **Then split by audience.** A maintainer-facing fix belongs in the repository.
   An operator-facing one belongs on the site, in the words of someone who has not
   read the source.
4. **Only then write anything.** Entries that survive all four become issues; the
   rest stay here as the record of what was considered and dropped, which is worth
   as much as the changes.
