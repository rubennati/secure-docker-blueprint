# Easy!Appointments

> **Status: Draft — not yet live-tested.**

Self-hosted appointment booking. Established open-source scheduler since 2013. PHP/MySQL — much lighter than Cal.com's Next.js stack. Good choice if you want a simple, stable booking system and don't need Cal.com's breadth.

## Architecture

| Service | Image | Purpose |
|---------|-------|---------|
| `app` | `alextselegidis/easyappointments:latest` | PHP + Apache + scheduling UI |
| `db` | `mariadb:11.4` | Customers, providers, services, appointments |

## When to pick Easy!Appointments

Compared to Cal.com / Cal.diy:

| Pick Easy!Appointments if… | Pick Cal.com / Cal.diy if… |
|---|---|
| You want a PHP-stack app (predictable, simple) | You want a modern Next.js feature set |
| You need basic 1:1 booking without bells and whistles | You need routing forms, team scheduling, workflows |
| You value a 13-year track record over newness | You want active feature velocity |
| You run only a few services per host (low RAM budget) | You have headroom for a Node.js app |

## Setup

```bash
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, TZ

mkdir -p .secrets volumes/mysql volumes/storage

openssl rand -base64 32 | tr -d '\n' > .secrets/db_pwd.txt
openssl rand -base64 32 | tr -d '\n' > .secrets/db_root_pwd.txt
sed -i "s|^DB_PWD_INLINE=.*|DB_PWD_INLINE=$(cat .secrets/db_pwd.txt)|" .env

docker compose up -d
docker compose logs app --follow
# Watch for: "apache2 -D FOREGROUND"

# First visit runs the installation wizard
# https://<APP_TRAEFIK_HOST>/index.php/installation
```

The installation wizard asks for:
- Admin username / password (pick a strong password)
- Company name / email / working hours

After install, the wizard page becomes inaccessible — standard login at `/index.php/backend`.

## Security Model

- **First-visit install wizard** — open the URL immediately after `docker compose up` so an attacker cannot register first.
- **`DB_PWD_INLINE` duplicates DB password** — Easy!Appointments reads `DB_PASSWORD` inline from env, no `_FILE` support.
- **`cap_drop: ALL`** + minimal `cap_add` on MariaDB.
- **`no-new-privileges:true`** on both services.
- **MariaDB on `app-internal` (`internal: true`)** — DB not reachable from outside.
- **Default access `acc-public` + `sec-2`** — booking URLs must be reachable by external visitors.

## Known Issues

- **Live-tested: no.**
- **`APP_TAG=latest` is not reproducible** — pin to a specific version for stable deployments.
- **Google Calendar sync** requires OAuth client ID / secret via Admin → Settings → Integrations. Not configured via env.
- **Email notifications** configured in UI (Admin → Settings → Business → Email). SMTP host / credentials live in the DB after setup, not in `.env`.
- **No built-in payment integration** — this is a booking tool, not a payment gateway. If you need "pay at booking", integrate Stripe manually or use Cal.com.

## Details

- [UPSTREAM.md](UPSTREAM.md)
- Sibling: [`apps/calcom/`](../calcom/) — commercial-support pathway
- Sibling: [`apps/caldiy/`](../caldiy/) — MIT community edition
