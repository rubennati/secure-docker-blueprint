# Upstream Reference

## Source

- **Repo:** https://github.com/Finsys/hawser
- **Docs:** https://github.com/Finsys/hawser/blob/main/README.md
- **Based on version:** 0.2.39
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

## Upgrade checklist

1. Check [Hawser releases](https://github.com/Finsys/hawser/releases)
2. Check if [PR #52](https://github.com/Finsys/hawser/pull/52) is merged → add socket-proxy
3. Bump `APP_TAG` in `.env`
4. `docker compose pull` → `docker compose up -d`
5. Verify health + Dockhand connection
