---
title: FAQ
description: Common questions about Secure Docker Blueprint and this site.
---

## Is this site the technical source of truth?

No. The repository is. Compose files, configuration, and implementation details live at [github.com/rubennati/secure-docker-blueprint](https://github.com/rubennati/secure-docker-blueprint). This site is a practical guide layer on top of it.

## Why is this site smaller than the repository?

The repository covers 40+ services. This site is deliberately curated — it covers the services and topics that benefit most from guided, narrative documentation. Not everything needs a guide page.

## Why start with Vaultwarden?

Vaultwarden is commonly the first service people deploy, it stores credentials, and it requires a tested backup and restore setup. That makes it a good reference target for what an operator guide should look like.

## Can I use the repository directly without this site?

Yes. The repository is self-contained. This site exists for people who prefer structured guides over reading compose files and READMEs directly.
