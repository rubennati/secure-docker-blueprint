# OWASP Threat Dragon

Threat modeling: draw data-flow diagrams and trust boundaries, record threats
against each element, document mitigations, and keep the model as a living
artifact rather than a one-off diagram. Functionally unrelated to every other
stack in this repository's Security category — it does not share, store or
transmit secrets at all.

```text
Architecture → Threat Dragon → Trust boundaries → Threats → Mitigations
```

## Where threat models live

Threat Dragon supports two storage modes, and this stack ships with the
simpler one active by default:

- **Local (default here)** — models are kept in the browser's own local
  storage. No server-side account, no OAuth app, no repository. This is
  enough to use the tool; models do not survive clearing browser data and do
  not sync across devices.
- **Git-backed (optional)** — models are read from and written to a real
  GitHub, GitLab or Bitbucket repository via OAuth. This needs a registered
  OAuth application with the provider and its client secret configured (see
  UPSTREAM.md for the exact variables per provider) — none of that is set up
  in this stack by default.

This container itself holds no threat-model data in either mode — it is
authentication and diagram-rendering middleware between your browser and
wherever the model actually lives.

## Services

| Service | Image | Purpose |
|---|---|---|
| threat-dragon-app | owasp/threat-dragon | Web UI + API (stateless) |

## Security model

- **Stateless** — no database, no volume. The container holds nothing
  between requests beyond in-memory session state.
- `read_only: true` + `cap_drop: ALL` with **no** `cap_add` — the image
  already runs as a fixed non-root user with no root-start entrypoint.
  Verified against a live container.
- **Real, generic `_FILE` secret support** — every environment variable this
  app reads (encryption keys, JWT signing keys, and any OAuth client secret
  you add) accepts a `<NAME>_FILE` counterpart — confirmed by reading
  upstream's env-loading source directly.
- **The image's own built-in healthcheck is broken in this release** — this
  stack overrides it with a working equivalent. See UPSTREAM.md.

## Setup

```bash
cp .env.example .env
# Edit: APP_TRAEFIK_HOST

mkdir -p .secrets
KEY_ID=$(openssl rand -hex 4)
KEY_VALUE=$(openssl rand -hex 32)
printf '[{"isPrimary": true, "id": "%s", "value": "%s"}]' "$KEY_ID" "$KEY_VALUE" \
  > .secrets/encryption_keys.txt
openssl rand -base64 48 | tr -d '\n' > .secrets/jwt_signing_key.txt
openssl rand -base64 48 | tr -d '\n' > .secrets/jwt_refresh_signing_key.txt

docker compose up -d
docker compose logs -f    # watch for "Express server listening at :: on port 3000"
```

Visit `https://<APP_TRAEFIK_HOST>` and open the New Model dialog to confirm.

## Backup

| | |
|---|---|
| **State** | None in this container in local-storage mode — threat models live in the browser, or in a Git repository if you configure the optional OAuth mode |
| **Reproducible** | Everything — the container itself is fully stateless |
| **Quiescing** | Not applicable |

No backup entry is needed for this stack in its default configuration. If
you enable Git-backed storage, the models are backed up wherever that
repository already is (GitHub/GitLab/Bitbucket) — not by this stack.

## Try it locally

```bash
cp .env.local.example .env.local   # fill the three encryption/signing values
docker compose -f docker-compose.local.yml --env-file .env.local up -d
# http://localhost:8080
docker compose -f docker-compose.local.yml --env-file .env.local down
```

## Verify on first deploy (Preview → Ready gate)

- [x] `docker compose config` clean; `docker compose up -d` — healthy — **verified locally, 2026-09-19**
- [x] `_FILE` secrets picked up correctly (no missing-required-property errors) and the app answers with a real HTTP response — **verified locally, 2026-09-19**
- [ ] A threat model actually created, diagrammed and saved through the web UI in local-storage mode
- [ ] Git-backed storage (GitHub/GitLab/Bitbucket OAuth) exercised end to end, if you enable it
- [ ] TLS and the chosen `APP_TRAEFIK_SECURITY` chain confirmed against the real domain

## Details

- [UPSTREAM.md](UPSTREAM.md) — source, upgrade checklist, deviations
