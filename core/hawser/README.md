# Hawser

Remote Docker agent for [Dockhand](https://github.com/Finsys/dockhand). Deploy on each host that Dockhand should manage.

## Mode

**Edge Mode** (default): Agent connects outbound to Dockhand via WebSocket. No port opening needed, works behind NAT/Firewall/Tailscale.

## Quick Start

```bash
# 1. Copy and configure
cp .env.example .env
nano .env  # Set DOCKHAND_SERVER_URL, AGENT_NAME

# 2. Create token (from Dockhand UI: Add Host → Hawser agent (edge) → Generate)
mkdir -p .secrets
echo -n 'your-token' > .secrets/hawser_token.txt

# 3. Start
docker compose up -d
```

## Verify

```bash
docker compose ps                    # Should be healthy
docker exec hawser-app wget -qO- http://127.0.0.1:2376/_hawser/health
# {"status":"healthy","mode":"edge","connected":true}
```

Host should appear as connected in Dockhand UI.

## Security Note

Docker Socket is mounted directly — Hawser has full Docker access. Socket-proxy is not supported yet ([PR #52](https://github.com/Finsys/hawser/pull/52)). Access is controlled via Dockhand's RBAC.

## Details

- [UPSTREAM.md](UPSTREAM.md) — Upgrade checklist, known limitations
