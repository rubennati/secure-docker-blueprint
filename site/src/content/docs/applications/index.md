---
title: Applications
description: Curated operator guides for self-hosted applications and business tools running on Secure Docker Blueprint.
---

Application and business-tool guides live here — what an operator deploys and uses day to day, on top of the [Core Infrastructure](/core/) every guide assumes is already running.

Guides cover the full operating path — setup, ongoing use, backup, restore, and updates — not just how to start a container.

## Vaultwarden

**Problem it solves:** centralizes credentials — browser, mobile, and desktop — in one self-hosted vault instead of trusting a third-party service with everything you log into.

[Go to the Vaultwarden guide →](/applications/vaultwarden/)

## Nextcloud

**Problem it solves:** keeps files, calendars and contacts on your own server and syncs them to desktops and phones, with sharing and document editing on top.

[Go to the Nextcloud guide →](/applications/nextcloud/)

## Seafile Pro

**Problem it solves:** private cloud file storage and sharing with browser-based Office document editing, collaborative documents, full-text search, and antivirus scanning — without depending on a third-party cloud provider.

[Go to the Seafile Pro guide →](/applications/seafile-pro/)

## What these guides cover

A useful guide has to address what to back up, what restore looks like, and how to update without data loss — that takes time to verify per application. Not every guide is complete in all respects yet; each page states clearly what has and has not been tested.

## Where to go next

- [Vaultwarden](/applications/vaultwarden/) — password manager; setup, backup, and restore verified.
- [Nextcloud](/applications/nextcloud/) — files, calendars and contacts; installation, mail and hardening verified on a live host, client sync and backup not yet exercised.
- [Seafile Pro](/applications/seafile-pro/) — file sync and collaborative editing; installation verified, backup and restore not yet tested.
- [Core Infrastructure](/core/) if Traefik isn't running yet — every application guide needs it first.
