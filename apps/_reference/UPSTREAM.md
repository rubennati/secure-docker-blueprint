# Upstream Reference

> **This is the template.** Copy it with the rest of `apps/_reference/` and replace
> every `__REPLACE_ME__`. Every app in the blueprint carries one of these — it is
> ✅ Ready criteria 8 and 9, and `scripts/ci/lifecycle-report.py` reads the
> `Last verified` line out of it.

## Source

- **Image:** https://hub.docker.com/r/VENDOR/IMAGE
- **GitHub:** https://github.com/VENDOR/REPO
- **Docs:** https://docs.example.com
- **License:** `__REPLACE_ME__` (e.g. MIT, Apache 2.0, AGPL-3.0 — see the license policy in `ROADMAP.md`)
- **Origin:** `__REPLACE_ME__` (e.g. Germany · Nextcloud GmbH · EU — or: US · Acme Inc · non-EU)
- **Based on version:** `__REPLACE_ME__`
- **Last verified:** `__REPLACE_ME__` (v`__REPLACE_ME__`)

> `Last verified: YYYY-MM-DD (vX.Y.Z)` is the current format and the one CI reads.
> The older `Last checked:` field does not satisfy criterion 8 — do not reintroduce it.
> Set this date only when the app was actually verified on a clean install, not when
> the tag was bumped: the date is what the ✅ in the README rests on.

## What we use

- Official image, pinned tag
- …

## Architecture

```
Internet → Traefik (TLS, port 443) → App :PORT
```

## What we changed and why

| Change | Reason |
|--------|--------|
| Docker Secrets | Blueprint standard — passwords never in plain environment variables |
| `app-internal: internal: true` | Database and backend services have no direct internet access |
| … | … |

## Upgrade checklist

1. Read the release notes for breaking changes: LINK
2. Check the GitHub Security tab for advisories against the current version
3. Back up volumes and database before upgrading
4. Bump `APP_TAG` in `.env.example`
5. `docker compose pull && docker compose up -d`
6. Verify core function works
7. Update **Based on version** above — and **Last verified** only if the upgrade was
   actually exercised on a real install

## Useful commands

```bash
# Shell into app
docker compose exec app sh

# Tail logs
docker compose logs app --follow
```
