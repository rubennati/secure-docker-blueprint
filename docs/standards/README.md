# Standards guide

Start with the task you are doing. These links lead to the rules and procedures;
this page does not add a second set of requirements. You do not need to read every
standard before making a small change.

## Find your starting point

| Task | Start here |
|---|---|
| Install or operate a server | [Root setup](../../README.md#getting-started), the chosen stack's README, then [deployment lifecycle](deployment-lifecycle.md) for updates and rollback |
| Fix or change an existing stack | [Contributing](../../CONTRIBUTING.md#workflow); use the references below for the files you change |
| Add a new stack | Check [the current application hold](../../ROADMAP.md#on-hold--after-v10-or-not-yet-needed) first; for an agreed addition, use the [new-app checklist](new-app-checklist.md) and [reference stack](../../apps/_reference/) |
| Deploy an application you build | [Custom applications](custom-application.md) and the [development patterns](../../development/) |
| Diagnose a failure | [Known symptoms and fixes](../../TROUBLESHOOTING.md), then the [troubleshooting method](troubleshooting.md) |

## Reference by subject

| Subject | Standards |
|---|---|
| Compose and configuration | [Compose structure](compose-structure.md), [environment files](env-structure.md), [names](naming-conventions.md) |
| Security and credentials | [Security baseline](security-baseline.md), [secret generation and handling](secrets.md) |
| Network and HTTPS routing | [Networks](networking.md), [Traefik security](traefik-security.md), [router labels](traefik-labels.md) |
| Recovery and host integration | [Restore](restore.md), [host-installed files](host-files.md), [log rotation](logrotate.md) |
| Documentation | [Purpose and ownership](documentation-workflow.md), [writing style](writing-style.md) |
| Validation and contribution | [CI checks](ci.md), [verification status model](status-model.md), [commits and public content](commit-rules.md) |

Verification results belong to the generated [Lifecycle overview](../../LIFECYCLE.md).
The [Roadmap](../../ROADMAP.md) owns planned work; each stack's README and
UPSTREAM record its setup, limitations and upgrade evidence.
