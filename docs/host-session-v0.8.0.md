# Host session — closing v0.8.0

Six monitoring stacks are configured and none has ever run. This is that work in one ordered run.

**Ordered by dependency, not by importance.** Block 1 is the receiver everything else alerts into, so it comes first — a monitor verified before there is anywhere for its alert to go has to be revisited. Blocks 3–5 are independent of each other.

> Update `docs/maintenance.md` (Progress Log) and each stack's `UPSTREAM.md` as you go, not afterwards from memory.

**Shares a precondition with v0.7.0.** Borgmatic's run monitoring pings Healthchecks or Uptime Kuma, so backup's proof layer depends on Block 2 here. If both sessions happen on the same host, do Block 1 and 2 before `backup/borgmatic` is switched on.

---

## Before you start

- [ ] Host reachable, Docker running, Traefik up with a working certificate
- [ ] A device that is supposed to receive alerts, with the ntfy app installed on it
- [ ] The receiver runs on **this** host. That is what verifies the chain; where it belongs in a real deployment is the adopter's call and is documented in [`monitoring/README.md`](../monitoring/README.md#where-the-receiver-runs), not decided here
- [ ] Decided: Uptime Kuma **or** Gatus for the uptime axis. Both is allowed, one is required

---

## Block 1 · ntfy — the receiver and the proven channel (~40 min)

Setup in [`monitoring/ntfy/README.md`](../monitoring/ntfy/README.md). This block produces the alerting evidence the milestone asks for.

- [ ] `cp .env.example .env`, `mkdir -p config`, `cp server.example.yml config/server.yml`
- [ ] `base-url` in `config/server.yml` matches `APP_TRAEFIK_HOST` in `.env`, and is **https**
- [ ] `docker compose up -d`, container reports healthy
- [ ] **Confirm `read_only: true` actually holds.** It is untested. If the container fails to start, read the log for the write target, add a tmpfs or a volume for it, and record why in the README
- [ ] Web interface reachable through Traefik, TLS valid
- [ ] `docker compose exec app ntfy user add --role=admin admin`
- [ ] `docker compose exec app ntfy user add monitoring` and `ntfy access monitoring alerts rw`
- [ ] **Confirm deny-all is in force:** open a topic URL unauthenticated and get refused. If anything is readable without credentials, `auth-default-access` did not apply — stop and fix it before this server stays reachable
- [ ] Subscribe the phone to the `alerts` topic
- [ ] `curl -u monitoring -d "test" https://<host>/alerts` — **the message arrives on the device**
- [ ] iOS only: notifications arrive but slowly or not in background → set `upstream-base-url`, restart, retest

**Watch for:** the rate limit. `sec-3` carries `rl-soft`, and a publisher bursting is exactly the incident case. If messages go missing under load, measure before switching profiles — the `-spa` variants are documented for VPN-gated apps only.

- [ ] Status → `✅` if every gate passed; `Last verified: YYYY-MM-DD (v0.8.0)` in `UPSTREAM.md`

## Block 2 · Healthchecks — the closed-circuit monitor (~40 min)

The scheduled-job axis, and the only service here that alerts on *absence*. Also the receiver for backup run monitoring, so v0.7.0 depends on it.

- [ ] Pending major version: `4.x`. If the v0.7.0 session already did it, skip ahead
- [ ] `docker compose up -d`, container healthy, interface reachable through Traefik
- [ ] Create a check with a short period and grace time
- [ ] Attach the ntfy integration to it, pointing at the topic from Block 1
- [ ] Ping it once — the check goes green
- [ ] **Then stop pinging and wait for the grace period to expire.** The alert must arrive on the device. This is the closed-circuit proof; a check that goes green proves nothing about the alarm
- [ ] Point `backup/borgmatic`'s run monitoring at a real check URL if v0.7.0 is being closed in the same session
- [ ] Status and `Last verified` updated

**Watch for:** `INTEGRATIONS_ALLOW_PRIVATE_IPS` defaults to false. If ntfy sits on a private address, webhook delivery is refused until it is enabled.

## Block 3 · Uptime Kuma or Gatus — the uptime axis (~40 min)

One of the two, not both. They are a preference pair.

- [ ] Pending major version if Kuma: `1.x → 2.x` is a real migration — take the database backup first
- [ ] `docker compose up -d`, container healthy, interface reachable
- [ ] Add one monitor against a service that is actually running
- [ ] Configure the ntfy notification on it
- [ ] **Stop the monitored container.** The down alert arrives on the device
- [ ] Start it again — the recovery alert arrives too. A channel that only fires one direction leaves you guessing
- [ ] Status and `Last verified` updated

## Block 4 · Beszel — the metrics axis (~40 min)

- [ ] Hub `docker compose up -d`, interface reachable through Traefik
- [ ] Agent added, the host appears with live CPU, memory and disk figures
- [ ] Per-container statistics visible — this is what distinguishes it from a plain host monitor
- [ ] Set a **disk usage** threshold deliberately low, so it fires
- [ ] Configure the ntfy notification — Beszel sends via Shoutrrr URLs and **has no email path**, so this is the channel
- [ ] The threshold alert arrives on the device, then reset the threshold to a sane value
- [ ] `monitoring/beszel-agent` verified on a second host if one exists; otherwise note it as untested and leave it 🚧
- [ ] Status and `Last verified` updated

**Watch for:** both images ship no healthcheck by design (`healthcheck: disable: true`). The hub UI is the liveness signal, and the hub itself is not covered by it — that gap is Block 2's job.

## Block 5 · changedetection.io — the content axis (~30 min)

- [ ] `docker compose up -d`, container healthy, interface reachable
- [ ] Add one watch against a page that changes predictably
- [ ] Configure the ntfy notification via the Apprise URL (`ntfy://…`)
- [ ] Trigger a change, or wait for one — the alert arrives on the device
- [ ] Status and `Last verified` updated

## Block 6 · Close the release

- [ ] Consistency Chain from `docs/maintenance.md`
- [ ] `python3 scripts/ci/check-baseline.py`, `check-structure.py` and `lifecycle-report.py --check` all clean
- [ ] `python3 scripts/ci/lifecycle-report.py --write`
- [ ] Record in `monitoring/README.md` under "Proving a channel works": **which channel was proven, and when**
- [ ] `CHANGELOG.md`: `[Unreleased]` → `[0.8.0]`, comparison links
- [ ] `ROADMAP.md`: v0.8.0 into "Shipped", "Last updated" bumped
- [ ] `README.md`: version badge → `v0.8.0`
- [ ] Progress Log row
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
