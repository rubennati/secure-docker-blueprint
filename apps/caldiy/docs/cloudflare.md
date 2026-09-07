# Cal.diY — Cloudflare Configuration

> **Status: ✅ Recommended edge layer for the internet-facing deployment** — v6.2.0-5 · 2026-07-26

Cal.diy is community-maintained and **not confirmed secure**; a live instance was compromised
once (the SMTP credential was exfiltrated). For an internet-facing deployment this guide
therefore recommends running it **behind Cloudflare as a proxy (orange cloud)**. Cal.diy does not depend on
Cloudflare to run — the local path in [`README.md`](../README.md) has none — so what follows
applies once you choose this deployment path. This document lists exactly what to configure in
Cloudflare and what each setting buys you.

Cloudflare is **one** layer. It does not replace origin hardening (CrowdSec, AppSec, disabled
signup, Docker Secrets, resource limits) — see [hardening-plan.md](hardening-plan.md). The two are
defense-in-depth: Cloudflare blocks at the edge, the origin blocks what slips through.

> **Plan note:** availability of individual features depends on your Cloudflare plan. Geo custom
> rules, Bot Fight Mode, one rate-limiting rule, and "Under Attack" mode are available on the
> **Free** plan; the full managed WAF ruleset and multiple rate-limit rules need **Pro+**. Each
> section notes where it matters.

---

## 0. Prerequisite — the DNS record must be *proxied*

Both the **A (IPv4)** and **AAAA (IPv6)** records for `cal.<yourdomain>` must be **proxied
(orange cloud)**, not DNS-only. DNS-only means traffic bypasses Cloudflare and none of this applies.
Only publish a family the origin actually listens on (see [`core/traefik/docs/ipv6-dual-stack.md`](../../../core/traefik/docs/ipv6-dual-stack.md)).

- **Verify:** the record shows the orange cloud; `dig +short cal.<domain>` (and `dig AAAA`) returns
  a Cloudflare anycast IP, **not** your origin IP.
- **Real client IP:** with the proxy on, the client IP arrives in `X-Forwarded-For`. Traefik
  already trusts Cloudflare's ranges (`entryPoints.*.forwardedHeaders.trustedIPs` in
  `core/traefik/ops/templates/traefik.yml.tmpl`) so `ClientHost` in logs and `ipAllowList`
  evaluation see the real IP. **No Traefik change needed** — but keep that CF range list current
  (source: https://www.cloudflare.com/ips/).

---

## 0.1 Scope every rule to this hostname

Other apps share this Cloudflare zone, so apply **nothing zone-wide** — scope everything to
`cal.<domain>`:

- **WAF custom + rate-limit rules:** add `http.host eq "cal.<domain>"` to the expression. Matches this app only.
- **Zone toggles** (SSL mode, Security Level, Browser Integrity Check): override per-host with a **Configuration Rule** matched on `http.host eq "cal.<domain>"`; the zone default stays untouched elsewhere.
- **Managed WAF ruleset:** deploy with a custom scope expression on `http.host`.
- **"Under Attack":** don't flip the zone switch — use a scoped custom rule with a JS/Managed Challenge action (§8).
- **Caveat:** a few Free-plan toggles are genuinely zone-wide (e.g. Bot Fight Mode). If you need those per-host, replace them with a scoped custom rule.

---

## 1. Lock the origin FIRST — everything else is bypassable without it

Geo and WAF at Cloudflare are worthless if an attacker connects to your **origin IP directly**,
skipping Cloudflare. This section is the most important one. Do at least one of:

| Option | What it does | Strength |
|--------|--------------|----------|
| **A — Cloudflare Tunnel** (`cloudflared`) | Origin has **no public inbound** at all; the tunnel dials out to Cloudflare | Strongest — no origin IP to find |
| **B — Origin firewall allowlist** | Host firewall lets **only Cloudflare IP ranges** reach ports 80/443; everything else dropped | Strong, simple |
| **C — Authenticated Origin Pulls** (mTLS) | Origin (Traefik) accepts TLS **only** when the client presents Cloudflare's origin-pull certificate | Strong, pairs with B |

**Option B example (host firewall):** allow inbound 80/443 only from the published Cloudflare
ranges (the same list already in `traefik.yml.tmpl`), drop the rest. This overlaps with the
Phase 3 firewall bouncer — see [`core/crowdsec/docs/firewall-bouncer.md`](../../../core/crowdsec/docs/firewall-bouncer.md).

**Also — don't leak the origin IP:**

- No unproxied (grey-cloud) record pointing at the same origin (a `direct.` or old `www.` A record undoes everything).
- Check DNS history and mail records — an `MX`/`autodiscover` on the same host can expose the IP.
- If the IP was ever public before Cloudflare, consider changing it.

---

## 2. SSL/TLS

| Setting | Value | Why |
|---------|-------|-----|
| Encryption mode | **Full (Strict)** | CF ↔ origin encrypted **and** origin cert validated. Traefik serves a valid Let's Encrypt cert, so Strict works |
| Always Use HTTPS | On | Redirect http→https at the edge |
| Minimum TLS Version | 1.2 (1.3 if all clients support it) | Drops legacy TLS |
| TLS 1.3 | On | |
| Automatic HTTPS Rewrites | On | Fixes mixed-content |
| Authenticated Origin Pulls | On *(if using §1 option C)* | Origin rejects non-Cloudflare TLS |

**HSTS:** the origin already sends HSTS via the `sec-3` chain (`APP_TRAEFIK_SECURITY=sec-3`). If
you *also* enable Cloudflare HSTS, keep the `max-age` aligned and re-read the browser-sticky
caveat in the [README](../README.md#security-chain-sec-3) — HSTS is hard to undo. Don't set two
conflicting max-ages.

---

## 3. Geo allowlist — human-facing surface only

Goal (Phase 3 of the hardening plan): only DACH/EU clients reach the **interactive** surface,
while provider webhooks stay open so calendars/Teams/Zoom keep syncing.

> **Why not the whole host:** Google Calendar push, Microsoft Graph, and Zoom webhooks are
> server-to-server from **US/global** provider infrastructure. Blocking the whole host to DACH
> would 403 those callbacks and break sync. So geo-gate the human paths and
> **exclude the webhook and auth paths.**

**WAF → Custom rules.** Build in the dashboard (use the "Country" field from the dropdown so you
don't have to hand-type the expression field name). Equivalent expression:

```text
(http.host eq "cal.<domain>")
  and (not ip.geoip.country in {"AT" "DE" "CH"})
  and not starts_with(http.request.uri.path, "/api/integrations")
  and not starts_with(http.request.uri.path, "/api/auth")
```

- **Action:** *Block* (hard) or *Managed Challenge* (softer — lets a real traveller through a
  challenge). Start with Managed Challenge, tighten to Block once you've watched the logs.
- **Extend to EU-wide:** add the EU country ISO codes to the `{ }` set. There is no single "EU"
  field — `ip.geoip.continent eq "EU"` also pulls in non-EU (CH, GB, RU, UA, NO), so an explicit
  country set is more precise.
- **Exclude the right paths:** keep `/api/integrations` (provider webhooks) and `/api/auth` (login
  flow) out of the block. **Confirm the exact webhook/callback paths against the cal.forte fork**
  before finalizing — the surface inventory in [hardening-plan.md](hardening-plan.md) §1.3 feeds
  this list.
- **Keep yourself in:** optionally add a higher-priority *Skip* rule for your own admin IP/ASN so
  a geo rule can never lock you out from the edge. Also keep the VPN/Tailscale origin path
  (`acc-*`), which does not depend on Cloudflare at all.

---

## 4. WAF managed rules

- Enable the **Cloudflare Managed Ruleset** (Free plan: the free managed ruleset; **Pro+**: full
  managed ruleset + **OWASP Core Ruleset**). Set OWASP sensitivity to Medium to start.
- This is defense-in-depth with CrowdSec **AppSec** (hardening-plan Phase 2.2): the edge WAF
  blocks common SQLi/XSS/traversal before they reach the origin; AppSec re-checks at the origin.
- **False positives:** watch `/api/integrations` and any upload/import paths. Add a scoped *Skip*
  for a specific ruleset/path if a legitimate call is blocked — don't disable the whole WAF.

---

## 5. Rate limiting

Protect the credential and booking surfaces (Free plan = one rate-limit rule; Pro+ = more):

| Path | Suggested limit | Action |
|------|-----------------|--------|
| `/api/auth/*` (login) | ~20 req / min / IP | Managed Challenge → Block on repeat |
| Booking POST endpoints | sane per-IP cap | Managed Challenge |

If you only get one rule on your plan, spend it on `/api/auth/*` (login brute-force is the
highest-value target). The origin `sec-3` chain also rate-limits (100 req/s), but the edge stops
it before it ever reaches your server.

---

## 6. Bots & scanning

| Setting | Value |
|---------|-------|
| Bot Fight Mode (Free) / Super Bot Fight Mode (Pro+) | On |
| Security Level | High (appropriate for a not-confirmed-secure app) |
| Browser Integrity Check | On |

---

## 7. Leaked credentials & extras

- **Leaked Credential Detection** (WAF): On — flags logins using known-breached credentials.
- **Scrape Shield:** optional.
- **Risky networks:** optionally challenge Tor / high-risk ASNs if you have no such users — blunt,
  use sparingly.

---

## 8. Emergency — "Under Attack" mode

A second kill-switch alongside the origin `acc-deny` (see [ops-runbook.md](ops-runbook.md) §7):
set the zone (or a scoped rule on `cal.<domain>`) to **"I'm Under Attack Mode"** → JavaScript
challenge for every visitor. Use it to ride out an active attack, then turn it back off.

---

## 9. Caching — do NOT cache the app

Cal.diy is dynamic and authenticated. **Never** add a "Cache Everything" cache rule / page rule on
this host — it can serve one user's authenticated page to another. Default Cloudflare caching
(static assets by extension) is fine. Verify no Cache Rule forces caching of HTML on `cal.<domain>`.

---

## 10. What Cloudflare does NOT replace

Cloudflare is the outer layer, not the whole defense. If it is bypassed via an origin-IP leak,
**§1 (origin lock) is your backstop.** These stay mandatory regardless of Cloudflare:

- CrowdSec `crowdsec-basic` + AppSec at the origin (hardening-plan Phase 2)
- `NEXT_PUBLIC_DISABLE_SIGNUP=true`, Docker Secrets, `deploy.resources` caps (Phase 1)
- Origin TLS + `sec-3` headers (Traefik)

---

## Verification checklist

- [ ] `cal.<domain>` is proxied (orange); `dig` returns a Cloudflare IP, not the origin
- [ ] Direct origin IP on :443 is refused (or firewall-allowlisted to Cloudflare ranges only) — §1
- [ ] SSL/TLS mode = Full (Strict); site loads with no cert errors
- [ ] Geo rule: request to `/` from a non-DACH VPN exit → blocked/challenged; from DACH → loads
- [ ] A provider webhook path (`/api/integrations/*/webhook`) is reachable from outside DACH
- [ ] Login works; the `/api/auth/*` rate-limit rule triggers under rapid retries
- [ ] No Cache Rule caches authenticated HTML on this host
- [ ] "Under Attack" mode toggles the challenge on/off as a kill-switch (then leave it off)

---

## See also

- [hardening-plan.md](hardening-plan.md) — where Cloudflare sits in the phased roadmap (Phase 3)
- [ops-runbook.md](ops-runbook.md) — origin kill-switch (`acc-deny`), incident procedure
- [`core/crowdsec/docs/firewall-bouncer.md`](../../../core/crowdsec/docs/firewall-bouncer.md) — host firewall / origin lock (§1 option B)
- [`core/crowdsec/docs/profiles.md`](../../../core/crowdsec/docs/profiles.md) — why geo is edge/allowlist, not a CrowdSec profile
- Cloudflare IP ranges — https://www.cloudflare.com/ips/ (mirrored in `traefik.yml.tmpl`)
