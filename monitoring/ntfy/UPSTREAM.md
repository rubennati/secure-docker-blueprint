# Upstream Reference

## Source

- **Project:** https://ntfy.sh
- **Documentation:** https://docs.ntfy.sh
- **GitHub:** https://github.com/binwiederhier/ntfy
- **Docker Hub:** https://hub.docker.com/r/binwiederhier/ntfy
- **License:** Apache-2.0 / GPL-2.0 (dual-licensed)
- **Use restrictions:** none — the repository carries both `LICENSE` (Apache-2.0) and `LICENSE.GPLv2`, and neither restricts commercial or hosted use — https://github.com/binwiederhier/ntfy · checked 2026-09-21
- **Decision facts checked:** 2026-09-21
- **Origin:** Germany · Philipp Heckel · EU
- **Domain:** Monitoring
- **Role:** Push notifications over HTTP, the receiving end for every other alert
- **Upstream reviewed:** 2026-07-27 — image, tag, configuration surface, channel
  support and licence checked against upstream documentation
- **Last verified:** 2026-11-08 (2.37.2) — over IPv4: a publisher account with read-write on one topic, a message published and polled with it, anonymous reads and publishing from the refused client answered `403`, the message kept after `down`/`up` (docs/labs/stack-refresh/2026-11-08-results.md)
  `read_only` holding, deny-all proven, users and grants from the CLI, an
  iPhone outside the tailnet subscribed through the public router, one message
  delivered to it.

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

## Version notes

- Moved to `v2.37.2` on 2026-11-05 (released 2026-11-04). No `server.yml` key is removed or
  renamed between v2.28.0 and v2.37.2, so `config/server.yml` needs no change.
  What changes underneath it:
  - v2.31.1 migrates the message cache schema from 16 to 17 at first start;
    going back to v2.31.0 or older needs the version set back by hand, and
    v2.32.0 makes an older ntfy refuse a database a newer one migrated in a
    breaking way. Back up `volumes/` before the move.
  - v2.31.0: a reconnect with `since=<message ID>` also returns messages from the
    same second, so a polling script may see duplicates.
  - v2.36.0 validates the whole configuration at start when `base-url` is set
    (it is here), so an invalid `server.yml` now stops the container instead of
    starting; daily usage counters reset once at the upgrade.
  - v2.37.0: UnifiedPush to a topic with no subscriber for four days answers
    `410` instead of `507`; responses carry `Retry-After` and `RateLimit`
    headers.
  - Security: v2.34.0 ends a user's subscriptions when access is reset or the
    user is deleted; v2.35.0 rejects Matrix push-gateway requests with invalid
    push keys, which on SQLite could store messages under a protected topic;
    v2.33.1 is built with Go 1.27.3, limits a subscription to 150 topics and
    fixes an "Illegal instruction" crash on amd64 CPUs without x86-64-v3.
  - Experimental clustering (v2.30.0 onwards) stays off; upstream says it is
    not ready for production.
  https://github.com/binwiederhier/ntfy/releases
- Moved to `v2.38.1` on 2026-11-23 (released 2026-11-16). No `server.yml` key is removed or
  renamed, and the message cache needs no migration. Both releases fix denial of service in
  message templating, which any client allowed to publish can use with `X-Template: yes`:
  v2.38.0 caps the string `replace`, `regexReplaceAll` and `join` build, which a crafted
  template could grow until the server ran out of memory; v2.38.1, a security release, checks
  values before printing them, enforces the execution deadline inside a single action, limits
  regular expressions, `cat`, `toPrettyJSON`, `concat`, `keys`, `uniq` and the sequence
  functions. v2.38.1 also stops slow S3 attachment uploads and unresponsive web push endpoints
  from holding memory and connections, and counts the web push subscription limit per IP
  prefix instead of per address; this stack keeps attachments on disk and sets up no web
  push, so those two do not reach it. v2.38.0 is built with Go 1.27.4. Upstream published no
  advisory ID for these fixes.
  - Breaking for templates: `printf` takes only plain directives (no argument indexes, no
    `%p`, no lists or dicts), and `html`, `js` and `urlquery` are no longer allowed. This
    stack ships no template directory; a publisher whose inline template uses one of those
    functions now gets `400` (ntfy error 40044) and has to change the template.
  - v2.38.0 shares rate limits across cluster nodes; clustering stays off here.
  - An instance upgraded from v2.37.2 with a user and cached messages keeps both: the poll
    returns the old messages, the admin account answers, an inline template still renders
    and one calling `html` is refused with `400` (local stack, 2026-11-23).
  Sources: https://github.com/binwiederhier/ntfy/releases/tag/v2.38.0,
  https://github.com/binwiederhier/ntfy/releases/tag/v2.38.1
- Moved to `v2.38.2` on 2026-11-26 (released 2026-11-24), a security release
  (https://github.com/binwiederhier/ntfy/releases/tag/v2.38.2): go-smtp 0.17.0 →
  0.26.0 (GO-2026-7029, memory exhaustion through `BDAT`) — incoming mail must now
  end its lines with CRLF, which matters only with the SMTP server on (off here);
  every `X-Forwarded-For` line is read, so a client can no longer forge its address
  past the rate and login limits behind a proxy that appends a second line; wildcard
  access entries such as `alerts_*` now also block reservations of the topics they
  cover, and a tier with a reservation limit of 0 reserves nothing (0 meant
  unlimited). No `server.yml` key changes. Messages cached under v2.38.1 are served
  after the upgrade, and publishing works.

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
