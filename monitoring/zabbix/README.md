# Zabbix

Enterprise monitoring: agents, SNMP, IPMI, HTTP and script checks, with
triggers, escalation chains and history. Three services — the server that
collects, the web interface, and PostgreSQL. Upstream:
[zabbix/zabbix-docker](https://github.com/zabbix/zabbix-docker).

`alpine-7.0.x` is the long-term-support line: full support to 2027-06-30,
limited support to 2029-06-30. 8.0 is where the new features are.

Next to the rest of [`monitoring/`](../README.md): Uptime Kuma answers "is it
up", Grafana and Prometheus draw whatever exposes a metrics endpoint, and this
is the one that also knows about SNMP, IPMI, escalation policies and
maintenance windows — at the price of being the largest thing here to learn.

## Architecture

```text
Traefik ──http──→ zabbix-web :8080       nginx + PHP, the only routed service
                      │
                      ├──→ zabbix-server :10051   collector, not routed
                      │         │
                      │         └── 10051/tcp published only with trapper.yml
                      │
                      └──→ zabbix-db :5432        (PostgreSQL, app-internal)
```

## Setup

```bash
cp .env.example .env            # host name
ops/init.sh                     # the database password and the directories
sudo chown -R 1997:1997 volumes/alertscripts volumes/externalscripts
docker compose up -d            # the first start creates the schema
```

The first start takes a few minutes: the server builds the schema and loads
Zabbix' built-in templates.

**Then sign in as `Admin` / `zabbix` and change that password.** It is the
built-in account, it is the same on every Zabbix installation, and it works
immediately — measured: a `user.login` call against `/api_jsonrpc.php` with
those credentials returns a session token on a fresh instance. Until you change
it, anyone who reaches the interface has the API too.

`acc-tailscale` is what makes that survivable.

## Monitoring anything but this host

The server reaches outward on its own: HTTP checks, SNMP, ICMP, a Prometheus
endpoint, a passive agent it connects to. None of that needs a published port.

Two things do need one, and they are the same port:

- **Active agents**, which connect to the server rather than waiting to be
  polled — the usual choice across a firewall or NAT.
- **`zabbix_sender`**, for scripts that push a value.

```bash
docker compose -f docker-compose.yml -f trapper.yml up -d
```

publishes 10051/tcp. It is outside Traefik: Zabbix' protocol is not HTTP, so no
access policy, no TLS termination and no rate limit from the proxy apply. What
protects it is your host firewall and Zabbix' own PSK or certificate
encryption, which this stack does not configure. Bind it narrowly where you
can — `APP_TRAPPER_BIND=10.0.0.5:10051`.

### There is no agent container here

Upstream runs its agent with `privileged: true` and `pid: host`, and the agent2
README says it "must be privileged or you may mount some system-wide volumes".
`privileged` has no exception path in this repository — unlike host mounts or
the host PID namespace, which do. So the agent is not shipped. Two ways round
it:

- **Install the agent on the host**, from your distribution's package. That is
  the same split [`backup/`](../../backup/README.md) uses: the agent that needs
  the machine lives on the machine.
- **Point Zabbix at a Prometheus endpoint.** Zabbix reads them natively, and
  [`monitoring/grafana-prometheus`](../grafana-prometheus/) ships a
  node_exporter overlay that produces one. Fewer metrics than the Zabbix agent,
  no privileged container.

## Security model

- **Change `Admin` / `zabbix` at the first sign-in.** See Setup.
- **`acc-tailscale`.** The interface describes every host, service and
  credential the installation monitors.
- **Only the web interface is routed.** The server and the database are on an
  internal network with no published port.
- **10051/tcp is an opt-in overlay**, not a default.
- **The update check is off.** `AllowSoftwareUpdateCheck` defaults to 1 and
  asks zabbix.com about new releases; `ZBX_ALLOWSOFTWAREUPDATECHECK=0` is set,
  and the generated configuration was checked to confirm it took.
- **`cap_drop: ALL`, `no-new-privileges`, non-root** on all three services.
- **LDAP, SAML and MFA are built in** and none is configured here. There is no
  OIDC.

## Known limits

- **No `read_only` on the server or the web interface.** Both entrypoints
  rewrite their configuration under `/etc` on every start — the server fails
  with `sed: can't create temp file … Read-only file system`, and a tmpfs on
  `/etc/zabbix` only replaces that with `Missing configuration file`, because
  it hides what the image ships. Vendoring the configuration to a host bind
  mount would work and would put the **database password** on the host, since
  the entrypoint writes it into that file. Inside the container is the better
  place for it.
- **Nothing is monitored yet.** The stack runs, the schema exists, the
  interface answers — but no agent has reported, no trigger has fired and no
  alert has been delivered.
- **SNMP traps are not carried.** They need 162/udp and a separate
  `zabbix-snmptraps` container sharing a volume with the server. The same
  reasoning as 10051 applies, and nobody has run it here.
- **No high availability.** Zabbix 7.0 supports an HA cluster of servers; this
  is one of each.
- **History growth is yours to manage.** Housekeeping settings live in the
  interface, not in this compose file, and a busy installation can fill a disk.
- **`sec-2` is not measured** against the interface.
- **Nothing here has run behind this repository's Traefik yet.** The stack is
  `scaffolded`.

## Backup

| | |
|---|---|
| **Everything** | `./volumes/postgres` — hosts, items, triggers, users, history. Dump it: `docker compose exec zabbix-db sh -c 'pg_dump -U zabbix zabbix' > zabbix.sql` |
| **Yours** | `./volumes/alertscripts` and `./volumes/externalscripts` — whatever you wrote. Not reproducible from anywhere else |
| **The password** | `.secrets/db_pwd.txt` |
| **Quiescing** | `pg_dump` is consistent on its own. Stop the server first if you want a dump with no half-written history batch |

```yaml
# /etc/borgmatic/config.yaml
source_directories:
  - /srv/secure-docker-blueprint/monitoring/zabbix/volumes/alertscripts
  - /srv/secure-docker-blueprint/monitoring/zabbix/volumes/externalscripts
```

Restore: put the volumes back with the script directories owned by
`1997:1997`, restore the secret, start the database, load the dump, then start
the server and the interface.
