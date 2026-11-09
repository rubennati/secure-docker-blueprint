---
title: What each monitoring stack catches
description: Uptime checks, a dead-man's switch, host metrics and the receiver the alerts go to — what each one catches, and where the receiver has to run.
---

A service that fails quietly is found by its users. These stacks find it first:
some by asking your services whether they answer, one by noticing that a job has
stopped reporting, one by watching the hosts themselves. Every one of them sends
its alerts somewhere — and where that somewhere runs decides whether the alert
arrives on the day it matters.

None of this is required to run an application. Each is a stack like any other,
behind [Traefik](/infrastructure/traefik/), and each keeps its interface on the
VPN by default.

## Is it up?

**[Uptime Kuma](/monitoring/uptime-kuma/)** and **[Gatus](/monitoring/gatus/)**
both probe your services on a schedule — HTTP, TCP, DNS, certificate expiry — and
alert when an answer is wrong. They differ in where the configuration lives.
Uptime Kuma is configured in its web interface and keeps everything in its
database. Gatus is configured in one YAML file, which can sit in version control
beside the rest of your setup. One of the two is enough.

## Did it run?

**[Healthchecks](/monitoring/healthchecks/)** works the other way round. Each job
pings a URL when it runs; Healthchecks alerts when an expected ping does *not*
arrive. An alarm wired like that detects its own failure: a backup that stopped
running, a timer disabled weeks ago, a host that went down, or a monitor that
died — all of which look like silence to the probes above.
[borgmatic](/operations/backup/) reports to it for that reason.

## What is the host doing?

**[Beszel](/monitoring/beszel/)** shows CPU, memory, disk and load per host and
per container, with threshold alerts. A disk-usage threshold warns before the
outage rather than during it. Further hosts run the
standalone agent, which connects out to the hub and opens no port.

## Where the alerts go

**[ntfy](/monitoring/ntfy/)** receives alerts over HTTP and pushes them to
phones, desktops and scripts. Every stack above can publish to it.

**A receiver on the monitored host stops with it.** When the host goes down, its
monitoring goes down — and a receiver, or an SMTP server, next to it stops too.
The outage that most needs an alert then produces none. ntfy is built to run on
a second host on its own; the ntfy project also runs a public instance, which
gives an off-host path without a second machine.

A channel that has never fired proves nothing. For each one you rely on, trigger
it once on purpose — stop a monitored container, let a check expire, cross a
threshold — and confirm the alert arrives on the device that is supposed to get
it.

## The rest of the category

The repository also ships ciao, Checkmate, Grafana with Prometheus, Zabbix,
Scrutiny for disk health, changedetection.io and Gotify. They are in
[the catalogue](/catalogue/#monitoring), each with what it is and its pinned
version.

## Where to go from here

- Traefik not running yet: [what every server needs](/infrastructure/)
- Backups that report when they stop: [backup and restore](/operations/backup/)
- Something already broken: [when something is broken](/operations/troubleshooting/)
