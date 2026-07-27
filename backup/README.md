# Backup

Backup has two directions, and a self-hoster needs both:

- **This infrastructure** — the Docker host and everything it runs. Recovered with [Borgmatic](borgmatic/).
- **The machines around it** — your laptop, desktop, other servers, backed up *to* infrastructure you own instead of somebody's cloud. That is [UrBackup](urbackup/).

They solve different problems and neither replaces the other. Separate top-level category because backup is ops-cross-cutting (it touches every data-producing service) and needs hardware-close access — block devices, mount points, credentials for remote targets.

## Status

🛡️ Ops-ready · ✅ Ready · 🚧 Preview · 📋 Planned

`🛡️ Ops-ready` means a restore has actually been performed — no service holds it yet. Full definitions: [`docs/standards/status-model.md`](../docs/standards/status-model.md).

| Tool | Direction | Status | Notes |
|---|---|---|---|
| [Borgmatic](borgmatic/) | This host → off-site | 🚧 | **The documented default for server backup.** Host-installed; configuration and restore procedure written, not yet exercised on a host. |
| [UrBackup](urbackup/) | Your devices → this host | 🚧 | Client backup for Windows, macOS and Linux; whole-disk image restore on Windows. Configuration complete, not yet verified. |
| Kopia | either | 📋 | Deduplicating, with a web UI and native object storage. Its repository-server mode is interesting for client backup too — clients never hold the storage credentials. No database hooks, so server-side dumps would need scripting. Candidate for v0.8.0. |
| Bareos | This host → tape / regulated retention | 📋 | Enterprise: Director, Storage and File daemons. Kept on the list for operators under retention or audit obligations, but **deliberately not built out** — the complexity is not justified for the single-operator setups this blueprint targets. |

For *server* backup pick one deduplicating tool — Borgmatic or Kopia, not both. Two repositories means two retention policies and two things to verify, for no gain. UrBackup is not in that comparison; it does a different job.

---

## What this category covers, and where it stops

**In scope:** backup and restore of the stacks in this repository — which data matters, how to capture it consistently, where to put it, and how to prove a restore actually works.

**Out of scope:** business continuity management and incident response as disciplines — business impact analysis, crisis communication, emergency manuals, insurance. Those are referenced (see [Standards](#standards)) and left to dedicated frameworks. This category stays operational.

**One deliberate exception to the repository's scope:** everything else here treats the host as the operator's business and stays inside Docker. Backup does not, because backup is the one function that cannot sensibly live in a container — see below. Host-level guidance here is generic and never assumes a distro, filesystem, or provider.

---

## Three layers people conflate

Getting these mixed up is the single most common way to end up with no usable recovery.

| | Snapshot | Backup | Archive |
|---|---|---|---|
| **Examples** | btrfs, ZFS, LVM, hypervisor or provider snapshots | Borg/Borgmatic, Kopia, Restic | WORM object storage, tape, cold storage |
| **Protects against** | accidental change, a bad upgrade — rollback in seconds | disk failure, fire, theft, ransomware | long-term loss; legal and retention obligations |
| **Retention** | hours to days | weeks to months | years to decades |
| **Fails when** | the underlying storage is lost — the snapshot goes with it | the only copy sits where a compromised host can reach it | nobody ever verifies it is still readable |

A snapshot depends on the original. Lose the disk and you lose both. **A snapshot is not a backup**, no matter how convenient the rollback.

The same applies to a provider's built-in backup product with a short fixed retention — typically seven rolling days. It covers "the server broke on Tuesday". It does not cover data you discover missing three weeks later, and it does not cover ransomware that sat quietly before it triggered. Useful, but not a long-term backup and not an archive.

---

## Where the backup agent belongs

**On the host.** Installed as a package, scheduled by a systemd timer.

This is a deliberate exception to how everything else in this repository works, and the reasoning is specific to backup:

- **A container cannot reach what needs backing up.** It would need `/:/host:ro` or `--privileged` to see other stacks' data, the Docker volume directory, and host configuration.
- **That contradicts this blueprint's own security baseline.** A backup container with read access to every volume is a container that can read every secret in the deployment. The Portainer Agent's `/:/host:ro` mount is already documented as a deviation — backup should not become the second one.
- **It has to work when Docker does not.** A containerised agent cannot run if the daemon is down, which is exactly when you may need it.

The one thing that genuinely belongs in the container world is the **database dump** — and Borgmatic reaches into containers for that without the agent living there (see below). That is the hybrid: host agent for files and scheduling, container-aware hooks for application consistency.

> If you deliberately run a containerised agent anyway, scope its mounts to the specific volumes it must read, never mount the Docker socket, and keep `no-new-privileges` and `cap_drop: ALL`. Understand that its read access is the blast radius.

---

## The five layers in practice

| Layer | What it does | Where it runs |
|---|---|---|
| 0 · Snapshot | Fast local rollback | Host filesystem or provider — **explained here, not implemented by this repo** |
| 1 · Consistency | Database dumps before the file backup runs | Borgmatic hook, reaching into the container |
| 2 · File data | Bind mounts and named volumes | Host agent |
| 3 · Off-site | 3-2-1, encryption, immutability | Remote target |
| 4 · Proof | Restore rehearsal, integrity check, run monitoring | Host + `monitoring/` |

### Layer 1 — application-consistent database backups

Copying a running database's files at the file level can capture a torn, mid-transaction state. The backup reports success; you find out at restore. Always take a logical dump.

Borgmatic dumps natively for **PostgreSQL, MySQL, MariaDB, MongoDB and SQLite** — which covers every engine in this repository. Since **Borgmatic 2.0.8** it can address a database *inside a container* directly:

```yaml
postgresql_databases:
  - name: caldiy
    container: caldiy-db
```

Borgmatic asks Docker for the container's address and connects. No published ports, no database client tools installed on the host, no `docker exec` wrapper. Dumps stream straight into the archive through named pipes — no intermediate files with awkward permissions.

Restore is `borgmatic restore --archive latest --database <name>`. Two things to know before you need it: **restore is destructive** — it replaces the live database — and **the database must already exist**; Borgmatic does not create it.

Borgmatic includes its own configuration file in the archive, so the credentials needed for a restore travel with the backup. That is convenient and it means the archive must be encrypted.

> **Older Borgmatic, or a different tool:** publish the database port to `127.0.0.1` and point the hook at it, or run the dump in a `before_backup` hook via `docker exec`. If you use a hook, make it **fail loudly** — a dump command that errors while the backup continues produces an archive that looks fine and contains nothing. Kopia and Restic have no database hooks; there you script the dump yourself.

**Where the per-app detail lives.** Each app README carries a `## Backup` section — which database and container, which volumes hold state, which are reproducible, whether the app needs quiescing, and a copy-pasteable borgmatic block. The template is in [`apps/_reference/README.md`](../apps/_reference/README.md). That way `/etc/borgmatic/config.yaml` is assembled from the apps rather than reverse-engineered from their compose files at the moment someone needs a restore. `LIFECYCLE.md` reports which apps still lack it.

### Layer 2 — both volume types, no preference

The blueprint uses bind mounts under `./volumes/` for most stacks and named volumes for a few. **Both are valid** — Docker itself recommends named volumes for portability and notes they are not suited to direct host access. The backup has to handle whatever an operator already runs.

| | Bind mount | Named volume |
|---|---|---|
| **How to back it up** | Add the path to `source_directories` | Helper container: `docker run --rm --volumes-from <stack> -v /backup:/backup …`, or add the Docker volume directory to `source_directories` |
| **Caveat** | none — it is an ordinary directory | the storage path is Docker-internal and differs under rootless Docker or a custom data root; copying it while containers write can be inconsistent |

If you are building fresh and have the choice, bind mounts make host-level backup simpler. If you already run named volumes, use the helper-container pattern — that is a documented approach, not a workaround.

### Layer 3 — off-site, and what ransomware protection really buys

3-2-1: three copies, two media types, one off-site. The newer 3-2-1-1-0 adds one offline or immutable copy and *zero* unverified backups — that last digit is monitoring, and it is the part most often skipped.

**Borg's append-only mode is weaker than it is usually described.** Borg's own documentation is explicit:

> "this only affects the low level structure of the repository, and running delete or prune or reading from the repository will still be allowed"

So a compromised client **can** make archives disappear logically. What append-only buys you is that the data is not physically removed: you can roll back to an earlier transaction using the repository's transaction log, by deleting segment files written after it. That recovery is manual, and **it only works if `borg compact` has not run since**. Append-only is also "not respected by tools other than Borg" — anyone with filesystem access to the repository bypasses it entirely.

Treat append-only as **delay and recoverability, not prevention**. What actually raises the bar:

- **Put the repository where the client cannot reach it.** A pull architecture, or a target the production host holds no delete credentials for.
- **Immutability at the storage layer.** S3 Object Lock in *compliance* mode cannot be bypassed until retention expires. *Governance* mode can be bypassed by anyone holding the bypass permission — it is not equivalent.
- **Keep the key off the host.** With `repokey` encryption the key material lives in the repository; export it with `borg key export` and store it, plus the passphrase, somewhere the production host does not reach. Both are required to restore — a host compromise must not hand over the backups, and losing the host must not lose the key.
- **Notice quickly.** Every recovery path above depends on discovering the problem before compaction or retention erases the evidence.

### Layer 4 — proving it works

A backup nobody has restored is a hypothesis. Three distinct checks, often confused:

| Check | Answers | How |
|---|---|---|
| Did the job run? | scheduling, silent failure | Borgmatic pings a monitor on start/finish/failure |
| Is the archive intact? | bit rot, truncation | `borgmatic check` on a schedule |
| Does the data come back? | the only question that matters | restore rehearsal into a scratch environment |

Borgmatic has built-in integrations for **Healthchecks** and **Uptime Kuma** — both already in [`monitoring/`](../monitoring/README.md). The dead-man's-switch pattern is what catches the failure mode where the timer silently stopped weeks ago.

Set an **RPO** (how much data may be lost — this sets backup frequency) and an **RTO** (how fast you must be back — this sets what you keep ready). For a single-operator setup, writing down "at most 24 hours of data, back within a day" and then configuring to match is enough. Undefined objectives produce undefined backups.

---

## Staged adoption

Do not build all of this at once. In order of risk reduction per unit of work:

**Stage 1 — the floor.** Encrypted daily backup of application data and compose configuration to one off-site target. Database hooks enabled for every stack that has a database. Key and passphrase stored off the host. *At this point you have a backup.*

**Stage 2 — trust it.** A restore rehearsal, written down. `borgmatic check` on a schedule. A monitor that alarms when a run is missed. *At this point you know the backup works.*

**Stage 3 — harden it.** A second copy on different media. Append-only or storage-level immutability, configured with its real limits understood. *At this point ransomware costs you time instead of everything.*

**Stage 4 — retain it.** Archive tier for anything with a long-term or legal retention need, verified for readability rather than assumed.

Prioritise by what hurts most to lose: databases first, then configuration and application data, then anything reproducible.

---

## Anti-patterns

- **Snapshots sold as backups.** They complement backups; they never replace them.
- **Untested backups.** "Job succeeded" is not evidence. Only a restore is.
- **A hook that fails quietly.** A dump command that errors while the backup continues produces an archive that looks complete and restores nothing.
- **Key and data on the same host.** Then one compromise takes both.
- **Governance-mode Object Lock treated as immutable.** It can be bypassed by design.
- **Relying solely on a provider's short-retention backup.** It covers outages, not late discovery.
- **Append-only assumed to be deletion-proof.** See Layer 3.

---

## Per-app separation — an option, not a rule

Separate repositories per app give independent retention, surgical restore and independent failure. They also multiply the number of configurations, schedules and restore rehearsals — and a rehearsal you never run is worse than a shared repository you have actually restored from.

**Start with one host-level configuration covering everything.** Split out an app when it has a genuinely different retention requirement, or when its data is large enough that a shared schedule stops working. Borgmatic supports multiple configuration files for exactly this.

---

## Layout

Backup differs structurally from every other category here: the agent is installed on the host, so `backup/borgmatic/` holds configuration and procedure rather than a Compose stack.

```
backup/borgmatic/
├── config.yaml.example      # source directories, database hooks, retention, monitoring
├── borgmatic.timer.example  # systemd schedule
├── README.md                # setup, targets, key handling
└── RESTORE.md               # the rehearsal, step by step
```

A tool that does run in a container (Kopia's server mode, for instance) follows the normal stack layout with `docker-compose.yml` and `.env.example`.

---

## Standards

Useful for structuring a backup concept, and required if you fall under one of them:

| Framework | What it asks for |
|---|---|
| **BSI IT-Grundschutz CON.3** | A written data backup concept: what is backed up, how often, retained how long, and evidence that restore was tested. RPO per system. Backups automated and protected against unauthorised access. |
| **NIST SP 800-34** | Backup frequency and off-site storage derived from criticality; RPO and RTO defined separately from maximum tolerable downtime; recovery plans tested. |
| **ISO 22301** | Recovery objectives defined and exercised as part of business continuity. |
| **NIS2** | Backup management and disaster recovery named explicitly under business continuity — binding for essential and important entities. A private self-hoster is normally out of scope but the practices transfer. |

All four converge on the same four verbs: **plan, document, protect, test.** For a single operator that means a short written concept, automated encrypted backups, and a restore you have actually performed.

---

## Why backup is a top-level category

1. **Ops-cross-cutting** — it reads from every other service's data. Structurally unlike a user-facing app.
2. **Privileged access** — block devices, broad read access, remote credentials. Higher sensitivity than general apps.
3. **Remote targets** — an external network dimension that apps do not have.
4. **Consistent with `monitoring/`** — both are ops concerns with cross-stack visibility.
