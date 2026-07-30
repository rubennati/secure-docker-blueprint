# Borgmatic

> **Status: ✅ Ready** — v2.1.6 · 2026-07-29 · backup and restore both performed
> on a live host; the rehearsal is logged in [`RESTORE.md`](RESTORE.md#rehearsal-log)

Host-installed backup for the stacks in this blueprint. Borg does the deduplicated, encrypted, append-capable storage; Borgmatic adds scheduling, retention, database dumps and monitoring on top.

**Why this directory has no `docker-compose.yml`:** the agent runs on the host, not in a container. A containerised agent would need read access to every volume — and therefore every secret — in the deployment. The reasoning is in [`../README.md`](../README.md#where-the-backup-agent-belongs).

| File | Purpose |
|---|---|
| [`config.yaml.example`](config.yaml.example) | Sources, targets, retention, database hooks, monitoring |
| [`borgmatic.timer.example`](borgmatic.timer.example) | systemd schedule — only if the package ships none |
| [`RESTORE.md`](RESTORE.md) | The rehearsal, and the real thing |
| [`ops/verify.sh`](ops/verify.sh) | What the newest archive actually contains — and what it must not |
| [`ops/browse.sh`](ops/browse.sh) | Mount an archive and read it as a directory tree |

---

## Requirements

- **Borgmatic ≥ 2.0.8** — earlier versions have no `container:` option for databases, and the v2 configuration format differs from v1. Check with `borgmatic --version`.
- **A client for every database engine you back up, on the host.** `mariadb-client`, `postgresql-client`, `mongodb-database-tools` as applicable. See [Databases](#databases). The dump command runs on the host, so a missing client fails the backup of that engine.
- **`python3-llfuse`**, if you want to browse an archive rather than extract from it. `borg mount` fails without it; `list` and `extract` do not need it.
- An SSH-reachable target. Any provider offering SSH/SFTP storage works; so does another machine you control.
- Root on the Docker host.

## Setup

**1. Install**

Check what your distribution offers before installing it — the packaged version is frequently older than the requirement above. Debian 13 ships 1.9.14, which predates the `container:` option entirely:

```bash
apt-cache policy borgmatic
```

If it is below 2.0.8, install from PyPI instead. This is what upstream recommends and what was used here:

```bash
sudo apt install pipx
sudo PIPX_HOME=/opt/pipx PIPX_BIN_DIR=/usr/local/bin pipx install borgmatic
borgmatic --version                 # must be >= 2.0.8
```

`PIPX_BIN_DIR=/usr/local/bin` matters: borgmatic runs as root from a systemd timer, and a default pipx installation lands in a user's `~/.local/bin`, which root's `PATH` does not include.

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

Do not confuse this with the `container:` option on a database entry — different mechanism, same word. That one names the container to dump *from*; this one names where a credential is read.

The file source is what makes this fit the blueprint cleanly: point it straight at the `.secrets/*.txt` file the stack already mounts as a Docker secret.

```yaml
password: "{credential file /srv/docker/apps/myapp/.secrets/db_pwd.txt}"
```

One copy of that password exists on the host. Borgmatic reads the same file Docker does, nothing is exported into its environment, and rotating the secret needs no second edit. It also strips a trailing newline itself — the failure this repository otherwise guards against with `| tr -d '\n'` everywhere.

## Ransomware — what append-only actually gives you

Restrict the backup key on the **target** to append-only, in that user's `~/.ssh/authorized_keys`:

```text
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

Two of these are scripted, because they are the ones worth running often enough
to mistype:

```bash
sudo ops/verify.sh /srv/docker /srv/other-deployment
```

Prints the database dumps in the newest archive with their sizes, asserts the
first path is present, and asserts the second is absent — the check that catches
a configuration reaching further than intended. Exits non-zero on either
failure, so a monitoring hook can call it.

```bash
sudo ops/browse.sh          # mount at /mnt/borg
sudo ops/browse.sh --umount
```

The rest by hand:

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
| PostgreSQL · MySQL · MariaDB · SQLite | 24 · 16 · 13 stacks, plus several SQLite | `container:` dump hook, plus that engine's client on the host |
| MongoDB | `apps/unifi`, `business/opensign` | `container:` dump hook, plus the MongoDB tools on the host |
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

### What `container:` actually does

It resolves the container's IP address through `docker inspect`. That is all. The dump command then runs **on the host** and connects to that address over TCP.

So it removes the need to publish database ports, and it does not remove the need for the client:

```text
[Errno 2] No such file or directory: 'mariadb-dump'
```

The alternative upstream documents is `mariadb_dump_command: docker exec …`, running the dump inside the container. It is not the default here, because borgmatic passes credentials through a defaults-file on the host that a container cannot see — making it work means also switching `password_transport` and forwarding the variable into the container.

### Version skew is a real failure, not a theoretical one

The host client comes from the distribution; the server version is pinned per stack. On Debian 13 that pairs an 11.8 client with, for example, a 10.11 server, and the newer client requires TLS the older server does not offer:

```text
TLS/SSL error: SSL is required, but the server does not support it
```

For a connection from the host to a container on a local bridge, `tls: false` on the database entry is the proportionate answer — the traffic never reaches a network. Where the database is genuinely remote, configure TLS on the server instead.

### Before you need them

**Restore is destructive**, and **the target database must already exist** — Borgmatic will not create it.

### More than one deployment on a host

`source_directories` and `container:` are matched literally, and a host running two deployments will have two sets of similar names. State full paths and exact container names rather than patterns, then prove the scoping by searching the archive for something that must *not* be in it:

```bash
sudo borgmatic list --archive latest --find '*other-deployment*' | grep -v '^local:'
```

An empty result is the evidence. Quiescing hooks deserve the same care: `docker exec <exact-container>` cannot resolve to the wrong project, `docker compose` can.

Borgmatic writes its own configuration into the archive so the credentials needed for a restore travel with the backup. That is deliberate, and it is another reason the archive must stay encrypted.

## Known limitations

- **Exercised against a local repository, not an SSH target.** Backup, archive inspection and restore have all been performed; the target was a directory on the same host. The SSH path and append-only enforcement are still written rather than proven.
- **Prune under append-only fails by design.** Plan where retention runs before enabling it.
- **`/var/lib/docker/volumes` read live.** Fine for ordinary files, not for databases — which is what the dump hooks are for. Verify your Docker root with `docker info --format '{{.DockerRootDir}}'`; rootless and custom data-root setups differ.
- **One host, one configuration.** Per-app repositories are possible via `/etc/borgmatic.d/` but are not the starting point — see [`../README.md`](../README.md#per-app-separation--an-option-not-a-rule).
