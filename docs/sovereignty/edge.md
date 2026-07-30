# The edge — who sits between the visitor and the server

The largest sovereignty decision in most self-hosted setups is not which
application to run. It is whether a CDN sits in front of it, and in which mode.
It is usually made once, in a DNS panel, by clicking an icon.

This document is about Cloudflare because that is what this blueprint's DNS-01
resolver integrates with. The reasoning applies to any reverse proxy service.

## DNS-only versus proxied

Cloudflare's dashboard shows a cloud icon per DNS record. Grey is DNS-only,
orange is proxied. They are entirely different arrangements.

**DNS-only (grey).** Cloudflare answers the name lookup and nothing else. The
visitor connects straight to your server. Traffic never touches Cloudflare.

DNS records are public by design — anyone can query them, and they are meant to
be queried. Publishing an A record through Cloudflare rather than another
provider is not a data-protection question. What Cloudflare does learn is the
pattern of *lookups* against your zone, which is metadata about interest in your
domain, not about your users' traffic.

**Proxied (orange).** The name resolves to Cloudflare's own addresses. Visitors
connect to Cloudflare, Cloudflare connects to you. That means:

- Cloudflare **terminates TLS**. Requests are decrypted at their edge — URLs,
  headers, cookies, form bodies, session tokens. It has to be this way for a CDN
  to cache, filter or rewrite anything.
- Your origin IP is hidden, which is a real security benefit against direct
  attack — provided nothing else leaks it.
- Traffic transits Cloudflare's global network. Cloudflare Inc is a US company
  (San Francisco, NYSE: NET), so US jurisdiction applies to the operator of that
  network regardless of which datacentre a given request passes through.

**Proxied mode buys
DDoS absorption, caching and edge filtering at the price of a third party seeing
your plaintext traffic.**

Whether that price is acceptable is a deployment question, not a general one. For
a public marketing site it is close to free. For a stack handling health records,
legal files or payroll it decides the deployment, and "but the server is in
Germany" does not answer it.

## The five encryption modes

Only relevant when proxied. Cloudflare offers five, and the names are
misleading — "Full" is not full.

| Mode | Browser → Cloudflare | Cloudflare → origin | Origin cert checked |
|---|---|---|---|
| Off | plaintext | plaintext | — |
| **Flexible** | encrypted | **plaintext** | — |
| Full | encrypted | encrypted | **no** |
| **Full (strict)** | encrypted | encrypted | yes |
| Strict (SSL-Only Origin Pull) | always encrypted | always encrypted | yes |

**Flexible encrypts the browser-to-Cloudflare leg only.** The visitor's browser shows a padlock. The
connection from Cloudflare to your server is unencrypted HTTP across the public
internet. The padlock is telling the user something that is not true for most of
the path. It exists for origins that cannot do TLS at all; this blueprint's
origin always can, so there is no case for it here.

**Full accepts any certificate**, including an expired one, a self-signed one, or
one presented by whoever has managed to get in the path. It authenticates
nothing. It is a step above Flexible and below what this stack can trivially
achieve.

**Use Full (strict).** Traefik already obtains a valid Let's Encrypt certificate,
so the requirement is met with no extra work. Cloudflare recommends Full or Full
(strict); of those two, only strict verifies the origin certificate.

## Filtering at the edge or at your server

Cloudflare offers a WAF, rate limiting and geoblocking. This blueprint runs
CrowdSec. They sit in different places and the difference matters:

| | At Cloudflare | At your server (CrowdSec) |
|---|---|---|
| Blocks before | it reaches your network | it reaches the application |
| Absorbs volumetric DDoS | yes | no — the traffic already arrived |
| Sees request content | yes, necessarily | yes, locally |
| You can read the logs | in their dashboard | on your disk |
| Works when proxying is off | no | yes |

Edge filtering stops traffic that would saturate your uplink — the thing your
server cannot do for itself. It cannot be done locally, because by
the time a packet reaches you the bandwidth is already spent.

Local filtering is better at everything downstream of that, and it keeps the
evidence where you can query it. The honest position is that they are
complementary, and that choosing edge filtering means accepting decryption — you
cannot have a WAF inspect requests it cannot read.

**Geoblocking stops opportunistic scanning from regions you have no users in**,
which reduces log noise. It does not stop a
motivated attacker, who will use a VPN exit or a compromised host in your own
country, and it will block travelling legitimate users. Treat it as noise
reduction, not as a control.

## Where the server itself sits

The hosting provider's jurisdiction applies to the machine, and the provider's
*corporate parent* matters as much as the datacentre's address. A German
datacentre operated by a US-owned company is subject to different pressures than
a German datacentre operated by a German company, whatever the marketing page
says about data residency.

This is out of the blueprint's hands — it configures software, not procurement.
But it is the layer underneath everything above, and a stack that is careful
about licences and telemetry while running on unexamined infrastructure has
optimised the smaller variable.

## What to decide

- **DNS-only through Cloudflare:** no traffic exposure. Fine.
- **Proxied:** Cloudflare reads your plaintext. A real decision, worth making
  deliberately rather than by leaving the icon orange.
- **If proxied, Full (strict).** Never Flexible.
- **Edge filtering and local filtering are complementary**, not alternatives.
- **Geoblocking reduces noise**, not risk.
