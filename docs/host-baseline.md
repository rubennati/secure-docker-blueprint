# Host baseline for a Docker host

What a Linux host needs before the blueprint's stacks run on it, apart from the
blueprint itself. The blueprint assumes these points; it does not set most of them up.
This page is general host hardening: the Docker-specific prerequisites are in
[`docs/standards/deployment-lifecycle.md`](standards/deployment-lifecycle.md), step 1, and
the ingress layers in [`docs/architecture.md`](architecture.md), "Ingress paths, profiles
and trust boundaries".

It is derived from one host — the lab host, a rented virtual machine with a public
IPv4 and IPv6 address, Debian 13, Docker Engine 29, Tailscale on the host — and from what
was measured there ([`docs/labs/ingress/2026-11-01-results.md`](labs/ingress/2026-11-01-results.md),
[`docs/host-verification-ingress.md`](host-verification-ingress.md)). A measurement on one
host is evidence for that shape, not a guarantee for another. Names below are roles:
`<public-if>` is the public interface, `<admin>` the administrative account,
`<break-glass>` the console-only account, `<tailnet-v4>`/`<tailnet-v6>` the host's
tailnet addresses.

## The host as tested

State: **configured** (set up, not exercised on purpose), **tested** (exercised, result
recorded), **not tested**, **open** (a known gap).

| Area | What the lab host had | State |
|---|---|---|
| System | Debian 13, cloud kernel, updated to the current point release; one reboot for a kernel update | tested (two reboots, a third with the `nftables.service` drop-in: T8) |
| Updates | `unattended-upgrades` for security updates, automatic reboot off — a kernel update waits for a planned reboot | configured |
| Time, journal, swap | `systemd-timesyncd` synchronised; journald persistent, capped at 200 MB; swap with a low `swappiness` | configured |
| Docker | Docker Engine 29 with Compose 5, `daemon.json`: `local` log driver with size limits, `ipv6` and `ip6tables` on, `userland-proxy: false` (`core/traefik/docs/ipv6-dual-stack.md`) | tested |
| Accounts | `<admin>`: key only, `sudo`; `<break-glass>`: password, no key, denied by sshd, for the provider console only; `root` locked | tested (console login, M1/M2) |
| SSH | keys only (`AuthenticationMethods publickey`), root login off, `MaxAuthTries 3`, `LoginGraceTime 30`, no X11 or agent forwarding; TCP forwarding left on | tested |
| Network | static public IPv4 and IPv6 from the provider, `accept_ra 0` on `<public-if>`; IPv4/IPv6 forwarding on (Docker); reverse-path filter loose on `<public-if>` | configured |
| Provider filter | 80 and 443/tcp on both families, 22/tcp from the operator's IPv4 only, ICMP; UDP 443 and 41641 not admitted | tested (X1, F4–F6) |
| Host ruleset | `inet blueprint_ingress` for the `direct` profile: input closed except loopback, established, ICMP, DHCP, UDP 41641 and the tailnet ranges; forward open with the tailnet anti-spoofing drop for IPv6 (IPv4 added 2026-11-04); persistent through a flush-free `/etc/nftables.conf` | tested (F1–F9, T8) |
| VPN | Tailscale on the host, `--snat-subnet-routes=false`, no Tailscale SSH, exit node, routes or DNS; untagged node; relayed (DERP) because the provider filter admits no UDP 41641 | tested, both start orders and three reboots (the last T8) |
| Names | the test zone public and DNS-only; split DNS on the tailnet answering it with `<tailnet-v4>` and `<tailnet-v6>` | tested |
| Published ports | Traefik alone: 80 and 443 on `0.0.0.0` and `[::]`, 443/udp as well; nothing else published except a resolver on loopback and `tailscale0` | tested (X1, E2) |
| Docker networks | one edge network per stack, internal networks for databases; Docker's default address pools — exhausted once with about thirty networks | tested |
| Start order | `nftables.service` before the network; `docker.service` and `tailscaled.service` unordered and in parallel; the order no longer matters with the SNAT fix | tested (F6–F8, F9 of the failure tests, three reboots, the last T8) |
| Restart behaviour | `unless-stopped` on every container; a crashed Traefik back in 8 s; a hung Traefik not detected without the optional watchdog | tested |
| Logging | container logs size-capped by the log driver; Traefik's access log on a bind mount without rotation on this host (72 MB after three days); `sysstat` and a five-minute container snapshot in the journal | configured — rotation **open** |
| Monitoring | none beyond the journal and `sysstat` | open |
| Backups | borg and borgmatic on the host, a local throwaway repository, no timer, no off-host copy | tested as restore rehearsals only — **open** for real use |
| Recovery | the provider console with `<break-glass>` (M1, M2); the firewall's timed way back; `nft delete table inet blueprint_ingress` from the console | tested |

## The baseline

Each point names what it is for, what it depends on, and how to check it.

### MUST — a Docker host reachable from the internet

1. **Only the reverse proxy's ports are reachable from outside.** Purpose: everything else
   is reached over the VPN. Ports: 80/tcp (ACME HTTP-01 or the redirect to HTTPS) and
   443/tcp; 443/udp only if HTTP/3 is wanted; nothing else.
   Check: an exposure test from a machine outside — `scripts/exposure-test.sh` — and
   `ss -ltunp` on the host.
2. **A filter in front of the host that agrees with that list** — the provider's firewall
   where there is one. Purpose: it holds while the host's own ruleset is being changed or
   is gone. 22/tcp only from a fixed administrative address, or not at all once the VPN
   carries management.
3. **A host ruleset that closes the input path and leaves Docker's forward path alone.**
   Purpose: services that terminate on the host — SSH, a resolver, an agent — answer the
   VPN only. Dependencies: Docker and the VPN own tables of their own; the ruleset is one
   table of its own, loaded with `nft -f`, never through `flush ruleset` (Debian's default
   `nftables.conf` begins with one, and its unit's stop action runs one — on a restart and
   on every package upgrade, unattended included: install `core/traefik`'s drop-in
   `nftables-no-flush.conf`, and use `systemctl reload nftables` on a running host). Check: `nft list tables` before and after, the other
   tables unchanged; a new SSH connection over the VPN works, over the public address it
   does not.
4. **Published ports are judged on the forward path, not on input.** Docker translates a
   published port and forwards the connection; an `input` rule never sees it, so a rule
   there looks closed and filters nothing. Anything that limits who reaches a published
   port belongs on the `forward` hook — the blueprint's `proxied` profile does this — or
   in the filter in front of the host. Bind a port that must not be public to a specific
   address (`127.0.0.1`, the VPN address), never to `0.0.0.0`.
5. **SSH: keys only, no root login, a limited set of accounts.** Check: `sshd -T`.
6. **A second way in that depends on neither the network path nor the VPN** — the
   provider's console with an account that has a password and is refused by sshd.
   Check it once before the VPN becomes the only way in, and again with the VPN stopped.
7. **Every change to the host ruleset with a way back that runs by itself.**
   `systemd-run --on-active=300 nft delete table inet blueprint_ingress`, cancelled with
   `systemctl stop` once a new session over the VPN works. Not a backgrounded `sleep`
   cancelled with `pkill -f`: that pattern matches the shell that runs it.
8. **IPv6 treated as a first-class path.** Every rule exists for both families; the
   provider filter, the host ruleset and the exposure test cover IPv6 as well.
9. **Security updates installed automatically, reboots planned.** A kernel update is
   only in effect after a reboot.

### SHOULD — recommended hardening and operation

1. **The VPN on the host with the client address kept.** With Tailscale on the Docker
   host: `tailscale set --snat-subnet-routes=false` on a host that routes no subnets —
   otherwise whether a VPN client keeps its address depends on whether Docker or
   `tailscaled` started last ([`core/traefik/docs/host-firewall.md`](../core/traefik/docs/host-firewall.md#reaching-the-routers-over-tailscale-on-the-host)).
   Check: `iptables -t nat -S ts-postrouting` holds no `MASQUERADE`.
2. **Split DNS for the VPN-only names**, answering `A` **and** `AAAA` with the host's
   tailnet addresses: with `A` alone an IPv6-preferring client takes the public `AAAA`.
3. **Persistence that is order-independent.** The host ruleset loads before the network;
   Docker and the VPN may start in either order. Check: a reboot with the console open,
   then the ruleset, the VPN and every container.
4. **Docker's daemon settings set once:** a log driver with size limits,
   `userland-proxy: false`, IPv6 and `ip6tables` on for a dual-stack host.
5. **Address pools sized for the number of networks** — with an edge network and an
   internal network per stack, Docker's default pools run out at about thirty. Set
   `default-address-pools` before the networks exist, on ranges that overlap nothing the
   host routes.
6. **Rotate what grows**: the reverse proxy's access log
   (`core/traefik/ops/host-files.manifest` lists a logrotate file), the journal's cap.
7. **A health watchdog for the reverse proxy** — Docker restarts a crashed container but
   not a hung one (`core/traefik/README.md`, "Watchdog").
8. **Backups off the host, and a restore rehearsed** per stack
   ([`backup/borgmatic/RESTORE.md`](../backup/borgmatic/RESTORE.md)).
9. **SSH without TCP forwarding** unless a tunnel is needed; `AllowUsers` with the
   administrative accounts.
10. **A recorded state of the host before every change** — `nft list ruleset`,
    `iptables-save`, `ss -ltunp`, `sshd -T` — so a change can be compared and undone.
11. **Privilege needs a second factor.** An administrative account with
    `NOPASSWD: ALL` and membership in the `docker` group is root for anyone who holds its
    SSH key — the key is the only factor. Give interactive `sudo` a password (or a
    hardware key through `pam_u2f`), and keep the account out of the `docker` group
    unless it runs Compose itself; automation gets its own account with exactly the
    commands it needs. Dependency: the console account of MUST 6 is the way back when the
    password is lost. Check: `sudo -l` shows no `NOPASSWD: ALL`; `id <admin>` lists no
    `docker`. (Final audit, finding FA-08.)
12. **Kernel parameters a forwarding host does not need at their defaults:**
    `net.ipv4.conf.all.send_redirects=0` and `net.ipv4.conf.default.send_redirects=0` (a
    Docker host forwards, but has no reason to tell a client about a better route),
    `net.ipv6.conf.all.accept_redirects=0` and `net.ipv6.conf.default.accept_redirects=0`,
    `kernel.kptr_restrict=1`; optionally `kernel.yama.ptrace_scope=1`. Forwarding
    (`net.ipv4.ip_forward=1`, IPv6 forwarding) stays as Docker sets it. In one file under
    `/etc/sysctl.d/`, loaded with `sysctl --system`. Check: `sysctl` of each name; a
    container still reaches the outside and a published port still answers.
    (FA-18; measured at the Debian 13 defaults on the lab host: `1`, `1`, `0`, `0`.)
13. **SSH with the current algorithm set only.** OpenSSH 10's defaults still offer
    SHA-1 and 64-bit-tag MACs, encrypt-and-MAC modes and NIST curves:

    ```text
    KexAlgorithms mlkem768x25519-sha256,sntrup761x25519-sha512,sntrup761x25519-sha512@openssh.com,curve25519-sha256,curve25519-sha256@libssh.org
    MACs hmac-sha2-256-etm@openssh.com,hmac-sha2-512-etm@openssh.com,umac-128-etm@openssh.com
    HostKeyAlgorithms ssh-ed25519,ssh-ed25519-cert-v01@openssh.com,sk-ssh-ed25519@openssh.com,sk-ssh-ed25519-cert-v01@openssh.com,rsa-sha2-512,rsa-sha2-256
    ```

    The `curve25519` entries stay as the fallback for clients without a post-quantum
    exchange. Before the reload, check every client with `ssh -Q kex` and `ssh -Q mac`,
    and keep a session open: `sshd -t`, `systemctl reload ssh`, then a **new** connection.
    Check: `ssh-audit` shows no `fail`; `sshd -T | grep -E '^(kexalgorithms|macs) '`.
    (FA-17; the set above parsed by `sshd -T` on OpenSSH 10.0p2, not applied on the lab
    host.)
14. **No key for `root` that nobody uses.** A provider's provisioning key stays in
    `/root/.ssh/authorized_keys` after the image boots. With `PermitRootLogin no` it is
    inert, but one configuration mistake away from a way in. Remove it once the
    administrative account works. Check: `/root/.ssh/authorized_keys` is empty or absent.
    (FA-19.)
15. **Watch the SSH daemon's own advisories.** A Critical in `openssh-server` without a
    distribution fix (FA-10 on the lab host) is mitigated by MUST 1–3: SSH answers the
    VPN only. Check: `apt list --upgradable`; the ruleset still refuses 22/tcp from outside.

### OPTIONAL — by threat model and deployment

- **CrowdSec's firewall bouncer** on the host, for ports the reverse proxy never handles
  (`core/crowdsec/docs/firewall-bouncer.md`); its set must never reach the management path.
- **A proxy in front of the origin** (Cloudflare, `proxied` profile) with the origin
  restricted to the proxy's ranges — tested on the lab host (X4, 2026-11-04,
  `docs/architecture.md`); the profile applies to the whole installation.
- **UDP 41641 admitted in the provider filter**, for direct tailnet connections instead
  of a relay.
- **Monitoring and alerting** for the host and the containers; the lab host had none.
- **Kernel and sysctl hardening** beyond SHOULD 12 (Lynis' list: auditd rules, file
  integrity, a GRUB password), measured against Docker's need for forwarding.

## Lessons from the lab host

- A rule that looks right in a file is not proof: every point above was accepted only
  after a measurement from outside the host. A request from the host to itself proves
  nothing about a client — Docker re-sources it.
- The order in which services start decided the VPN's behaviour until the SNAT fix; test
  both orders, not only the boot that happened.
- `docker kill` and `docker stop` count as manual stops: the restart policy then leaves
  the container down.
- A configuration that Traefik rejects on reload goes unnoticed until the next start
  (now checked by `render.sh` and `validate.sh`).

## Open

- SHOULD 11–15 were added after the final audit of the lab host and were **not applied
  there** (decision of 2026-11-04: documentation only); their measurements are the audit's
  readings, not a hardened host.

- Log rotation for the reverse proxy and monitoring were not set up on the lab host.
- Backups ran into a throwaway repository on the same host; an off-host target was not
  tested.
- The IPv4 tailnet anti-spoofing drop (added 2026-11-04) was measured on the lab host
  with a forged source from a container; the operator's own clients confirm that the
  tailnet path still works (regression of 2026-11-04).
