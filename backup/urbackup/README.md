# UrBackup Server

> **Status: 🚧 Preview** — 2.5.x · 2026-07-27 · config complete, **not yet verified on a live server**

Client and endpoint backup: laptops, desktops and other machines back up to storage **you** own — your server, your NAS — instead of a proprietary cloud. Clients exist for Windows, macOS and Linux.

This is the other half of [`backup/`](../README.md). [Borgmatic](../borgmatic/) backs up the Docker host; UrBackup backs up the machines around it. They do not overlap and neither replaces the other.

| | Borgmatic | UrBackup |
|---|---|---|
| Backs up | the server this blueprint runs on | your laptops, desktops, other machines |
| Runs | on the host | in Docker, here |
| Restore | files and databases | files, plus whole-disk on Windows |

## Setup

```bash
cd backup/urbackup
cp .env.example .env          # set the host, the storage path, the access policy
mkdir -p volumes/database
docker compose up -d
```

Then open the web interface and **create the administrator account immediately**. Until one exists, whoever reaches the interface first can create it.

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

The web interface indexes every file on every client and can trigger restores. It is an administrative surface, so `APP_TRAEFIK_ACCESS` defaults to `acc-tailscale` (VPN-only). Changing it to `acc-public` should be a deliberate decision, not a convenience.

Two baseline deviations are inherent to a backup server and documented in [`UPSTREAM.md`](UPSTREAM.md): no `user:` directive and no `read_only`, because the server must write client files with their original ownership and maintain a large writable tree. `cap_drop: ALL` and `no-new-privileges` still apply.

`SYS_ADMIN` is commented out in the compose file. Enable it only if the backup volume is btrfs and you use snapshot-backed storage.

## Verify on first deploy (Preview → Ready gate)

Everything below is unconfirmed. Each item must pass before this stack moves out of Preview:

- [ ] Container starts and stays healthy — **the healthcheck uses `curl`, which has not been confirmed to exist in this image.** Check with `docker exec <name> sh -c 'which curl wget'` and adjust the healthcheck if it is absent.
- [ ] Web interface reachable through Traefik, TLS valid, access policy enforced
- [ ] Administrator account created; anonymous access no longer possible
- [ ] One client added by hostname and a first backup completes
- [ ] A file restored from that backup and its content verified — not just the file's presence
- [ ] Resource limits survive a full backup without an OOM kill
- [ ] Storage path confirmed excluded from Borgmatic's sources

Once all pass: set `Last verified` in `UPSTREAM.md`, update the status here and in [`../README.md`](../README.md), and regenerate `LIFECYCLE.md`.

## Known limitations

- **Whole-disk image backup is Windows-only.** macOS and Linux clients back up files.
- **The container image is author-maintained, not an official release** — the project distributes packages, not containers. See [`UPSTREAM.md`](UPSTREAM.md).
- **Rolling upstream tags.** `2.5.x` moves, so the pin is a digest and must be re-resolved on each upgrade.
