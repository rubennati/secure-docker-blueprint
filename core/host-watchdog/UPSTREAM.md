# Upstream Reference

## Source

- **License:** Apache-2.0
- **Decision facts checked:** 2026-09-21
- **Origin:** First-party · this repository · no single jurisdiction
- **Domain:** Infrastructure
- **Role:** Optional host scripts that restart the Docker daemon or the proxy after a confirmed, sustained failure
- **Last verified:** 2026-11-09 (in-repo scripts) — lab host (VM): both watchdogs installed from the host-files manifest, `dockerd` and Traefik each frozen and restarted once after three confirmed checks, reported to Healthchecks, and the escalation held with the restarted service frozen again — after the three fixes the rehearsal found

No upstream project — both scripts are authored here and released as part of
Secure Docker Blueprint, under the repository's own license.

## Why this directory has no compose stack

Both scripts run on the host as root, invoked by a systemd timer — not in a
container. `docker-daemon-watchdog.sh` restarts the Docker daemon itself,
which a container cannot do for the daemon it depends on; `traefik-watchdog.sh`
needs `docker restart` on the Traefik container, the same host-level access
Borgmatic already has for its database hooks. Reasoning in
[`README.md`](README.md).

## What "verified" would mean here

There is no external release to track — changes to these scripts are recorded
in this repository's own `CHANGELOG.md`, and there is no upgrade path beyond
copying a newer version of the script and its `.example` files.

"Verified" means run on a real, disposable host: the confirmed-failure
threshold actually triggers the one recovery attempt, the attempt succeeds
where it should, the escalation path holds where it should not, and the
Healthchecks ping sequence matches what the README describes. Both scripts had
that rehearsal on the lab host on 2026-11-09 (README, "What this is not"); it
found three faults, fixed in the same change.

## Upgrade checklist

1. Read the diff in this repository's own history for the two scripts.
2. Re-copy the changed script(s) and any changed `.example` file to their
   installed locations.
3. `sudo systemctl restart <name>-watchdog.timer` — the service is a
   `oneshot`, so nothing needs restarting beyond the timer picking up the new
   binary on its next run.
4. Repeat the rehearsal in [`README.md`](README.md#what-this-is-not) before
   trusting the change.
