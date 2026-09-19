# PrivateBin

General-purpose zero-knowledge encrypted paste. Text, passwords, API tokens,
recovery codes, configuration fragments — anything short-lived that needs to
move between two people without landing in chat history or email. Optional
burn-after-read and expiration.

## What this is, and what it is not

The flow is **sender-initiated**, the same direction as Yopass: you write
the paste, PrivateBin encrypts it in your browser and gives you a URL, you
send that URL to whoever needs it. There is no way for someone else to
generate a link that asks *you* for a secret — for that, see
[Yopass](../yopass/) (paid Business feature upstream) or
[Hemmelig](../hemmelig/) (built in, with a manual key hand-off step).

**PrivateBin is not a credential inbox or vault.** It has no accounts, no
organization of what you've sent, and nothing that persists beyond a given
paste's own expiration. It does not replace a dedicated credential-intake
product (e.g. heylogin) that tracks requests, approvals or a standing
relationship with external submitters — it is a single-use, disposable
paste with client-side encryption.

## Services

| Service | Image | Purpose |
|---|---|---|
| privatebin-app | privatebin/nginx-fpm-alpine | Web UI + API (nginx + php-fpm, filesystem storage) |

## Security model

- **Zero-knowledge**: encryption and decryption happen entirely in the
  browser via the URL fragment key; the server only ever stores ciphertext.
- **No accounts, no admin panel, no server-side key** — there is nothing
  here beyond the pastes themselves, each with its own expiration.
- `read_only: true` + `cap_drop: ALL` with **no** `cap_add` — the image
  already runs as a fixed non-root UID/GID (`65534:82`) with no root-start
  entrypoint. Verified against a live container.
- The `/tmp` and `/run` tmpfs mounts explicitly allow execution
  (`tmpfs: /run:exec,...`) — the image's s6-overlay init copies executable
  service scripts into `/run` at every start, and Docker's tmpfs default
  does not include exec permission. Without this, the container reports
  healthy-looking logs but nginx and php-fpm never actually start. See the
  compose file's Security block and UPSTREAM.md.

## Setup

```bash
cp .env.example .env
# Edit: APP_TRAEFIK_HOST

mkdir -p volumes/data
sudo chown 65534:82 volumes/data

docker compose up -d
docker compose logs -f    # watch for "ready to handle connections"
```

Visit `https://<APP_TRAEFIK_HOST>` and create a test paste to confirm.

## Backup

| | |
|---|---|
| **State** | `./volumes/data` — every paste, as encrypted blobs on disk |
| **Reproducible** | Nothing — this is the only copy of whatever hasn't expired yet |
| **Quiescing** | Not needed. Each paste is a self-contained file; a dump mid-write affects only that one file |

```yaml
files:
    - path: /srv/docker/apps/privatebin/volumes/data
```

**Restore order:** restore `./volumes/data`, then start the container. A
paste restored past its own expiration is simply gone the next time
PrivateBin's garbage collection runs — that is expected, not a restore
failure.

## Local testing (no Traefik)

```bash
cp .env.local.example .env.local
mkdir -p volumes/local/data
sudo chown 65534:82 volumes/local/data
docker compose -f docker-compose.local.yml --env-file .env.local up -d
# http://localhost:8080
docker compose -f docker-compose.local.yml --env-file .env.local down
```

## Verify on first deploy (Preview → Ready gate)

- [x] `docker compose config` clean; `docker compose up -d` — healthy — **verified locally, 2026-09-19**
- [x] `GET /` returns 200 and serves the PrivateBin UI — **verified locally, 2026-09-19**
- [ ] A paste created and decrypted once through the actual web UI, including burn-after-read, behind Traefik on a real host
- [ ] The data-directory ownership requirement confirmed on the real host's filesystem (not tested here beyond a local Docker Desktop volume)
- [ ] TLS and the chosen `APP_TRAEFIK_SECURITY` chain confirmed against the real domain

## Details

- [UPSTREAM.md](UPSTREAM.md) — source, upgrade checklist, deviations
