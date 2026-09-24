# Upstream Reference

## Source

- **Image:** https://hub.docker.com/r/zabbix/zabbix-server-pgsql · https://hub.docker.com/r/zabbix/zabbix-web-nginx-pgsql
- **GitHub:** https://github.com/zabbix/zabbix-docker
- **Docs:** https://www.zabbix.com/documentation/7.0/
- **License:** AGPL-3.0
- **Use restrictions:** none — https://www.zabbix.com/license · checked 2026-09-24
- **Edition gating:** none — one edition, every feature in the open-source build; Zabbix sells support and services rather than features — https://www.zabbix.com/support · checked 2026-09-24
- **Commercial model:** no paid edition — https://www.zabbix.com/support · checked 2026-09-24
- **Decision facts checked:** 2026-09-24
- **Origin:** Latvia · Zabbix, Riga — the project's own record adds Tokyo and New York; the site's copyright line reads "Zabbix LLC" · EU
- **Domain:** Monitoring
- **Role:** Enterprise monitoring — agents, SNMP, IPMI and HTTP checks with triggers, escalation and history
- **Based on version:** `alpine-7.0.31`

## Project maturity

7.0 is the long-term-support line: full support to 2027-06-30, limited support
to 2029-06-30. 8.0 is where new features land; this is where a deployment that
wants to be left alone lives. `alpine-7.0.31` was published between the
evaluation and this stack.

## What we use

- `zabbix/zabbix-server-pgsql:alpine-7.0.31` — the collector, not routed.
- `zabbix/zabbix-web-nginx-pgsql:alpine-7.0.31` — nginx and PHP, the only
  routed service.
- `postgres:17.11-alpine` — pinned to 17 because that is the client the server
  image ships (`postgresql17-client`).
- `trapper.yml`, an opt-in overlay that publishes 10051/tcp.

**No agent container.** Upstream runs its agent `privileged: true` with
`pid: host`, and the agent2 README says it "must be privileged or you may mount
some system-wide volumes". `privileged` has no exception path in this
repository, so the agent is installed on the host — the shape `backup/` uses
for its agent — or replaced; see the README.

## What we changed and why

| Change | Reason |
|--------|--------|
| `ZBX_ALLOWSOFTWAREUPDATECHECK=0` | `AllowSoftwareUpdateCheck` defaults to 1 in the shipped `zabbix_server.conf`: the server asks zabbix.com whether a newer release exists |
| 10051/tcp is not published | Active agents and `zabbix_sender` need it; a deployment that only monitors what the server can reach outward does not. It is an overlay |
| No agent service | `privileged` has no exception path here |
| PostgreSQL 17 rather than a newer major | The server image carries the 17 client |
| Databases on `internal: true` | Upstream's compose puts everything on one bridge network |
| No `read_only` on server or web | Measured below |

## Verified on the images (2026-09-24)

Not a host verification: a throwaway network, no Traefik router, no agent.

- All three services healthy; schema created on the first start (408 rows in
  `hosts`, Zabbix' built-in templates).
- `AllowSoftwareUpdateCheck=0` appears in the configuration the entrypoint
  generates, so the setting takes effect rather than being ignored.
- **`read_only` does not work, in either of the two obvious shapes.**
  With `read_only: true` the server exits on
  `sed: can't create temp file '/etc/zabbix/zabbix_server.confXXXXXX':
  Read-only file system` — the entrypoint rewrites that file in place on every
  start. Adding a tmpfs on `/etc/zabbix` replaces one failure with another:
  `Missing configuration file: /etc/zabbix/zabbix_server.conf`, because the
  tmpfs hides the file the image ships. Vendoring the configuration to a host
  bind mount would make it writable — and would put the database password,
  which the entrypoint writes into that file, on the host. Leaving it inside
  the container is the better of the two.
- **The default login works immediately and gives API access.** A
  `user.login` call with `Admin` / `zabbix` against `/api_jsonrpc.php` returned
  a session token on a freshly created instance; a wrong password is refused
  with "Incorrect user name or password or account is temporarily blocked".
- **`ports:` on a service that is only on an `internal: true` network is
  silently ignored.** The first version of `trapper.yml` published 10051 while
  the server sat on `app-internal` alone: `docker inspect` showed
  `PortBindings` set to the requested address and `NetworkSettings.Ports` null,
  `docker port` printed nothing, and the port refused connections. Docker
  accepts the request and never activates the mapping, because an internal
  network cannot route. The overlay now adds a second, routable network, and
  the port then accepts connections.
- Idle with nothing monitored: PostgreSQL 52 MiB anonymous, server 26 MiB,
  web 30 MiB.

What a host run still has to establish: the route through `core/traefik`, an
agent or a Prometheus endpoint actually feeding data, a trigger firing, an
alert delivered, and a restore from the volume.

## What reaches the network on its own

With `ZBX_ALLOWSOFTWAREUPDATECHECK=0`, nothing. Zabbix reaches exactly what you
configure it to monitor.

## Upgrade checklist

1. Read the release notes and the upgrade page for the 7.0 line —
   https://www.zabbix.com/documentation/7.0/en/manual/installation/upgrade
2. Raise `APP_TAG` in `.env` and in `.env.local.example`
3. `docker compose pull && docker compose up -d` — the server migrates the
   schema itself on start, and a major upgrade can take a while on a large
   history
4. `docker compose logs zabbix-server` — no migration error
5. Sign in and check that data is still arriving
6. Record the result in `Last verified` once it ran behind `core/traefik`

## Diff against upstream

```bash
# Upstream's own compose files — one bridge network, published ports, an agent
# with privileged: true
curl -s https://raw.githubusercontent.com/zabbix/zabbix-docker/7.0/docker-compose_v3_alpine_pgsql_latest.yaml

# Every setting the server reads, with upstream's defaults
docker run --rm --entrypoint sh zabbix/zabbix-server-pgsql:alpine-7.0.31 \
    -c 'cat /etc/zabbix/zabbix_server.conf'
```
