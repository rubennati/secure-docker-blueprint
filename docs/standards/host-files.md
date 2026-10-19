# Host files

Files a stack installs outside the checkout — a logrotate stanza, systemd units,
a watchdog script, a backup agent's configuration — and how the repository keeps
track of them after they are installed. A blueprint update changes the checkout
and nothing under `/etc`; without this, a corrected file reaches a host only when
somebody remembers to copy it again.

## The rule

A stack that needs a file on the host lists it in `ops/host-files.manifest`.
`scripts/host-files.sh` renders the listed files with the real deployment path
into `<stack>/config/host/` (ignored by git), compares the rendered copies with
what is installed, and prints the commands that install them. It never writes
outside the checkout and never runs `sudo`; installing stays the operator's act.

```bash
scripts/host-files.sh render core/traefik          # -> core/traefik/config/host/
scripts/host-files.sh install-commands core/traefik # printed, not run
scripts/host-files.sh check                         # every rendered stack
./scripts/overview.sh --host                        # the same, after the service table
scripts/host-files.sh diff core/traefik /etc/logrotate.d/traefik
```

Rendering a stack is the statement that it is in use on this host: `check`
without arguments covers the stacks that have a `config/host/` and lists the
others as skipped, so a host that runs no backup agent is not told that its
agent is missing.

## The manifest

One line per file, six fields separated by whitespace; `#` starts a comment.

```text
# source (relative to the stack)   target on the host           mode  owner      compare  required
config/logrotate/traefik           /etc/logrotate.d/traefik     0644  root:root  exact    required
ops/scripts/traefik-watchdog.env.example  /etc/traefik-watchdog.env  0600  root:root  derived  optional
-                                  /root/.borg-passphrase       0600  root:root  presence required
```

| Field | Meaning |
|---|---|
| source | the file in the stack that is rendered; `-` for a `presence` entry, which the operator creates and the repository does not ship |
| target | the absolute path on the host |
| mode, owner | what the installed file must have; `install-commands` prints them, `check` compares them |
| compare | how the installed file is judged — below |
| required | `required`: the stack does not work without it, and its absence is an error once the stack is rendered. `optional`: a component the operator may leave out — its absence is reported, not counted |

The one placeholder a source may carry is `/path/to/secure-docker-blueprint`;
rendering replaces it with the checkout's path. A source without it is copied
as it is.

A source under `config/host/` is one the stack's own render writes, and only in
the mode that needs it — `core/traefik`'s `cloudflare-ranges.nft` exists with
`TRAEFIK_FORWARDED_PROXY=cloudflare` and not otherwise. Such an entry must be
`optional`; it is the one source the manifest check does not require to exist,
and `render` leaves it alone. A `required` source must exist in the checkout,
under `config/host/` or anywhere else, so a wrong path fails in CI.

### The three ways of comparing

| `compare` | For | `check` reports |
|---|---|---|
| `exact` | a script, a unit, a stanza — files the operator does not edit | `identical` when the installed file equals the rendered one byte for byte; `differs` otherwise, with the command that shows the difference |
| `derived` | a file the operator fills in after installing — `*.env` from an `.env.example`, a YAML configuration from its example | the **settings** are compared, not the values. A setting is a top-level key: `NAME=` in an env-style file, `name:` in YAML. Uncommented in the example, it is required; commented out (`# NAME=`), it is optional. `adapted` when every required setting is present — the values are the operator's; `differs` when a required setting is absent; a setting the example does not know is named in the `adapted` line and is not an error |
| `presence` | a secret — a passphrase, a private key | existence, mode and owner through `stat`; the content is never read, shown or diffed |

Mode and owner are compared for every entry; a mismatch is `differs` whatever
the content says.

### The states

| State | Meaning | Exit status |
|---|---|---|
| `identical` | installed as shipped, or a secret present with the right mode and owner | — |
| `adapted` | a derived file carrying every setting the example names | — |
| `not installed` | an optional file that is absent | — |
| `not produced` | an optional file under `config/host/` that the stack did not render in its current mode; nothing to install — and, if a copy is still installed, the line says so. `check` does not know the mode: whether the file *should* exist is the stack's own `validate.sh` to say | — |
| `skipped` | a stack with a manifest and no `config/host/` — not rendered on this host | — |
| `missing` | a required file that is absent | 1 |
| `differs` | content, settings, mode or owner differ from the manifest | 1 |
| `unreadable` | the installed file exists and cannot be read as this user — run with `sudo` to compare the content | 1 |
| `not rendered` | `check <stack>` was asked for a stack whose `config/host/` does not exist | 1 |

Every line names the source file and the host path, so the reader knows which
file in the checkout to look at and which file on the host it stands for.

## What the tool does not do

- It does not install. `install-commands` prints one `sudo install` line per
  file with the mode and owner from the manifest, a `daemon-reload` after
  systemd units and a `logrotate -d` after a logrotate stanza; the operator
  reviews and runs them. A `derived` file is installed only when it is absent —
  the installed copy carries the operator's values and is never overwritten.
- It does not print a secret. `diff` refuses a `presence` entry, and shows a
  `derived` file's full difference only with `--show`, because such a file may
  carry a URL with a token or a credential.
- It does not decide whether a partially installed optional component is
  consistent — a timer without its service is two lines, `identical` and
  `not installed`, for the reader to judge.

## Adding a host file to a stack

1. Ship the file in the stack — under `config/` or `ops/`, with the
   `/path/to/secure-docker-blueprint` placeholder where the deployment path
   belongs.
2. Add its line to `ops/host-files.manifest`; a stack without one gets the file
   with the header shown above.
3. In the stack's README, replace any `cp` or `tee` instruction with
   `scripts/host-files.sh render <stack>` followed by `install-commands`.
4. `scripts/ci/test_host_files.py` renders every shipped manifest; a manifest
   that names a missing source, an unknown `compare` or a relative target
   fails there.

Which stacks carry a manifest today: `core/traefik`, `core/host-watchdog`,
`backup/borgmatic`. Host files that a README describes without shipping them —
the CrowdSec host-firewall bouncer's drop-in and scripts, the `sysctl` files of
Zammad and Seafile, WordPress's cron line — get a manifest when they are
shipped as files.
