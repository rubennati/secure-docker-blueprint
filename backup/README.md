# Backup

Self-hosted backup tools — separate top-level category because backup is ops-cross-cutting (touches every data-producing service) and needs hardware-close access (block devices, mount points, credentials for S3 / SFTP targets). Same rationale as [`monitoring/`](../monitoring/README.md).

## Status

✅ Ready · 🚧 Draft · 📋 Planned

| App | Approach | Status | Notes |
|---|---|---|---|
| Kopia | Deduplicating snapshots to S3 / SFTP / filesystem | 📋 | Modern, fast, Go-based. Web UI + server mode. Good for most homelabs. |
| Borgmatic | Borg wrapper — YAML-config, cron-scheduled, SSH/SFTP targets | 📋 | Config-as-code alternative to Kopia. No UI — runs as a scheduled container. Actively maintained. |
| Bareos | Bacula-fork: Director + Storage + File daemons | 📋 | Enterprise. For regulated backup policies (retention, audit trail). Heavy. |
| UrBackup | Image + file backup for Windows / Linux endpoints | 📋 | Best for workstations — bare-metal restore, web UI, agent-based. |

## Choosing an approach

| Need | Pick |
|---|---|
| "Back up my Docker volumes nightly to S3 / Backblaze — web UI" | Kopia |
| "Back up to SSH/SFTP targets, config-as-code, no UI" | Borgmatic |
| "Back up Windows/Mac workstations + do bare-metal restore" | UrBackup |
| "Regulated backup policy with retention enforcement + audit trail" | Bareos |
| "Just docker-compose-level backup of one app" | Per-app `exec db pg_dump` + `tar czf volumes/` in a cron (no dedicated tool) |

Kopia and Borgmatic overlap in scope (both do deduplicating off-site backup) but differ in UX: Kopia has a web UI and S3-native support; Borgmatic is config-as-code and SSH/SFTP-first. Pick one, not both. The rest of the tools cover distinct workload classes.

## Per-App Backup Isolation

Each app gets its **own dedicated backup repository** — not one shared repository for everything.

**Why isolation matters:**

- **Independent retention**: a database may need daily backups with 90-day retention; a static blog can make do with weekly + 30 days. One policy per app, set where it makes sense.
- **Surgical restore**: recovering Nextcloud does not touch Ghost's backup chain. Restore one app, leave everything else untouched.
- **Blast radius control**: a corrupted or compromised backup repository for one app does not affect any other app's backup history.
- **Failure independence**: if a backup job fails for one app, all other backup jobs continue unaffected.

In practice this means: one `borgmatic.yml` (or Kopia snapshot policy) per app, one target repository path per app, one cron schedule per app.

## Layout

Each app subdirectory follows the blueprint structure:

```
backup/<app>/
├── docker-compose.yml
├── .env.example
├── .gitignore
├── README.md
├── .secrets/        # gitignored
└── volumes/         # gitignored
```

## Why backup is a top-level category (and not under `apps/`)

1. **Ops-cross-cutting** — backup reads from every other service's volumes. Structurally different from a user-facing app.
2. **Privileged access** — typically needs `/dev/` access (block-level), `SYS_ADMIN` cap, or broad read-mounts of other containers' data. Higher security-sensitivity than general apps.
3. **Remote targets** — S3 buckets, offsite SFTP, tape libraries. Deployment has an external network dimension that apps don't.
4. **Consistent with `monitoring/`** — both are Ops concerns with cross-stack visibility. Applying the same rule keeps the repo coherent.

See [`docs/architecture/directory-layout.md`](../docs/architecture/directory-layout.md) (on the `docs` branch) for the full categorisation rule.
