# Upstream Reference

## Source

- **Image:** https://hub.docker.com/r/heyform/community-edition
- **GitHub:** https://github.com/heyform/heyform
- **Project:** https://heyform.net
- **License:** AGPL-3.0
- **Use restrictions:** none — https://github.com/heyform/heyform/blob/main/LICENSE · checked 2026-09-24
- **Edition gating:** none in the self-hosted build — the server carries no plan, quota or licence check; the limits on the pricing page are quotas of the hosted service — https://heyform.net/pricing · checked 2026-09-24
- **Commercial model:** free self-hosted; the paid plans are the hosted service, billed on responses, storage and team size, with a commission on payments collected through a form — https://heyform.net/pricing · checked 2026-09-24
- **Decision facts checked:** 2026-09-24
- **Origin:** United States · HeyForm · non-EU
- **Domain:** Publishing, forms and scheduling
- **Role:** Form builder and response collector, with conversational forms, logic, file uploads and submission export
- **Based on version:** `v3.0.3`

## Project maturity

8 985 stars, 34 contributors, release v3.0.3 on 2026-09-09. One maintainer
carries the project: the top committer has 213 commits and the next has 32.
The `latest` tag moves on release candidates as well as releases, which is why
`.env.example` pins a version.

Upstream's own deployment file is `docker-compose.test.yml`.

## What we use

The published image, unchanged. One container carries the NestJS API, the
GraphQL endpoint and the built web application, all on port 9157.

## What we changed and why

| Upstream | Here | Why |
| --- | --- | --- |
| `percona/percona-server-mongodb:4.4` | `mongo:8.0.32` | upstream's newest image of that line is from 2024-04 |
| MongoDB with no credentials | authentication on | it is a database |
| `eqalpha/keydb:latest`, `--protected-mode no`, no password | `valkey/valkey:8.1.4-alpine` with a password | KeyDB's last release is from 2023-10 |
| `:latest` | `v3.0.3` | `latest` also moves on release candidates |
| runs as root | `user: "1000:1000"` | nothing in the image needs root |
| writable filesystem | `read_only: true` | the only path written is the upload volume |
| no healthcheck | `/health/ready` | upstream ships the endpoint but no check |
| published port | Traefik only | |
| `APP_DISABLE_REGISTRATION=false` | `true` | a reachable instance otherwise hands an account to anyone |
| `ENABLE_GOOGLE_FONTS` defaults to `true` | `false` | fonts otherwise load from Google for respondents too |
| settings in plain environment variables | five from Docker Secrets | |

The image has no `_FILE` variant for any setting, so `config/entrypoint.sh`
exports `MONGO_URI`, `SESSION_KEY`, `FORM_ENCRYPTION_KEY`, `REDIS_PASSWORD`
and `SMTP_PASSWORD` from Docker Secrets before the image's own entrypoint
runs.

Compose clears an image's `CMD` when `entrypoint` is set, so the start command
is repeated in the compose file. Upstream's `CMD` probes three paths for the
built server; in v3.0.3 it is at `dist/src/main.js`.

## Verified on the images (2026-09-24)

The upstream compose pins a MongoDB from 2024 and a KeyDB from 2023. Whether
v3.0.3 runs on current versions of both was the open question before this
stack existed. It does — measured, not assumed, against `mongo:8.0.32` and
`valkey/valkey:8.1.4-alpine` with the full security baseline in place
(`read_only`, `cap_drop: ALL`, `no-new-privileges`, uid 1000, MongoDB
authentication, Valkey password):

- All three containers reach `healthy`. The application logs
  `Nest application successfully started`.
- MongoDB 8: the 24 collections are created on first start. An account, a
  workspace, a project, a form and its published version are written and read
  back.
- Valkey 8: four key families in use — `sess:`, `verify_email:`, `limit:day:`
  and `cooldown:`. Sign-in issues a session cookie and the next request is
  authorised.
- A respondent with no account opens the published form and submits an answer;
  the submission is stored in MongoDB with the answer intact.
- A file uploads under `read_only: true` as uid 1000, lands in the upload
  volume and is served back from `/static/upload/`.
- `POST /api/upload` with neither a session nor a form context is refused
  (`Invalid upload context`).
- CORS: an unrelated `Origin` gets no `Access-Control-Allow-*` header back;
  the configured one gets `Access-Control-Allow-Origin` with
  `Access-Control-Allow-Credentials: true`.

Resource use with one workspace and a published form: application 150 MiB
anonymous / 11 processes, MongoDB 110 MiB anonymous plus 207 MiB reclaimable
page cache / 71 processes, Valkey 3 MiB.

### Two behaviours that surprise

**`APP_HOMEPAGE_URL` is three settings at once.** HeyForm derives the session
cookie's `Domain`, the allowed CORS origin and the links in outgoing e-mail
from it. Set it to anything but the host name people actually use and sign-in
returns success while the browser drops the cookie — which presents as a
wrong password, not as a configuration error. Reaching a local instance on
`127.0.0.1` when the value says `localhost` reproduces it exactly.

**Two headers gate the API.** `signUp` and `login` require `x-device-id`, and
the respondent endpoints require `x-anonymous-id`; without them the request is
refused with `Forbidden request error` before anything else is checked. The
browser sets both. It matters when scripting against the API, and it means the
refusal seen from a bare `curl` is a missing header rather than a fault.

## Security advisories

42 published, all in 2026: 3 critical, 16 high, 20 medium, 3 low. The most
recent is from 2026-08-10, before v3.0.3.

Most record no patched version, so the useful figure is the vulnerable range
rather than the count. Every high one ends at 3.0.0 or earlier. Of the three
critical:

| Advisory | Range | Against v3.0.3 |
| --- | --- | --- |
| [GHSA-432x-54v2-p7p7](https://github.com/heyform/heyform/security/advisories/GHSA-432x-54v2-p7p7) — unauthenticated `/api/upload` | `<= 3.0.0-rc.8` | fixed; verified above |
| [GHSA-fg7j-rmgr-rc9g](https://github.com/heyform/heyform/security/advisories/GHSA-fg7j-rmgr-rc9g) — CORS wildcard reflection with credentials | through a commit v3.0.3 contains | fixed; verified above |
| [GHSA-chmm-jqpm-3pwx](https://github.com/heyform/heyform/security/advisories/GHSA-chmm-jqpm-3pwx) — stored XSS in form field titles | `<= Latest` | **open** |

The third is open-ended and applies to the pinned version. The form builder
assigns a field's title and description with `innerHTML`, so a workspace
member who can edit a form can leave script that runs when another member
opens that form in the builder. Its CVSS vector is
`AV:N/AC:L/PR:L/UI:R/S:C/C:H/I:H/A:H` — it needs an account on the instance
with permission to edit a form, and a second person to open it.

An outside respondent cannot reach it: filling in a published form does not
render the builder. So the exposure is between members of a workspace, which
is the other reason registration ships closed here — with it open, anyone who
can reach the host name can become such a member.

## Upgrade checklist

1. Read the release notes and the advisory list; check whether
   GHSA-chmm-jqpm-3pwx has gained a patched version.
2. Bump `APP_TAG`. Check whether the built server is still at
   `dist/src/main.js` — the compose file names it directly.
3. Check whether any new setting needs to be a secret, and whether
   `ENABLE_GOOGLE_FONTS` and `APP_DISABLE_REGISTRATION` still default the way
   this stack assumes.
4. `docker compose up -d` and confirm `/health/ready`, a sign-in and one
   submission.

## Diff against upstream

```bash
# Upstream's own compose — :latest, published port, no read_only, no database
# authentication, MongoDB 4.4, KeyDB with protected mode off
curl -s https://raw.githubusercontent.com/heyform/heyform/main/docker-compose.test.yml

# Every setting the server reads, with its defaults
curl -s https://raw.githubusercontent.com/heyform/heyform/main/packages/server/src/environments/index.ts
```
