# Host session — closing v0.8.0

Six monitoring stacks are configured and none has ever run. This is that work in one ordered run.

**Ordered by dependency, not by importance.** Block 1 is the receiver everything else alerts into, so it comes first — a monitor verified before there is anywhere for its alert to go has to be revisited. Blocks 3–5 are independent of each other.

> Update `docs/maintenance-log.md` and each stack's `UPSTREAM.md` as you go, not afterwards from memory.

**Shares a precondition with v0.7.0.** Borgmatic's run monitoring pings Healthchecks or Uptime Kuma, so backup's proof layer depends on Block 2 here. If both sessions happen on the same host, do Block 1 and 2 before `backup/borgmatic` is switched on.

---

## Before you start

- [x] Host reachable, Docker running, Traefik up with a working certificate
- [x] A device that is supposed to receive alerts, with the ntfy app installed on it
- [x] The receiver runs on **this** host. That is what verifies the chain; where it belongs in a real deployment is the adopter's call and is documented in [`monitoring/README.md`](../monitoring/README.md#where-the-receiver-runs), not decided here
- [x] Decided: **Uptime Kuma** for the uptime axis. `monitoring/gatus` stays in the
      repository as the alternative and is not part of this milestone

---

## Block 1 · ntfy — the receiver and the proven channel (~40 min)

Setup in [`monitoring/ntfy/README.md`](../monitoring/ntfy/README.md). This block produces the alerting evidence the milestone asks for.

- [x] `cp .env.example .env`, `mkdir -p config`, `cp server.example.yml config/server.yml`
- [x] `base-url` in `config/server.yml` matches `APP_TRAEFIK_HOST` in `.env`, and is **https**
- [x] `docker compose up -d`, container reports healthy
- [x] **Confirm `read_only: true` actually holds.** It does (2026-09-07, v2.28.0). What did not hold was the process user: the image runs as root, and root with every capability dropped cannot write into a cache or auth directory the operator owns — `unable to open database file`. The commented `user:` line is now active with `APP_UID`/`APP_GID`, and the directories the operator creates are writable. It was untested before. If the container fails to start, read the log for the write target, add a tmpfs or a volume for it, and record why in the README
- [x] Web interface reachable through Traefik, TLS valid — TLS 1.3 and the router verified from the internet through the endpoints the app uses; the web app itself sits on the operator router (Tailscale) since the split below
- [x] `docker compose exec app ntfy user add --role=admin admin`
- [x] `docker compose exec app ntfy user add monitoring` and `ntfy access monitoring alerts rw`
- [x] **Confirm deny-all is in force:** open a topic URL unauthenticated and get refused. If anything is readable without credentials, `auth-default-access` did not apply — stop and fix it before this server stays reachable
- [x] Subscribe the phone to the `alerts` topic — an iPhone outside the tailnet, through a second, read-only public router (`GET` on the topic and `/v1/account` only; everything else stays `acc-tailscale`)
- [x] `curl -u monitoring -d "test" https://<host>/alerts` — **the message arrives on the device** (2026-09-08 00:05 UTC, published from the operator side; the public router refuses `POST` by design)
- [x] iOS only: notifications arrive but slowly or not in background → set `upstream-base-url`, restart, retest — set from the start; the message arrived

**Watch for:** the rate limit. `sec-3` carries `rl-soft`, and a publisher bursting is exactly the incident case. If messages go missing under load, measure before switching profiles — the `-spa` variants are documented for VPN-gated apps only.

- [x] Status → `✅` if every gate passed; `Last verified: YYYY-MM-DD (v0.8.0)` in `UPSTREAM.md` — `Last verified: 2026-09-08 (v2.28.0)`, the version in parentheses being what the lifecycle report reads

## Block 2 · Healthchecks — the closed-circuit monitor (~40 min)

The scheduled-job axis, and the only service here that alerts on *absence*. Also the receiver for backup run monitoring, so v0.7.0 depends on it.

- [x] Pending major version: `4.x`. If the v0.7.0 session already did it, skip ahead — pinned `v4.2` already; moved to the current `v4.4` before verifying, so the verification names a version that is not already behind
- [x] `docker compose up -d`, container healthy, interface reachable through Traefik — after `chown 999:999 volumes/data` (the README's known issue, confirmed) and with `INTEGRATIONS_ALLOW_PRIVATE_IPS` added, without which the ntfy integration could not target the Docker network
- [x] Create a check with a short period and grace time — period 1 min, grace 1 min
- [x] Attach the ntfy integration to it, pointing at the topic from Block 1 — server URL `http://ntfy-app` (the public router refuses `POST` by design), the publisher token, plus the email integration as a second channel into Mailpit
- [x] Ping it once — the check goes green — pinged from a container by the internal address; from the host, the ping URL sits behind `acc-tailscale`
- [x] **Then stop pinging and wait for the grace period to expire.** The alert must arrive on the device. This is the closed-circuit proof; a check that goes green proves nothing about the alarm — flipped to down at 22:30:58 UTC on 2026-09-07, ntfy and email delivered within a second, both on the iPhone; pinged again, the recovery arrived the same way at 22:31:33 UTC
- [ ] Point `backup/borgmatic`'s run monitoring at a real check URL if v0.7.0 is being closed in the same session — not in this session; the receiver it needs now exists
- [x] Status and `Last verified` updated — `Last verified: 2026-09-08 (v4.4)`

**Watch for:** `INTEGRATIONS_ALLOW_PRIVATE_IPS` defaults to false. If ntfy sits on a private address, webhook delivery is refused until it is enabled.

## Block 3 · Uptime Kuma — the uptime axis (~40 min)

- [x] `docker compose up -d`, container healthy, interface reachable — on `2.5.3` (pinned `2.4.0`); the image runs as root with Docker's default capabilities, not as uid 1000 as the README said
- [x] Add one monitor against a service that is actually running — TCP port monitor on a lab container (`obot-app:8080`), 20-second heartbeat, no retries
- [x] Configure the ntfy notification on it — `http://ntfy-app`, topic `alerts`, access token
- [x] **Stop the monitored container.** The down alert arrives on the device — down at 22:45:05 UTC on 2026-09-07, on the iPhone
- [x] Start it again — the recovery alert arrives too. A channel that only fires one direction leaves you guessing — up at 22:45:22 UTC, on the iPhone
- [x] Status and `Last verified` updated — `Last verified: 2026-09-08 (2.5.3)`

## Block 4 · Beszel — the metrics axis (~40 min)

- [x] Hub `docker compose up -d`, interface reachable through Traefik — on `0.19.0` (pinned `0.18.7`); the hub image runs as root; the README's service names were `hub` and `agent`, the hub's is `beszel-hub`
- [x] Agent added, the host appears with live CPU, memory and disk figures — public key derived from the hub's `id_ed25519` with `ssh-keygen -y`, agent on the host network, system registered at the Tailscale address as the README says
- [x] Per-container statistics visible — this is what distinguishes it from a plain host monitor — 38 containers in the first sample
- [x] Set a **disk usage** threshold deliberately low, so it fires — 1 % for 1 minute against a disk at 73 %
- [x] Configure the ntfy notification — Beszel sends via Shoutrrr URLs and **has no email path**, so this is the channel — `ntfy://monitoring:…@ntfy-app/alerts?scheme=http`, test notification on the iPhone
- [x] The threshold alert arrives on the device, then reset the threshold to a sane value — arrived on the iPhone on 2026-09-08; threshold back to 90 %
- [ ] `monitoring/beszel-agent` verified on a second host if one exists; otherwise note it as untested and leave it 🚧 — no second host; the agent that ran is the one inside `monitoring/beszel`, the standalone stack stays `scaffolded`
- [x] Status and `Last verified` updated — hub `Last verified: 2026-09-08 (0.19.0)`; the agent stack keeps its stamp

**Watch for:** both images ship no healthcheck by design (`healthcheck: disable: true`). The hub UI is the liveness signal, and the hub itself is not covered by it — that gap is Block 2's job.

## Block 5 · changedetection.io — the content axis (~30 min)

- [x] `docker compose up -d`, container healthy, interface reachable — on `0.60.3` (pinned `0.55.8`); runs as root; two example watches on external sites appear on first start
- [x] Add one watch against a page that changes predictably — a throwaway nginx page on `proxy-public`, which first failed with `Fetch blocked: … private/reserved IP address`: 0.60 guards against fetching internal addresses, now a switch (`CD_ALLOW_PRIVATE_ADDRESSES`, off by default)
- [x] Configure the ntfy notification via the Apprise URL (`ntfy://…`) — `ntfy://monitoring:…@ntfy-app/alerts`, test notification on the iPhone
- [x] Trigger a change, or wait for one — the alert arrives on the device — page changed at 23:16:25 UTC on 2026-09-07, notification sent 25 seconds later, on the iPhone
- [x] Status and `Last verified` updated — `Last verified: 2026-09-08 (0.60.3)`

## Block 6 · Close the release

- [x] Consistency Chain from `docs/maintenance.md` — no real hostnames in tracked files, `__REPLACE_ME__` only inside the checkers that look for it, links updated
- [x] `python3 scripts/ci/check-baseline.py`, `check-structure.py` and `lifecycle-report.py --check` all clean
- [x] `python3 scripts/ci/lifecycle-report.py --write` — 30 baseline-aligned, the five monitoring stacks among them
- [x] Record in `monitoring/README.md` under "Proving a channel works": **which channel was proven, and when** — five rows, one per stack, all 2026-09-08
- [x] `CHANGELOG.md`: `[Unreleased]` → `[0.8.0]`, comparison links — and the duplicated `Changed`/`Fixed` headings in the unreleased section merged
- [x] `ROADMAP.md`: v0.8.0 into "Shipped", "Last updated" bumped — the roadmap has no shipped section; shipped work belongs to the changelog, so the section is removed and the review date moved, as for v0.7.0
- [x] `README.md`: version badge → `v0.8.0`
- [x] `maintenance-log.md` row
- [ ] `git tag v0.8.0` and `gh release create v0.8.0 --draft`

---

## What "done" means

One verified service per axis, plus **one alerting channel proven to actually arrive on the device that is supposed to receive it**. Not configured — arrived.

Disk health is out of scope: Scrutiny needs physical-disk passthrough, which is host-specific.

Whether an alert also arrives while the sending host itself is down is a property of the deployment, not of this milestone. Verifying that means the receiver is not on the monitored host — the placement question Block 1 raises, answered where the deployment is.

## If time runs short

Do Blocks 1 and 2. Together they are the closed-circuit chain: something that notices absence, and somewhere the notice arrives. The observing monitors in Blocks 3–5 are the easier half and only work while they are running anyway.

## Feeding v0.9.0

Every container started in this session is a measurement opportunity, and v0.9.0 needs measured values rather than guessed ones. The procedure is in [`resource-measurement.md`](resource-measurement.md) — start the sampler before Block 1 and let it run through the session.
