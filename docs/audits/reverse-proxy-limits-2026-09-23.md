# Reverse proxy limits — what the proxy owns, and what the numbers are for

An evaluation, not a decision. It collects what a request passes through in a
blueprint installation, what each layer does well, what the proxy's limits are
actually for, and which questions the chain review has to answer. The review
itself is the ROADMAP item *Traefik labels and middlewares, checked against the
applications*; what it decides is written into
[`../standards/traefik-security.md`](../standards/traefik-security.md), which
owns the chains.

Nothing here changes a chain, a value or a stack.

## Why it exists

Two things this repository measured in September 2026:

- **Five interfaces did not load behind the chain they ship with.** Their first
  load issues more requests than the rate limit's bucket holds, so part of the
  page came back `429`: Windmill (about 850 requests), Twenty (412), Open WebUI
  (173), Dify's workflow editor (291) and CISO Assistant (77). Each was handled
  one at a time — a wider bucket, a different chain — which answers the symptom
  and not the question.
- **The proxy went down and stayed down.** A load test held about 400 parallel
  TLS connections; the container reached its memory limit and the kernel ended
  it. It did not come back, because the nightly log rotation had sent it a
  signal through `docker kill`, which cancels the restart policy until the next
  start. Every route was gone until someone started it by hand.

The first is a limit set without a stated purpose. The second is the proxy
failing at the one job nothing else can do for it. Both point at the same
question: what is this component responsible for, and what should its numbers be
measured against?

## What varies between installations

A blueprint cannot assume its own diagram. The parts in brackets exist in some
installations and not in others:

```text
client
  → [DNS/CDN proxy, e.g. Cloudflare]      not ours; changes the client address
  → host firewall                          not ours; should expose 80 and 443 only
  → [threat enforcement, CrowdSec]         optional, ships default-off
  → reverse proxy (Traefik)                TLS, access policy, routing, headers, limits
  → [front door: Authentik, basic auth]    for applications with no login of their own
  → Docker network                         internal by default, no route out unless asked
  → application                            its own authentication, its own lockout
```

Two consequences the review has to carry:

- **The first hop is not always the proxy.** With a CDN proxy in front, every
  request arrives from that proxy's addresses. Anything the proxy decides per
  client address — rate limits, access policies, bans — then needs the forwarded
  address and a statement about which sender may set it. Without that, a limit
  either counts every visitor as one client or trusts a header anybody can send.
- **Layers are optional by design.** A chain that only holds when CrowdSec is
  switched on is not a chain a blueprint can ship.

## Who does what well

[`../architecture.md`](../architecture.md) already states the rule — a layer
earns its place when it observes, decides, enforces or fails differently from
the others, and every piece of changing state has exactly one owner. Applied to
the path above:

| Layer | Does well | Cannot | If it fails |
|---|---|---|---|
| Host firewall | Closing ports, before a connection exists | Anything about the content of a request | Everything behind it is exposed to whatever the port allows |
| CDN proxy | Absorbing volume, hiding the origin address | Knowing the application | Origin takes the traffic directly |
| Threat enforcement | Recognising a sender by behaviour across requests and time | Judging a single first request | Known-bad senders reach the proxy |
| Reverse proxy | TLS, who may reach a route at all, headers, routing, keeping itself and the origin reachable | Knowing who a user is, or whether a password was right | Every route is gone at once |
| Front door (Authentik, basic auth) | Requiring an identity before the application is reached | Fine-grained rights inside the application | The application answers unauthenticated requests |
| Application | Authentication, lockout after failed attempts, two-factor, roles and rights | Bounding what reaches it | Its own data is at stake |

The proxy is the only layer whose failure takes every route with it. That is the
weight behind the availability part of its job, and the reason the memory limit,
the restart policy and the timeouts are not details.

## What the limits are for

A rate limit in the proxy is worth having when it keeps the proxy and the origin
answering while one client asks for a lot. That is a statement about
availability, and it is measurable: the number is right when a normal first load
passes and a runaway client is slowed.

It is **not** the defence against password guessing. That belongs to the
application — lockout, two-factor, and an audit trail — with a front door for
applications that have no login of their own, and behaviour-based enforcement
watching the same path. A counter in the proxy that survives a restart nowhere
and knows no accounts cannot carry that job. It contributes; it does not own it.

Stated that way, three of the open questions below answer themselves, and the
remaining ones become measurable.

## Evidence on the table

Measured in September 2026, behind Traefik 3.7 with the chains this repository
ships:

| Observation | Number |
|---|---|
| First load, Windmill | ~850 requests; `429` under both shipped buckets (50 and 200) |
| First load, Twenty | 412 requests; 302 × `429` at burst 50, 130 × `429` at burst 200; assets carry `max-age=0`, so a warm browser repeats all of them |
| First load, Open WebUI · Dify editor · CISO Assistant | 173 · 291 · 77 requests; 65 · 64 · 14 × `429` at burst 50 |
| First load, Langfuse · LiteLLM | 152 · 160 requests; no `429` |
| Proxy memory, 400 concurrent held requests | 94.7 MiB against 19.8 MiB idle, without TLS; about 190 KiB per request in flight |
| The same load with a concurrency limit of 100 per client address | 41.2 MiB, and the load ended in 16 s instead of 56 s |
| Concurrency limit and fast requests | 300 fast requests passed a limit of 100 exactly as they passed no limit at all |
| Concurrency limit without a source criterion | One client's budget is every client's budget — a single sender exhausted it |
| Proxy memory, ordinary operation | 45–60 MiB idle, 110–128 MiB while browsers loaded code-split interfaces |

Two findings of the same session are already settled and are inputs, not
questions: the proxy's memory limit now comes from that measurement, and the log
rotation no longer signals the container through `docker kill`, which had
cancelled its restart policy.

## Open questions

1. **What is each chain for?** Every chain states a purpose in one sentence, and
   its numbers follow from it. Without that, the next 429 is answered with
   another bucket.
2. **Static files and dynamic endpoints through the same counter?** Every `429`
   above hit a bundle of static files. Splitting them — a router for the hashed
   asset paths, the limit on the rest — is the surgical answer; it costs one
   more router per stack and knowledge of each application's asset prefix.
3. **Does the proxy limit login paths at all?** A stricter limit on a login path
   is possible and cheap, and it is not what stops password guessing. Worth
   having as a brake, or noise that suggests protection it does not provide?
4. **Concurrency instead of, or beside, frequency.** A limit on requests in
   flight bounds what the proxy pays for — the measurement above shows both the
   effect and its cost. It needs a source criterion, and long-lived requests
   (websockets, streams, job logs) hold their slot for their whole lifetime,
   which is untested here.
5. **Timeouts at the entrypoint.** Held connections are the pattern that took
   the proxy down. Response and idle timeouts bound them without counting
   anything.
6. **Cache headers for hashed assets.** An interface that repeats 412 requests
   on every visit is a load the proxy should not have to absorb. Belongs to the
   application; the question is whether the blueprint states it as a requirement.
7. **Where does the client address come from?** With a CDN proxy in front, per
   address means per CDN address unless the forwarded header is trusted — and
   trusting it needs a statement about who may set it. This affects rate limits,
   access policies and every ban decision.
8. **What does threat enforcement already cover?** CrowdSec watches the same
   requests. Where it decides the same thing, the proxy's counter adds tuning
   work rather than depth.
9. **Applications with no login of their own.** The access policy they ship, and
   the documented way to put a front door in front of them, are part of the
   answer — the operator decides, the blueprint has to make the decision
   informed and the path short.
10. **Different applications, different appetite.** A password manager may be
    worth a stricter setting than a dashboard, at a cost in convenience. The
    review should say how a stack states that, rather than leaving every operator
    to guess from a chain's number.
11. **Local use.** A stack run without a proxy at all is a supported case; no
    decision here may assume the chain exists.

## What decides, and where it is written

Each question is answered with the same three sentences: what does it protect,
what does it cost when it is wrong, and what measurement shows it working. A
change that cannot state all three does not go in.

Where the answer lands:

- the chain or block, in `core/traefik/ops/templates/dynamic/` — with the
  measurement in the comment, as the blocks there already do;
- its purpose and its numbers, in
  [`../standards/traefik-security.md`](../standards/traefik-security.md);
- the choice per stack, in its `.env.example`, with the reason in its
  `README.md`;
- anything an operator must do to an existing installation, in `CHANGELOG.md`
  under *Migration*.

An operator who wants more than the default must be able to turn it up without
editing anything the repository owns. Whether today's variables carry that is
question 10.
