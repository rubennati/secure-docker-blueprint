# Borgmatic

> **Status: 🚧 Preview** — v2.0.8+ · 2026-07-26 · configuration and procedure are written, **not yet exercised on a host**

Host-installed backup for the stacks in this blueprint. Borg does the deduplicated, encrypted, append-capable storage; Borgmatic adds scheduling, retention, database dumps and monitoring on top.

**Why this directory has no `docker-compose.yml`:** the agent runs on the host, not in a container. A containerised agent would need read access to every volume — and therefore every secret — in the deployment. The reasoning is in [`../README.md`](../README.md#where-the-backup-agent-belongs).

| File | Purpose |
|---|---|
| [`config.yaml.example`](config.yaml.example) | Sources, targets, retention, database hooks, monitoring |
| [`borgmatic.timer.example`](borgmatic.timer.example) | systemd schedule — only if the package ships none |
| [`RESTORE.md`](RESTORE.md) | The rehearsal, and the real thing |

---

## Requirements

- **Borgmatic ≥ 2.0.8** — earlier versions have no `container:` option for databases, and the v2 configuration format differs from v1. Check with `borgmatic --version`.
- An SSH-reachable target. Any provider offering SSH/SFTP storage works; so does another machine you control.
- Root on the Docker host.

## Setup

**1. Install**

```bash
sudo apt install borgmatic          # or the equivalent for your distro
borgmatic --version                 # must be >= 2.0.8
```

**2. Prepare the target**

Create a dedicated SSH key for backups — not your admin key.

```bash
sudo ssh-keygen -t ed25519 -N '' -f /root/.ssh/id_borg -C "borg backup $(hostname)"
sudo ssh-copy-id -i /root/.ssh/id_borg.pub backup-user@backup.example.com
```

**3. Set the passphrase**

```bash
openssl rand -base64 32 | tr -d '\n' | sudo tee /root/.borg-passphrase > /dev/null
sudo chmod 600 /root/.borg-passphrase
```

**4. Initialise the repository**

```bash
sudo BORG_PASSCOMMAND='cat /root/.borg-passphrase' \
  borg init --encryption=repokey-blake2 \
  ssh://backup-user@backup.example.com:22/./borg/$(hostname)
```

**5. Export the key — do not skip this**

```bash
sudo BORG_PASSCOMMAND='cat /root/.borg-passphrase' \
  borg key export ssh://backup-user@backup.example.com:22/./borg/$(hostname) \
  /root/borg-key-$(hostname).txt
```

Move that file **off this host** and store it with the passphrase. See [Keys](#keys) below.

**6. Configure**

```bash
sudo mkdir -p /etc/borgmatic
sudo cp config.yaml.example /etc/borgmatic/config.yaml
sudo chmod 600 /etc/borgmatic/config.yaml
sudo nano /etc/borgmatic/config.yaml
sudo borgmatic config validate
```

**7. First run**

```bash
sudo borgmatic create --verbosity 1 --list --stats
sudo borgmatic list
```

**8. Schedule**

```bash
systemctl list-unit-files | grep borgmatic     # units may already be packaged
sudo systemctl enable --now borgmatic.timer
systemctl list-timers borgmatic.timer
```

**9. Prove it** — go to [`RESTORE.md`](RESTORE.md). Until a restore has succeeded, this is not a backup.

---

## Keys

Two separate things are required to read the backup, and losing either loses everything:

| | Where it lives | Where a copy must also live |
|---|---|---|
| Repository key | inside the repository (`repokey` mode) | exported, off this host |
| Passphrase | `/root/.borg-passphrase` | with the exported key, or in a password manager |

Two rules that sound contradictory but are not:

1. **A compromise of this host must not hand over the backups.** So the key copy does not belong on this host, and the target should not accept deletion from it.
2. **Losing this host must not lose the key.** So a copy has to exist somewhere else — a password manager, an encrypted offline medium, print in a safe.

Store the passphrase and the exported key together. Separating them protects against nothing and doubles the chance of losing one.

## Credentials

Borgmatic never needs a password written into its configuration. It offers four credential sources — `file`, `container`, `systemd` and KeePassXC — and two matter here:

| Source | Syntax | Used for |
|---|---|---|
| **file** | `"{credential file /path}"` | everything in this setup |
| container | `"{credential container NAME}"` | reads Docker secrets from `/run/secrets` — **only works when borgmatic runs inside a container**, which it deliberately does not here |

The file source is what makes this fit the blueprint cleanly: point it straight at the `.secrets/*.txt` file the stack already mounts as a Docker secret.

```yaml
password: "{credential file /srv/docker/apps/myapp/.secrets/db_pwd.txt}"
```

One copy of that password exists on the host. Borgmatic reads the same file Docker does, nothing is exported into its environment, and rotating the secret needs no second edit. It also strips a trailing newline itself — the failure this repository otherwise guards against with `| tr -d '\n'` everywhere.

## Ransomware — what append-only actually gives you

Restrict the backup key on the **target** to append-only, in that user's `~/.ssh/authorized_keys`:

```
command="borg serve --append-only --restrict-to-path /home/backup-user/borg",restrict ssh-ed25519 AAAA... borg backup myhost
```

Understand precisely what this buys, because it is routinely overstated. From Borg's own documentation:

> "this only affects the low level structure of the repository, and running delete or prune or reading from the repository will still be allowed"

So a compromised client **can still make archives disappear** logically. What survives is the data: it is not physically removed, and you can roll back to an earlier transaction by removing segment files written after it. That recovery is manual, and it **only works while `borg compact` has not run**. Append-only is also not honoured by anything other than Borg — filesystem access to the repository bypasses it completely.

**Append-only buys delay and recoverability, not prevention.** Three things raise the bar further:

- **Retention runs somewhere else.** With append-only enforced, this host cannot prune. Run retention from the target, or with a second key that is not on this host.
- **Storage-level immutability** where the target offers it. Object Lock in *compliance* mode cannot be bypassed; *governance* mode can be, by anyone holding the bypass permission. They are not equivalent.
- **Notice quickly.** Every recovery path above expires — the monitoring hook is what makes the difference between a bad week and a total loss.

## Operating

```bash
sudo borgmatic create --stats     # run now
sudo borgmatic list               # archives
sudo borgmatic info               # repository size, last archive
sudo borgmatic check              # integrity (slow with the data check)
sudo borgmatic prune --stats      # apply retention (fails under append-only)
journalctl -u borgmatic -n 50     # what the last run did
```

## What connects to what

Borgmatic's integrations map onto stacks this blueprint already ships. This table is the reason the backup layer needs almost no new infrastructure:

| Borgmatic integration | In this repository | How it connects |
|---|---|---|
| PostgreSQL · MySQL · MariaDB · SQLite | 24 · 16 · 13 stacks, plus several SQLite | `container:` dump hook |
| MongoDB | `apps/unifi`, `business/opensign` | `container:` dump hook |
| Healthchecks | `monitoring/healthchecks` ✅ | `healthchecks.ping_url` |
| Uptime Kuma | `monitoring/uptime-kuma` ✅ | `uptime_kuma.push_url` |
| Zabbix | `monitoring/` — planned | available when that stack lands |
| btrfs · ZFS · LVM | host filesystem | borgmatic takes the snapshot itself |
| systemd | host | the scheduling timer |
| ntfy · Loki · Apprise · PagerDuty · Pushover · Sentry | not in this repository | external services, all optional |
| rclone · BorgBase | not in this repository | alternative storage targets |

Two of these change how the layers work:

- **Filesystem snapshots.** Borgmatic can take a btrfs, ZFS or LVM snapshot, back up from the frozen view, and discard it. That removes the "files changed while I was reading them" problem for the Docker volume directory — the one place file-level backup is otherwise weakest. Snapshots still are not backups; here one is used as a consistent *source* for the backup.
- **MongoDB.** Easy to miss because it is not in the usual list, but two stacks here run it.

## Databases

Five engines are covered natively — PostgreSQL, MySQL, MariaDB, SQLite and MongoDB — with the dump streamed into the archive. Add one entry per database in `config.yaml`, using `container:` to name the container.

Two things to know before you need them: **restore is destructive**, and **the target database must already exist** — Borgmatic will not create it.

Borgmatic writes its own configuration into the archive so the credentials needed for a restore travel with the backup. That is deliberate, and it is another reason the archive must stay encrypted.

## Known limitations

- **Not yet exercised on a host.** The configuration validates and the procedure is written; neither has run against a real target. That is what moves this from 🚧 to ✅.
- **Prune under append-only fails by design.** Plan where retention runs before enabling it.
- **`/var/lib/docker/volumes` read live.** Fine for ordinary files, not for databases — which is what the dump hooks are for. Verify your Docker root with `docker info --format '{{.DockerRootDir}}'`; rootless and custom data-root setups differ.
- **One host, one configuration.** Per-app repositories are possible via `/etc/borgmatic.d/` but are deliberately not the starting point — see [`../README.md`](../README.md#per-app-separation--an-option-not-a-rule).
