---
title: What each application is for
description: The problem each self-hosted application solves, what it needs running first, and where several of them overlap.
---

These are the services you actually use — the reason for the server rather than
part of it. Every one of them expects [Traefik](/infrastructure/traefik/) to be
running first; they publish no ports themselves and are reached through it.

| | Solves | Also needs |
|---|---|---|
| [Vaultwarden](/applications/vaultwarden/) | credentials in one vault, synced to browser, phone and desktop, instead of a third party holding everything you log into | SMTP, for email verification |
| [Nextcloud](/applications/nextcloud/) | files, calendars and contacts on your own server, synced to desktops and phones, with sharing on top | SMTP |
| [Invoice Ninja](/applications/invoiceninja/) | invoices and quotes, what has been paid, and a portal where each client can view and settle them | SMTP |
| [Seafile Pro](/applications/seafile-pro/) | file sync built for large directory trees, with full-text search and antivirus scanning | a commercial licence; OnlyOffice for in-browser editing |
| [OnlyOffice](/applications/onlyoffice/) | opening `.docx`, `.xlsx` and `.pptx` in the browser, embedded inside another application | an application to embed it — it is not used on its own |

## Where the choice is not obvious

Several of these solve overlapping problems, and three more in the repository
compete with them without having a guide here. **Nextcloud and Seafile both do
file sync** — one is a suite, the other is a sync engine, and the decision is not
a matter of taste. **OnlyOffice, Collabora and Euro-Office** are three editors
for the same job, separated by resource cost and by who governs them.

[Choosing between services →](/applications/choosing/)

## What each guide contains

Installation with sensible defaults, a *Verify* section that confirms it actually
works, what to back up and how to update it, and the failures that service really
produces rather than hypothetical ones.

Each opens with the version it is written against and, where one exists, the date
it was verified — followed by a line naming what has not been exercised. Read
that line before trusting a service with data.

## What is not here

The repository ships considerably more services than these — dashboards, photo
libraries, monitoring, e-signature, project management — each with its own
README and Compose files.
[The full list is in the repository](https://github.com/rubennati/secure-docker-blueprint#whats-included),
and [choosing between alternatives](/applications/choosing/) covers what separates
them where several compete.

## Where to go from here

- Traefik not running yet: [what every server needs](/infrastructure/)
- Before real data goes into any of these: [backup and restore](/operations/backup/)
- Weighing licences, jurisdictions and what a service sends home:
  [data sovereignty](/sovereignty/)
