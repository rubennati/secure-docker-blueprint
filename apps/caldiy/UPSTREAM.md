# Upstream Reference

## Source

- **Project site:** https://cal.diy/
- **Docs:** https://cal.diy/docs
- **Docker deployment guide:** https://cal.diy/docs/docker
- **License:** MIT
- **Relationship:** Community-edition spin-out of Cal.com, announced 2026 after Cal.com moved its production code behind a closed-source licence
- **Origin:** Community fork of Cal.com · no dedicated company
- **Last checked:** 2026-04-18

## What we use

- Upstream Cal.diy community image (path TBD at setup — see `.env.example` caveat)
- Official `postgres:17` as primary backend
- Docker Secrets where `_FILE` is supported (same set as Cal.com)

## What we changed vs. upstream examples

Cal.diy docs include a Docker deployment section. Our compose mirrors the `apps/calcom/` blueprint pattern for drop-in consistency:

| Change | Reason |
|--------|--------|
| `app-internal` network (`internal: true`) | DB not reachable from host |
| `security_opt: no-new-privileges:true` on both services | Baseline |
| Healthcheck-gated `depends_on` | Prevents app startup before Postgres is ready |
| Telemetry disabled (`CALCOM_TELEMETRY_DISABLED=1`) | Blueprint default |
| `_FILE`-based Docker Secrets for everything the app supports | Consistent with Cal.com sibling |
| `DB_PWD_INLINE` for Prisma URL | Same limitation as Cal.com; documented |

## Why Cal.diy exists and why we ship it

Cal.com, Inc. announced in 2026 that they split their codebase:

- **Closed-source production core** — rewritten authentication, data handling, commercial billing. Stays with Cal.com, Inc. under a proprietary licence.
- **Cal.diy** — a stripped community edition under MIT, community-maintained, explicitly labelled "strictly for personal, non-production use." No security guarantees from Cal.com, Inc.

For a self-hosting blueprint that explicitly targets OSS-first deployments, Cal.diy is the honest option for users who want a fully OSS path and accept the "non-production" framing.

For users who want commercial-grade support + continued feature development, `apps/calcom/` with a pinned pre-2026 AGPL tag remains accessible — and that is what most production users should pick.

## Upgrade checklist

Cal.diy is community-maintained, so release cadence is less predictable than Cal.com.

1. Watch the Cal.diy upstream repo (link it here once the GitHub URL is confirmed)
2. Back up:
   ```bash
   docker compose exec db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' \
     > caldiy-$(date +%Y%m%d).sql
   tar czf caldiy-data-$(date +%Y%m%d).tgz ./volumes/data
   ```
3. Bump `APP_TAG` in `.env`
4. `docker compose pull && docker compose up -d`
5. Watch Prisma migrations on first boot:
   ```bash
   docker compose logs app --follow
   ```

### Rollback

Restore DB dump, revert `APP_TAG`. Prisma migrations are forward-only.

## Useful commands

```bash
# Shell into app
docker compose exec app sh

# Manual DB dump
docker compose exec db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > dump.sql

# Restore DB
cat dump.sql | docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

## Known unknowns at blueprint-draft time

- Exact upstream registry path of the Docker image — verify at `cal.diy/docs/docker` before first boot
- GitHub repository URL (Cal.diy docs reference GitHub for feedback but don't link directly in the landing page copy)
- Feature differences from Cal.com — enterprise / routing-forms / team-workflow modules may be stripped
- Tagging convention — whether upstream uses semver, dated tags, or rolling `latest`

These are reasons this file is marked draft. Live-testing will resolve them.
