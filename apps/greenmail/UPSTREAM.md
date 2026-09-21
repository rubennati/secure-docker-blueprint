# Upstream Reference

## Source

- **Image:** https://hub.docker.com/r/greenmail/standalone
- **GitHub:** https://github.com/greenmail-mail-test/greenmail
- **Docs:** https://greenmail-mail-test.github.io/greenmail/
- **License:** Apache-2.0
- **Decision facts checked:** not yet
- **Origin:** Community · Marcel May · Germany · EU
- **Domain:** Developer tools
- **Role:** SMTP, IMAP and POP3 test server with a mailbox per recipient, for automated tests
- **Based on version:** `2.1.13`

No `Last verified` line yet — see [Verification performed](#verification-performed-2026-09-18)
below for exactly what has been exercised and what has not. The field
asserts Traefik/TLS routing was confirmed on a real host, which this session
could not do; setting it early would claim evidence that does not exist. This
stack stays `scaffolded` until that happens.

## What we use

- Official image, pinned tag: `greenmail/standalone:2.1.13`.
- Runs as a non-root `greenmail` user by upstream default (verified via
  `docker inspect`) — no `user:` override in compose.
- Upstream's default `GREENMAIL_OPTS` (test-all setup, all protocols on
  `0.0.0.0`, TLS via a baked-in self-signed keystore, auth disabled) is
  repeated explicitly in `environment:` rather than left to the image's own
  default, so it is visible and editable here.

## Architecture

```text
Internet → Traefik (TLS, port 443) → greenmail :8080 (REST API / Swagger UI)
Other containers on proxy-public → greenmail :3025/:3110/:3143/:3465/:3993/:3995 (mail protocols)
```

Stateless — GreenMail holds test mail in memory only, by design. No database,
no volume.

## What we changed and why

| Change | Reason |
|--------|--------|
| `read_only: true` + `tmpfs: [/tmp]` | Verified working against a real SMTP send and IMAP retrieval — see below |
| `-Dgreenmail.startup.timeout=10000` added to `GREENMAIL_OPTS` | Upstream's 2000ms default missed under this sandbox's CPU contention: the SMTPS listener failed to bind in time, which crashed the whole runner out of `main()` while already-bound listeners (SMTP) kept answering — a degraded, confusing partial failure rather than a clean start or a clean crash. Reproduced and fixed 2026-09-18. |
| Traefik routes only port 8080 | The mail protocol ports are not HTTP; other stacks reach them directly on `proxy-public`, the same pattern `apps/mailpit` already uses |
| `app-internal` network not added | No database or internal service to isolate |

## Verification performed (2026-09-18)

Against the local test stack, and against the production `docker-compose.yml`
on a throwaway `proxy-public` network without Traefik:

- `docker pull greenmail/standalone:2.1.13` — succeeds
- Booted with `no-new-privileges`, `cap_drop: ALL`, `read_only`,
  `tmpfs: [/tmp]`, non-root user `greenmail`, no published ports (production)
  — all six mail listeners and the API server started with no exceptions in
  the log, once `-Dgreenmail.startup.timeout=10000` was added (see above);
  the failure reproduced first at the image's 2000ms default
- **SMTP:** two messages accepted over the raw protocol (`250` at every step)
  and one through Python's `smtplib` (`send_message`, 0.1s)
- **IMAP** (`:3143`): `LOGIN` with an arbitrary password
  (`-Dgreenmail.auth.disabled`), `SELECT INBOX`, `SEARCH`, `FETCH RFC822`
  returned the exact subject and body sent; `STORE \Deleted` + `EXPUNGE`
  emptied the mailbox, so the server keeps real per-recipient mailbox state
- **POP3** (`:3110`): `USER`/`PASS`, `STAT` (1 message) and `RETR` returned
  the sent body
- **IMAPS** (`:3993`): TLS handshake and login succeed against the baked-in
  keystore
- **Cross-stack use:** a separate container on `proxy-public` sent mail to
  `greenmail:3025` and read it back from `greenmail:3143` by service name —
  the consumption pattern the stack is designed for

Only the Swagger UI at `:8080/` was confirmed for the REST API; its endpoints
were not exercised.

**Not yet exercised:** Traefik routing of the API (the router label
`acc-private@file,sec-2@file` resolves, but no Traefik ran), and the SMTPS
and POP3S listeners (`:3465`, `:3995`) — a plain TCP connect to a TLS port is
logged by GreenMail as a failed handshake, so probe them with a TLS client.

## Upgrade checklist

1. Read the release notes for breaking changes: https://github.com/greenmail-mail-test/greenmail/releases
2. Check the GitHub Security tab for advisories against the current version
3. Bump `APP_TAG` in `.env.example` and `.env.local.example`
4. `docker compose pull && docker compose up -d`
5. Re-run the SMTP send / IMAP fetch verification above
6. Update **Based on version** above — and **Last verified** only if the
   upgrade was actually exercised

## Useful commands

```bash
# Tail logs
docker compose logs greenmail --follow

# From any container on proxy-public: send, then read back over IMAP
python3 - <<'PY'
import smtplib, imaplib
from email.message import EmailMessage
m = EmailMessage(); m["From"] = "app@example.com"; m["To"] = "qa@example.com"
m["Subject"] = "hello"; m.set_content("body")
smtplib.SMTP("greenmail", 3025, timeout=20).send_message(m)
i = imaplib.IMAP4("greenmail", 3143, timeout=20); i.login("qa@example.com", "any"); i.select("INBOX")
print(i.fetch(b"1", "(RFC822)")[1][0][1].decode())
PY
```
