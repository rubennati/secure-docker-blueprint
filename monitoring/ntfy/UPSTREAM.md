# Upstream Reference

## Source

- **Project:** https://ntfy.sh
- **Documentation:** https://docs.ntfy.sh
- **GitHub:** https://github.com/binwiederhier/ntfy
- **Docker Hub:** https://hub.docker.com/r/binwiederhier/ntfy
- **License:** Apache-2.0 / GPL-2.0 (dual-licensed)
- **Origin:** Germany · Philipp Heckel · EU
- **Based on version:** `v2.26.3` (released 2026-07-20)
- **Upstream reviewed:** 2026-07-27 — image, tag, configuration surface, channel
  support and licence checked against upstream documentation
- **Last verified:** `__REPLACE_ME__`

> `Last verified` stays unset on purpose. It is ✅ criterion 8 and what CI reads,
> and it means one thing only: this stack ran on a clean install. Reviewing
> upstream documentation is not that, which is why the review carries its own
> line above.

## What we use

- Official `binwiederhier/ntfy` image, `serve` command
- File-based configuration (`config/server.yml`) — one place for every setting,
  rather than splitting between file and `NTFY_*` environment variables
- SQLite for the message cache and the user database — no database server
- Traefik labels for HTTPS routing

## What we changed vs. upstream examples

| Change from upstream | Reason |
|---|---|
| **Traefik labels instead of `-p 80:80`** | Blueprint routing standard |
| **`auth-default-access: deny-all`** | Upstream defaults to read-write, which makes every topic world-readable and world-writable once the server is public |
| **`behind-proxy: true`** | Traefik terminates TLS; without it, rate limiting sees only the proxy address |
| **`security_opt: no-new-privileges:true`, `cap_drop: ALL`** | Baseline hardening |
| **`read_only: true` + tmpfs** | Container should not write outside its mounted state |
| **Config mounted `:ro`** | Container should not modify its own configuration |
| **`user:` commented rather than set** | Upstream documents a UID/GID example but requires the mounted paths to be chown'd first; enabling it blind starts a server that cannot write |
| **Separate `volumes/lib` for `auth-file`** | Upstream examples keep only `/var/cache/ntfy`; the user database belongs on a path with different backup value |

## Configuration

Everything lives in `config/server.yml`. The settings that matter most:

| Setting | Why it matters |
|---|---|
| `base-url` | Must match the routed host and be https — attachment links and subscribed devices are pinned to it |
| `auth-default-access` | The control that makes public exposure defensible |
| `behind-proxy` | Real client address for rate limiting |
| `upstream-base-url` | Required for iOS instant notifications; sends only a message ID and a SHA256 checksum of the topic URL upstream, not message content |

See the [ntfy config reference](https://docs.ntfy.sh/config/) for the full list.

## Upgrade checklist

1. Check [ntfy releases](https://github.com/binwiederhier/ntfy/releases) — 2.x has
   been configuration-stable; read the notes for `server.yml` key changes anyway
2. Bump `APP_TAG` in `.env`
3. `docker compose pull && docker compose up -d`
4. Verify: `/v1/health` reports healthy, an existing subscription still receives,
   and a publish with an existing token still authenticates

## Diff against upstream

Upstream ships no compose file to diff against — the install page documents a
handful of `docker run` flags instead. What is worth re-checking on an upgrade is
the configuration surface, since `server.yml` is where the deviations live:

```bash
# Every setting the running image knows, with its default — compare against
# config/server.yml to spot keys that were added, renamed or removed upstream.
docker compose exec app ntfy serve --help

# The config keys this stack actually sets
grep -vE '^\s*(#|$)' config/server.yml
```

The two settings that must never silently revert to their upstream defaults are
`auth-default-access` (upstream: read-write) and `behind-proxy` (upstream: false).

## Useful commands

```bash
# Health endpoint (what the container healthcheck reads)
docker compose exec app wget -qO - http://127.0.0.1:80/v1/health

# List users and their per-topic grants
docker compose exec app ntfy user list
docker compose exec app ntfy access

# Publish a test message
docker compose exec app ntfy publish --user <user> alerts "test"
```
