# UrBackup Server

Client and endpoint backup: laptops, desktops and other machines back up to storage **you** own — your server, your NAS — instead of a proprietary cloud. Clients exist for Windows, macOS and Linux.

This is the other half of [`backup/`](../README.md). [Borgmatic](../borgmatic/) backs up the Docker host; UrBackup backs up the machines around it. They do not overlap and neither replaces the other.

| | Borgmatic | UrBackup |
|---|---|---|
| Backs up | the server this blueprint runs on | your laptops, desktops, other machines |
| Runs | on the host | in Docker, here |
| Restore | files and databases | files, plus whole-disk on Windows |

Project, source, licence and origin: [`UPSTREAM.md`](UPSTREAM.md).

## Try it locally

Runs on `http://localhost:55414` without Traefik, DNS or a certificate.

```bash
cp .env.local.example .env.local
mkdir -p volumes/local/database volumes/local/backups
sudo chown 0:101 volumes/local/database volumes/local/backups
sudo chmod 775 volumes/local/database volumes/local/backups
docker compose -f docker-compose.local.yml --env-file .env.local up -d
# http://localhost:55414
docker compose -f docker-compose.local.yml --env-file .env.local down
```

## Setup

```bash
cd backup/urbackup
cp .env.example .env          # set the host, the storage path, the access policy
mkdir -p volumes/database volumes/backups
# The entrypoint writes here as root without DAC_OVERRIDE, the server as uid 101
sudo chown 0:101 volumes/database volumes/backups
sudo chmod 775 volumes/database volumes/backups
docker compose up -d
```

Then create the administrator account **before the host name is reachable by anyone else**. Until one exists, whoever reaches the interface first can create it. From the shell it needs no browser and no race:

```bash
docker compose exec -u 101 urbackup-app urbackupsrv reset-admin-pw -a admin -p '<password>'
```

After that an anonymous login is refused (lab host).

### Storage

`BACKUP_STORAGE_PATH` is where client backups land, and it grows without bound. Point it at the volume with room — an absolute path such as `/srv/backups/urbackup` is the normal case; the `./volumes/backups` default is only sensible for a small test.

> **Keep that path out of Borgmatic's `source_directories`.** Otherwise the host backup dutifully backs up every client backup, and the archive grows without limit for no gain.

### Adding clients

Install the client from [urbackup.org](https://www.urbackup.org/download.html), then add the machine in the web interface by hostname or IP. This works with the default bridge networking because the **server** opens the connection to the client, not the other way round.

## Networking

The default keeps the container on `proxy-public` with the web interface behind Traefik. That costs LAN broadcast discovery, which is why clients are added manually.

If you want auto-discovery:

```bash
docker compose -f docker-compose.yml -f network-host.yml up -d
```

Read [`network-host.yml`](network-host.yml) before you do — it drops Traefik routing and network isolation, leaving the interface on plain HTTP at the host address. Restrict it at the firewall or bind it to a VPN interface if you go that way.

| Port | Protocol | For |
|---|---|---|
| 55414 | TCP | web interface — via Traefik by default |
| 55413 | TCP | FastCGI backend for the web interface |
| 55415 | TCP | clients connecting over the internet — publish only if you have them |
| 35623 | UDP | broadcast discovery — outbound, needs host networking |

## Security notes

The web interface indexes every file on every client and can trigger restores. It is an administrative surface, so `APP_TRAEFIK_ACCESS` defaults to `access-vpn` (VPN-only). Changing it to `access-public` should be a deliberate decision, not a convenience.

Two baseline deviations are inherent to a backup server and documented in [`UPSTREAM.md`](UPSTREAM.md): no `user:` directive and no `read_only`, because the server must write client files with their original ownership and maintain a large writable tree. `cap_drop: ALL` and `no-new-privileges` still apply.

`SYS_ADMIN` is commented out in the compose file. Enable it only if the backup volume is btrfs and you use snapshot-backed storage.

## Verify on first deploy

Check on the first deploy:

- [x] Container starts and stays healthy — the image has neither `curl` nor `wget`; the healthcheck uses bash's `/dev/tcp` (lab host)
- [x] Web interface reachable through Traefik, TLS valid, access policy enforced (lab host)
- [x] Administrator account created with `urbackupsrv reset-admin-pw`; an anonymous login is refused (lab host)
- [x] One client added by address and a first full file backup completes — a Linux client 2.5.31 in an unprivileged LXC (lab host)
- [ ] A file restored from that backup and its content verified — the four backed-up files downloaded from the server matched their checksums, but the restore to the client stopped at the client's own check ("No permissions to create files") on the LXC client; not repeated on a VM or bare-metal client
- [ ] Resource limits survive a full backup without an OOM kill
- [ ] Storage path confirmed excluded from Borgmatic's sources

## Backup

Backing up a backup server sounds circular, and mostly it is — but not entirely.

| | |
|---|---|
| **Database** | SQLite inside the UrBackup data directory — no database server, no dump hook |
| **State** | the UrBackup database: which client backed up what, when, and where it landed |
| **Excluded — deliberately** | **`BACKUP_STORAGE_PATH`** — the client backups themselves |
| **Quiescing** | **Required.** Stop the container, or snapshot the filesystem, before copying the database. |

**`BACKUP_STORAGE_PATH` must not appear in borgmatic's `source_directories`.**
It holds every client backup this server has taken, already deduplicated by
UrBackup. Feeding it into a Borg repository re-deduplicates terabytes to no
benefit, and one oversight here can outgrow the backup target overnight.

What is worth capturing is the small part: the database that indexes the client
backups. Losing it does not lose the file data, but it does mean the web
interface no longer knows what exists — restores become a matter of reading the
storage tree by hand.

Verify the exclusion holds rather than assuming it:

```bash
sudo borgmatic create --dry-run --list | grep -c "$BACKUP_STORAGE_PATH"
```

Zero is the expected answer.

This stack is the second direction of `backup/` — it protects the machines around
the host, while `backup/borgmatic` protects the host. Neither backs up the other,
and neither is a substitute.

## Restore

Documented from upstream's administration manual, not yet runtime-verified
against this stack.

### The storage tree

A file backup is a plain copy of the client's tree under the backup storage path,
one directory per client, then one per run named `YYMMDD-HHMM` (newest last):

```bash
ls "$BACKUP_STORAGE_PATH/<client>"
cp -a "$BACKUP_STORAGE_PATH/<client>/<run>/<path>" /tmp/restored
```

Works without the web interface or a live UrBackup process. Upstream can also
export a run over SMB, FTP/SFTP or WebDAV for a client to pull from directly.

### The web interface

Files and directories download as a ZIP, capped by upstream at 4 GB. Pushing a
restore back to the client instead requires that client to be **online** — the
server asks it to confirm before it writes anything.

### The client

`urbackupclientctl browse` lists what the server holds for that machine;
`urbackupclientctl restore-start` begins the restore. On Windows, the tray icon
carries the same under "Access/restore backups".

### Image backups

Restore from a bootable Debian-based CD/USB, for Windows clients only.

## Known limitations

- **Whole-disk image backup is Windows-only.** macOS and Linux clients back up files.
- **The container image is author-maintained, not an official release** — the project distributes packages, not containers. See [`UPSTREAM.md`](UPSTREAM.md).
- **Rolling upstream tags.** `2.5.x` moves, so the pin is a digest and must be re-resolved on each upgrade.

## Open findings

<!-- findings:start — generated by scripts/ci/lifecycle-report.py from upstream-status.json; edit the text around it -->

**Findings in the upstream images** at the pin `2.5.x` — the newest upstream release. Scanned 2026-11-09; counted are findings with a published fix, as CRITICAL · HIGH. They come with the images as upstream publishes them.

| Image | Base system | Libraries | Programs |
|---|---|---|---|
| `uroni/urbackup-server:2.5.x@sha256:fd218c45192f…` | 4 · 19 | — | — |

<!-- findings:end -->

The pinned image, `uroni/urbackup-server:2.5.x`, ships with 4 CRITICAL vulnerabilities that have published fixes, in Debian 13's brotli and perl. The newest build, of 2026-08-30 (2.5.38), has not been rebuilt by upstream.

**Risk:** neither package is part of the backup protocol; brotli matters only if the server decompresses brotli data from a hostile server. Watch for the next build.
