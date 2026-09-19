# Hemmelig

Client-side encrypted secret sharing with a built-in secret-request
workflow: someone can generate a link that asks a third party for a
credential, without that person needing an account.

## License — read this first

Hemmelig is under the **O'Saasy License Agreement**, a 2025 MIT-derived
license, not a standard OSI-approved open-source license (confirmed against
the upstream `LICENSE` file and GitHub's own license detector, which reports
`NOASSERTION` for it). It grants everything MIT does — use, copy, modify,
merge, distribute, sublicense — with one added restriction: nobody may offer
the software to third parties as a hosted, managed or SaaS product that
competes with the original licensor. **Self-hosting it for your own use, as
this stack does, is fully permitted and unaffected by that clause.** Do not
describe this stack as "open source" without that qualification.

## Secret requests need a manual step

Hemmelig's request flow (`docs/secret-request.md` upstream) works like this:

1. You (the requester) create a request and get a link — this needs a
   Hemmelig account with dashboard access, unlike Yopass's plain
   sender-creates-a-link flow.
2. You send that link to whoever holds the secret.
3. They open it, type the secret, and it is encrypted **in their browser**.
   The decryption key is generated client-side and put in the URL fragment
   for the *view* link — but that view link is only useful to you once you
   also have the key.
4. **They must send you the decryption key separately** — Hemmelig's own
   documentation states this explicitly: *"They receive a decryption key
   which they must send back to you."* There is no mechanism in Hemmelig
   that transmits the key to you automatically.
5. You open your dashboard, take the secret's URL and combine it with the
   key they sent you to view the secret.

So the "no account needed" part is true only for the person supplying the
secret — the requester needs an account, and the key still has to travel
back to the requester through whatever channel they agreed on out of band
(chat, a second Hemmelig link, a phone call). This is a real usability gap
compared to a fully self-contained flow, and this repository is not
smoothing over it.

## Services

| Service | Image | Purpose |
|---|---|---|
| hemmelig-app | hemmeligapp/hemmelig | Web UI + API + SQLite (single container) |

## Security model

- **Client-side encryption** — secrets are encrypted in the browser before
  transmission; the server stores ciphertext and the decryption key travels
  only in a URL fragment, never to the server.
- **No `read_only: true`** (documented deviation, not silently dropped) —
  the entrypoint's Prisma migration step downloads a platform-specific
  binary into `node_modules` on every container start. See the compose
  file's Security block for what was actually verified.
- `cap_drop: ALL` + a narrow `cap_add` for the same reason Postgres/Redis
  need one in this repository: the entrypoint starts as root, fixes
  ownership on the two data directories, then drops to its own user via
  `gosu`.
- The two secrets it needs (`BETTER_AUTH_SECRET`, an optional analytics HMAC
  key) go through Docker Secrets via a custom entrypoint wrapper — the image
  itself has no `_FILE` support.
- No separate database container: SQLite lives in the `database` volume.

## Setup

```bash
cp .env.example .env
# Edit: APP_TRAEFIK_HOST

mkdir -p .secrets volumes/database volumes/uploads
openssl rand -base64 32 | tr -d '\n' > .secrets/better_auth_secret.txt
openssl rand -base64 32 | tr -d '\n' > .secrets/analytics_hmac_secret.txt

docker compose up -d
docker compose logs -f    # watch for "All migrations have been successfully applied" then "Server is running on port 3000"
```

Visit `https://<APP_TRAEFIK_HOST>` and register the first (admin) account.

## Backup

| | |
|---|---|
| **Database** | SQLite · `./volumes/database/hemmelig.db` |
| **State** | `./volumes/database` (database) · `./volumes/uploads` (uploaded files, if enabled) |
| **Password** | `.secrets/better_auth_secret.txt` — rotating it invalidates every active session |
| **Quiescing** | Not needed for a consistent file copy, but avoid backing up mid-write; there is no dedicated dump tool for SQLite here beyond a file copy |

```yaml
files:
    - path: /srv/docker/apps/hemmelig/volumes/database
    - path: /srv/docker/apps/hemmelig/volumes/uploads
```

**Restore order:** stop the container, restore both volumes together (the
database may reference uploaded file paths), start the container.

## Local testing (no Traefik)

```bash
cp .env.local.example .env.local   # fill BETTER_AUTH_SECRET
mkdir -p volumes/local/database volumes/local/uploads
docker compose -f docker-compose.local.yml --env-file .env.local up -d
# http://localhost:8080
docker compose -f docker-compose.local.yml --env-file .env.local down
```

## Verify on first deploy (Preview → Ready gate)

- [x] `docker compose config` clean; `docker compose up -d` — healthy — **verified locally, 2026-09-19**
- [x] Migrations apply cleanly and `GET /api/health/ready` reports `"status":"healthy"` across database, storage and memory checks — **verified locally, 2026-09-19**
- [ ] A full secret-request round trip (request created, secret submitted, key sent back out of band, secret viewed) through the actual web UI
- [ ] TLS and the chosen `APP_TRAEFIK_SECURITY` chain confirmed against a real domain
- [ ] Restart the container and confirm SQLite state and uploaded files survive

## Details

- [UPSTREAM.md](UPSTREAM.md) — source, upgrade checklist, deviations
