# Keycloak — admin console blocked by the proxy's frame header

**Stack:** `core/keycloak`  
**Date:** 2026-09-07  
**Keycloak version:** 26.7.3

## Summary

The admin console never loaded through Traefik: a modal reported a timeout on
the third-party-cookie check, and the browser console showed that the page
refused to load in a frame because `X-Frame-Options` was `deny`. The header
came from the security chain, not from Keycloak. Fixed by removing the proxy's
header with a per-app middleware after the chain — the pattern
[`docs/standards/traefik-security.md`](../standards/traefik-security.md)
prescribes for applications that set the header themselves.

## Symptom

```text
Something went wrong
Timeout when waiting for 3rd party check iframe message.
```

Browser console:

```text
Refused to display 'https://sso.example.com/' in a frame because it set
'X-Frame-Options' to 'deny'.
```

## Root cause

The console starts by loading
`/realms/master/protocol/openid-connect/3p-cookies/step1.html` in a hidden
iframe from its own origin, to learn whether the browser accepts third-party
cookies. Keycloak sends no frame header on that page, and none on
`login-status-iframe.html`, which `keycloak-js` embeds from the application's
origin; the console itself answers with `X-Frame-Options: SAMEORIGIN` and a
CSP `frame-ancestors 'self'`. The stack shipped `sec-2-spa`, whose `hdr-basic`
block sets `frameDeny: true`. Traefik adds that header to every response, so
the framed page arrived with `DENY` and the browser refused it.

Measured against the container, without the proxy:

| Page | `X-Frame-Options` | `Content-Security-Policy` |
|---|---|---|
| `/admin/master/console/` | `SAMEORIGIN` | `frame-src 'self'; frame-ancestors 'self'; object-src 'none';` |
| `.../3p-cookies/step1.html` | none | `frame-src 'self'; object-src 'none';` |
| `.../login-status-iframe.html` | none | `frame-src 'self'; object-src 'none';` |

## Fix

Keep the security level and put a middleware that removes the proxy's header
**in front of** the chain:

```yaml
- "traefik.http.routers.${COMPOSE_PROJECT_NAME}.middlewares=${APP_TRAEFIK_THREAT}${APP_TRAEFIK_ACCESS}@file,${COMPOSE_PROJECT_NAME}-strip-xfo,${APP_TRAEFIK_SECURITY}@file"
- "traefik.http.middlewares.${COMPOSE_PROJECT_NAME}-strip-xfo.headers.customResponseHeaders.X-Frame-Options="
```

The first attempt placed `strip-xfo` after the chain, the way `business/matomo`
and `apps/vaultwarden` carry it, and it changed nothing: the header stayed
`DENY`. Traefik applies the response changes of the first middleware in the
list last, so a chain that sets the header behind a strip that removes it wins.
Measured on Traefik v3.6 against a throwaway nginx on `proxy-public` that
answers `/none` without a frame header and `/own` with `SAMEORIGIN`, through
`acc-local` from a container on the same network:

| Router middlewares | `/none` | `/own` |
|---|---|---|
| `acc-local, sec-2-spa` (as shipped) | `DENY` | `DENY` — the app's value is replaced |
| `acc-local, sec-2-spa, strip-xfo` (Matomo and Vaultwarden order) | `DENY` | `DENY` |
| `acc-local, strip-xfo, sec-2-spa` (the fix) | none | none |
| `strip-xfo, acc-local, sec-2-spa` | none | none |

An `e` variant of the chain (`SAMEORIGIN` instead of `DENY`) is not the
answer either: measured the same way, `sec-2e` and `sec-3e` set `SAMEORIGIN`
on every response, and `login-status-iframe.html` is a page an application on
another origin is meant to frame.

The strip removes the application's own `X-Frame-Options` as well; what keeps
the admin console out of foreign frames is Keycloak's CSP `frame-ancestors
'self'`, which the proxy does not touch. The realm's *Security Defenses* tab is
where an operator changes those values.

## Also affected

`business/matomo` and `apps/vaultwarden` carry the same middleware after the
chain, since 2026-08-17, and both are `scaffolded` — neither has been verified
on a host, which is how the order went unnoticed. Moving the middleware ahead
of the chain is the same one-line change; it is not part of this fix.
