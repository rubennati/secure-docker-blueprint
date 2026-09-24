# HeyForm

Form builder and response collector. Forms are built in a browser, published at
a URL, and the answers land in this installation's own database.

AGPL-3.0 · [heyform/heyform](https://github.com/heyform/heyform) ·
image `heyform/community-edition`

## Architecture

Three containers.

| Service | Image | Holds |
| --- | --- | --- |
| `heyform-app` | `heyform/community-edition` | the API, the GraphQL endpoint and the built web application |
| `heyform-db` | `mongo` | forms, submissions, users, workspaces |
| `heyform-cache` | `valkey/valkey` | sessions, verification codes, sign-in attempt counters, submission cooldowns |

Only `heyform-app` joins `proxy-public`. The other two sit on an `internal:
true` network with no route off the host.

Uploaded files are the one thing not in MongoDB: they go to `volumes/upload`
and are served back from `/static/upload/`.

## Setup

```bash
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, TZ, and the SMTP block if you have a mail server
ops/init.sh                 # secrets and the data directories
docker compose up -d
```

Then create the first account. The stack ships with registration closed, so
there is no sign-up page yet — open it for as long as it takes to register:

```bash
# 1. open registration
sed -i 's/^APP_DISABLE_REGISTRATION=true/APP_DISABLE_REGISTRATION=false/' .env
docker compose up -d heyform-app

# 2. open https://<APP_TRAEFIK_HOST> and create your account

# 3. close it again
sed -i 's/^APP_DISABLE_REGISTRATION=false/APP_DISABLE_REGISTRATION=true/' .env
docker compose up -d heyform-app
```

Everyone after you arrives by workspace invitation, which keeps working with
registration closed — but the invitation is sent by e-mail, so it needs SMTP.
Without mail, repeat the three steps above for each person.

## Who may create an account

`APP_DISABLE_REGISTRATION` is the whole of it.

Upstream leaves it `false`. That means an instance anyone can reach hands an
account to anyone who asks for one — and a new account can create its own
workspace, build forms and collect submissions on your installation. It is
closed here, and the first account is made by opening it deliberately for a
minute.

With it closed, the sign-up page is gone and `signUp` is refused, with one
exception: a visitor holding a valid workspace invitation may still register,
because that is how invitations work. The invitation has to exist, be
unexpired and match the workspace's current code.

## Publishing forms to the outside

The default is `acc-tailscale`: the instance is reachable over the VPN and
nowhere else. That covers forms whose respondents are on the VPN too.

Forms for people outside it need `APP_TRAEFIK_ACCESS=acc-public`, and that
publishes the whole instance, not just the forms. HeyForm serves the builder,
the collected submissions and the pages respondents fill in from one port, and
routes every one of them through a single `/graphql` endpoint — so there is no
path split that publishes the form and keeps the rest private.

What that does and does not mean:

- The dashboard and every admin mutation stay behind the session cookie. The
  GraphQL resolvers check authorisation individually; publishing the origin
  does not publish the data.
- What does become reachable is the sign-in surface, the schema, and the
  endpoints a respondent uses. Sign-in is rate-limited per account and
  address. Sign-up and the respondent endpoints require a header the browser
  sets, which a script can also set once it is known.
- So before switching: close registration (above), and consider a CrowdSec
  profile in `APP_TRAEFIK_THREAT` — the sign-in endpoint is the part worth
  watching.

## Without SMTP

`SMTP_HOST` empty is a supported configuration. Four features depend on mail:

| Feature | Without mail |
| --- | --- |
| Workspace invitations | the invitation is created but never delivered |
| Password reset | no way to reset a forgotten password |
| E-mail verification | keep `APP_VERIFY_USER_EMAIL=false`, or accounts cannot be used |
| New-device sign-in alert | not sent |

`APP_VERIFY_USER_EMAIL=true` without a reachable mail server makes every new
account unusable: the code is generated, stored in Valkey and never arrives.
Turn the two on together or leave both off.

## Try it locally

```bash
cp .env.local.example .env.local
ops/init.sh
docker compose -f docker-compose.local.yml --env-file .env.local up -d
# http://localhost:9157 — registration is open here; sign up and build a form
docker compose -f docker-compose.local.yml --env-file .env.local down
```

Use `localhost`, not `127.0.0.1`. The session cookie is issued for the host
name in `APP_HOMEPAGE_URL`, so a browser or client on the other spelling
drops it and every request after sign-in comes back unauthorised.

## Security model

- **All three containers**: `no-new-privileges`, `cap_drop: ALL`. MongoDB gets
  five capabilities back, which its entrypoint needs to take ownership of the
  data directory before dropping to its own user.
- **`read_only: true` everywhere.** The application writes to `/tmp` and to
  the upload volume, and nothing else. Valkey writes nothing at all —
  snapshotting is off, because everything it holds expires on its own and none
  of it has to survive a restart.
- **The application runs as uid 1000.** The image declares no user and runs as
  root; nothing in it needs root, and `ops/init.sh` creates the upload
  directory owned by that uid.
- **MongoDB has authentication and Valkey has a password.** Upstream's own
  compose has neither — it runs MongoDB with no credentials and KeyDB with
  `--protected-mode no`.
- **Five credentials come from Docker Secrets** through `config/entrypoint.sh`,
  because HeyForm reads settings from the environment and has no `_FILE`
  variant for any of them.
- **`TRUST_PROXY=1`** so the sign-in limiter counts real client addresses
  rather than treating the whole instance as one client. Raise it only by the
  number of proxies you actually added in front of Traefik: the value decides
  which entry in `X-Forwarded-For` is believed, and too high a number believes
  a header the client wrote.

### Uploads

Files land in `volumes/upload` and are served back from `/static/upload/` on
the same origin as the application. Upstream's default allow-list is images and
office documents — no HTML, no SVG — which is why it is left alone here and
`UPLOAD_FILE_TYPES` is not offered as a setting in `.env.example`. Widening it
to either of those would mean a file an outsider uploaded can run script on
your origin.

`POST /api/upload` needs either a signed-in session or a valid form context; an
upload with neither is refused.

## What leaves the host

Nothing, with one setting changed from upstream's default.

`ENABLE_GOOGLE_FONTS` defaults to `true` upstream, which loads the editor's
fonts from Google — for whoever fills in a form as much as for whoever builds
it. It is `false` here and the bundled fonts are used.

What remains, and is off unless you configure it: SMTP goes wherever you point
it; reCAPTCHA, Akismet spam filtering, the Unsplash image picker, Stripe and
the social-login providers are each off until given a key, and each is a
third-party call when enabled.

The container asks `/api/changelog/latest` for release notes; that is served
from this installation's own database, not fetched.

## Known limits

- `sec-2` is not measured against this application. It is a React front end
  that loads its assets in one burst, which is the pattern the `-spa` rate
  limits exist for. If assets fail to load on first visit, that is the first
  thing to look at.
- There is no upstream health endpoint that covers everything: `/health`
  answers as long as the process is up, `/health/ready` checks MongoDB and
  Valkey. The healthcheck uses the second.
- Sign-in attempts are limited per account and address. There is no limit on
  account creation beyond `APP_DISABLE_REGISTRATION`.
- `FORM_ENCRYPTION_KEY` encrypts form passwords and the hidden-field payloads
  in a form URL. There is no re-encryption step, so changing it after forms
  exist makes those unreadable.
- One critical advisory is open against the pinned version:
  [GHSA-chmm-jqpm-3pwx](https://github.com/heyform/heyform/security/advisories/GHSA-chmm-jqpm-3pwx),
  stored XSS in form field titles, with no patched version. It needs an
  account that may edit a form, and a second member who opens that form in the
  builder; someone filling in a published form cannot reach it. Registration
  being closed is what keeps that set of accounts to people you invited.
  UPSTREAM.md has the other 41 advisories and their ranges.

## Backup

Two things: the MongoDB database and `volumes/upload`. Valkey holds nothing
worth keeping.

```yaml
# /etc/borgmatic/config.yaml
source_directories:
  - /srv/secure-docker-blueprint/apps/heyform/volumes/upload
  - /srv/secure-docker-blueprint/apps/heyform/.secrets

mongodb_databases:
  - name: heyform
    hostname: heyform-db
    username: heyform
    password: "${HEYFORM_DB_PWD}"
    authentication_database: admin
```

Back up `.secrets/` with it. `SESSION_KEY` only signs sessions, but
`FORM_ENCRYPTION_KEY` is needed to read what is already stored, and the
MongoDB password is in `mongo_uri.txt`.
