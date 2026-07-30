# Upstream Reference

## Source

- **Homepage:** https://torsion.org/borgmatic
- **Repo:** https://projects.torsion.org/borgmatic-collective/borgmatic
- **Docs:** https://torsion.org/borgmatic/#documentation
- **License:** GPL-3.0-or-later
- **Origin:** Community · borgmatic-collective (Dan Helfman) · no single jurisdiction
- **Author:** Dan Helfman
- **Based on version:** `2.1.6`
- **Last verified:** 2026-07-29 (2.1.6)

### Borg, the storage engine underneath

- **Homepage:** https://borgbackup.readthedocs.io/
- **License:** BSD-3-Clause
- **Based on version:** `1.4.0` (Debian 13 package)

Borgmatic 2.x drives Borg 1.2 and 1.4. Borg 2 is not required and is not used
here.

## Why this directory has no compose stack

The agent runs on the host. A containerised agent would need read access to every
volume in the deployment, and therefore every secret. Reasoning in
[`../README.md`](../README.md#where-the-backup-agent-belongs).

Consequently there is no image to pin. What is pinned instead is the **minimum
version**: 2.0.8, the release that introduced the `container:` option the
database hooks depend on.

## Installation, and why not from the distribution

| Source | Version on Debian 13 | Usable |
|---|---|---|
| `apt install borgmatic` | 1.9.14 | No — predates `container:`, and the v1 configuration format differs |
| `pipx install borgmatic` | 2.1.6 | Yes |

Install into a system location so the systemd timer, running as root, can find
it:

```bash
sudo PIPX_HOME=/opt/pipx PIPX_BIN_DIR=/usr/local/bin pipx install borgmatic
```

## What the host also needs

A client for every database engine backed up. `container:` resolves the
container's IP through Docker; the dump command runs on the host and connects
over TCP.

| Engine | Package on Debian |
|---|---|
| MariaDB / MySQL | `mariadb-client` |
| PostgreSQL | `postgresql-client` |
| MongoDB | `mongodb-database-tools` |

This couples the backup to the distribution's client versions while each stack
pins its server independently — see the TLS note in
[`README.md`](README.md#version-skew-is-a-real-failure-not-a-theoretical-one).

## Upgrade checklist

1. Read the [release notes](https://projects.torsion.org/borgmatic-collective/borgmatic/releases).
2. `sudo pipx upgrade borgmatic`
3. `sudo borgmatic config validate` — the schema tightens between releases.
4. `sudo borgmatic create --dry-run --verbosity 1`
5. Re-run the rehearsal in [`RESTORE.md`](RESTORE.md) before relying on it again.

## Verified on

| Date | Version | What was exercised |
|---|---|---|
| 2026-07-29 | 2.1.6 | Configuration validated, first archive created with a MariaDB dump hook and maintenance-mode command hooks, archive contents inspected, database restored into a throwaway container and read back. Repository was local; the SSH target was not exercised. |
