# Upstream Reference

## Source

- **Project:** https://www.urbackup.org/
- **GitHub:** https://github.com/uroni/urbackup_backend
- **Image:** https://hub.docker.com/r/uroni/urbackup-server
- **License:** AGPL-3.0-or-later — self-hosting for personal or commercial use is explicitly permitted
- **Origin:** Germany · Martin Raiber (uroni) · EU
- **Based on version:** `2.5.x` series, digest `sha256:e2fdc0d5…` (published 2026-04-23)
- **Last verified:** `__REPLACE_ME__`

> Not yet verified on a host. The date is set only once a client has been backed
> up and a restore confirmed — see `README.md` "Verify on first deploy".

## What we use

- `uroni/urbackup-server`, digest-pinned. The image is published by the UrBackup
  author but is **not** listed as an official image on urbackup.org, which names
  only Windows, Linux, FreeBSD and NAS packages. Treat it as author-maintained
  rather than officially released.
- No database container — UrBackup keeps its own SQLite database under
  `/var/urbackup`.
- Bridge networking with the web interface behind Traefik. Host networking is an
  opt-in overlay, not the default.

**Tag scheme:** upstream ships rolling series tags (`2.5.x`, `latest`) with no
exact semver. `2.5.x` and `2.5.x-btrfs` resolve to the same digest — btrfs
support is in the default image; only `-zfs` differs. Because the tags move, the
digest is what pins this. Re-resolve it on every upgrade:

```bash
docker buildx imagetools inspect uroni/urbackup-server:2.5.x --format '{{.Manifest.Digest}}'
```

## What we changed vs. upstream examples

| Change | Reason |
|--------|--------|
| Bridge networking instead of `network_mode: host` | Upstream's compose example uses host networking. That removes network isolation and rules out Traefik. Manual client addition works without it, because the server initiates the connection to the client — only broadcast discovery needs the host namespace. Available as `network-host.yml` for those who want it. |
| Web interface behind Traefik with `acc-tailscale` | The interface indexes every client's files and can trigger restores. It is an administrative surface and does not belong on the public internet by default. |
| `no-new-privileges:true` + `cap_drop: ALL` | Blueprint baseline. |
| `SYS_ADMIN` commented out | Upstream enables it for btrfs storage. Off unless the backup volume is btrfs and that mode is in use. |
| Port 55415 not published | Only needed for clients reaching the server over the internet. Publish deliberately, not by default. |
| Resource limits set | Upstream sets none. Starting values, to be retuned from measurement. |

## Known deviations from the security baseline

| Deviation | Why |
|---|---|
| No `user:` directive | The server writes client files while preserving their ownership and permissions. Forcing a UID breaks restores of files owned by other users. |
| No `read_only: true` | The server maintains its own database and a large writable backup tree. |

Both are inherent to what a backup server does, not oversights. `cap_drop: ALL`
and `no-new-privileges` still apply.

## Upgrade checklist

1. Check the [release notes](https://www.urbackup.org/download.html) for breaking changes
2. Check the GitHub Security tab for advisories against the current version
3. Re-resolve the digest for the series tag (command above)
4. Back up `./volumes/database` before upgrading — it holds the client index
5. Bump `APP_TAG` in `.env`, then `docker compose pull && docker compose up -d`
6. Confirm existing clients still appear and a browse of an old backup works
7. Update **Based on version** here — and **Last verified** only if the upgrade
   was actually exercised

## Useful commands

```bash
docker compose logs app --follow
docker compose exec app urbackupsrv --help
```

## Known limitations

- **Image backup is Windows-only.** Bare-metal restore of a whole disk applies to
  Windows clients. macOS and Linux clients do file-level backup.
- **Not officially containerised.** The image is author-maintained; the project
  itself distributes packages, not containers.
- **Broadcast discovery needs host networking.** Without it, add clients by
  hostname or IP.
