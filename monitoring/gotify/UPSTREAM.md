# Upstream Reference

## Source

- **Image:** https://github.com/gotify/server/pkgs/container/server
- **GitHub:** https://github.com/gotify/server
- **Docs:** https://gotify.net/docs/
- **License:** MIT (the logo is CC BY 4.0, stated in the same file)
- **Decision facts checked:** 2026-09-23
- **Use restrictions:** none — https://github.com/gotify/server/blob/master/LICENSE · checked 2026-09-23
- **Origin:** Germany · Gotify community project · EU
- **Domain:** Monitoring
- **Role:** Self-hosted push notifications — applications post with a token, clients hold a stream open
- **Based on version:** `3.1.1`

## Origin, stated precisely

The project publishes no imprint. The GitHub organisation states no location;
the maintainer who holds most of the history states Berlin. That is weaker
evidence than a legal page, and it is what **Origin** above rests on.

## Project maturity

15 946 stars, 249 commits in the twelve months to 2026-09-20, releases through
2026-09-15. 3.0.0 dropped `config.yml` in favour of environment variables, which
is why this stack configures everything through `environment:`.

**3.1.1 is the minimum version.** GHSA-phfm-q6fr-wv34, high, "Creating users
doesn't require an elevated session", is fixed there.

## What we use

- `ghcr.io/gotify/server:3.1.1` — upstream's own registry rather than the Docker
  Hub copy of the same image, which keeps the scan and the pull off Docker Hub's
  anonymous limit.
- One container. SQLite in the data directory; upstream ships no database
  service and the server needs none.

## What we changed and why

| Change | Reason |
|--------|--------|
| `user: "${APP_UID}:${APP_GID}"` | The image runs as root. The server binds port 80, which Docker's default `net.ipv4.ip_unprivileged_port_start=0` permits an unprivileged process to do, so root buys nothing here |
| `GOTIFY_DEFAULTUSER_PASS_FILE` from a Docker Secret | Upstream's default administrator is `admin`/`admin`, created on the first start. `_FILE` is native — every Gotify variable has one |
| `GOTIFY_REGISTRATION: "false"` | Upstream's default, restated so the setting is visible rather than inherited |
| `GOTIFY_PLUGINSDIR: ""` | No plugin directory is created in the data volume, and no compiled plugin is loaded into the server process. Verified: with it empty, the first start created `gotify.db` and `images/` and no `plugins/` |
| `GOTIFY_SERVER_SECURECOOKIE: "true"` | Traefik terminates TLS, so the session cookie can be restricted to HTTPS. Upstream leaves it off because it also supports plain HTTP |
| `GOTIFY_SERVER_TRUSTEDPROXIES` | Without it the access log records Traefik's address for every request |
| Healthcheck reads the `/health` payload | The endpoint answers without a token and reports the database separately, so a green status code alone would not say the database is reachable |
| `read_only: true`, `cap_drop: ALL`, `tmpfs: /tmp` | Verified against 3.1.1; only `/tmp` and the data volume are written |
| `APP_TRAEFIK_ACCESS=acc-tailscale` | The monitoring default. A receiver has to be reachable by the devices that carry it, which is a topology decision — `monitoring/README.md`, "Where the receiver runs" |

## Verified on the image (2026-09-23)

Not a host verification: this ran the image directly, without Traefik and
without TLS.

- Started with `read_only`, `cap_drop: ALL`, `no-new-privileges` and uid 1000:
  healthy, `Listen address=[::]:80`.
- `GOTIFY_DEFAULTUSER_PASS_FILE` took effect — the administrator's credentials
  answered 200 on `/current/user`, a wrong password 401.
- With `GOTIFY_PLUGINSDIR` empty, the data directory held `gotify.db` and
  `images/` only.
- `/health` returned `{"health":"green","database":"green"}`.

What a host run still has to establish: the route behind Traefik with TLS, a
refused client outside the access policy, the Android app receiving a message,
a restart, and the restore in the README.

## Upgrade checklist

1. Read the release notes — https://github.com/gotify/server/releases
2. Raise `APP_TAG` in `.env` and in `.env.local.example`
3. `docker compose pull && docker compose up -d`
4. `docker compose logs gotify-app` — the version line, then `Listen address`
5. Sign in, post one message with an application token, confirm a client
   receives it
6. Record the result in `Last verified` once it ran behind Traefik

## Diff against upstream

Upstream publishes no compose file in the repository; its example lives in the
install documentation at https://gotify.net/docs/install.

```bash
# The commands and flags this version accepts
docker run --rm ghcr.io/gotify/server:3.1.1 --help

# What the image sets by default — entrypoint, port, healthcheck
docker image inspect ghcr.io/gotify/server:3.1.1 --format '{{json .Config}}'
```
