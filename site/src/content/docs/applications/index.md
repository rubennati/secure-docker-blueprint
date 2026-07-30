---
title: Applications
description: Curated operator guides for self-hosted applications and business tools running on Secure Docker Blueprint.
---

Application and business-tool guides live here — what an operator deploys and uses day to day, on top of the [Core Infrastructure](/core/) every guide assumes is already running.

Guides cover setup, ongoing use, backup, restore and updates.

The blueprint ships far more services than have a guide here. A guide is written once a service has been set up and verified end to end, so this list grows slowly and on purpose. The [repository](https://github.com/rubennati/secure-docker-blueprint#whats-included) lists every service it contains, each with its own README.

## Vaultwarden

**Problem it solves:** centralizes credentials — browser, mobile, and desktop — in one self-hosted vault instead of trusting a third-party service with everything you log into.

[Go to the Vaultwarden guide →](/applications/vaultwarden/)

## Nextcloud

**Problem it solves:** keeps files, calendars and contacts on your own server and syncs them to desktops and phones, with sharing and document editing on top.

[Go to the Nextcloud guide →](/applications/nextcloud/)

## Invoice Ninja

**Problem it solves:** issues invoices and quotes, tracks what has been paid, and gives each client a portal to view and settle them — on your own server, with the payment data staying there.

[Go to the Invoice Ninja guide →](/applications/invoiceninja/)

## Seafile Pro

**Problem it solves:** private cloud file storage and sharing with browser-based Office document editing, collaborative documents, full-text search, and antivirus scanning — without depending on a third-party cloud provider.

[Go to the Seafile Pro guide →](/applications/seafile-pro/)

## Where to go next

- [Vaultwarden](/applications/vaultwarden/) — password manager
- [Nextcloud](/applications/nextcloud/) — files, calendars and contacts
- [Invoice Ninja](/applications/invoiceninja/) — invoicing, quotes and a client portal
- [Seafile Pro](/applications/seafile-pro/) — file sync and collaborative editing
- [Core Infrastructure](/core/) if Traefik isn't running yet — every application guide needs it first

Each guide opens with its status, the version it sets up, when that was last checked, and what has not been exercised.
