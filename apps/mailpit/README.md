# Mailpit

An SMTP sink. Every message a stack sends here is accepted, kept and shown in a
web UI, and nothing is delivered anywhere. It exists for trying out the stacks
that send mail: an application with SMTP configured but no relay reachable
either drops every message silently or refuses to start, and with a sink in
place the confirmation, the password reset and the reminder become readable
instead of vanishing.

## Architecture

Single service:

| Service | Image | Purpose |
|---------|-------|---------|
| `mailpit` | `axllent/mailpit` | SMTP on port 1025, web UI and API on port 8025 |

One static binary. Messages live in a SQLite file under `./volumes/data`,
pruned beyond `MP_MAX_MESSAGES`.

## Setup

```bash
# 1. Create .env
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, TZ

# 2. Create the message store, owned by USERMAP_UID (your own account, by default)
mkdir -p volumes/data

# 3. Start
docker compose up -d

# 4. Open in browser
# https://<APP_TRAEFIK_HOST>
# Reachable through Tailscale/VPN only by default (acc-tailscale).
```

No secrets, no accounts, no setup page.

## Verify

```bash
docker compose ps                                                      # mailpit healthy
docker compose exec mailpit wget -qO- http://127.0.0.1:8025/api/v1/messages   # {"total":0,...}
```

Send one message from a throwaway container on the proxy network, with a login
that does not exist:

```bash
docker run --rm --network proxy-public python:3-alpine python -c "import smtplib; s=smtplib.SMTP('mailpit',1025,timeout=10); s.login('anything','goes'); s.sendmail('probe@example.com',['you@example.com'],'Subject: probe\r\n\r\nhello'); print('sent')"
```

It appears in the UI within a second. That is the whole path a stack takes.

## Pointing a stack at it

Every stack has its own SMTP variables — the names differ, the values do not:

| Setting | Value | Why |
|---|---|---|
| host | `mailpit` | the service name, resolvable from every container on `proxy-public` |
| port | `1025` | plain SMTP. Many clients force STARTTLS on 587 and implicit TLS on 465, and this port offers neither |
| username | anything non-empty | some applications refuse to boot without one |
| password | anything non-empty | the same — put it in the stack's `.secrets/` file as usual |
| encryption | none | the traffic never leaves the Docker bridge |

Restart the stack, trigger a password reset, and read it in the UI.

## Security model

- **Everything in the inbox is readable by whoever reaches the UI.** Password
  resets, verification links, invitations. The UI has no login of its own, so
  the router ships `acc-tailscale`; opening it further needs `MP_UI_AUTH_FILE`
  (an htpasswd file, which then also protects the API).
- **Every container on `proxy-public` reaches port 1025.** A sink has to be
  reachable by every stack that sends, which is also why it is for trying
  things out: a stack whose users are real people sends real reset links, and
  those belong in a mailbox, not in a store the whole host can read.
- **The HTTP side is gated by hostname.** `MP_ALLOWED_HOSTS` is set to
  `APP_TRAEFIK_HOST`, so the API and the UI answer requests that arrive through
  Traefik and the healthcheck on localhost, and refuse a container calling
  `http://mailpit:8025/` with 403. It is a Host-header check — a forged header
  still passes — so it stops a casual read, not a determined one.
- **Any username and password is accepted, in plaintext**
  (`MP_SMTP_AUTH_ACCEPT_ANY`, `MP_SMTP_AUTH_ALLOW_INSECURE`). Applications
  expect to authenticate, and the sink has no user database to check them
  against.
- **Unprivileged, read-only, no capabilities.** The binary runs as
  `USERMAP_UID`, the root filesystem is read-only, and the only write goes to
  `/data`.
- **No outbound call.** Upstream checks the GitHub API for a newer release;
  `MP_DISABLE_VERSION_CHECK` turns that off. The link checker, HTML checker and
  screenshots in the UI fetch external resources only when you click them.

## Backup

| | |
|---|---|
| **Database** | None of its own. |
| **State** | `./volumes/data/mailpit.db` — test messages, pruned beyond `MP_MAX_MESSAGES`. |
| **Reproducible** | everything |
| **Quiescing** | Not applicable. |

Nothing to back up. The store holds messages that were never meant to arrive
anywhere; delete `./volumes/data` whenever it is in the way.

## Known issues

- **Port 1110 in `docker ps`** is the image's POP3 declaration. The server is
  off unless `MP_POP3_AUTH_FILE` is set, and nothing publishes the port.
- **A stack that hard-codes port 587** sends STARTTLS and fails. Mailpit can
  serve STARTTLS with a certificate (`MP_SMTP_TLS_CERT`, `MP_SMTP_TLS_KEY`),
  which this stack does not configure; use 1025 where the port is a setting.

## Details

- [UPSTREAM.md](UPSTREAM.md) — source, upgrade checklist
