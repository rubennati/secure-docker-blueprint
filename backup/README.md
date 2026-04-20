# Backup

Self-hosted backup tools — separate top-level category because backup is ops-cross-cutting (touches every data-producing service) and needs hardware-close access (block devices, mount points, credentials for S3 / SFTP targets). Same rationale as [`monitoring/`](../monitoring/README.md).

## Status

✅ live-tested · ⚠️ draft · 📋 planned

| App | Approach | Status | Notes |
|---|---|---|---|
| Kopia | Deduplicating snapshots to S3 / SFTP / filesystem | 📋 | Modern, fast, Go-based. Desktop UI + server mode. Good for most homelabs. |
| Bareos | Bacula-fork: Director + Storage + File daemons | 📋 | Enterprise. For regulated backup policies (retention, audit trail). Heavy. |
| UrBackup | Image + file backup for Windows / Linux endpoints | 📋 | Best for workstations — bare-metal restore, web UI, agent-based. |

## Choosing an approach

| Need | Pick |
|---|---|
| "Back up my Docker volumes nightly to S3 / Backblaze" | Kopia |
| "Back up Windows/Mac workstations + do bare-metal restore" | UrBackup |
| "Regulated backup policy with retention enforcement + audit trail" | Bareos |
| "Just docker-compose-level backup of one app" | Per-app `exec db pg_dump` + `tar czf volumes/` in a cron (no dedicated tool) |

The three tools do not overlap meaningfully — pick one per workload class. Kopia alone covers the 80% homelab case.

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
