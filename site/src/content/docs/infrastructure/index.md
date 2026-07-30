---
title: What every server needs
description: The two pieces set up per server rather than per service — which one is required, which one is a layer you choose, and what each is actually for.
---

Two things here are installed once on a host and then shared by everything that
runs on it. They do not have the same standing, and treating them as if they did
is how a server ends up with an intrusion detector and no working certificates.

## Traefik — required

**Without it, nothing else in this blueprint is reachable.** The applications
publish no ports of their own. They attach to a Docker network called
`proxy-public` and expect something in front to terminate TLS and route requests
by hostname. Traefik is that something, and it also carries the middleware each
service switches on: security headers, rate limits, and the access rules that
decide whether a service answers the open internet or only your VPN.

One certificate strategy, one set of access policies, one place to change them.

[Traefik — routing and TLS →](/infrastructure/traefik/)

## CrowdSec — a layer you add

**Optional, and worth adding once something is public.** It reads Traefik's
access log, decides which addresses are attacking, and — through enforcement you
install separately — blocks them, either inside the proxy or at the host
firewall.

The scoping matters more here than the feature list. Behind a VPN-only access
policy CrowdSec sees almost nothing, because the requests are refused before they
reach a log it reads. Measured on this blueprint: 120 requests against a VPN-only
host moved its counter by three. It earns its place the moment a service faces
the open internet, and not much before.

[CrowdSec — intrusion detection →](/infrastructure/crowdsec/)

## Also server-wide, without a guide

**Single sign-on.** [Authentik](https://github.com/rubennati/secure-docker-blueprint/blob/main/core/authentik/README.md)
is set up once and then attached per route as a proxy middleware, so several
applications can share one login. Seven containers, and it needs SMTP, a database
and Redis of its own — it is a service to operate, not a setting to switch on.
The configuration is checked and the stack has been brought up; there is no
walked-through guide here.

## Server-wide, and covered elsewhere

**Document editing.** OnlyOffice is also set up once and shared by several
applications, which makes it look like it belongs here. It does not: nothing
breaks without it, and it exists for the applications that embed it. It sits with
them — [OnlyOffice](/applications/onlyoffice/).

**Backups.** Server-wide, but a different job with its own failure modes, and it
has its own section — [backup and restore](/operations/backup/).

**Monitoring and alerting.** The repository ships stacks for it. There is no
guide here yet.

## Where to go from here

- Nothing running yet: [preparing a server](/getting-started/server-setup/)
  covers the host decisions that are expensive to reverse, then hands over to
  Traefik.
- Traefik up and verified: pick a service under
  [applications](/applications/), or add
  [CrowdSec](/infrastructure/crowdsec/) if anything will be public.
- Want the shape of the whole thing first:
  [how a server fits together](/architecture/).
