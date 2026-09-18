# GreenMail

A mail server for application and integration testing. It speaks SMTP, IMAP
and POP3 (each with a TLS variant), keeps a real mailbox per recipient, and
accepts any username and password — so a test suite can send mail through it,
log in as the recipient and assert on what arrived.

| | [Mailpit](../mailpit/) | GreenMail |
|---|---|---|
| Protocols in this repository | SMTP in, web UI out (POP3 exists upstream and is off here) | SMTP, IMAP, POP3 and their TLS variants |
| Read mail with | a browser | any IMAP or POP3 client, per recipient |
| Typical caller | a person looking at what a stack would have sent | an automated test that connects as the recipient |

## Architecture

```text
Internet → Traefik (TLS, port 443) → greenmail :8080 (REST API / Swagger UI)
Other containers on proxy-public → greenmail :3025 :3110 :3143 :3465 :3993 :3995
```

One container. Test mail lives in memory and is gone after a restart — no
database, no volume. The mail ports are not HTTP and are not published to the
host; other stacks reach them by service name on `proxy-public`, the same way
they reach Mailpit.

## Setup

```bash
cp .env.example .env
docker compose up -d
```

Set `APP_TRAEFIK_HOST` in `.env` for the API and Swagger UI; access defaults to
`acc-private`. From any container on `proxy-public`, point SMTP at
`greenmail:3025` and IMAP or POP3 at `greenmail:3143` / `greenmail:3110`,
logging in with the recipient's address and any password.

Two things follow from the test-double design:

- **Authentication is off** (`-Dgreenmail.auth.disabled`). Anything on
  `proxy-public` can read every mailbox. Do not send real mail through it.
- **TLS uses a self-signed keystore** baked into the image
  (`changeit`). Test clients must skip certificate verification.

## Status

`scaffolded`. 2026-09-18 (2.1.13): the local and production compose files were
booted with the hardened settings, a message was sent over SMTP and retrieved
over IMAP and POP3, and a second container used the server by service name.
Traefik routing has not been run against a real host. Full log in
[`UPSTREAM.md`](UPSTREAM.md#verification-performed-2026-09-18).

## Local deployment validation

```bash
cp .env.local.example .env.local
docker compose -f docker-compose.local.yml --env-file .env.local up -d
curl http://localhost:8080/                 # Swagger UI
docker compose -f docker-compose.local.yml --env-file .env.local down
```

The local stack publishes every port on `127.0.0.1` so a test on the host can
reach `127.0.0.1:3025` and `127.0.0.1:3143` directly.

## Backup

No state to protect. Test mail is held in memory and discarded on restart —
that is the correct behaviour for an integration-test double, not a gap.
