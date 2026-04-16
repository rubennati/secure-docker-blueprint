---
name: New app request
about: Propose a new app for the blueprint
title: 'Add app: <name>'
labels: new-app
assignees: ''
---

## App details

- **Name**: 
- **Upstream project**: (link)
- **Docker image**: (Docker Hub or registry link)
- **License**: (app's own license)
- **Category**: (e.g. CMS, password manager, monitoring, document management)

## Why add it?

What use-case does it cover that isn't already in the blueprint?

## Complexity estimate

How many services does it need? Examples:
- **Small**: single container (like Whoami, Dockhand)
- **Medium**: app + database (like Ghost, WordPress)
- **Large**: app + database + cache + workers (like Paperless, Nextcloud, Seafile)

## Known caveats

- Does the image support `_FILE` secret pattern, or does it need an entrypoint wrapper?
- Does it use s6-overlay, supervisord, my_init (no `user:` in compose), or direct exec?
- Does it need iframe embedding (needs `sec-*e` security chain)?
- Does it have an admin panel that should be VPN-restricted?
- Does it send emails / use webhooks / call home?

## Willing to contribute?

- [ ] Yes, I'll open a PR following CONTRIBUTING.md
- [ ] Just proposing; someone else is welcome to pick this up
