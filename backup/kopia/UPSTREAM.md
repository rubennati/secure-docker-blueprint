# Upstream Reference

## Source

- **Image:** https://hub.docker.com/r/kopia/kopia
- **GitHub:** https://github.com/kopia/kopia
- **Docs:** https://kopia.io/docs/
- **License:** Apache-2.0
- **Decision facts checked:** 2026-09-23
- **Use restrictions:** none — https://github.com/kopia/kopia/blob/master/LICENSE · checked 2026-09-23
- **Origin:** No country stated · Kopia community project · no country
- **Domain:** Backup
- **Role:** Repository server for Kopia clients — deduplicated, encrypted snapshots from other machines, without handing them the repository password
- **Based on version:** `0.23.1`

## Origin, stated precisely

The project publishes no imprint and the GitHub organisation states no
location. **Origin** above records that rather than a guess.

## Project maturity

14 174 stars, pushed 2026-09-20, newest release 0.23.1 on 2026-06-16. Still
0.x: upstream has not declared a 1.0, and the repository format has been stable
across the 0.2x line.

## What we use

- `kopia/kopia:0.23.1`, one container, in **repository-server mode**
  (`kopia server start`). Clients connect over gRPC with their own accounts.
- The repository on this host's disk by default. A remote provider is a
  different `repository create` line and changes nothing else in the stack.

## What we changed and why

| Change | Reason |
|--------|--------|
| Repository-server mode, no host mounts | The shape `backup/README.md` allows for a container. Upstream's own compose examples run `privileged: true` with `/:/data:ro` for the UI mode, which is the pattern that document rejects |
| `config/entrypoint.sh` exports three passwords from Docker Secrets | Kopia reads `KOPIA_PASSWORD`, `KOPIA_SERVER_PASSWORD` and `KOPIA_SERVER_CONTROL_PASSWORD` from the environment; no `_FILE` variant exists for any of them |
| `ops/init.sh` generates the TLS certificate with `openssl` | Kopia's `--tls-generate-cert` refuses to start when the file already exists — measured: `TLS cert file already exists: "/app/config/tls.crt"`, exit 1. A flag that breaks every restart cannot live in the compose command |
| `user: "${APP_UID}:${APP_GID}"`, `read_only: true`, `cap_drop: ALL` | The image runs as root and needs nothing root can do here. Verified: the server starts and serves clients with all of it |
| Traefik service over `https` with `backend-selfsigned@file` | gRPC needs HTTP/2 with TLS end to end, so the container terminates TLS itself. `core/traefik` gains that transport in this change — a serversTransport comes from the file provider only |
| `--no-check-for-updates` | Upstream's default polls GitHub for new releases |
| `APP_TRAEFIK_ACCESS=acc-tailscale` | Every machine that backs up here has to reach this host |
| Healthcheck accepts 401 | Every path needs the server login, so an unauthenticated 401 is the proof that the server is answering |

## Verified on the image (2026-09-23)

Not a host verification: this ran the stack's own files and, for the Traefik
question, a throwaway Traefik v3.7 configured the way this repository
configures its own — not `core/traefik` on a host.

- `ops/init.sh` created the three secrets, the certificate and the repository;
  the server started healthy with `read_only`, `cap_drop: ALL`,
  `no-new-privileges` as uid 1000.
- `/` answered 401 without credentials and 200 with them; `/metrics` likewise
  401.
- `kopia server user add` works **through the entrypoint**
  (`/bin/sh /config/entrypoint.sh /bin/kopia …`). A plain `docker compose exec
  … /bin/kopia …` has no repository password and prompts for one — the same
  trap `apps/calrs` recorded.
- A client container connected over gRPC with `--server-cert-fingerprint`,
  created a snapshot, listed it, and **restored it** — 3 files, 1 directory.
- **gRPC survives a Traefik hop.** Through a Traefik with
  `serversTransport: insecureSkipVerify` and an `https` backend, a client
  connected and created a snapshot; the UI answered 200 through the same
  router. This was the open question in the 2026-09-22 evaluation.
- **A serversTransport cannot come from Docker labels.** With the equivalent
  labels on the container, Traefik logged "servers transport not found
  kopia-selfsigned@docker" and served nothing. Hence the file-provider entry in
  `core/traefik`.
- `kopia server acl add --user … --target "type=snapshot" --access APPEND` was
  accepted and appears in `acl list`. The target syntax is `key=value`;
  `type:snapshot` is rejected.
- Idle memory 142 MiB with one connected client.

What a host run still has to establish: the route through `core/traefik` with a
public certificate, a refused client outside the access policy, a client
connecting without a fingerprint over that route, a backup window large enough
to see the rate limit, and the restore in the README performed from the
restored volumes.

## Upgrade checklist

1. Read the release notes — https://github.com/kopia/kopia/releases
2. Raise `APP_TAG` in `.env` and in `.env.local.example`
3. `docker compose pull && docker compose up -d`
4. `docker compose logs kopia-server` — `SERVER ADDRESS: https://[::]:51515`
5. From a client: `kopia snapshot list`, then one new snapshot
6. Record the result in `Last verified` once it ran behind `core/traefik`

## Diff against upstream

```bash
# Upstream's own compose examples — the UI mode, with privileged and /:/data:ro
curl -s https://raw.githubusercontent.com/kopia/kopia/master/tools/docker/docker-compose.yml

# The flags this version accepts, including the hidden ones
docker run --rm kopia/kopia:0.23.1 server start --help-full
```
