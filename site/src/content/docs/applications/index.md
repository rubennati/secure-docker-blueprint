---
title: What each application is for
description: Every application the repository ships that has been checked — the problem it solves, what it needs beyond the proxy, how big it is, and which ones have a full guide here.
---

These are the services you actually use — the reason for the server rather than
part of it. Every one of them expects [Traefik](/infrastructure/traefik/) to be
running first; they publish no ports themselves and are reached through it.

Two lists below, and the difference between them is how much has been written
down, not how good the software is.

## With a full guide

Installation walked through and written up, with a *Verify* section, what to back
up, how to update it, and the failures that service really produces.

| | Solves | Also needs |
|---|---|---|
| [Invoice Ninja](/applications/invoiceninja/) | invoices and quotes, what has been paid, and a portal where each client can view and settle them | SMTP |
| [Nextcloud](/applications/nextcloud/) | files, calendars and contacts on your own server, synced to desktops and phones, with sharing on top | SMTP |
| [OnlyOffice](/applications/onlyoffice/) | opening `.docx`, `.xlsx` and `.pptx` in the browser, embedded inside another application | an application to embed it — it is not used on its own |
| [Paperless-ngx](/applications/paperless-ngx/) | scanned paper becoming a searchable archive, via OCR and a consume folder | the OCR language packs you need; SMTP is optional |
| [Cal.diY](/applications/caldiy/) | appointment booking pages people can self-serve — the Cal.com community edition | SMTP, a Cloudflare-proxied domain |
| [Dashy](/applications/dashy/) | one page linking everything you run, configured in a single YAML file | nothing beyond the proxy |
| [Ghost](/applications/ghost/) | publishing with newsletters and paid memberships built in | SMTP, which also gates the first login |
| [n8n](/applications/n8n/) | chaining HTTP calls, webhooks and scheduled jobs into workflows visually | nothing beyond the proxy |
| [Seafile Pro](/applications/seafile-pro/) | file sync built for large directory trees, with full-text search and antivirus scanning | a commercial licence; OnlyOffice for in-browser editing |
| [Vaultwarden](/applications/vaultwarden/) | credentials in one vault, synced to browser, phone and desktop, instead of a third party holding everything you log into | SMTP, for email verification |

Each opens with the version it is written against and the date it was verified,
followed by a line naming what has not been exercised. Read that line before
trusting a service with data.

## Checked, but no guide written yet

These ship in the repository with their configuration checked against the
security baseline, and each was brought up at least once — that is where the date
in its `UPSTREAM.md` comes from. What does **not** exist for them is a walked-through
installation on this site, and **no restore has been rehearsed for any of them.**

The repository README for each is the working instruction. Treat the effort
column as the honest signal: a one-container stack is an evening, a
six-container one is not.

All but Adminer also ship a `docker-compose.local.yml`, which runs the service on
your own machine with no proxy, DNS or certificate — see [what every server
needs](/infrastructure/).

| | Solves | Needs beyond the proxy | Containers |
|---|---|---|---|
| [Adminer](https://github.com/rubennati/secure-docker-blueprint/blob/main/apps/adminer/README.md) | a web interface onto an existing database — MySQL, MariaDB, PostgreSQL, SQLite and more | a database to point it at | 1 |
| [BookStack](https://github.com/rubennati/secure-docker-blueprint/blob/main/apps/bookstack/README.md) | a wiki with real structure: shelves, books, chapters, pages | database | 2 |
| [Easy!Appointments](https://github.com/rubennati/secure-docker-blueprint/blob/main/apps/easyappointments/README.md) | appointment booking on PHP and MySQL, running since 2013 and with no build step | database | 2 |
| [Heimdall](https://github.com/rubennati/secure-docker-blueprint/blob/main/apps/heimdall/README.md) | a launcher page for your services, with optional per-service status | — | 1 |
| [Homarr](https://github.com/rubennati/secure-docker-blueprint/blob/main/apps/homarr/README.md) | a dashboard built around integrations, showing live state rather than only links | — | 1 |
| [Homepage](https://github.com/rubennati/secure-docker-blueprint/blob/main/apps/homepage/README.md) | a dashboard configured in YAML, split by concern across several files | — | 1 |
| [IT-Tools](https://github.com/rubennati/secure-docker-blueprint/blob/main/apps/it-tools/README.md) | formatters, hash and UUID generators, regex testing, encoders — without pasting your data into someone else's site | — | 1 |
| [NocoDB](https://github.com/rubennati/secure-docker-blueprint/blob/main/apps/nocodb/README.md) | a spreadsheet-like interface and an API over a SQL database | — | 1 |
| [OpenProject](https://github.com/rubennati/secure-docker-blueprint/blob/main/business/openproject/README.md) | the full project platform — Gantt, work packages, time tracking, wikis | database | 6 |
| [Vikunja](https://github.com/rubennati/secure-docker-blueprint/blob/main/business/vikunja/README.md) | task management — kanban, lists, Gantt and table views | SMTP, database | 2 |

**Access defaults differ, and are not all restrictive.** Four of them —
BookStack, Cal.diY, Easy!Appointments and Ghost — ship reachable from the open
internet, because they exist to be read by people who are not on your VPN.
Everything else in the table ships VPN-only. Check the value in that stack's
`.env.example` rather than assuming: it is one line, and it decides who can
reach the thing.

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
