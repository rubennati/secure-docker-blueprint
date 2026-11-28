# Stacks in use

The stacks below run on real hosts. Their failures reach people, and their upgrades
are the ones a release has to get right first. Every release checks each of them
before the tag: is there a new upstream version, does it fix a security issue, does
it break something, and did the upgrade run in a lab on data. The
[Release Chain](maintenance.md#release-chain) does not tag while a row is older than
the release.

This page names roles and counts, never hosts. The facts per stack stay with their
owners: the pin in `.env.example`, upgrade paths and breaking changes in
`UPSTREAM.md`, findings in [`../LIFECYCLE.md`](../LIFECYCLE.md). This page records
that they were read, and when.

## Criticality

| Level | Meaning |
|---|---|
| very high | The edge, the management plane, or data whose loss or exposure cannot be undone. An upgrade gets a lab run on data and a backup before it. |
| high | A service people rely on daily that a restore brings back. An upgrade gets a lab run when the release notes mention a migration or a breaking change. |
| medium | A test or helper stack. Its own release notes are enough. |

## Stacks

Checked on 2026-11-28 for the release after v0.9.10. *Version checked* is the pin
the check ended with.

| Stack | Role | Criticality | Hosts | Version checked | New version | Security fix | Breaking change | Lab upgrade test |
|---|---|---|---|---|---|---|---|---|
| `core/traefik` | reverse proxy, TLS, access middlewares | very high | 4 | v3.8.0 | yes, from v3.7.20 | none new — 3.8.0 carries the fixes 3.7.20 brought | none for this configuration; checked against the 3.8 migration notes | yes — routing, access, headers and the CrowdSec plugin identical to 3.7.20 |
| `core/crowdsec` | intrusion detection, bouncer for Traefik | very high | 2 | v1.8.2 | no | — | — | — |
| `core/dockhand` | container management, with PostgreSQL and the socket proxy | very high | 1 | v1.0.60, PostgreSQL 16.16, socket proxy v0.5.0 | yes, from v1.0.59 | none new; three HIGH advisories of 2026-11-25 affect v1.0.58 and older | none stated | yes — user and authentication kept, API `401` without a login |
| `core/hawser` | Dockhand agent on a managed host | very high | 3 | 0.2.54 | yes, from 0.2.53 | no | none stated | no — needs a Dockhand server; the release notes were read |
| `core/dnsmasq` | split DNS for the VPN names | high | 1 | 2.93 | no | — | — | — |
| `monitoring/gatus` | uptime checks | high | 1 | v5.38.0 | no | — | — | — |
| `monitoring/ntfy` | push notifications | high | 1 | v2.38.3 | yes, from v2.38.1 | yes, in v2.38.2 and v2.38.3 | small ones, listed in `UPSTREAM.md`; none for publishing with a token | yes — cached messages survive, publishing works |
| `apps/vaultwarden` | password manager, MariaDB | very high | 1 | 1.37.5, MariaDB 12.3.3 | no; MariaDB 12.3.3 rebuilt on Docker Hub | MariaDB 12.3.4 not on Docker Hub yet | — | — |
| `apps/seafile` | file sync, MariaDB | very high | 2 | 13.0.30, SeaDoc 2.0.14, MariaDB 10.11.19 | yes, from 13.0.29 | yes | none | yes — library and file kept |
| `apps/seafile-pro` | file sync, Professional Edition | very high | 1 | 13.0.30, ClamAV 1.5.5, SeaSearch 1.0.8 | yes | yes, Seafile and ClamAV | `app-internal` becomes internal: `down`, then `up -d` | yes — Seafile with the Community Edition image of the same release; ClamAV and the network on Pro |
| `apps/onlyoffice` | document editing for Seafile | high | 2 | 10.0.0 | no | — | — | — |
| `apps/tymeslot` | scheduling | high | 1 | 1.51.0 | yes, from 1.41.0 | no advisory | 1.43 Stripe Connect (payments only), 1.44 `TRUSTED_PROXIES` | yes — 1.41 → 1.49 → 1.51, 43 migrations on data, user kept |
| `apps/paperless-ngx` | document management | very high | 2 | 3.5.1, Tika 3.4.0.0 | yes, from 3.4.2 | no advisory in 3.5.x; Tika 3.4 fixes a CRITICAL CXF flaw | 3.5 admits only `PAPERLESS_URL`'s host; the healthcheck was adapted. Tika 3.4 refuses Office files over 50 MiB (`TIKA_MAX_ATTACHMENT_BYTES`) | yes — migrations ran, documents kept, new upload consumed; Tika cap measured |
| `apps/immich` | photo library | very high | 1 | v3.4.2, Valkey 9.2.1, PostgreSQL 18.7 | yes, from v3.3.6 | yes | an existing installation moves from PostgreSQL 14 by dump and restore (README) | yes — asset kept; 14 → 18 by the README steps, fresh install on 18 |
| `apps/photoprism` | public photo gallery, MariaDB | high | 1 | 261029, MariaDB 12.3.3 | no; MariaDB 12.3.3 rebuilt on Docker Hub | MariaDB 12.3.4 not on Docker Hub yet | — | — |
| `apps/whoami` | routing test | medium | 3 | v1.12.0 | no | — | — | — |

## Host components

The same targets for every host. Two hosts on different Engine releases behave
differently under the same blueprint, and the difference shows up as a fault on one of
them. The update policy for these packages is in
[`host-baseline.md`](host-baseline.md#docker-and-vpn-packages).

| Component | Minimum | Target | Why the minimum |
|---|---|---|---|
| Docker Engine (`docker-ce`) | 28.0 | the current 29.x release, the same on every host | 28.0 is the first release that accepts `"ipv6": true` without `fixed-cidr-v6` and keeps a port published on a loopback address off the network ([`deployment-lifecycle.md`](standards/deployment-lifecycle.md#1--prepare-the-host)) |
| containerd (`containerd.io`) | 1.7, as Engine 28.0 ships it | the release Docker's repository ships with the target Engine — 2.x for Engine 29 | No separate minimum: the Engine release decides it |
| Compose plugin (`docker-compose-plugin`) | 2.33.1 | the current 5.x release | 2.33.1 is the first release that knows `gw_priority`, which `core/traefik` uses |
| Tailscale | 1.66.1 | the current stable release | 1.66.1 is the first release whose `tailscale set` takes `--snat-subnet-routes`, which keeps a VPN client's address ([`host-baseline.md`](host-baseline.md) SHOULD 1) |

Checked on 2026-11-26: the hosts run Engine 29 on two different releases — one host
behind the others. Bringing them to one release is a maintenance-window step under
[Updating Docker on a host](host-baseline.md#updating-docker-on-a-host).

## Checking a release

For each row, before the tag:

1. Read the upstream releases since the version checked, and the advisories.
2. Note in the stack's `UPSTREAM.md` what changed for this blueprint: breaking
   changes, required intermediate versions, migrations, changed defaults.
3. Run the upgrade in a lab on data when the criticality asks for it, or say why not.
4. Update the row: version checked, the four answers, and the date above the table.

A database major version is never moved as part of this check. It is its own step,
with a migration guide in the stack's README, proposed separately.

`scripts/overview.sh --host` on a host lists the images whose tag differs from
`.env.example` and the Docker and VPN packages with an update pending.
