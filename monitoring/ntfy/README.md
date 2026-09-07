# ntfy

Push notification server. The monitoring services publish to a topic over HTTP;
phones, desktops and scripts subscribe to it. Self-hosted, no account anywhere,
no vendor between the alert and the device.

It is the receiving end of the alerting chain described in
[`../README.md`](../README.md#alerting) — every service in this category can
reach it, which is what makes it usable as the single channel across all of them.

## Where to run this

**Not next to the services it receives from.** When the monitored host stops, its
monitoring services stop — and a receiver on the same host stops with them, so the
outage that most needs an alert produces none.

This stack is built to be deployed on its own: one Traefik, one compose file, no
dependency on anything else in the repository. Put it on a second host, a small
VPS, or use the public instance the ntfy project operates instead of running one
at all. The reasoning is in [`../README.md`](../README.md#where-the-receiver-runs).

## Setup

```bash
cp .env.example .env               # Edit: domain, access policies, APP_UID/APP_GID
mkdir -p config volumes/cache volumes/lib   # owned by APP_UID — the server runs as that user
cp server.example.yml config/server.yml    # Edit: base-url must match the domain
docker compose up -d
docker compose logs -f ntfy-app    # Watch for: "Listening on :80"
```

Then create the accounts — the server denies everything until they exist:

```bash
docker compose exec ntfy-app ntfy user add --role=admin admin
docker compose exec ntfy-app ntfy user add monitoring
docker compose exec ntfy-app ntfy access monitoring alerts rw
docker compose exec ntfy-app ntfy token add --label publishers monitoring
```

`NTFY_PASSWORD` in the environment makes `user add` non-interactive; a passphrase
of a few words is what a phone keyboard can take. The token is what the
monitoring services publish with (`Authorization: Bearer tk_…`), so the
passphrase stays on the phone.

Verify the path end to end before pointing a monitor at it:

```bash
# from the operator's network — publishing is not on the public router
curl -u monitoring -d "test from the blueprint" https://ntfy.example.com/alerts
```

The message has to arrive on the subscribed device, not merely return HTTP 200.
It did, on 2026-09-08 (v2.28.0): an iPhone outside the tailnet, through the
public router, with `upstream-base-url` set.

## Security Model

| | |
|---|---|
| **Identity** | runs as `APP_UID:APP_GID`, the owner of `./config` and `./volumes`; every capability dropped |
| **Access** | two routers — public and read-only on the subscribed topics (`acc-public` + `sec-4`), everything else on the operator's side (`acc-tailscale`) — see below |
| **Authentication** | `auth-default-access: deny-all`; users and per-topic grants created with the CLI |
| **Secrets** | None in `.env`. Credentials live in the user database at `./volumes/lib/user.db`. |
| **Filesystem** | `read_only: true`, config mounted `:ro` |

### Access policy

A notification receiver has to be reachable from the devices that carry it,
including over mobile data — a receiver behind the VPN only delivers while the
VPN is up, which is the same coupling this stack exists to avoid. So the stack
puts two routers on one server:

| Router | Rule | Policy | Serves |
|---|---|---|---|
| `ntfy` | `GET` on the topics in `NTFY_PUBLIC_TOPICS`, and `/v1/account` | `APP_TRAEFIK_ACCESS` (`acc-public`) | subscribing, polling, the WebSocket, the apps' auth check and account lookup |
| `ntfy-ui` | everything else | `APP_TRAEFIK_UI_ACCESS` (`acc-tailscale`) | the web app, login, account management, publishing |

Traefik takes the longer rule first, so a `POST`, an unlisted topic or any other
path from the internet lands on the operator router and is refused there.

What makes the public router defensible is `auth-default-access: deny-all` in
`config/server.yml`: nothing on it answers without credentials — an anonymous
subscribe is a 403 from ntfy, not a topic listing. Leaving that at the upstream
default while exposing the server publicly makes every topic on it
world-readable and world-writable to anyone who guesses the name. Behind that
stand ntfy's own per-client limit (60 requests, then one every 5 s), the
chain's rate limit, and the threat slot for CrowdSec.

Measured from the internet on 2026-09-08 (v2.28.0): subscribe with credentials
200, anonymous 403, `POST`, `/`, `/v1/health` and an unlisted topic 403 on the
operator router, TLS 1.3.

Where every receiving device is on the tailnet anyway, set `APP_TRAEFIK_ACCESS`
to `acc-tailscale` as well — then nothing is public, and nothing else changes.

## Integration patterns

| Source | How |
|---|---|
| Uptime Kuma, Gatus, Beszel, changedetection.io | native ntfy notification, or a Shoutrrr / Apprise URL |
| Healthchecks | native ntfy integration per check |
| `backup/borgmatic` | run monitoring hook posting to the topic |
| Anything else | `curl -d "message" -u <user> https://ntfy.example.com/<topic>` |

One topic per concern beats one topic for everything — a grant is per topic, so a
publisher that only reports backups cannot read the rest.

## Backup

| | |
|---|---|
| **Database** | None. SQLite files, not a database server — no dump hook needed. |
| **State** | `./volumes/lib/user.db` (users, tokens, per-topic grants) · `./config/server.yml` |
| **Reproducible** | `./volumes/cache` (message cache and attachments) — safe to exclude |
| **Quiescing** | Not needed for `user.db` in practice; it changes only when accounts change. Back it up after account changes rather than on a tight schedule. |

Losing `user.db` costs the accounts and grants, not the delivery path — publishers
have to be re-created and re-granted. Losing `config/server.yml` costs the server
identity, including `base-url`, which subscribed devices are pinned to.

Full architecture: [`backup/README.md`](../../backup/README.md).

## Known Issues

Verified on a host on 2026-09-08 (v2.28.0). What the session found:

- **Root with every capability dropped cannot write into the operator's
  directories.** The image runs as root; with `cap_drop: ALL` that root has no
  `DAC_OVERRIDE`, so a cache directory owned by the operator is unwritable and
  the server dies with `unable to open database file`. The stack therefore runs
  as `APP_UID:APP_GID` — the user that owns `./config` and `./volumes`. Create
  the directories before the first start; Docker would create them as root.
- **`read_only: true` holds.** The cache and the auth database live on the two
  mounted volumes, `/tmp` is a tmpfs, nothing else is written.
- **The rate limit is the first suspect if notifications go missing.** `sec-4`
  carries `rl-hard`; a subscription is one long-lived request and an alert is
  one request, so the phone side has headroom. A publisher bursting during an
  incident is exactly when the limit bites — measure before switching.
- **iOS needs `upstream-base-url`.** Apple restricts background processing, so a
  self-hosted server cannot push to iOS on its own. The setting is commented in
  `server.example.yml`, including what leaves the host when it is on; with it
  set, the message arrived on an iPhone outside the tailnet.
