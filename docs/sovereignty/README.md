# Data Sovereignty

Self-hosting answers *where the data sits*. It does not, on its own, answer who
governs the software, what still leaves the machine, or who sees the traffic on
its way in. Those are three separate questions, and running your own server
answers none of them by itself.

This area keeps them apart, because conflating them is how a stack ends up
"self-hosted" while its traffic is decrypted by a third party and its intrusion
detection reports to an external API.

| | Question | Document |
|---|---|---|
| 1 | Who owns and licenses the software? | [provenance.md](provenance.md) |
| 2 | What leaves the machine while it runs? | [data-egress.md](data-egress.md) |
| 3 | Who sits between the visitor and the server? | [edge.md](edge.md) |

## Why these three and not a score

Ranking the stacks 1–10 would compress "AGPL, German GmbH, no outbound calls"
and "source-available, no stated jurisdiction, reports to a vendor API" onto one
axis. The argument then moves to the weighting instead of to the facts, and the
number goes stale silently — a licence change or an acquisition invalidates it
without anything failing.

So this publishes the facts and their sources, and leaves the weighing to the
operator. What counts as acceptable depends on the deployment: a public blog and
a practice's patient records do not share a threshold.

## What this is not

Not legal advice, and not a GDPR compliance statement. Where the software comes
from and where personal data is processed are related questions, but they are not
the same one — a US-owned project running entirely on your German server may be
fine, and an EU-owned project that phones home may not be. The facts here are
inputs to that assessment, not the assessment.

## Where the facts live

Per-stack, in `UPSTREAM.md` — one owner per fact:

```markdown
- **License:** AGPL-3.0
- **Origin:** Germany · Nextcloud GmbH · EU
```

`scripts/ci/sovereignty-report.py` reads all of them into
`site/src/data/sovereignty.json`, which the operator site renders. CI runs it
with `--check`, so a stack cannot lose either field without failing the build.
