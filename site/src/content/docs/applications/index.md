---
title: What each application is for
description: Every application the repository ships — the problem it solves, what it needs beyond the proxy, and a guide for each one.
---

These are the services you actually use — the reason for the server rather than
part of it. Every one of them expects [Traefik](/infrastructure/traefik/) to be
running first; they publish no ports themselves and are reached through it.

Each one has a guide: installation walked through, a *Verify* section, what to
back up, how to update it, and the failures that service really produces. What
each guide states at the top is how much of it has been confirmed on a running
host — some were brought up and checked, some are written from the repository
files and have never been started here. Nextcloud is the one whose data has been
restored from a backup on a live host; for the rest, the restore is documented
and unrehearsed.

Most also ship a `docker-compose.local.yml`, which runs the service on your own
machine with no proxy, DNS or certificate — see [what every server
needs](/infrastructure/). Adminer is the exception, because it needs a database
to point at rather than one of its own.

## The applications

| | Solves | Also needs |
|---|---|---|
| [Adminer](/applications/adminer/) | a web interface onto a database another stack already runs | a database to point it at |
| [BookStack](/applications/bookstack/) | a wiki with real structure: shelves, books, chapters, pages | nothing beyond the proxy |
| [Cal.diY](/applications/caldiy/) | appointment booking pages people can self-serve — the Cal.com community edition | SMTP, a Cloudflare-proxied domain |
| [Dashy](/applications/dashy/) | one page linking everything you run, configured in a single YAML file | nothing beyond the proxy |
| [Documenso](/applications/documenso/) | document signing you host yourself, with a signing certificate you generate | SMTP, OpenSSL for the certificate |
| [Easy!Appointments](/applications/easyappointments/) | appointment booking on a PHP stack, with no build step | nothing beyond the proxy |
| [Ghost](/applications/ghost/) | publishing with newsletters and paid memberships built in | SMTP, which also gates the first login |
| [Heimdall](/applications/heimdall/) | a launcher page for your services, with optional per-service status | nothing beyond the proxy |
| [Homarr](/applications/homarr/) | a dashboard whose tiles show live state rather than only links | API tokens for what it displays |
| [Homepage](/applications/homepage/) | a dashboard described in YAML files, reloaded on change | nothing beyond the proxy |
| [Immich](/applications/immich/) | photo and video backup from phones, searchable by what is in the picture | storage for the library |
| [Invoice Ninja](/applications/invoiceninja/) | invoices and quotes, what has been paid, and a portal where each client can view and settle them | SMTP |
| [IT-Tools](/applications/it-tools/) | formatters, generators and converters that never leave the browser | nothing beyond the proxy |
| [Listmonk](/applications/listmonk/) | newsletters, subscriber lists and double opt-in | an SMTP relay entered after setup |
| [n8n](/applications/n8n/) | chaining HTTP calls, webhooks and scheduled jobs into workflows visually | nothing beyond the proxy |
| [Nextcloud](/applications/nextcloud/) | files, calendars and contacts on your own server, synced to desktops and phones, with sharing on top | SMTP |
| [NocoDB](/applications/nocodb/) | a spreadsheet interface and an API over a database | nothing beyond the proxy |
| [OnlyOffice](/applications/onlyoffice/) | opening `.docx`, `.xlsx` and `.pptx` in the browser, embedded inside another application | an application to embed it — it is not used on its own |
| [OpenProject](/applications/openproject/) | work packages, Gantt charts, boards and time tracking | nothing beyond the proxy |
| [OpnForm](/applications/opnform/) | a form builder with conditional logic, uploads and webhooks | SMTP for notifications |
| [Paperless-ngx](/applications/paperless-ngx/) | scanned paper becoming a searchable archive, via OCR and a consume folder | the OCR language packs you need; SMTP is optional |
| [PhotoPrism](/applications/photoprism/) | a photo library that indexes and classifies itself | disk space for the models |
| [Seafile](/applications/seafile/) | file sync and sharing with desktop and mobile clients | SMTP for invitations |
| [Seafile Pro](/applications/seafile-pro/) | file sync built for large directory trees, with full-text search and antivirus scanning | a commercial licence; OnlyOffice for in-browser editing |
| [Vaultwarden](/applications/vaultwarden/) | credentials in one vault, synced to browser, phone and desktop, instead of a third party holding everything you log into | SMTP, for email verification |
| [Vikunja](/applications/vikunja/) | task management — boards, lists, Gantt and table views | a local build step |
| [WordPress](/applications/wordpress/) | the CMS, with PHP and Apache hardened | an SMTP relay via plugin |

Each opens with the version it is written against and the date it was verified,
followed by a line naming what has not been exercised. Read that line before
trusting a service with data.

## Where the choice is not obvious

Several of these solve overlapping problems. **Nextcloud and Seafile both do file
sync** — one is a suite, the other is a sync engine, and the decision is not a
matter of taste. **Four dashboards** differ mainly in how you configure them.
**Cal.diY and Easy!Appointments** book appointments with very different
appetites for host resources.

[Choosing between services →](/applications/choosing/)

## What is deliberately absent

The repository ships around sixty stacks. The two tables above cover the ones
with a verification date behind them; the rest are configured but have never been
brought up here, so listing them alongside would suggest a standing they do not
have. They are in the repository with their own READMEs, and
[the full list](https://github.com/rubennati/secure-docker-blueprint#whats-included)
is there rather than here.

## Where to go from here

- Traefik not running yet: [what every server needs](/infrastructure/)
- Before real data goes into any of these: [backup and restore](/operations/backup/)
- Weighing licences, jurisdictions and what a service sends home:
  [data sovereignty](/sovereignty/)
