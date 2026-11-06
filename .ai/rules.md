# Working Rules

Operational guidance for completing work in this repository. Technical standards
are routed through [`AGENTS.md`](../AGENTS.md) and [the task guide](routing.md).

## Scope and authorization

Carry out the agreed task, including the edits and checks needed to complete it.
Authorization remains valid for that scope; do not ask again at each step.

Ask when essential information is missing, a material decision is not covered by
the request, or the next action would extend the scope or introduce consequences
not already authorized. Explain the concrete decision or consequence.

Plan complex work in useful, testable units. A plan does not require a separate
approval unless it introduces such a decision. Run available checks yourself;
hand over commands only when execution needs access or action the user must supply.

Commit, push, merge and deployment authorization follows the requested scope;
see [`commit-rules.md`](../docs/standards/commit-rules.md). Do not overwrite other
work, expose private data, or perform an unauthorized destructive operation.

## Evidence and sources

Use official upstream documentation, releases and registries for the version in
question. Compare them with the repository's actual configuration and test
results. Historical records and community discussions are context, not automatic
instructions for the current task.

Check claims about available image tools, supported options and current releases.
Distinguish a confirmed result, an inference and an unknown. If a check cannot run,
state the limitation; do not report it as passed or change a verification stamp.

An upstream issue does not automatically require waiting or a local workaround.
Recommend a course based on impact, security, support and maintenance cost.

## Proportionate validation

Choose checks that can detect defects caused by the change. Repository-wide CI
requirements still apply before merge; a small local edit need not rerun unrelated
checks at every step. Report relevant failures and distinguish environment problems
from defects. See [`quality-gates.md`](quality-gates.md).

## Documentation and review

Update affected instructions and generated views in the same change set. Use the
[File Map](../docs/maintenance.md#file-map--single-source-of-truth) to change facts
at their source. Record significant decisions, incidents and host evidence where
they belong; routine sessions need no additional log entry.

Write repository content in English and discuss it with the maintainer in German.
Give direct, factual assessments of configurations and products, acknowledge errors,
and state recommendations as recommendations. Avoid personal attacks.

Public content follows
[`commit-rules.md`](../docs/standards/commit-rules.md#public-content).
