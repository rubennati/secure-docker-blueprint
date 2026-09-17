# Secrets

Generation, storage and rotation for every secret this blueprint manages.

For where a secret fits in `.env.example` and the compose file, see
[Env Structure](env-structure.md) and
[Security Baseline](security-baseline.md#secrets). This document
covers what those two only point at: how to create a secret's value, how to
handle it once created, and how to change it later without inventing a
process per stack.

---

## Scope

Four kinds of secret appear across this repository's stacks, evidenced from
their `.env.example` files:

| Kind | Examples | Generated how |
|---|---|---|
| Database password | `db_pwd`, `db_root_pwd`, `redis_pwd` | locally, with `openssl rand` |
| Application/admin secret | `admin_pwd`, `bootstrap_admin_pwd`, `in_pwd` | locally, with `openssl rand` |
| Signing / encryption / session key | `authentik_secret_key`, `jwt_key`, `secret_key_base`, `encryption_key`, `nextauth_secret` | locally, with `openssl rand` |
| Externally-issued API token | `CF_DNS_API_TOKEN` | issued by the provider — not generated locally |

The first three are covered in full below. The fourth is stored, rotated and
protected the same way as any other secret; only its *generation* step
differs — request it from the provider that issues it.

---

## Generation

Prefer `openssl rand`. It is already required by every stack that documents
secret generation in this repository, needs no new dependency, and is
appropriate for every kind above.

```bash
mkdir -p .secrets
openssl rand -base64 32 | tr -d '\n' > .secrets/db_pwd.txt
```

**Always strip the trailing newline** (`| tr -d '\n'`). A newline is part of
the file's bytes, and Docker mounts a secret file's bytes verbatim — an
unstripped newline becomes part of the compared password or key.

**`-base64` vs `-hex`.** `-base64` packs more entropy per character, which is
why it is the default for most secrets in this repository. Switch to `-hex`
when the value must not contain characters that can break a URL or a
connection string (`+`, `/`, `=`) — this repository already does exactly that
for values embedded in a DSN, e.g. a Postgres connection string:

```bash
openssl rand -hex 32 > .secrets/db_pwd.txt   # hex = URL-safe for the connection string
```

**Length by role**, taken from what stacks in this repository already pin:

| Role | Typical length | Example |
|---|---|---|
| Database password | 32 bytes (`-base64 32` or `-hex 32`) | `db_pwd`, `redis_pwd` |
| Admin/bootstrap password | 24 bytes (`-base64 24`) | `bootstrap_admin_pwd`, `in_pwd` |
| Signing / session / app secret key | 32–64 bytes, per what the application expects | `authentik_secret_key` (60), `secret_key_base` (64), `jwt_key` (48), `encryption_key` (32) |

Check the application's own documentation for a minimum length or required
encoding before picking one outside this range — Documenso's
`encryption_key`, for instance, states a 32-character minimum in its own
`.env.example` comment. Where a stack's `.env.example` already documents a
specific command, that command is the authority for that stack; this table
is for a new stack or a value the stack's own file doesn't already cover.

**API tokens** are requested from the service that issues them (Cloudflare's
dashboard, for `CF_DNS_API_TOKEN`), scoped to only what the integration
needs. Store the issued value exactly as received — do not re-encode it.

---

## Storage and handling

- **`.env.example` never carries a real value** — not even a plausible-looking
  example. Placeholder or generation instructions only. See
  [Env Structure](env-structure.md).
- **A real secret lives in its own file under `.secrets/`**, one file per
  secret, wired into the container as a Docker file-based secret
  (`security_opt`/`_FILE` pattern) or read by a custom entrypoint from
  `/run/secrets/` — see [Security Baseline](security-baseline.md#secrets)
  for the three patterns and which stacks use which. A secret is never placed
  in `environment:` or `env_file:`.
- **`.secrets/` and `volumes/` are gitignored repository-wide**
  (`**/.secrets/`, `**/volumes/` in the root `.gitignore`) — this is already
  enforced; nothing here changes it.
- **Permissions.** The default is owner-only, matching the working example in
  `core/keycloak/README.md`:

  ```bash
  chmod 700 .secrets
  chmod 600 .secrets/*.txt
  ```

  Compose's `secrets:` block ignores `uid`/`gid`/`mode` outside Swarm — what
  the container actually sees is the host file's own ownership and mode. When
  a service reads its secret as a non-root user at request time (rather than
  a root entrypoint that reads it once and drops privileges), owner-only
  permissions lock the container out entirely. That case needs group access
  granted explicitly instead — see
  [Compose Structure](compose-structure.md#two-properties-of-file-based-secrets-that-surprise-people):

  ```bash
  sudo chown "$USER":<container-gid> .secrets/foo.txt
  chmod 640 .secrets/foo.txt
  ```

  A stack's own README states which of the two it needs; this document does
  not override that.
- **Backups contain every secret this blueprint manages.** Borgmatic backs up
  the whole deployment root, `.secrets/` included, by design — see
  `backup/borgmatic/config.yaml.example`. That is exactly why the archive
  must stay encrypted, and why a restored archive gets the same handling
  discipline as a live `.secrets/` directory: readable only by whoever is
  performing the restore, and never left sitting somewhere more exposed than
  the original.
- **Never let a secret's value reach**: a README, a compose file (beyond a
  `secrets:` reference by name), shell history, an application or access log,
  an error message, or a commit. If a command must contain the raw value
  interactively, treat that terminal's history and scrollback as sensitive
  too.

---

## Rotation

The generic shape is the same for every secret:

```text
prepare → introduce new secret → update dependent service(s) → restart/reload
→ verify → revoke old secret → record completion
```

What each step means depends on which of three categories the secret is in.

### 1. Database / application credential

*Both ends must change together* — the database only ever recognizes the
password currently set for that role, so there is no window where old and
new both work.

1. **Prepare**: generate the new value (Generation, above) into a new file —
   do not overwrite the live one yet.
2. **Introduce**: change the credential at the database (or the application's
   own admin interface, for an app-level secret), then write the new value
   over the mounted secret file:

   ```bash
   printf '%s' "$NEW_VALUE" > .secrets/db_pwd.txt
   ```

   Write in place with `printf`, not an editor. Most editors save by writing
   a temporary file and renaming it over the target — that replaces the file
   the bind mount is attached to, and the running container keeps serving the
   old one. See [Compose Structure](compose-structure.md#two-properties-of-file-based-secrets-that-surprise-people).
3. **Update / restart**: `docker compose up -d --force-recreate <service>` —
   `restart` does not re-resolve a bind-mounted secret file; only recreating
   the container does.
4. **Verify**: the service reports healthy *and* an actual operation
   succeeds against the new credential (a login, a write) — a healthy status
   alone does not prove the new secret is the one in use.
5. **Revoke**: there is usually nothing separate to revoke — changing the
   database role's password already invalidates the old one. Securely remove
   the old value once the new one is confirmed working.
6. **Record**: the `.secrets/` file itself is the record; note the rotation
   date in the stack's own operational log if it keeps one.

### 2. API token

*Old and new can often overlap* — most providers let you issue a second
token before revoking the first, which removes the all-or-nothing risk of
category 1.

1. **Prepare**: request a new token from the provider, scoped identically to
   the one being replaced.
2. **Introduce**: write the new token into `.secrets/`.
3. **Update / restart**: force-recreate the affected service.
4. **Verify**: confirm the integration actually works with the new token —
   for `CF_DNS_API_TOKEN`, a certificate renewal or `validate.sh` run that
   exercises the DNS-01 path.
5. **Revoke**: revoke the *old* token at the provider. This is the step that
   actually closes exposure — an unrevoked old token left valid defeats the
   rotation.
6. **Record**: note the rotation date if the provider doesn't already log it.

### 3. Signing / encryption / session key

*Rotation can have consequences beyond the secret itself* — this is the one
category where a generic procedure is not enough. Rotating a session-signing
key generally just forces every active session to re-authenticate, which is
usually acceptable. Rotating an encryption-at-rest key can make data already
encrypted under the old key unreadable unless the application supports
re-encryption or key versioning — and not every application does.

**Check the specific application's own documentation before rotating one of
these.** This standard does not invent a per-app procedure without evidence;
where the stack's `UPSTREAM.md` or upstream docs describe rotation behavior
for a given key, follow that. Where they don't, treat the key as
non-rotatable without a maintenance window and a tested backup, and confirm
the blast radius (sessions only, or stored data too) before proceeding.

---

## Emergency rotation

A secret is known or suspected to be compromised. This is the generic
procedure faster than working through the categories above from scratch —
adapt with the category-specific detail once you're past the first step.

1. **Contain.** If the secret grants remote access on its own (an API token,
   a VPN key), consider revoking it at the source immediately, even before a
   replacement is ready. A short outage is cheaper than continued exposure.
2. **Rotate / revoke.** Generate the replacement (Generation, above), follow
   the matching category's procedure, and revoke the compromised value at its
   source — the database role, the provider console, whichever applies.
3. **Restart / reload.** Force-recreate every service that depended on the
   compromised value.
4. **Invalidate sessions or tokens.** For a signing or session key, confirm
   that rotating it actually invalidated existing sessions — that's usually
   the entire point of rotating it under compromise. Verify by checking that
   an old session or token is rejected, not only that a new one works.
5. **Verify.** Every affected service is healthy and functionally exercised.
6. **Assess further exposure.** The compromised value may exist in more
   places than the live `.secrets/` file:
   - **Git history** — if it was ever committed, rotating it is not enough;
     follow [Commit Rules](commit-rules.md)'s path for a pushed secret:
     `git filter-repo` + force push + rotate (already rotated by this point).
   - **Backups** — every archive taken before rotation still contains the old
     value; that is expected and not itself actionable once the old value is
     revoked and inert everywhere. It becomes actionable only if the backup
     archive or its encryption key is *also* suspected compromised.
   - **Logs** — a secret that leaked into an application or access log needs
     that log rotated/purged in addition to the secret itself.

---

## Stack-specific boundary

This document is the reusable baseline: how to generate a value, where it
lives, what its permissions should be, and the generic rotation shape.

What it deliberately does not cover is *application-specific* rotation
behavior — whether a given app supports rotating a key live, whether it needs
a specific CLI command or maintenance mode, or what breaks if you don't
follow its own procedure. That belongs in the stack's own `UPSTREAM.md` or
README when the upstream project documents it, and only when it documents
it — this standard does not invent that guidance without evidence. Where a
stack's own README already documents something differently (Keycloak's
`700`/`600` permission commands, for instance), that stays there; this
document points to it rather than restating it.
