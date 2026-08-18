# Dependency Sweep — 2026-07-26

Repo-wide inventory of pinned image tags against the upstream releases available
on that date. Point-in-time record: the versions below are what was current then,
not what the tree pins now. Current pins are in each stack's `.env.example`; the
procedure is the Version Chain in [`../maintenance.md`](../maintenance.md#chains).

Repo-wide check of pinned image tags vs. current upstream releases (~30 of ~50 services verified;
rest listed below to finish). Update path = Version Chain above; prefer digest-pinning on bump
(reference: `apps/caldiy`).

### Applied this session (security-critical)

| Service | From | To |
|---|---|---|
| apps/vaultwarden | 1.36.0 | **1.37.0** (SSRF + 7 more fixes) |
| core/authentik | 2026.2.2 | **2026.5.6** |
| apps/nextcloud | 32.0.6 | **32.0.13** (33/34 exist — major, deliberate) |
| apps/ghost | 6.27.0 | **6.54.0** |
| core/crowdsec | v1.7.7 | **v1.7.8** |
| apps/paperless-ngx | 2.20.13 | **3.0.3** (🚧 major — verify: Python 3.11+, API v1 removed, search Whoosh→tantivy reindex) |
| business/invoiceninja | 5.13.24 | **5.13.26** |

### Pending — verified, security-relevant (apply next)

**Applied 2026-07-26** (second wave): wordpress **7.0.2** 🚧, listmonk **v6.2.0**, portainer(+agent)
**2.39.5**, dolibarr **23.0.3**, changedetection **0.55.8**, photoprism **260601**, bookstack
**v26.05.2**, immich **v3.0.3** 🚧, healthchecks **v4.2** 🚧. (🚧 = major, verify migration on deploy.)

Still pending:

| Service | Pinned | Latest | Note |
|---|---|---|---|
| core/traefik | v3.6 | **3.7.9** | floating `v3.6` auto-patches to 3.6.24; evaluate 3.7 (deliberate minor upgrade) |

### Feature/minor — applied 2026-07-26

n8n 2.31.6 · homarr v1.72.0 · onlyoffice 9.4.0 · nocodb 2026.07.0 (🚧 CalVer switch) · openproject 17.6.0 · dashy 4.5.0 · kimai 2.61.0 · gatus v5.36.0

### Up-to-date (no action)

it-tools (2024.10.22, dormant) · beszel + agent (0.18.7)

### Structural (fix regardless of version)

- ~~business/opensign pinned to `main`~~ — **fixed 2026-07-26: digest-pinned.** Upstream ships no semver tags (only `main`/`staging`/`docker_beta`), so both images pinned to `main@sha256:…` for reproducibility (re-pin on upgrade).
- **Floating major tags** — matomo `5-apache`, opnform/invoiceninja nginx `1`/`1.29`, clamav `1.4`. Pin specific (contrast: caldiy is digest-pinned).
- **`main` and `dev` diverged** — Dependabot bumps on `main`, app work on `dev`. Converge.

### Registry check (2026-08-16)

Every image reference in the tree resolved through its `.env.example` and compared
against its registry — 98 references. The script is in the session scratchpad and
is not part of CI; `scripts/ci/list-images.sh` covers 11 stacks by hand and is the
thing worth replacing with the discovery `check-structure.py` already has.

**Three comparisons in that run were wrong.** A comparison that parses only
numbers reads `2021.11.28` as newer than `2.8.1` (`apps/heimdall`), `20220121` as
newer than `260601` (`apps/photoprism`, which tags `YYMMDD`), and the build number
`511` as newer than `5.13.26` (`business/invoiceninja`). All three of those stacks
are current. A tag comparison has to reject a candidate whose scheme differs from
the pinned one.

**Acted on:**

| Stack | Was | Now | Why |
|---|---|---|---|
| `business/zammad` | `7.1.1-0036` | `7.1.2-0013` | 18 advisories published 2026-08-04, one critical |
| `apps/unifi` | `mongo:4.4` | `mongo:8.0` | 4.4 reached end of life in February 2024. The pin rested on a claim the image's own documentation contradicts — it supports 3.6–7.0 from UniFi 8.1 and 8.0 from 9.0, and this stack runs 10.x |

**Still behind, not acted on:**

- `business/opensign` runs `mongo:6.0`, which reached end of life in July 2025. What OpenSign supports has not been checked against upstream, so the version to move to is unknown.
- Database and runtime bases are a major behind in several stacks — PostgreSQL 16/17 against 18, MariaDB 10.11/11.4 against 12, Redis 7.4 against 8, Elasticsearch 8.15 against 9. All of these are on supported branches; being behind is not the same as being unsupported, and a database major is a migration rather than a pin change.
- Roughly a dozen stacks are one minor or patch behind. Nothing there is security-driven as far as this check can tell.

**The check is incomplete.** Docker Hub rate-limits after about a hundred tag
queries, so the run degraded partway through and the figures above cover what
completed. Re-running it needs either pacing or an authenticated token.

### Sweep status (2026-07-26)

**Verified current (no action):** it-tools · beszel(+agent) · monicahq 4.1.2 · photoview 2.4.0

**Bumped this session (3rd wave):** easyappointments 1.6.0 · lychee v7.7.1 · librephotos 2026w25 · heimdall v2.8.1 · homepage v1.13.2 🚧 · opnform 2.2.2 🚧

**4th wave applied:** matomo `5.12.0-apache` (was floating `5-apache`) · adminer **5.5.0** 🚧 (major 4→5) · unifi **10.4.57** · dockhand **v1.0.39**.

**Verified current (no action):** it-tools · beszel(+agent) · monicahq · photoview · whoami v1.11.0 · dnsmasq 2.90-r3 · hawser 0.2.39.

**Operator-owned (you version these — no registry check):** vikunja (local build `vikunja-local`) · acme-certs (`ghcr.io/rubennati/cert-ops-tool`) · seafile / seafile-pro (proprietary).

**Genuinely open — awkward tag scheme, decide before pinning:**

- zammad — scheme decided: pin `X.Y.Z-NNNN` at the **highest** build of the target release. A release
  keeps receiving builds after it ships, so the first build of a version is not the version. Now at
  `7.1.2-0013`.
- uptime-kuma — `2.4.0` exists but 1.x→2.x is a major transition; verify before leaving `1.23.17`.

The sweep is otherwise complete: every registry-checkable service is verified or bumped.

---
