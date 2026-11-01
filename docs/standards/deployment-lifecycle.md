# Deployment lifecycle

How an operator takes this repository into production and keeps it there. It is written
for the person running the host, not for someone changing the repository —
[`../maintenance.md`](../maintenance.md) is the maintainer's counterpart.

## Two lifecycles, not one

Conflating them is the mistake this document exists to prevent.

| | Blueprint release | Upstream image |
|---|---|---|
| What moves | this repository — compose shapes, middleware, standards, defaults | one stack's pinned image tag |
| Named by | a Git tag, `vX.Y.Z` | `APP_TAG=` and friends in `.env` |
| Recorded in | [`../../CHANGELOG.md`](../../CHANGELOG.md) | the stack's `UPSTREAM.md` |
| Adopted by | checking out a different tag | changing the pin and recreating the stack |
| Reversible by | checking out the previous tag | changing the pin back, **if the data allows it** |

They move independently and can be taken independently. Pulling the default branch takes
both at once, which is why the procedure below pins a release.

## 1 — Prepare the host

Docker Engine 28.0+ with Compose 2.33.1+, a Linux host, `envsubst` from `gettext-base`, and a
domain — at Cloudflare for DNS-01 certificates, the one provider `core/traefik` wires; at
any provider for HTTP-01 or TLS-ALPN-01.
The root [`README.md`](../../README.md#getting-started) states these as the requirements.
Engine 28.0 is the first release that accepts `"ipv6": true` without `fixed-cidr-v6`,
the shape the dual-stack prerequisites document, and the first that keeps a port
published on a loopback address off the network (moby#49325); on 27.x the documented
`daemon.json` does not start the daemon. Compose 2.33.1 is the first release that knows `gw_priority`, which `core/traefik/docker-compose.yml` uses to pin the published ports to `proxy-public`; an older Compose refuses the file.

**The Docker daemon bounds container logs — the stacks do not.** No service in this
repository sets a `logging:` block, and Docker's default driver, `json-file`, rotates
nothing: a container's log grows until the disk is full. The bound is a daemon default
in `/etc/docker/daemon.json`, set once for every container on the host:

```json
{
  "log-driver": "local",
  "log-opts": { "max-size": "10m", "max-file": "3" }
}
```

`local` is the driver to prefer: it compresses, it rotates by default (20 MB × 5
files when no option is given), and its files are read by the daemon alone — `docker
compose logs` and the Docker API work as before, which is how every tool in this
repository reads container output. `json-file` with the same `max-size` and `max-file`
is the alternative for a host where a tool tails the files under
`/var/lib/docker/containers/` directly; nothing in this repository does. Traefik's own
access and error logs are files it writes itself and are rotated by `logrotate`
([`logrotate.md`](logrotate.md)), not by the daemon.

A changed daemon default applies to containers created after it. A container that
already runs keeps the driver and options it was created with until it is recreated —
`docker compose up -d --force-recreate` in the stack directory — so on an existing host
the limit arrives stack by stack, not at the daemon restart.

`live-restore` is a separate decision about the daemon, not about logging: with it,
containers keep running while the daemon itself restarts or is upgraded. The operator
site's server setup recommends it; it is recorded in `.ai/decisions.md` and belongs in
the same file, as its own line.

**Not yet standardised here:** host firewall policy, unattended upgrades, the account the
stacks run under, and kernel or `sysctl` expectations. A deployment works without them
being written down; it is simply not this repository that says what they should be.

## 2 — Choose a release

```bash
git clone https://github.com/rubennati/secure-docker-blueprint.git
cd secure-docker-blueprint
git checkout "$(git tag --sort=-v:refname | head -n1)"   # the newest release
```

Deploy from a tag, not from the default branch. The default branch is where work lands
between releases: it is checked by CI on every change, but the combination of stacks on it
at any given moment is not one anybody has operated.

Which releases exist: `git tag --sort=-v:refname`. What changed between two of them:
[`CHANGELOG.md`](../../CHANGELOG.md).

## 3 — Configure a stack

`cp .env.example .env`, then set every `__REPLACE_ME__` the file carries. Each stack's
`README.md` documents its variables, and `.env.example` names every value that has to be
set. Secrets do not belong in `.env` — see [`secrets.md`](secrets.md) for what goes in
`.secrets/` and how it is generated.

## 4 — Deploy in order

**Traefik first.** It creates `proxy-public` and the edge networks `EDGE_NETWORKS` in
its `.env` lists — the external network each stack that publishes a domain attaches to;
a stack started before it fails on a missing network, and a stack whose edge network is
not listed is unreachable without a log line
([`core/traefik/docs/edge-networks.md`](../../core/traefik/docs/edge-networks.md)).

After that the order follows one rule: **a stack starts after whatever creates a network
it declares as external, or provides a middleware its Traefik labels name.** Those are the
only cross-stack runtime dependencies the repository has, and each is declared in the
stack's own compose file rather than remembered here:

| Before | Comes | Why |
|---|---|---|
| `core/traefik` | every stack publishing a domain | creates `proxy-public` and the listed edge networks |
| `core/authentik` | stacks whose Traefik labels use forward-auth | the middleware answers at its address |
| `core/crowdsec` | stacks joining `crowdsec-security` | the network is created there |

Which stacks those are is a property of the tree, so read it off rather than trusting a
number written here:

```bash
grep -rl 'crowdsec-security' --include=docker-compose.yml .
grep -rl 'forward-auth'      --include=docker-compose.yml .
```

Anything else can start in any order.

## 5 — Validate

`./scripts/overview.sh` states which release the deployment is on, whether the working
tree has drifted from it, and which stacks are configured and running. Below the service
table it reports the Traefik routers: those still on the names the middleware model
replaces (`scripts/migrate-traefik-env.sh` prints the changes, as a dry run), the
positions a `.env` leaves empty (Traefik disables such a router), and the routers naming
a TLS option other than the deployment standard; `--routers` lists every router with its
four positions.

Per-stack verification is the stack's own `README.md`. Stacks carrying `ops/scripts/` have
their own checks — `core/traefik` renders and validates its configuration that way.

## 6 — Back up

[`restore.md`](restore.md) covers both directions: Borgmatic with database-aware dumps,
and what restoring actually means per persistence pattern. Read it **before** the first
backup rather than after the first loss — it is the document that says which of your
stacks need a dump rather than a file copy.

## 7 — Update the Blueprint

```bash
git fetch --tags
git tag --sort=-v:refname | head -n5                              # newest releases
git log --oneline "$(git describe --tags --abbrev=0)"..<target>   # what it changes
git checkout <target>
```

`.env`, `.secrets/` and `volumes/` are ignored by Git and survive the checkout. What
changes underneath them is the compose files, the middleware and the defaults, so read
the `CHANGELOG.md` entries between the two tags first: an entry saying an upgrade
**requires operator action** means a stack will not come back up unchanged.

Then recreate the stacks the release touched. `docker compose up -d` applies a changed
compose file; a stack whose service names changed also needs `--remove-orphans`.
`core/traefik` renders its configuration from templates, so a release that changes
a template takes effect only after `bash ops/scripts/render.sh` in that directory
and a `--force-recreate` of the proxy where the static configuration changed.

A checkout carries the stack files; it does not carry what a stack installed
outside it — a logrotate stanza, systemd units, a backup agent's configuration.
After the checkout, compare those with what the release ships:

```bash
./scripts/overview.sh --host
```

`differs` names the file in the checkout and the file on the host; the commands
that bring the host file up to date are printed, never run
([`host-files.md`](host-files.md)).

## 8 — Update an upstream image

Independent of the above. The pin lives in `.env`:

```bash
# in the stack directory
$EDITOR .env                           # APP_TAG=<new version>
docker compose up -d
```

`UPSTREAM.md` records which version the repository pins and what its upgrade path is. A
newer Blueprint release usually carries newer pins in `.env.example`, but it does not
change the `.env` you already have — adopting a release and adopting its pins are two
separate acts.

## 9 — Roll back

Returning to the previous Blueprint release is `git checkout` of the earlier tag followed
by recreating the affected stacks. That part is reliable.

**Rolling an image back is not symmetrical.** An application that has migrated its
database on first start after an upgrade will usually not run against the older image, and
no pin change undoes the migration. The way back is the backup, not the tag. Treat an
image upgrade as one-way unless upstream documents a downgrade path, and take the backup
before it rather than after.

## 10 — Identify which release a deployment came from

`./scripts/overview.sh` prints it. Underneath it is plain Git:

```bash
git describe --tags --exact-match     # the release, when the checkout is on one
git describe --tags                   # the nearest release plus the drift
git status --porcelain                # local modifications
```

A deployment that is not a Git checkout cannot answer this question, and neither can one
whose working tree has been edited in place. Both are reported rather than guessed at.

## What this document does not decide

- **Host hardening outside Docker** — firewall, updates, the account the stacks run under.
- **Whether a deployment must remain a Git checkout.** Everything above assumes it is,
  because that is what makes the release identifiable. Copying the directory instead
  works and loses that.
- **Staged or multi-host deployment.** One host, one checkout.
