# Which PostgreSQL client dumps and restores a stack's database — a decision paper

**Status: proposal for a decision, nothing implemented** (2026-11-04). It answers the final
audit's FA-03 for `backup/borgmatic`; the 26 `postgresql_databases` entries in the stack
READMEs stay as they are until the decision is taken.

## The problem, measured

`backup/borgmatic` runs on the host, and its `container:` option only resolves the database
container's address: `pg_dump` and `pg_restore` are the **host's** client. Debian 13 ships
client 17; the stacks pin their servers between 14 and 18.

| Pairing | What happens | Measured on the step 8 lab host |
|---|---|---|
| client 17, server 17 | works | Tymeslot: restore exit 0, 39 tables, the account logged in |
| client 17, server 14 or 16 | the backup reports success; `pg_restore` stops on `SET transaction_timeout`, which the older server rejects | Paperless-ngx, listmonk, Immich: Fail |
| client 17, server 18 | `pg_dump` refuses a newer server — the backup itself fails | not run; follows from `pg_dump`'s version rule |

In the repository that is a silent loss of recoverability for 17 stacks below 17 and a failing
backup for 8 above it.

## Three options

| | A — the matching client next to the agent | B — a separate dump container | C — `docker exec` into the database container |
|---|---|---|---|
| **How** | one `postgresql-client-<major>` per server major on the host (the PostgreSQL project's APT repository), named per entry (`pg_dump_command: /usr/lib/postgresql/16/bin/pg_dump`); or the agent itself in a container that carries every client | `pg_dump_command: docker run --rm --network <stack>-internal postgres:<the stack's DB_TAG> pg_dump -h db …` — a throwaway container from the server's own image | `pg_dump_command: docker exec <stack>-db pg_dump`, `pg_restore_command: docker exec -i <target>-db pg_restore` — the client inside the running server's image |
| **Version match** | by hand: an entry names a major, and a stack's major upgrade must update the entry and install the client | by construction, if the entry reads the stack's `DB_TAG` | by construction: the client ships with the server |
| **Credentials** | over TCP: the password reaches the host client (borgmatic's `password_transport`) | over TCP: the password has to reach a new container (environment or a mounted pass file) | none: the official image trusts the local socket (`local all all trust`, read on the lab host); the dump runs as the container's own user |
| **Docker socket** | host variant: not needed beyond what `container:` already uses; container variant: **the agent needs the socket and every volume** — what `backup/README.md` rules out ("Where the backup agent belongs") | the agent starts containers — it uses the socket, as root, which it already is | the agent runs `docker exec` — it uses the socket, as root, as the quiescing hooks already do |
| **New trust boundary** | host variant: a third-party APT repository on the host, one package per major; container variant: a container that can read every secret | a new, short-lived member on the stack's `internal` network, with the database password | none new: the dump runs inside the boundary that already holds the data |
| **Load** | on the host | on the host (an image pull on the first run) | inside the database container — its memory and `pids` limits apply to `pg_dump` too |
| **Restore** | the same client, against a throwaway server | the same image, against a throwaway server | `docker exec -i` into a throwaway server of the same image — the restore uses the same mechanism |
| **Proven restore** | **yes**, host variant: Paperless-ngx (client 16 → server 16.14: 74 tables, 48 media files identical, documents and search hits as live) and listmonk (client 16: 16 tables, 94 rows identical) | **no** — not run | **yes**: Paperless-ngx (dump and restore through `docker exec`: 74 tables, 42 media files identical, a throwaway instance matching the live one, `document_sanity_checker` clean) |
| **Fails when** | a stack moves to a new major without the entry following; the APT repository is unavailable | the image cannot be pulled; the network name changes | the database container is not running (as with `container:` today); the container's limits are too tight for a large dump |

## Recommendation

**C — `docker exec` with the server's own client, for dump and restore.** It is the only option
that matches versions by construction, has a proven restore, needs no credential transport and
adds no trust boundary: the agent already runs as root with the Docker socket, and the
quiescing hooks already use `docker exec <exact-container>`. Its two costs are named in each
entry: the container must be running, and a large database needs headroom in the database
container's `memory` and `pids` limits during the dump.

A stays the documented fallback for a host that must not let the agent exec into containers;
the container variant of A is not recommended (it is the deviation `backup/README.md`
argues against). B is not recommended before it has a restore of its own: it moves the
password into a new container on the internal network for no gain over C.

## What the decision would change

- The 26 `postgresql_databases` entries: `pg_dump_command` and `pg_restore_command` (and
  `psql_command` where used) through `docker exec <exact-container>`; `container:` kept for the
  address where an entry still needs it; the client prerequisite for PostgreSQL removed from
  `backup/borgmatic/README.md`, the limits note added.
- `backup/borgmatic/RESTORE.md`: the restore through `docker exec -i` into the throwaway server.
- One restore rehearsal per PostgreSQL major in use (14, 16, 17, 18) before the entries are
  called verified; the Paperless-ngx rehearsal covers 16 only.
- MariaDB and MySQL are not part of this decision: their client skew is the TLS one
  `backup/borgmatic/README.md` already handles with `tls: false`.
