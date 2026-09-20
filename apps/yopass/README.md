# Yopass

Ephemeral, zero-knowledge secret sharing. Yopass encrypts the secret in the
sender's browser before it ever reaches the server; the decryption key lives
only in the link's URL fragment, which a browser never sends to any server.
The server stores ciphertext with an expiration and cannot read it.

**What this is for:** a one-time or time-boxed link to hand someone a
password, API key or token — instead of pasting it into chat, email or a
ticket. **What this is not:** a place to store anything long-term, and not an
account system — nobody logs in.

## Sender-initiated vs. requested secrets

Yopass's normal flow is **sender-initiated**: you create the secret, you get
a link, you send the link. There is no way for someone else to ask you for a
credential and get a link *they* control.

That "secret request" flow — a recipient generates a link, an external
person fills in a secret without an account, the recipient later retrieves
it — is a real Yopass feature, but it is **Yopass Business, a licensed,
non-free product** (confirmed against the upstream README, 2026-09-19: listed
under business features as *"Collect a secret through an end-to-end
encrypted request link (license required)"*). It is not part of the
self-hosted open-source server this stack runs, and no configuration here
enables it. If you need that specific workflow without buying a license, see
[Hemmelig](../hemmelig/) — its self-hosted, non-commercial edition includes a
secret-request flow, with a different tradeoff (see its README).

## Services

| Service | Image | Purpose |
|---|---|---|
| yopass-app | jhaals/yopass | Web UI + API |
| memcached | memcached | Ephemeral secret store (TTL-based; no persistence by design) |

## Security model

- **Zero-knowledge**: encryption happens in the browser; the server only
  ever stores ciphertext and never sees the decryption key.
- **No accounts, no admin panel, no long-lived secret of its own** — there is
  nothing here to leak beyond whatever ciphertext is currently stored, and
  that expires on its own.
- One-time links are deleted after their first retrieval; every other link
  expires on its configured TTL. Memcached enforces this itself — there is no
  cleanup job to run or forget.
- `read_only: true` + `cap_drop: ALL` on both containers, with **zero**
  `cap_add` — the Yopass image already runs as a fixed non-root UID
  (distroless build) and Memcached's official image already starts as its
  own service user. Verified against live containers; neither needed a
  capability re-added.
- Memcached has no host port and is not on `proxy-public` — only `yopass-app`
  can reach it.

## Setup

```bash
cp .env.example .env
# Edit: APP_TRAEFIK_HOST

docker compose up -d
docker compose logs -f    # watch for "Starting yopass server"
```

Visit `https://<APP_TRAEFIK_HOST>` and create a secret to confirm.

## Optional: Argon2 key derivation

Yopass supports memory-hard Argon2id key derivation for password-protected
secrets (`--argon2` flag). This repository does not enable it by default: it
requires the `'wasm-unsafe-eval'` Content-Security-Policy directive, which
means any Traefik middleware in front of this app that replaces the CSP
header (rather than only adding to it) would break it. Enabling it means
adding `ARGON2: "true"` to the `environment:` block and confirming the
active `APP_TRAEFIK_SECURITY` chain does not strip that directive — not
verified against this repository's own `sec-*` chains.

## Backup

| | |
|---|---|
| **State** | None. Every value in Memcached carries its own TTL and is not meant to survive a restart. |
| **Reproducible** | Everything — a fresh container with no data is the expected steady state whenever nothing is mid-flight. |
| **Quiescing** | Not applicable — there is nothing to dump. |

No backup entry is needed for this stack. A secret in flight during a
restart is lost, which matches its own stated lifetime guarantees (Yopass
never promised delivery across a server restart).

## Try it locally

```bash
cp .env.local.example .env.local
docker compose -f docker-compose.local.yml --env-file .env.local up -d
# http://localhost:8080
docker compose -f docker-compose.local.yml --env-file .env.local down
```

## Verify on first deploy (Preview → Ready gate)

- [x] `docker compose config` clean; `docker compose up -d` — both healthy — **verified locally, 2026-09-19**
- [x] `GET /` returns 200 — **verified locally, 2026-09-19**
- [ ] A secret created and retrieved once through the actual web UI (not just the API) behind Traefik on a real host
- [ ] TLS and the chosen `APP_TRAEFIK_SECURITY` chain confirmed against the real domain

## Details

- [UPSTREAM.md](UPSTREAM.md) — source, upgrade checklist, deviations
