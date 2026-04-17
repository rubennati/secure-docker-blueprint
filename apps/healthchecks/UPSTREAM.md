# Upstream Reference

## Source

- **Image:** https://hub.docker.com/r/healthchecks/healthchecks
- **Project home:** https://healthchecks.io/
- **GitHub:** https://github.com/healthchecks/healthchecks
- **Docs:** https://healthchecks.io/docs/self_hosted/
- **License:** BSD 3-Clause
- **Based on version:** `v3.13`
- **Last checked:** 2026-04-17

## What we use

- Official `healthchecks/healthchecks` image, pinned tag
- SQLite backend — default, no external database needed
- Blueprint-standard Traefik + Docker-compose layout
- Bind-mount volume for `./volumes/data/` (the SQLite file + cached assets)

## What we changed and why

| Change | Reason |
|--------|--------|
| Traefik labels instead of port `:8010:8000` | Blueprint routes all HTTP through Traefik |
| Bind-mount volume (`./volumes/data/`) instead of named volume | Consistent with blueprint backup patterns (named volumes are harder to find for non-Docker users) |
| `security_opt: no-new-privileges` | Blueprint baseline |
| Env var `ALLOWED_HOSTS` set to `${APP_TRAEFIK_HOST}` | Inbox source used `*`/missing — Django host-header injection surface |
| Env var `SITE_ROOT` uses `https://${APP_TRAEFIK_HOST}` | Inbox had hardcoded `http://192.168.x.x:8010` (real IP leak prevented) |
| `REGISTRATION_OPEN` defaults to `False` | Inbox didn't set it — self-service signup should be explicit opt-in, not default |
| `DEBUG=False` explicit | Inbox had it; kept as safety |
| SMTP password via env (no `_FILE`) | Upstream does not support `_FILE` for `EMAIL_HOST_PASSWORD`. Stays in `.env`. |
| Access policy default `acc-tailscale` | Personal monitoring pattern; ping URLs only need to be reachable from the monitored hosts, which for most home/small-team setups means VPN |
| Security chain default `sec-3` | Strict headers, soft rate limit — appropriate for a Django app with forms |

## Upgrade checklist

Healthchecks uses semver. Django migrations run on container start.

1. Check [GitHub releases](https://github.com/healthchecks/healthchecks/releases) for breaking changes — especially "Database schema" or "Config changes" sections
2. Back up the SQLite DB:
   ```bash
   docker compose exec app sqlite3 /data/hc.sqlite ".backup '/data/hc.sqlite.backup'"
   cp volumes/data/hc.sqlite.backup /safe/offsite/location/
   ```
3. Bump `APP_TAG` in `.env`
4. `docker compose pull && docker compose up -d`
5. Watch logs for migration output:
   ```bash
   docker compose logs app --tail 100 --follow
   ```
6. Verify UI loads, existing checks still listed

### Rollback

If the upgrade breaks, restore the pre-upgrade SQLite backup and revert `APP_TAG`.

## Related images

None. Self-contained Django app.

## Useful commands

```bash
# Create an additional superuser (or initial one, via Setup step 4)
docker compose exec app /opt/healthchecks/manage.py createsuperuser

# Run any Django management command
docker compose exec app /opt/healthchecks/manage.py <command>

# Backup SQLite DB to a file inside the volume (then copy offsite)
docker compose exec app sqlite3 /data/hc.sqlite ".backup '/data/hc.sqlite.backup'"

# Send a test email (verify SMTP config)
docker compose exec app /opt/healthchecks/manage.py sendtestemail your@email.example

# Django shell (for advanced debugging)
docker compose exec app /opt/healthchecks/manage.py shell
```
