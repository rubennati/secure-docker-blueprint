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

**The host itself** — updates, accounts, SSH, the provider filter, the second way in, the
VPN — is outside the blueprint; [`docs/host-baseline.md`](../host-baseline.md) is the
baseline it assumes, with what was tested on a host and what is open.

**The host firewall and management access.** `core/traefik` renders a recommended
`nftables` ruleset for the exposure profile it derives — `config/host/ingress.nft`,
installed by the operator, never applied by the repository — and the two requirements
that go with it: administration arrives over the VPN by key, and a second path that does
not depend on ingress (the hoster's console, a second interface) exists for the day the
first is gone. No automatically filled rule reaches the management plane. What the
internet reaches is measured from another machine with `scripts/exposure-test.sh`, and
`validate.sh --strict` requires that measurement's marker for a public binding
([`core/traefik/docs/host-firewall.md`](../../core/traefik/docs/host-firewall.md), [DEC-078](../../.ai/decisions.md#dec-078)).

**Not yet standardised here:** unattended upgrades, the account the stacks run under,
and kernel or `sysctl` expectations. A deployment works without them being written
down; it is simply not this repository that says what they should be.

## 2 — Choose a release and the stacks

A host carries only the stacks it runs. A Git partial checkout (sparse checkout) gives
it exactly those directories and keeps them a Git checkout, so the release stays
identifiable and an update can be previewed per stack. A full clone is for working on
the repository itself. Copying stack directories out of a clone also works, but loses
the release identity, and `core/crowdsec` finds Traefik's logs by a relative path
(`../traefik/volumes/logs`) that expects the same layout.

The recommended location is `/srv/docker`, with each stack at
`/srv/docker/<category>/<stack>`. It is a default, not a requirement: any other path
works, for example `/srv/<category>/<stack>`. Paths in examples elsewhere in the
repository — backup sources, logrotate stanzas — assume `/srv/docker` and change with
it; [`scripts/host-files.sh`](../../scripts/host-files.sh) renders host files with the
real path.

```bash
# An empty directory you own
sudo mkdir -p /srv/docker && sudo chown "$USER" /srv/docker

# Clone without files, then take the newest release
git clone --sparse --no-checkout https://github.com/rubennati/secure-docker-blueprint.git /srv/docker
cd /srv/docker
git checkout "$(git tag --sort=-v:refname | head -n1)"
git sparse-checkout set scripts docs/standards

# The host's own list of stacks
cp stacks.example stacks
```

At this point the host holds the files at the repository root, the scripts and the
standards. `stacks` is the host's own list of stacks, one path per line; Git ignores it,
so it survives every update. The template starts with the base most hosts need:

| Path | Why |
|---|---|
| `core/traefik` | HTTPS ingress for every stack that publishes a domain |
| `core/crowdsec` | threat detection; it blocks nothing until a remediation is enabled |
| `apps/whoami` | the test target the Traefik and CrowdSec checks run against |

Edit the list, then check it out:

```bash
# Check out what the file lists
scripts/stacks.sh apply

# The release, and where file and checkout differ
scripts/stacks.sh status
```

`scripts` and `docs/standards` are always checked out: the first holds `stacks.sh`,
`overview.sh` and `host-files.sh`, the second the rules the stack documentation links
to. Every other line is a choice, the template's included. A path that does not exist in
the checked-out release is refused, and nothing changes.

**Removing a line removes the stack's directory.** Git deletes a directory that leaves
the partial checkout together with the files it ignores — `.env`, `.secrets/` and
`volumes/`, which holds the stack's data. `stacks.sh apply` therefore refuses while a
stack it would remove still has such files, lists them and changes nothing. Stop the
stack, back up or move its data, delete it, then apply again. A stack that is merely
unused can stay in the list. Plain Git offers no such check: `git sparse-checkout set`
or `add` with a shorter list deletes without asking.

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
| `core/crowdsec` | stacks joining `crowdsec-security` | `core/traefik` creates the network; `core/crowdsec` joins it as `external: true` |

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
# The newest releases
git fetch --tags
git tag --sort=-v:refname | head -n5

# Preview the release for these stacks, confirm, take it
scripts/stacks.sh update <target>
```

`stacks.sh update` shows the files the release changes in the stacks on this host and
nothing else, names any listed stack the release no longer contains — its directory
and data stay — and asks before it checks the release out; `--yes` skips the question.
It refuses while the checkout does not match `stacks` (run `apply` first) or while
tracked files have been edited in place. `git diff HEAD..<target> -- <stack>` shows one
stack's change in full.

On a full clone the same steps are plain Git:

```bash
# What the release changes
git log --oneline "$(git describe --tags --abbrev=0)"..<target>

# Take it
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
and a `--force-recreate` of the proxy where the static configuration changed — which
interrupts every stack it routes for about seven seconds
([`edge-networks.md`](../../core/traefik/docs/edge-networks.md)).

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

A partial checkout answers it the same way as a full clone. A deployment that is not a
Git checkout cannot answer this question, and neither can one whose working tree has
been edited in place. Both are reported rather than guessed at.

## What this document does not decide

- **Host hardening outside Docker** — firewall, updates, the account the stacks run under.
- **Staged or multi-host deployment.** One host, one checkout.
