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
cp .env.example .env               # Edit: domain, access policy
mkdir -p config
cp server.example.yml config/server.yml    # Edit: base-url must match the domain
docker compose up -d
docker compose logs -f app         # Watch for: "Listening on :80"
```

Then create the accounts — the server denies everything until they exist:

```bash
docker compose exec app ntfy user add --role=admin admin
docker compose exec app ntfy user add monitoring
docker compose exec app ntfy access monitoring alerts rw
```

Verify the path end to end before pointing a monitor at it:

```bash
curl -u monitoring -d "test from the blueprint" https://ntfy.example.com/alerts
```

The message has to arrive on the subscribed device, not merely return HTTP 200.

## Security Model

| | |
|---|---|
| **Access** | `acc-public` + `sec-3` — see below |
| **Authentication** | `auth-default-access: deny-all`; users and per-topic grants created with the CLI |
| **Secrets** | None in `.env`. Credentials live in the user database at `./volumes/lib/user.db`. |
| **Filesystem** | `read_only: true`, config mounted `:ro` |

### Access policy

`acc-public` is a deliberate deviation from the VPN-only default the rest of this
category uses. A notification receiver has to be reachable from the devices that
carry it, including over mobile data — a receiver behind the VPN only delivers
while the VPN is up, which is the same coupling this stack exists to avoid.

What makes that defensible is `auth-default-access: deny-all` in `config/server.yml`:
no topic is readable or writable without an explicit grant. Leaving that at the
upstream default while exposing the server publicly makes every topic on it
world-readable and world-writable to anyone who guesses the name.

Where every receiving device is on the tailnet anyway, `acc-tailscale` is the
tighter choice and costs nothing.

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

Nothing here has been verified on a host — this stack is `🚧 preview`. The
following are the parts most likely to need adjustment, listed so they are checked
deliberately rather than discovered:

- **`read_only: true` is untested.** ntfy writes to the mounted cache and lib
  paths, which stay writable, but any additional write target would surface as a
  start-up failure. Drop the flag if it does, and record why.
- **The rate limit is the first suspect if notifications go missing.** `sec-3`
  carries `rl-soft`, and a publisher bursting during an incident is exactly when
  the limit matters. The SPA variants are documented for VPN-gated apps only, so
  the answer here is a measurement, not a swap.
- **iOS needs `upstream-base-url`.** Apple restricts background processing, so a
  self-hosted server cannot push to iOS on its own. The setting is present and
  commented in `server.example.yml`, including what leaves the host when it is on.
- **Running as a fixed UID needs a chown first.** The `user:` line is commented
  for that reason; enabling it without chowning the mounted paths starts a server
  that cannot write its databases.
