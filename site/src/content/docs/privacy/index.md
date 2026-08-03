---
title: Privacy
description: What this site stores, what it loads, and what the hosting platform records — a short answer, because a static site with no analytics has little to describe.
---

:::caution[If you are reading this in a fork]
The controller named below is the original author. Replace it with your own
before you publish, or remove the page.
:::

## Short version

This site sets no cookies, runs no analytics, embeds no third-party fonts,
videos or trackers, and has no forms. Nothing you do here is recorded by us,
because there is nothing here that records.

That is a consequence of how it is built, not a promise of restraint — and the
sections below say where data still arises anyway.

## Who is responsible

Ruben-Paul Nati, Spittelauer Lände 25, 1090 Vienna, Austria. Contact and the
full disclosure are in the [legal notice](/legal/).

## What the site itself stores

| | |
|---|---|
| Cookies | none |
| Analytics | none |
| Embedded third-party content | none — no external fonts, scripts, images or video. The browser does send network error reports to Cloudflare; see [below](#one-automatic-report) |
| Forms | none |
| Local storage | none |
| Session storage | one flag, only if the leave-site confirmation is set to ask once per visit. It records that you were asked. It leaves your browser at no point and is discarded when the tab closes. |

The site is static: pages are files, and there is no application behind them
that could keep a record.

## Who handles a request on its way here

Serving a page requires a request, and a request has a sender. Three companies
touch it before it reaches you, each processing what any web server processes:
IP address, time, the page requested, the referring page and the browser's
user-agent string, in logs they keep under their own terms and retention.

| Who | Role | Where |
|---|---|---|
| **Cloudflare, Inc.** | the address this domain resolves to. It terminates the encrypted connection, so it handles the request in clear text, and it caches and forwards | USA |
| **GitHub, Inc.** — GitHub Pages | holds the files and answers what Cloudflare does not serve from cache | USA |
| **Fastly, Inc.** | the delivery network GitHub Pages itself runs behind | USA |

Cloudflare being in front means the connection is decrypted there rather than
at the origin. That is how a content delivery network works and is not a
misconfiguration — the same trade this site
[describes elsewhere](/sovereignty/edge/), applied to itself.

This is technically necessary to deliver the page and is used here for nothing
else. We do not receive, read or analyse those logs, and none of the three
platforms offers a setting that would switch them off.

**All three are US companies, so a request transfers data to a third country.**
Cloudflare states it relies on the European Commission's Standard Contractual
Clauses and is additionally certified under the EU-U.S. Data Privacy Framework
([Cloudflare, GDPR](https://www.cloudflare.com/trust-hub/gdpr/)). GitHub states
it relies on the Standard Contractual Clauses
([GitHub Privacy Statement](https://docs.github.com/site-policy/privacy-policies/github-general-privacy-statement)).
Fastly is engaged by GitHub rather than by this site, and its handling falls
under GitHub's arrangements.

### One automatic report

Cloudflare's response asks the browser to send network error reports to
`a.nel.cloudflare.com` when a request fails. It is set by the platform, carries
no content of the page, and is the one outbound request this site causes that
is not a request for the page itself.

## What happens when you follow a link

Citations point at other people's sites. Following one is a request to them, and
from that moment their privacy terms apply, not this page's. That is why each
link shows its destination host before you follow it and asks for confirmation.

**Nothing about you is transmitted to those sites by this one.** No referral
tracking, no identifiers appended to the link.

## Your rights

Where personal data is processed, the GDPR gives you rights of access,
rectification, erasure, restriction, portability and objection, and the right to
complain to a supervisory authority — in Austria the Datenschutzbehörde.

In practice there is very little here to exercise them against: this site holds
no personal data. A request would concern the hosting provider's server logs,
and the contact address in the [legal notice](/legal/) is the place to start.

## Changes

This page describes the site as built. If analytics, a form or an embedded
service is ever added, this page changes in the same commit — otherwise it stops
being true the moment the feature ships.
