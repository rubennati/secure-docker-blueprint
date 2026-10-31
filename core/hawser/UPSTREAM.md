# Upstream Reference

## Source

- **Repo:** https://github.com/Finsys/hawser
- **Docs:** https://github.com/Finsys/hawser/blob/main/README.md
- **License:** MIT
- **Decision facts checked:** not yet
- **Origin:** Finsys · **no country or legal entity stated** — no imprint on fnsys.pro
- **Domain:** Infrastructure
- **Role:** Remote Docker agent for Dockhand, connecting outbound so the managed host publishes no port
- **Based on version:** `0.2.53`
- **Last checked:** 2026-04-14

## What we changed and why

| Change | Reason |
|--------|--------|
| Socket-Proxy removed | Hawser hardcodes Unix socket, no TCP support yet ([PR #52](https://github.com/Finsys/hawser/pull/52) pending) |
| Docker Socket mounted directly | Only option until PR #52 is merged |
| Token via Docker Secret + entrypoint wrapper | Hawser has no `_FILE` support, but Go binary (no my_init) so wrapper works |
| Healthcheck from official docs | `/_hawser/health` endpoint, checks Docker connectivity |
| No Traefik labels | Edge mode = outbound WebSocket, not a web app |
| No network definition | Needs internet access for Dockhand connection, no internal services |

## Known limitations

- **No socket-proxy**: Hawser can't use TCP Docker connections yet. Monitor [PR #52](https://github.com/Finsys/hawser/pull/52). When merged, add socket-proxy back for defence-in-depth.
- **Docker Socket access**: Direct mount gives full Docker control. Dockhand's RBAC controls what actions are allowed through the UI.

## Quick Start

```bash
cp .env.example .env
nano .env  # Set DOCKHAND_SERVER_URL, AGENT_NAME

# Create token from Dockhand UI:
# Add Host → Hawser agent (edge) → Generate connection token
mkdir -p .secrets
echo -n 'your-token' > .secrets/hawser_token.txt

docker compose up -d
docker compose logs -f
```

## Verify

```bash
# Container healthy?
docker compose ps

# Health endpoint
docker exec hawser-app wget -qO- http://127.0.0.1:2376/_hawser/health
# Expected: {"status":"healthy","mode":"edge","connected":true}

# Check in Dockhand UI: host should appear as "connected"
```

## Version / tag notes

- **`0.2.46` changed the authentication default.** Authentication is now required;
  `ALLOW_INSECURE_NO_AUTH=true` restores the previous behaviour. This stack passes
  `HAWSER_TOKEN`, so the bump from `0.2.39` to `0.2.47` does not lock it out — a
  deployment that relied on the old default would be locked out.
- `0.2.47` restricts `/etc/hawser/config` to mode 0600. Moved on 2026-09-13.

## Version notes

- Moved to `0.2.53` on 2026-10-31 (released 2026-10-30), together with Dockhand
  v1.0.56, not run at this tag. 0.2.53 takes its settings from environment
  variables only, without `--port`, `--server` or `--token` flags — this stack
  configures the container through the environment already, so nothing changes;
  0.2.50 sets the `REQUEST_TIMEOUT` default to 30 s; 0.2.48 adds `TOKEN_FILE`, a
  way to hand the token over as a file instead of `HAWSER_TOKEN`, not adopted
  here yet; 0.2.49 adds `MAX_MESSAGE_SIZE_MB`; 0.2.52 passes `DOCKER_CONFIG` and
  `TMPDIR` through to compose and changes the systemd unit of the host install,
  which does not apply to the container. No advisory.

## Upgrade checklist

1. Check [Hawser releases](https://github.com/Finsys/hawser/releases)
2. Check if [PR #52](https://github.com/Finsys/hawser/pull/52) is merged → add socket-proxy
3. Bump `APP_TAG` in `.env`
4. `docker compose pull` → `docker compose up -d`
5. Verify health + Dockhand connection
