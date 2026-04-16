# Paperless-ngx — Configuration Reference

App-specific configuration options, bucketed by effort-vs-value:
- **Mandatory** — every production instance sets this
- **Nice-to-have** — recommended default unless there is a reason against it
- **Use-case-dependent** — only when a concrete need is documented (the use-case is named as the trigger)

Items not listed = leave upstream default.

Table format per item: `ENV var | What | Our default | Effort | Bucket | Rationale / note`. Cross-references between sections are marked explicitly. "Current state vs. repo" at the end of each section.

See also: [README.md](README.md) for setup/verify, [UPSTREAM.md](UPSTREAM.md) for source references and upgrade checklist.

---

## Structure

| Section | Mandatory | Nice-to-have | Use-case | Don't touch |
|---|---:|---:|---:|---:|
| Hosting & Security | 4 | 3 | 11 | — |
| Authentication & SSO | 1 | 4 | 10 | — |
| Document Consumption | 0 | 7 | 26 | 1 |
| OCR Settings | 3 | 7 | 6 | — |
| Software Tweaks | 3 | 5 | 10 | 1 |
| Audit, Trash & Backup-Lifecycle | 1 ENV + 2 procedures | 2 ENV + 3 procedures | 1 ENV + 3 procedures | — |
| Paths & File-Name-Handling | 0 | 2 | 6 | 6 |
| Docker-Options, Frontend & Monitoring | 2 | 0 | 5 | 2 |
| Email (Send / Parse / OAuth / GPG) | 0 | 8 | 7 | — |
| Extensions / Integrations | 0 | 0 | 3 (TODO) | — |
| **ENV totals** | **14** | **38** | **91** | **10** |

Plus **5 mandatory procedures/commands** (sanity-check, exporter, upgrade playbook, `createsuperuser`, trash retention) and **14 management commands** catalogued with intended use.

---

## Open Mandatory Action-Items (delta vs. current repo)

What is missing today but falls into a Mandatory bucket:

| # | Section | Item | Impact |
|---|---|---|---|
| 1 | Hosting & Security | `PAPERLESS_ALLOWED_HOSTS` | Default `*` leaves HTTP Host-header injection window open |
| 2 | Hosting & Security | `PAPERLESS_TRUSTED_PROXIES` | Audit log shows wrong IPs, fail2ban/CrowdSec see nothing useful |
| 3 | Hosting & Security | `PAPERLESS_URL` (explicit; also covers ALLOWED_HOSTS / CORS / CSRF implicitly) | Single source of truth for the instance URL |
| 4 | Hosting & Security | `PAPERLESS_USE_X_FORWARD_HOST` + `USE_X_FORWARD_PORT` + `PROXY_SSL_HEADER` | We set proxy headers in Traefik, Django doesn't trust them → broken redirects / cookie flags |
| 5 | Authentication | `PAPERLESS_ACCOUNT_ALLOW_SIGNUPS=false` | Explicit instead of implicit default |
| 6 | Audit & Trash | `PAPERLESS_EMPTY_TRASH_DELAY=30` | Explicit for compliance relevance |
| 7 | Backup-Lifecycle | Automated backup via `document_exporter` + scheduled cron | No backup = no archive |
| 8 | Backup-Lifecycle | DB upgrade playbook (Paperless major + PostgreSQL major) | Currently blank; risk at next major bump |

## Nice-to-have items with security impact

Not mandatory in our definition, but largest ROI in the security bucket:

| # | Section | Item | Why it matters |
|---|---|---|---|
| A | Document Consumption | `WEBHOOKS_ALLOW_INTERNAL_REQUESTS=false` | SSRF protection — prevents workflow webhooks from hitting Redis / internal APIs |
| B | Document Consumption | `WEBHOOKS_ALLOWED_SCHEMES=https` | No cleartext webhook payloads |
| C | Authentication | `PAPERLESS_SESSION_COOKIE_AGE=172800` (2 days instead of 2 weeks) | Shorter exposure window on cookie theft |
| D | Hosting (use-case) | `/admin/` router with `acc-tailscale` | Django admin bypasses MFA and SSO — brute-forceable if public |

## Noted inconsistencies (aufräum candidates, not CONFIG decisions)

- Our env names `PAPERLESS_WORKERS` / `PAPERLESS_THREADS` differ from upstream (`PAPERLESS_WEBSERVER_WORKERS` / `PAPERLESS_THREADS_PER_WORKER`) — unnecessary abstraction
- `OCR_USER_ARGS` is hardcoded in `docker-compose.yml` — should be a `.env.example` variable
- Upstream has deprecation hints pointing `PAPERLESS_WEBSERVER_WORKERS/BIND_ADDR/PORT` towards `GRANIAN_*` — check at next major upgrade

---

# 1. Hosting & Security

## 1.1 Mandatory

| ENV var | What | Our default | Effort | Rationale / note |
|---|---|---|---|---|
| `PAPERLESS_SECRET_KEY` | Django session-signing key | `file:///run/secrets/SECRET_KEY` via `PAPERLESS_SECRET_KEY_FILE` | low | Django's default is public; every instance needs its own. Via Docker Secret. |
| `PAPERLESS_URL` | Base URL of the instance | `https://${APP_TRAEFIK_HOST}` | low | Implicitly sets `ALLOWED_HOSTS`, `CORS_ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` in one place — single source of truth. |
| `PAPERLESS_ALLOWED_HOSTS` | HTTP host-header allowlist | implicit via `PAPERLESS_URL` — **do not set separately** | — | Default `*` enables host-header injection (password-reset emails with attacker-controlled domain). Covered by `PAPERLESS_URL`. Exception: multi-domain setup → explicit comma list. |
| `PAPERLESS_TRUSTED_PROXIES` | Accepted reverse-proxy IPs for X-Forwarded-For | `172.16.0.0/12` (Docker default pool) | low | Without this the audit log only shows Traefik's IP; fail2ban/CrowdSec are blind; X-Forwarded-For spoofing possible. Exception: exact `proxy-public` subnet known → set more precisely. |

## 1.2 Nice-to-have

| ENV var | What | Our default | Effort | Rationale / note |
|---|---|---|---|---|
| `PAPERLESS_USE_X_FORWARD_HOST` | Django honours `X-Forwarded-Host` | `true` | low | We set this header in Traefik. Without it: redirects and outbound emails show wrong host URL. |
| `PAPERLESS_USE_X_FORWARD_PORT` | Django honours `X-Forwarded-Port` | `true` | low | Consistent with `USE_X_FORWARD_HOST`; matters when running on non-standard ports. |
| `PAPERLESS_PROXY_SSL_HEADER` | Django detects HTTPS via proxy header | `["HTTP_X_FORWARDED_PROTO", "https"]` | medium | We set `X-Forwarded-Proto=https` in Traefik; Django may trust it. Critical for secure session-cookie flag and correct `https://` redirects. **Only valid because Traefik is the sole ingress.** Do not set if any plain-HTTP path can reach the container. |
| `PAPERLESS_COOKIE_PREFIX` | Session-cookie namespace | unset | low | Needed only when multiple Paperless instances share a host domain (otherwise cookie collision). |

## 1.3 Use-case-dependent

| Use-case | ENV var | Recommendation | Note |
|---|---|---|---|
| **Sub-path hosting** (`example.com/paperless`) | `PAPERLESS_FORCE_SCRIPT_NAME` = `/paperless` | Only with sub-path routing; we use a subdomain → not relevant | Must be set together with `PAPERLESS_STATIC_URL` |
| **Sub-path hosting** | `PAPERLESS_STATIC_URL` = `/paperless/static/` | Only with `FORCE_SCRIPT_NAME` | — |
| **Forward-Auth active** (Authentik/Authelia proxy mode) | `PAPERLESS_ENABLE_HTTP_REMOTE_USER` = `true` | Only when the ingress **strips** incoming `Remote-User` headers and sets them post-auth | **Critical**: without stripping = auth bypass (any client sending `Remote-User: admin`). Setup must be documented + tested. |
| **Forward-Auth + API use** | `PAPERLESS_ENABLE_HTTP_REMOTE_USER_API` = `true` | Only with Forward-Auth, same condition | For API clients prefer API tokens over header auth |
| **Custom auth-header name** | `PAPERLESS_HTTP_REMOTE_USER_HEADER_NAME` | Only if provider uses a non-default header | — |
| **SSO logout chain** | `PAPERLESS_LOGOUT_REDIRECT_URL` = OIDC end-session URL | Only with OIDC SSO | Without it, user lands on Paperless login page instead of ending the SSO session |
| **CORS for external client** | `PAPERLESS_CORS_ALLOWED_HOSTS` | Additional origins explicitly | Only for mobile/web client on a different domain |
| **CSRF for external frontend** | `PAPERLESS_CSRF_TRUSTED_ORIGINS` | Additional origins explicitly | Only for embedding / PWA |
| **Self-signed IMAP** | `PAPERLESS_EMAIL_CERTIFICATE_LOCATION` | Path to CA file | Only for internal IMAP with own CA |
| **Initial admin without `createsuperuser`** | `PAPERLESS_ADMIN_USER` + `ADMIN_PASSWORD` + `ADMIN_MAIL` | Unset — we use `docker compose exec app python manage.py createsuperuser` | Only in Kubernetes/ECS where no interactive exec is available. Does **not** change existing passwords. |
| **⚠️ Dangerous** | `PAPERLESS_AUTO_LOGIN_USERNAME` | **Never set if publicly reachable** | Bypasses authentication entirely. Only in strictly-internal setups behind another full auth layer. |

## 1.4 Current state vs. repo

- ✅ `PAPERLESS_URL` — set in `docker-compose.yml`
- ✅ `PAPERLESS_SECRET_KEY_FILE` — set via Docker Secret
- ❌ `PAPERLESS_ALLOWED_HOSTS` — **missing** (default `*` active)
- ❌ `PAPERLESS_TRUSTED_PROXIES` — **missing**
- ❌ `PAPERLESS_USE_X_FORWARD_HOST` — missing
- ❌ `PAPERLESS_USE_X_FORWARD_PORT` — missing
- ❌ `PAPERLESS_PROXY_SSL_HEADER` — missing

We already set `X-Forwarded-Proto=https` + `X-Forwarded-Host` in the Traefik middleware, but Django does not trust them because the mandatory/nice-to-have vars are missing. Silent half-setup that can cause hard-to-diagnose bugs (wrong links in emails, wrong secure flags on cookies).

---

# 2. Authentication & SSO

Builds on Hosting & Security. In particular: `PAPERLESS_DISABLE_REGULAR_LOGIN` does **not** protect the Django `/admin/` endpoint — that needs a separate Traefik router protection (use-case row there).

## 2.1 Mandatory

| ENV var | What | Our default | Effort | Rationale / note |
|---|---|---|---|---|
| `PAPERLESS_ACCOUNT_ALLOW_SIGNUPS` | Self-registration via login page | `false` (explicit) | low | Default is already `false`, but an archive app must document intent. Prevents regressions on future upstream default changes. Exception: planned signup flow with moderation workflow. |

## 2.2 Nice-to-have

| ENV var | What | Our default | Effort | Rationale / note |
|---|---|---|---|---|
| `PAPERLESS_ACCOUNT_DEFAULT_HTTP_PROTOCOL` | Protocol for generated URLs (login callbacks, mails) | `https` (explicit) | low | Default is already `https`, but security-relevant enough to document. Prevents silent HTTP-URL generation on config drift. |
| `PAPERLESS_SESSION_COOKIE_AGE` | Session cookie lifetime (seconds) | `172800` (2 days) instead of default `1209600` (2 weeks) | low | Shorter lifetime = less damage on stolen cookie / device compromise. User re-login every 2 days is acceptable in practice. Exception on UX complaints: `604800` (1 week). |
| `PAPERLESS_ACCOUNT_SESSION_REMEMBER` | Enables "remember me" (otherwise cookie ends with browser close) | `true` (default) | low | When `true`: `SESSION_COOKIE_AGE` applies. When `false`: cookie dies with browser — too aggressive for typical Paperless use. |
| `PAPERLESS_ACCOUNT_EMAIL_VERIFICATION` | Email verification on signup / email change | `mandatory` if SMTP is configured | low | Protects against typos and fake accounts. Paperless automatically sets this to `none` if no SMTP server is reachable — so without SMTP setup the item has no effect. |

## 2.3 Use-case-dependent

| Use-case | ENV var | Recommendation | Note |
|---|---|---|---|
| **Activate SSO (OIDC via Authentik etc.)** | `PAPERLESS_APPS` = `allauth.socialaccount.providers.openid_connect` | Only once SSO provider is configured | Django app must be loaded before provider is usable |
| **Activate SSO** | `PAPERLESS_SOCIALACCOUNT_PROVIDERS` (JSON) | Via `sso.yml` overlay; client secret stays in `.env` | Paperless does not support `_FILE` inside a JSON env var. Known limitation, documented in README. |
| **SSO + auto-provision** | `PAPERLESS_SOCIAL_AUTO_SIGNUP` = `true` | Only if every IdP user should auto-get a Paperless account | Default `false` = user must already exist in Paperless. `true` = anyone in the IdP group gets auto-provisioned on first login. |
| **SSO active** | `PAPERLESS_SOCIALACCOUNT_ALLOW_SIGNUPS` | `true` = SSO users may create new accounts; `false` = only existing users may link | Default `true`. With `AUTO_SIGNUP=false`, `ALLOW_SIGNUPS=true` enables manual account linking in profile. |
| **SSO + group sync** | `PAPERLESS_SOCIAL_ACCOUNT_SYNC_GROUPS` = `true` | Only if IdP groups map 1:1 onto Paperless groups (same names) | Groups must pre-exist in Paperless. IdP provider config needs `"SCOPES": ["openid","profile","email","groups"]`. |
| **SSO + default groups for new users** | `PAPERLESS_SOCIAL_ACCOUNT_DEFAULT_GROUPS` | Comma list of existing Paperless groups | Users are added to these on first SSO login |
| **SSO exclusive (no regular login)** | `PAPERLESS_DISABLE_REGULAR_LOGIN` = `true` | Only with functional SSO chain + `/admin/` protection via Traefik | **Important**: does not protect `/admin/` or API token auth. `/admin/` router with `acc-tailscale` is the complement, otherwise Django-admin login bypass. |
| **SSO + auto-redirect** | `PAPERLESS_REDIRECT_LOGIN_TO_SSO` = `true` | Combine with `DISABLE_REGULAR_LOGIN` | Users land at SSO provider instead of Paperless login page |
| **Signups allowed (internal)** | `PAPERLESS_ACCOUNT_DEFAULT_GROUPS` | Comma list; groups must exist | Only relevant when `ACCOUNT_ALLOW_SIGNUPS=true` — not our case |
| **Privacy / UX** | `PAPERLESS_ACCOUNT_EMAIL_UNKNOWN_ACCOUNTS` | Default `true` | Controls whether password-reset to unknown email sends a mail (`true`) or not (`false`). `false` prevents user enumeration. For internal Paperless default is fine. |

## 2.4 Current state vs. repo

- ❌ `PAPERLESS_ACCOUNT_ALLOW_SIGNUPS` — missing (default `false` active but not documented)
- ❌ `PAPERLESS_ACCOUNT_DEFAULT_HTTP_PROTOCOL` — missing
- ❌ `PAPERLESS_SESSION_COOKIE_AGE` — missing (2-week default active)
- ❌ `PAPERLESS_ACCOUNT_EMAIL_VERIFICATION` — missing (driven by SMTP status, not explicit)
- 🟡 SSO block (`SOCIALACCOUNT_*`, `DISABLE_REGULAR_LOGIN`, `REDIRECT_LOGIN_TO_SSO`) — prepared as `sso.yml` overlay + commented examples in `.env.example`, not active

---

# 3. Document Consumption

## 3.1 Core consumption logic

| ENV var | What | Our default | Effort | Bucket | Rationale / note |
|---|---|---|---|---|---|
| `PAPERLESS_CONSUMER_IGNORE_PATTERNS` | Paths to ignore during consume | default (`.DS_Store`, `._*`, `.stfolder/*`, `.stversions/*`, `desktop.ini`, `@eaDir/*`, `Thumbs.db`) | low | **Nice-to-have** | Default covers Mac/Windows/Synology junk. Extend only if scanner produces its own cruft. |
| `PAPERLESS_CONSUMER_BARCODE_SCANNER` | Barcode-detection library | default `PYZBAR` | low | **Nice-to-have** | Fallback `ZXING` only when pyzbar misses small/low-quality codes. Relevant only if barcode features are active. |
| `PAPERLESS_CONSUMER_DELETE_DUPLICATES` | Auto-delete duplicate scans | `false` (default) | low | **Use-case-dependent** | Use-case: scanner grabs same stack twice, mail forwards with repeated attachments. Default `false` is safer — Paperless keeps original as evidence. Flip to `true` only with high-dupe workflow and accepted risk. |
| `PAPERLESS_CONSUMER_DISABLE` | Disable consume-folder entirely | unset | low | **Use-case-dependent** | Use-case: Paperless fed only via UI upload / API, consume folder not mounted. Saves a few MB RAM. |
| `PAPERLESS_CONSUMER_RECURSIVE` | Watch subdirs of consume-folder | `false` (default) | low | **Use-case-dependent** | Use-case: required for `SUBDIRS_AS_TAGS` or `COLLATE_DOUBLE_SIDED`. Otherwise off. |
| `PAPERLESS_CONSUMER_SUBDIRS_AS_TAGS` | Subfolder names → tags | `false` (default) | medium | **Use-case-dependent** | Use-case: scan workflow with pre-sorted folders (`consume/invoices/`, `consume/contracts/`). Requires `RECURSIVE=true`. |

## 3.2 Polling vs. iNotify

| ENV var | What | Our default | Effort | Bucket | Rationale / note |
|---|---|---|---|---|---|
| `PAPERLESS_CONSUMER_POLLING` | Poll interval (s) instead of iNotify | `0` (iNotify active) | low | **Use-case-dependent** | Use-case: consume folder on network share (CIFS/NFS/SSHFS) where iNotify events do not propagate. Reasonable value `30`-`60`. Costs CPU per poll. |
| `PAPERLESS_CONSUMER_POLLING_RETRY_COUNT` | Retries before consuming identical file | default `5` | low | **Use-case-dependent** | Only with polling. Default usually fine. |
| `PAPERLESS_CONSUMER_POLLING_DELAY` | Pause between retries (s) | default `5` | low | **Use-case-dependent** | Only with polling. Increase on slow network shares where large PDFs are still copying. |
| `PAPERLESS_CONSUMER_INOTIFY_DELAY` | Settle time after last event before consume | default `0.5` (s) | low | **Nice-to-have** | Raise to `2.0`-`5.0` when scanner/network fires multiple events per file — otherwise double consume. |

## 3.3 Pre/Post-consumption hooks

Powerful but each script is a new dependency and attack surface. Activate only with concrete need.

| ENV var | What | Our default | Effort | Bucket | Rationale / note |
|---|---|---|---|---|---|
| `PAPERLESS_PRE_CONSUME_SCRIPT` | Script executed before consume | unset | high | **Use-case-dependent** | Use-cases: external OCR (e.g. `pdf2pdfocr` for higher quality), rotation, custom de-duplication, metadata injection. **Script blocks consume — runtime matters.** Script must be reachable inside container (volume mount), executable. |
| `PAPERLESS_POST_CONSUME_SCRIPT` | Script executed after consume | unset | high | **Use-case-dependent** | Use-cases: notifications (Ntfy/Gotify/Telegram), external archive sync, webhook to CrowdSec or n8n. Alternative for most cases: **Paperless Workflows** (UI-based, more maintainable). Script route only when workflow actions aren't enough. |

**Operational note**: both hooks receive the document as env vars (`DOCUMENT_SOURCE_PATH`, `DOCUMENT_ID`, etc.). When used → append to README "Known Issues": "Pre/Post hooks active, scripts version-controlled in `./config/hooks/`."

## 3.4 Barcodes

Separate feature cluster. Enable only if a scan workflow with barcode pages exists.

| ENV var | What | Our default | Effort | Bucket | Rationale / note |
|---|---|---|---|---|---|
| `PAPERLESS_CONSUMER_ENABLE_BARCODES` | Master switch for barcode detection | `false` (default) | medium | **Use-case-dependent** | Use-case: multi-scans on one stack split via PATCH-T separator. Pointless without workflow. |
| `PAPERLESS_CONSUMER_BARCODE_TIFF_SUPPORT` | Scan TIFFs for barcodes | `false` | low | **Use-case-dependent** | Only on TIFF-producing scanners (rare). |
| `PAPERLESS_CONSUMER_BARCODE_STRING` | Separator-barcode text | default `PATCHT` | low | **Use-case-dependent** | Change only with custom separator sheets. |
| `PAPERLESS_CONSUMER_BARCODE_RETAIN_SPLIT_PAGES` | Keep separator page in output | `false` (default) | low | **Use-case-dependent** | Default discards pure separator page (correct). `true` only if the separator carries payload data. |
| `PAPERLESS_CONSUMER_ENABLE_ASN_BARCODE` | Set Archive Serial Number from barcode | `false` | medium | **Use-case-dependent** | Use-case: paper originals get ASN sticker at scan time → ASN ends up on document → later paper↔digital mapping. Good for structured paper archive. |
| `PAPERLESS_CONSUMER_ASN_BARCODE_PREFIX` | ASN prefix | default `ASN` | low | **Use-case-dependent** | Only with `ENABLE_ASN_BARCODE`. |
| `PAPERLESS_CONSUMER_BARCODE_UPSCALE` | Pre-detection upscale factor | default `0.0` (off) | low | **Use-case-dependent** | `1.5`-`2.0` when small codes are missed. CPU cost. |
| `PAPERLESS_CONSUMER_BARCODE_DPI` | DPI for PDF→image during barcode detection | default `300` | low | **Use-case-dependent** | `600` for small/fine codes. Combinable with `UPSCALE`. |
| `PAPERLESS_CONSUMER_BARCODE_MAX_PAGES` | Scan first N pages only | default `0` (all) | low | **Use-case-dependent** | `1` or `2` when separator/ASN pages are always at the front — saves massive CPU on large PDFs. |
| `PAPERLESS_CONSUMER_ENABLE_TAG_BARCODE` | Assign tags from barcodes | `false` | medium | **Use-case-dependent** | Use-case: scanner workflow with tag stickers/codes. Otherwise not needed. |
| `PAPERLESS_CONSUMER_TAG_BARCODE_MAPPING` | Regex mapping barcode→tag | default `{"TAG:(.*)": "\\g<1>"}` | medium | **Use-case-dependent** | Only with `ENABLE_TAG_BARCODE`. |

## 3.5 Workflow webhooks (SSRF protection)

Paperless workflows can send outbound webhooks. Without guardrails → SSRF vector (anyone with admin access builds a workflow → request to internal services).

| ENV var | What | Our default | Effort | Bucket | Rationale / note |
|---|---|---|---|---|---|
| `PAPERLESS_WEBHOOKS_ALLOW_INTERNAL_REQUESTS` | Webhooks may hit local/private IPs | `false` | low | **Nice-to-have** | Default `true` = SSRF risk. `false` prevents workflow webhook from reaching `http://redis:6379/` or `http://localhost:8000/api/`. |
| `PAPERLESS_WEBHOOKS_ALLOWED_SCHEMES` | Allowed URL schemes for webhooks | `https` (not default `http,https`) | low | **Nice-to-have** | Webhook payloads may carry sensitive data → no cleartext. |
| `PAPERLESS_WEBHOOKS_ALLOWED_PORTS` | Whitelist of ports for webhooks | unset (= all ports allowed) | low | **Use-case-dependent** | Use-case: only specific external webhook targets — then `443,8443` or similar. Otherwise leave unset. |

## 3.6 Collate double-sided scans

For scanners without duplex. Nice feature when workflow requires it, otherwise off.

| ENV var | What | Our default | Effort | Bucket | Rationale / note |
|---|---|---|---|---|---|
| `PAPERLESS_CONSUMER_ENABLE_COLLATE_DOUBLE_SIDED` | Merge two single-sided scans into duplex | `false` | medium | **Use-case-dependent** | Use-case: ADF without duplex; user scans fronts, flips stack, scans backs. Requires `RECURSIVE=true`. |
| `PAPERLESS_CONSUMER_COLLATE_DOUBLE_SIDED_SUBDIR_NAME` | Subdir where collate is active | default `double-sided` | low | **Use-case-dependent** | Only with collate enabled. |
| `PAPERLESS_CONSUMER_COLLATE_DOUBLE_SIDED_TIFF_SUPPORT` | Allow TIFFs in collate | `false` | low | **Use-case-dependent** | Only with collate + TIFF scanner. |

## 3.7 Thumbnails & dates (side items)

| ENV var | What | Our default | Effort | Bucket | Rationale / note |
|---|---|---|---|---|---|
| `PAPERLESS_FILENAME_DATE_ORDER` | Parse date from filename | unset | low | **Use-case-dependent** | Use-case: scanner saves with `YYYY-MM-DD` prefix → Paperless treats that as creation date. Convenient when workflow looks like that. |
| `PAPERLESS_DATE_ORDER` | Day/month/year order when parsing document text | default `DMY` | low | **Nice-to-have** | For DE/EU documents `DMY` matches; US docs → `MDY`. Set once and date detection works more reliably. |
| `PAPERLESS_IGNORE_DATES` | Date values to ignore (e.g. birth date) | unset | low | **Use-case-dependent** | Use-case: forms with fixed dates that would otherwise be detected as document date. |
| `PAPERLESS_NUMBER_OF_SUGGESTED_DATES` | Alternative dates to suggest | default `3` | low | **Nice-to-have** | Default is useful. `0` disables it for very slow hardware. |
| `PAPERLESS_THUMBNAIL_FONT_NAME` | Font for plain-text thumbnails | default `LiberationSerif` | low | **—** | Don't touch. |

## 3.8 Current state vs. repo

| Bucket | Item | State |
|---|---|---|
| Nice-to-have | `CONSUMER_IGNORE_PATTERNS` | default active, not explicit |
| Nice-to-have | `INOTIFY_DELAY` | default active, not explicit |
| Nice-to-have | `WEBHOOKS_ALLOW_INTERNAL_REQUESTS` | **missing** (default `true` → SSRF window open) |
| Nice-to-have | `WEBHOOKS_ALLOWED_SCHEMES` | **missing** (default `http,https`) |
| Nice-to-have | `DATE_ORDER` | **missing** (default `DMY` happens to fit) |
| Use-case | Barcodes | not active — OK |
| Use-case | Pre/Post hooks | not active — OK |
| Use-case | SUBDIRS_AS_TAGS / COLLATE | not active — OK |

---

# 4. OCR Settings

## 4.1 Languages (setup)

| ENV var | What | Our default | Effort | Bucket | Rationale / note |
|---|---|---|---|---|---|
| `PAPERLESS_OCR_LANGUAGE` | Primary OCR language(s) (Tesseract codes) | `deu` (DE/AT docs) | low | **Mandatory** | Default `eng`. Without adjustment = significantly worse OCR for non-English documents. Multiple via `+` (`deu+eng`), costs CPU. 3-letter codes per Tesseract (`chi_sim`, not `chi-sim`). |
| `PAPERLESS_OCR_LANGUAGES` | Additional language packages installed (Docker-only) | `deu` | low | **Mandatory** | Docker-only env var. Installs tesseract-traineddata on container start. Must cover `OCR_LANGUAGE`, otherwise OCR runs empty. Space-separated list. Docker tag `chi-tra` — package names and Tesseract codes sometimes differ. |

## 4.2 OCR mode & output

| ENV var | What | Our default | Effort | Bucket | Rationale / note |
|---|---|---|---|---|---|
| `PAPERLESS_OCR_MODE` | When to run OCR | `skip` (default) | low | **Nice-to-have** | `skip` = OCR only pages without text (safe, saves CPU, preserves scanner OCR). `redo` = replace scanner OCR (when scanner quality is bad). `force` = rasterise everything (large files, only for exotic PDFs). Default is the right compromise 95% of the time. |
| `PAPERLESS_OCR_SKIP_ARCHIVE_FILE` | Create archive (PDF/A) version | `never` (default) | low | **Use-case-dependent** | Use-case: tight storage + docs already have text → `with_text`. `always` = keep only original (saves space, loses "searchable"-guarantee). |
| `PAPERLESS_OCR_OUTPUT_TYPE` | PDF variant for archive version | `pdfa` (default) | low | **Nice-to-have** | `pdfa` = PDF/A-2b, archive standard, good default. `pdfa-1` only if external archive system requires PDF/A-1. `pdf` = no PDF/A conversion, smaller files but not archive-standard. |

## 4.3 Image pre-processing

| ENV var | What | Our default | Effort | Bucket | Rationale / note |
|---|---|---|---|---|---|
| `PAPERLESS_OCR_CLEAN` | Run unpaper before tesseract | `clean` (default) | low | **Nice-to-have** | `clean` = unpaper cleans input, better OCR, costs CPU. `clean-final` = cleaned images replace original (loses color/detail). `none` = no unpaper. Default fits scan workflow. |
| `PAPERLESS_OCR_DESKEW` | Correct slight rotations | `true` (default) | low | **Nice-to-have** | Straightens skewed scans before OCR. Standard scanner issue. **Note**: automatically disabled when `OCR_MODE=redo`. |
| `PAPERLESS_OCR_ROTATE_PAGES` | Detect + correct 90°/180°/270° rotation | `true` (default) | low | **Nice-to-have** | Fixes pages fed upside-down. |
| `PAPERLESS_OCR_ROTATE_PAGES_THRESHOLD` | Rotation detection aggressiveness | default `12` | low | **Use-case-dependent** | Use-case: correctly-oriented pages get falsely rotated → raise to `15` (conservative). Wrongly-oriented not fixed → lower to `2`-`5` (aggressive). |
| `PAPERLESS_OCR_IMAGE_DPI` | Fallback DPI for images without DPI metadata | unset (auto) | low | **Use-case-dependent** | Use-case: scanner produces DPI-less images → PDF dimensioned wrong. Then set to scanner DPI (e.g. `300` or `600`). |
| `PAPERLESS_OCR_COLOR_CONVERSION_STRATEGY` | Ghostscript color strategy for PDF/A generation | default (`LeaveColorUnchanged` implicit) | low | **Use-case-dependent** | Use-case: PDF/A creation fails with colour-profile errors → switch to `RGB` or `UseDeviceIndependentColor`. Don't change without cause — some options break archive creation. |

## 4.4 Performance limits

| ENV var | What | Our default | Effort | Bucket | Rationale / note |
|---|---|---|---|---|---|
| `PAPERLESS_OCR_PAGES` | OCR only first N pages | `3` | low | **Nice-to-have** | Default: all pages. Our `3` = aggressive performance decision, good for bulk consume (invoices, contracts usually have relevant content on pages 1-3). For full-text-search-relevant docs: remove / set `0`. **Note**: with `OCR_MODE=redo`/`force`, text on excluded pages is copied verbatim, not re-OCRed. |
| `PAPERLESS_OCR_MAX_IMAGE_PIXELS` | Pixel limit for OCR input | unset (Pillow default) | low | **Use-case-dependent** | Use-case: very large scans trigger OCR warning and are skipped → raise. Protection against malicious files — change only for real documents affected. |

## 4.5 Advanced — OCRmyPDF user-args

| ENV var | What | Our default | Effort | Bucket | Rationale / note |
|---|---|---|---|---|---|
| `PAPERLESS_OCR_USER_ARGS` | JSON with OCRmyPDF API options | `{"invalidate_digital_signatures":true,"continue_on_soft_render_error":true}` | medium | **Mandatory** (with these values) | The two defaults prevent the two most common consume failures: signed PDFs (bank, tax office) block OCR without `invalidate_digital_signatures`. Soft render errors otherwise fail the whole document. Other useful options per use-case: `"optimize": 3` (smaller archive PDFs, +CPU), `"unpaper_args": "--pre-rotate 90"` (special scanner patterns). **Note**: many API options are mutually incompatible — test before setting. |

## 4.6 Important incompatibilities (from upstream docs)

Prevents self-braking combinations:

| Combination | Effect |
|---|---|
| `OCR_CLEAN=clean-final` + `OCR_MODE=redo` | `clean-final` silently falls back to `clean` |
| `OCR_DESKEW=true` + `OCR_MODE=redo` | Deskew automatically disabled |
| `OCR_PAGES=N` + `OCR_MODE=redo`/`force` | Excluded pages keep original text verbatim — no OCR |

## 4.7 Current state vs. repo

| Bucket | Item | State |
|---|---|---|
| Mandatory | `OCR_LANGUAGE` | ✅ `deu` in `.env.example` |
| Mandatory | `OCR_LANGUAGES` | ✅ `deu` in `.env.example` |
| Mandatory | `OCR_USER_ARGS` | ✅ sensible defaults in `docker-compose.yml` (hardcoded, not env variable) |
| Nice-to-have | `OCR_PAGES` | ✅ set to `3` |
| Nice-to-have | `OCR_MODE` / `OCR_CLEAN` / `OCR_DESKEW` / `OCR_ROTATE_PAGES` / `OCR_OUTPUT_TYPE` | defaults active, not explicit |
| Use-case | rest | not set — OK |

**Minor friction**: `OCR_USER_ARGS` is hardcoded in `docker-compose.yml` instead of `.env.example` — would be more maintainable as an env variable (end-user can tweak without patching compose).

---

# 5. Software Tweaks

## 5.1 Performance — worker topology

Core rule: `TASK_WORKERS × THREADS_PER_WORKER ≤ CPU cores`. Exceed = Paperless becomes extremely slow.

| ENV var | What | Our default | Effort | Bucket | Rationale / note |
|---|---|---|---|---|---|
| `PAPERLESS_TASK_WORKERS` | Parallel background tasks (OCR, mail, index, training) | `1` (small), `2` on ≥4 cores | low | **Mandatory** | Upstream default `1`. Without deliberate setting, bulk consume yields single-file OCR and hour-long queues. Scale with cores. |
| `PAPERLESS_THREADS_PER_WORKER` | Tesseract threads within a worker job (OCR parallelisation per document) | `2` | low | **Mandatory** | Without setting Paperless uses `max(floor(cpu_count / TASK_WORKERS), 1)` — can compute wrong values under container CPU limits. Explicit = reproducible. |
| `PAPERLESS_WEBSERVER_WORKERS` | Frontend/API processes (Granian) | `1` (default) | low | **Nice-to-have** | Default fits single-user / small teams. `2-4` only for many concurrent UI users or heavy API integration. Each worker loads the app separately → RAM multiplier. |
| `PAPERLESS_WORKER_TIMEOUT` | Hard-kill timeout for OCR jobs (s) | default `1800` (30 min) | low | **Use-case-dependent** | Use-case: very large PDFs (100+ pages, weak hardware) get aborted → raise to `3600`. Don't raise pointlessly, otherwise broken jobs hang forever. |

## 5.2 Memory & conversion limits

| ENV var | What | Our default | Effort | Bucket | Rationale / note |
|---|---|---|---|---|---|
| `PAPERLESS_CONVERT_MEMORY_LIMIT` | ImageMagick RAM cap (MB) | unset (= unlimited) | low | **Use-case-dependent** | Use-case: OOM or "unable to extend pixel cache" errors during consume → set to `512` or `1024`, forces ImageMagick to disk instead of RAM. Slower but stable. |
| `PAPERLESS_CONVERT_TMPDIR` | ImageMagick scratch disk | unset (= `/tmp`) | low | **Use-case-dependent** | Use-case: `/tmp` is tmpfs (RAM) and fills up on large docs → redirect to host-mounted volume. Standard Docker default is fine. |
| `PAPERLESS_MAX_IMAGE_PIXELS` | Pillow-global pixel limit | unset (Pillow default) | low | **Use-case-dependent** | See OCR section — DoS protection, raise only on purpose. |
| `PAPERLESS_ENABLE_COMPRESSION` | HTTP gzip compression in webserver | default `true` | low | **—** | Do not set explicitly. Traefik `compress` middleware in `sec-*` chain handles this. Double compression is pointless. Per upstream, proxy-level compression is preferred anyway. |

## 5.3 Database — connection & caching

| ENV var | What | Our default | Effort | Bucket | Rationale / note |
|---|---|---|---|---|---|
| `PAPERLESS_DB_TIMEOUT` | Connection timeout (s) | unset (Django default) | low | **Use-case-dependent** | Use-case: slow or remote DB → raise. Unnecessary for local container DB. |
| `PAPERLESS_DB_POOLSIZE` | PostgreSQL connection pool per worker | unset (no pool) | medium | **Use-case-dependent** | Use-case: "couldn't get a connection" errors or DB timeouts under load → `8`. **Note**: PG `max_connections` must match: `(TASK_WORKERS + CELERY_WORKERS) × POOLSIZE + safety-margin`. With 1/1 worker and pool 8 → `≥20`. PG only, ignored on MariaDB. |
| `PAPERLESS_DB_READ_CACHE_ENABLED` | Cache DB reads in Redis | `false` (default) | high | **Use-case-dependent** | Use-case: very DB-heavy UI / many documents + noticeable query latency. **Danger**: every external DB manipulation (backup-restore, manual SQL) requires `invalidate_cachalot` command. Without it = cache serves stale data → inconsistency bugs. Don't enable lightly. |
| `PAPERLESS_READ_CACHE_TTL` | Cache lifetime (s) | default `3600` (1h) | low | **Use-case-dependent** | Only with `DB_READ_CACHE_ENABLED=true`. High TTL = more RAM, longer staleness on manual DB changes. |
| `PAPERLESS_READ_CACHE_REDIS_URL` | Dedicated Redis instance for read-cache | unset (= main Redis) | high | **Use-case-dependent** | Use-case: cache entries shouldn't compete with scheduled tasks / queues for RAM → separate Redis with `maxmemory-policy allkeys-lru`. Not needed in standard setup. |

## 5.4 Scheduling — cron jobs

| ENV var | What | Our default | Effort | Bucket | Rationale / note |
|---|---|---|---|---|---|
| `PAPERLESS_EMAIL_TASK_CRON` | Email fetch interval | `disable` (when no mail rules); otherwise default `*/10 * * * *` | low | **Use-case-dependent** | No mail consume? Then `disable` saves 144 idle polls/day. With mail rules: default fine; time-critical workflows → `*/5`. |
| `PAPERLESS_TRAIN_TASK_CRON` | Auto-classifier training | default `5 */1 * * *` | low | **Nice-to-have** | Hourly is enough. Very high docs/hour → more often. |
| `PAPERLESS_INDEX_TASK_CRON` | Search-index optimisation | default `0 0 * * *` | low | **Nice-to-have** | Nightly, good. Only shift if another I/O-heavy job runs at the same time (lock collision possible on SQLite). |
| `PAPERLESS_SANITY_TASK_CRON` | Checksum / file-integrity check | default `30 0 * * sun` | low | **Mandatory** | Weekly integrity check **must** run on an archive system. Default fine. Results should be visible in log. |
| `PAPERLESS_WORKFLOW_SCHEDULED_TASK_CRON` | Evaluate scheduled workflows | default `5 */1 * * *` | low | **Use-case-dependent** | No workflows active → `disable`. Otherwise default. |

*(Trash crons `EMPTY_TRASH_TASK_CRON` + `EMPTY_TRASH_DELAY` live in the Audit + Trash + Backup section — not repeated here.)*

## 5.5 NLP & date parsing

| ENV var | What | Our default | Effort | Bucket | Rationale / note |
|---|---|---|---|---|---|
| `PAPERLESS_ENABLE_NLTK` | Natural-language-processing for matching model | `true` (default) | low | **Nice-to-have** | Substantially better auto-classification (tags/correspondents). Disable only for very weak hardware or if matching isn't used. Docker image has NLTK data bundled — no separate download. |
| `PAPERLESS_DATE_PARSER_LANGUAGES` | Languages for content-date parser | derive from `OCR_LANGUAGE` | low | **Nice-to-have** | **Note**: different format than `OCR_LANGUAGE`! OCR = Tesseract codes (`deu`), date parser = dateparser codes (`de`). Combine via `+` (e.g. `de+en`). Without: Paperless infers from OCR language — usually works, but explicit is more robust. |

## 5.6 Django apps

| ENV var | What | Our default | Effort | Bucket | Rationale / note |
|---|---|---|---|---|---|
| `PAPERLESS_APPS` | Load additional Django apps | unset | low | **Use-case-dependent** | Use-case: SSO activation → `allauth.socialaccount.providers.openid_connect`. See Auth section. Only add what you actually need, watch order with multiple apps. |

## 5.7 Current state vs. repo

| Bucket | Item | State |
|---|---|---|
| Mandatory | `TASK_WORKERS` | ✅ set to `1` |
| Mandatory | `THREADS_PER_WORKER` (as `PAPERLESS_THREADS`) | ✅ set to `2` |
| Mandatory | `SANITY_TASK_CRON` | default active, not explicit |
| Nice-to-have | `WEBSERVER_WORKERS` (as `PAPERLESS_WORKERS`) | ✅ set to `1` |
| Nice-to-have | `ENABLE_NLTK` | default `true`, not explicit |
| Nice-to-have | `DATE_PARSER_LANGUAGES` | **missing** |
| Nice-to-have | `TRAIN_TASK_CRON` / `INDEX_TASK_CRON` | defaults active, not explicit |
| Use-case | rest (DB cache, DB pool, memory limits, etc.) | not set — OK |

**Inconsistency**: our env names in `.env.example` (`PAPERLESS_WORKERS` / `PAPERLESS_TASK_WORKERS` / `PAPERLESS_THREADS`) map to upstream names in compose. It works, but is unnecessary abstraction. Future cleanup: rename to upstream names (`PAPERLESS_WEBSERVER_WORKERS` / `PAPERLESS_TASK_WORKERS` / `PAPERLESS_THREADS_PER_WORKER`) for 1:1 comparability with upstream docs.

---

# 6. Audit, Trash & Backup-Lifecycle

This section mixes ENV-based items with procedures (backup, upgrade, management commands). Both bucketed consistently.

## 6.1 Audit trail

Paperless maintains an audit log of changes to documents, tags, correspondents, document types. Single switch but important for traceability.

| ENV var | What | Our default | Effort | Bucket | Rationale / note |
|---|---|---|---|---|---|
| `PAPERLESS_AUDIT_LOG_ENABLED` | Enable audit log | `true` (explicit) | low | **Nice-to-have** | Default is `true`, but for an archive system the audit log **is** the core evidence of who changed what when. Explicit setting documents intent — survives upstream default changes. |

**Management side**: the `prune_audit_logs` command trims log entries of deleted documents (see Management Commands below).

## 6.2 Trash / retention

Paperless has a trash mechanism. Deleted documents go there first and get permanently removed after N days.

| ENV var | What | Our default | Effort | Bucket | Rationale / note |
|---|---|---|---|---|---|
| `PAPERLESS_EMPTY_TRASH_DELAY` | Days until permanent deletion | `30` (default) | low | **Mandatory** | Default `30` is enough for oops-recovery. Explicit because it's compliance-relevant. Below `7` dangerous (no weekend undo). Above `90` only for compliance requirement — costs storage because files sit in trash dir. |
| `PAPERLESS_EMPTY_TRASH_TASK_CRON` | When trash is emptied | default `0 1 * * *` (daily 01:00) | low | **Nice-to-have** | Default fine. Move only when competing I/O runs at 01:00 (backup window). |
| `PAPERLESS_EMPTY_TRASH_DIR` | Target dir for deleted originals | unset (= hard delete) | low | **Use-case-dependent** | Use-case: extra safety net beyond Paperless trash. Setting to `../media/trash` (or own persistent volume) = originals are moved there instead of deleted. **Important**: volume must be persistent (survives container updates) and needs own retention/cleanup outside Paperless. |

## 6.3 Backup strategy (procedure, not ENV-based)

For an archive app, backup is **not** nice-to-have — it is core infrastructure. Paperless offers two approaches.

### What must be backed up

| Asset | Content | Container path | Host path (our layout) |
|---|---|---|---|
| **Database** | Document metadata, tags, users, workflows, audit log | — | `./volumes/postgres/` |
| **Media** | Originals + archive PDFs + thumbnails | `/usr/src/paperless/media` | `./volumes/media/` |
| **Data** | Search index + ML classifier model + logs | `/usr/src/paperless/data` | `./volumes/data/` |
| **Consume** | Inbox folder — usually empty, but important during scans | `/usr/src/paperless/consume` | `./volumes/consume/` |
| **Export** | Target of document_exporter | `/usr/src/paperless/export` | `./volumes/export/` |
| **Secrets** | DB password, secret key, SMTP password | — | `./.secrets/` |
| **Config** | Env, compose | — | `.env` + `docker-compose.yml` |

### Recommended procedures (bucketed)

| Procedure | What | Bucket | Note |
|---|---|---|---|
| **`document_exporter` (Paperless-native)** | Exports metadata + originals + manifest as directory or ZIP. Incremental via `--compare-checksums`. | **Mandatory** | App-native, version-independent. Import via `document_importer` into empty instance — survives major upgrades. Caveat: **API tokens** are not exported, must be regenerated. |
| **Volume backup** (tar / restic / borg) | Back up all `./volumes/*` + `.secrets/` + `.env` | **Nice-to-have** | Fast, complete, but **version-bound**: restore only works in same Paperless+Postgres version. No cross-version rescue. |
| **Off-site sync** | Restic / Borg / rsync to S3, Hetzner Storage Box, etc. | **Nice-to-have** | Protection against host loss. Client-side encryption (Restic/Borg do it natively). |
| **Scheduled automation** | Cron or systemd timer triggering `document_exporter --compare-checksums --delete` + external sync | **Nice-to-have** | Without automation, backup doesn't happen. Schedule before Paperless's own cron jobs (index-optimise etc.) or in a maintenance window. |
| **Passphrase-encrypted export** | `document_exporter --passphrase <secret>` | **Use-case-dependent** | Use-case: export leaves trusted host. **Critical**: without passphrase, no import. Store passphrase safely. |
| **`--data-only` export** | Only DB, no files | **Use-case-dependent** | Use-case: DB major upgrade (PG 16 → 17) without dragging the full media zip. |
| **Test restore** (periodic) | Restore into separate staging Paperless, verify a few docs | **Use-case-dependent** | Use-case: compliance / audit requirement. Without test-restore, backup claim is unproven. |

### Things to watch when backing up

- **Stop or very quiet Paperless** during volume backups (otherwise half-written files / DB-vs-files inconsistency)
- `document_exporter` runs while Paperless runs — but **documents consumed during export** don't land in the export. Exporter records the timestamp.
- **Do NOT mount `/export/` into the container image** — use a host volume — otherwise lost on container rebuild

## 6.4 Database upgrade strategy

| Scenario | Procedure | Bucket |
|---|---|---|
| **Paperless minor upgrade** (e.g. 2.20 → 2.21) | `docker compose pull && docker compose up -d` — migrations run automatically | **Mandatory procedure** to document |
| **Paperless major upgrade** (2.x → 3.0) | 1. Backup via `document_exporter`. 2. Read release notes. 3. Compose pull. 4. Up. 5. If issues: rollback via restore into empty container. | **Mandatory procedure** to document |
| **PostgreSQL major upgrade** (16 → 17) | 1. `document_exporter --data-only`. 2. Fresh Postgres instance with new version. 3. Start Paperless against new DB. 4. `document_importer --data-only`. | **Use-case-dependent** — only when PG major is changed |

## 6.5 Management commands (maintenance cheatsheet)

Per command: purpose, when to use. All via `docker compose exec app <cmd>`.

| Command | What | Bucket | When to use |
|---|---|---|---|
| `document_sanity_checker` | Checks checksums, missing files, permissions, orphans | **Mandatory** | Runs weekly via cron. Manually on corruption suspicion or after volume restore. |
| `document_exporter <target>` | Export backup | **Mandatory** | Before every major upgrade. Regularly via automation. |
| `document_importer <source>` | Restore backup | **Mandatory** | After setting up an empty instance or for recovery. |
| `createsuperuser` | Create admin user | **Mandatory** | Once after first setup. Alternative via `PAPERLESS_ADMIN_USER` (see Hosting section). |
| `prune_audit_logs` | Trim audit entries of deleted docs | **Nice-to-have** | Once after audit-log activation when there are old pre-activation deleted docs. Rarely needed otherwise. |
| `document_thumbnails` | Regenerate thumbnails | **Nice-to-have** | After upgrade with new thumbnail format or when thumbnails are missing/broken. |
| `document_index reindex` | Rebuild search index from scratch | **Use-case** | When search returns empty or faulty results. |
| `document_index optimize` | Compact search index | **—** | Runs automatically nightly. Manual not needed. |
| `document_retagger` | Apply matching rules to existing docs | **Use-case** | After larger change of matching rules. Testable with `--id-range`. |
| `document_renamer` | Rename after changed `FILENAME_FORMAT` | **Use-case** | Only after filename format change. **Backup first.** |
| `document_fuzzy_match --ratio 85` | Fuzzy duplicate detection (post-consume) | **Use-case** | Once after import of large legacy batches. `--delete` only with backup. |
| `document_create_classifier` | Retrain ML classifier | **—** | Runs automatically hourly. Manual only for debug. |
| `document_archiver --overwrite` | Regenerate PDF/A archive versions | **Use-case** | After OCR settings change when existing archive files are affected. |
| `invalidate_cachalot` | Invalidate DB read cache | **Use-case** | Only when `DB_READ_CACHE_ENABLED=true` AND manual DB change happens (restore, external SQL). Otherwise data inconsistency. |
| `decrypt_documents` | Remove legacy encryption | **—** | Only for ancient instances with pre-0.9 encryption. No longer relevant. |

## 6.6 Incident-response cross-reference

When things break — quick moves that fit this section:

| Situation | Quick move |
|---|---|
| Suspected compromised account | Keep Paperless reachable but switch access to `acc-deny` chain (Traefik hot-reload, no container restart) → only shell-access users can still enter, admin kill-switch |
| Suspected data corruption | Don't stop the container → immediately `document_sanity_checker` + `document_exporter`, then diagnose |
| Pre/post-consume script out of control | Set `PAPERLESS_PRE_CONSUME_SCRIPT` / `POST_CONSUME_SCRIPT` to empty + `docker compose up -d` (faster than script debug) |
| OOM from large doc | Set `PAPERLESS_CONVERT_MEMORY_LIMIT` temporarily → restart |

(Full incident-response playbook = separate topic, not part of this CONFIG.md.)

## 6.7 Current state vs. repo

| Bucket | Item | State |
|---|---|---|
| Nice-to-have | `AUDIT_LOG_ENABLED=true` | default active, not explicit |
| Mandatory | `EMPTY_TRASH_DELAY` | default `30` active, not explicit |
| Use-case | `EMPTY_TRASH_DIR` | not set (= hard delete) — OK |
| Mandatory procedure | `document_exporter` backup | **documentation missing** — UPSTREAM.md mentions it but no concrete automation recommendation |
| Mandatory procedure | Scheduled backup automation | **missing** — no cron, no script in repo |
| Mandatory procedure | DB upgrade playbook | **missing** — Paperless minor covered via `docker compose pull`, Postgres major is blank |
| Mandatory command | `createsuperuser` in README | ✅ present |
| Mandatory command | `document_sanity_checker` documented | **missing in README** (runs automatically, but manual invocation needed on suspicion) |

---

# 7. Paths & File-Name-Handling

## 7.1 Paths & folders (mostly Docker-bound)

Most path vars are for bare-metal installs. In the Docker container they're fixed container paths — the host side is adjusted via volume mounts in `docker-compose.yml`, not via ENV.

| ENV var | What | Our default | Effort | Bucket | Rationale / note |
|---|---|---|---|---|---|
| `PAPERLESS_CONSUMPTION_DIR` | Container path of consume folder | `/usr/src/paperless/consume` (fixed) | — | **—** | Don't change in Docker. Host side via volume mount (`./volumes/consume:/usr/src/paperless/consume`). |
| `PAPERLESS_DATA_DIR` | Container path for search index, SQLite, ML model | `/usr/src/paperless/data` (fixed) | — | **—** | As above — volume mount handles host path. |
| `PAPERLESS_MEDIA_ROOT` | Container path for originals + archive PDFs | `/usr/src/paperless/media` (fixed) | — | **—** | As above. |
| `PAPERLESS_STATICDIR` | Static assets (CSS/JS from frontend) | default, don't touch | — | **—** | Only relevant for sub-path setup, see Hosting section `STATIC_URL`. |
| `PAPERLESS_LOGGING_DIR` | Log directory | default `DATA_DIR/log/` | low | **Use-case-dependent** | Use-case: centralised log forwarding (Promtail/Loki/Filebeat) needs dedicated mount — redirect to its own volume. Otherwise default fine. |
| `PAPERLESS_NLTK_DIR` | Path to NLTK data for matching | pre-bundled in Docker image | — | **—** | Docker image ships it. Must be set for bare-metal. Don't touch in Docker. |
| `PAPERLESS_MODEL_FILE` | Path to ML classifier file | default `DATA_DIR/classification_model.pickle` | — | **Use-case-dependent** | Use-case: move classifier to another volume (e.g. faster SSD for DATA_DIR). Rare. |
| `PAPERLESS_LOGROTATE_MAX_SIZE` | Log file size before rotation (bytes) | default `1 MiB` | low | **Nice-to-have** | Default fine for most. With active log forwarding (Promtail consumes immediately) keep small; for local debug raise to `10485760` (10 MiB) for better debuggability. |
| `PAPERLESS_LOGROTATE_MAX_BACKUPS` | Number of rotated log files | default `20` | low | **Nice-to-have** | Default fine. `5-10` usually enough, `50+` for longer forensic window. |

## 7.2 Filename format (main topic of this section)

Paperless stores documents under internal UUIDs (`0000123.pdf`) by default. With `PAPERLESS_FILENAME_FORMAT` this becomes a readable structure in the media directory.

Relevance depends on workflow: if you only go through the Paperless UI, filename doesn't matter. If you hold backups for manual inspection or process files outside Paperless, it's worth gold.

| ENV var | What | Our default | Effort | Bucket | Rationale / note |
|---|---|---|---|---|---|
| `PAPERLESS_FILENAME_FORMAT` | Template for filenames/folders in media dir | unset (= UUIDs) | medium | **Use-case-dependent** | Use-case: backup inspection without Paperless, external DMS sync, compliance (human-readable filing). After activation: every new document renamed accordingly. Existing documents only after `document_renamer` command. **Backup before change.** Jinja templates very powerful — see below. |
| `PAPERLESS_FILENAME_FORMAT_REMOVE_NONE` | Omit empty placeholders instead of writing "none" | `false` (default) | low | **Use-case-dependent** | Only relevant with `FILENAME_FORMAT`. `true` = `{correspondent}/{title}` becomes `/title.pdf` on missing correspondent instead of `none/title.pdf`. Cleaner for UI browsing. |

### Template placeholders (cheatsheet)

Simple variables for `PAPERLESS_FILENAME_FORMAT`:

```
{{ title }}                 {{ correspondent }}        {{ document_type }}
{{ tag_list }}              {{ asn }}                  {{ owner_username }}
{{ original_name }}         {{ doc_pk }}               {{ storage_path }}

{{ created }}               {{ added }}                     ← ISO-date YYYY-MM-DD
{{ created_year }}          {{ created_year_short }}
{{ created_month }}         {{ created_month_name }}        {{ created_month_name_short }}
{{ created_day }}
{{ added_year }}  ...etc
```

### Example formats (by complexity)

| Format | Result | Use-case |
|---|---|---|
| `{{ created_year }}/{{ correspondent }}/{{ title }}` | `2026/Finanzamt/Invoice XY.pdf` | Simple chronological filing by year + sender |
| `{{ correspondent }}/{{ created_year }}/{{ created_month }}/{{ title }}` | `Bank/2026/04/Statement.pdf` | Sender-centric with year + month |
| `{{ document_type }}/{{ created }} {{ title }}` | `Invoice/2026-04-15 Invoice_0042.pdf` | Type-centric, ISO date in name |
| `{{ storage_path }}/{{ title }}` | Uses UI-set storage path + title | Combinable with UI-based storage paths (see below) |

### Advanced — Jinja templates

`PAPERLESS_FILENAME_FORMAT` supports full Jinja templates. With if/else, loops, custom filters (`get_cf_value`, `datetime`, `localize_date`, `slugify`).

| Feature | Purpose | Bucket |
|---|---|---|
| `{% if document.archive_serial_number %}...{% endif %}` | Conditional paths (ASN ranges, PDF-only, etc.) | **Use-case-dependent** |
| `{{ custom_fields \| get_cf_value('Invoice Number') }}` | Custom fields into filename | **Use-case-dependent** |
| `{{ document.created \| localize_date('medium', 'de_DE') }}` | Localised date formats | **Use-case-dependent** |
| `{{ title \| slugify }}` | URL-safe filename without umlauts / special chars | **Use-case-dependent** — important on unicode-hostile filesystems / sync tools |

**Pitfalls**:
- OS path-length limits (especially Windows/NAS with 260-char cap) — can be exceeded with long `tag_list`
- Placeholder errors → Paperless silently falls back to default naming (no UI warning, only log)
- `../` in FILENAME_FORMAT works → files land outside media dir → **lost on Docker rebuild**. Never use.

## 7.3 Storage paths (app-internal, not ENV)

Paperless also has a UI feature called "Storage Paths":
- Filename formats configurable per document in the UI
- Assigned per document via matching algorithm (like tags/correspondents) or manually
- Override the global `FILENAME_FORMAT` for assigned documents

| Feature | Purpose | Bucket |
|---|---|---|
| Maintain storage paths in UI | Different filing structure per document group (e.g. invoices flat-by-date, contracts by sender) | **Use-case-dependent** — app-internal, no ENV |

**Relationship to `FILENAME_FORMAT`**: globally, `FILENAME_FORMAT` applies to all docs without a storage path. Docs with a storage path ignore the global format and use the storage-path template. Both can reference each other via the `{{ storage_path }}` placeholder.

## 7.4 Binaries (bare-metal relics)

Only relevant when Paperless does **not** run in our Docker image — there `convert` + `gs` live on standard paths.

| ENV var | What | Our default | Bucket |
|---|---|---|---|
| `PAPERLESS_CONVERT_BINARY` | Path to ImageMagick `convert` | Docker default | **—** |
| `PAPERLESS_GS_BINARY` | Path to Ghostscript `gs` | Docker default | **—** |

## 7.5 Current state vs. repo

| Bucket | Item | State |
|---|---|---|
| — | `PATH` vars (`CONSUMPTION_DIR`, `DATA_DIR`, etc.) | Docker defaults active, volume mounts in place |
| Nice-to-have | `LOGROTATE_MAX_SIZE` / `MAX_BACKUPS` | defaults active, not explicit |
| Use-case | `FILENAME_FORMAT` | **not active** (= UUID names in media dir) |
| Use-case | `FILENAME_FORMAT_REMOVE_NONE` | not relevant (FILENAME_FORMAT off) |
| Use-case | Storage paths (UI) | not configured (as expected, UI feature) |

**Open consideration**: for future backup inspection / external DMS sync, a moderate `FILENAME_FORMAT` (e.g. `{{ created_year }}/{{ correspondent }}/{{ title }}`) would be clear value — costs only one `document_renamer` run after activation. Not mandatory but worth considering.

---

# 8. Docker-Options, Frontend & Monitoring

## 8.1 Cross-references (already covered)

| Topic | Where covered |
|---|---|
| Logging (`LOGGING_DIR`, `LOGROTATE_MAX_SIZE`, `LOGROTATE_MAX_BACKUPS`) | → Paths & File-Name-Handling |
| Binaries (`CONVERT_BINARY`, `GS_BINARY`) | → Paths & File-Name-Handling |
| Worker topology (`WEBSERVER_WORKERS`, `TASK_WORKERS`, `THREADS_PER_WORKER`) | → Software Tweaks |
| OCR language install (`OCR_LANGUAGES`) | → OCR Settings |

## 8.2 Container network binding (Docker internals)

| ENV var | What | Our default | Effort | Bucket | Rationale / note |
|---|---|---|---|---|---|
| `PAPERLESS_BIND_ADDR` | IP the webserver listens on inside container | default `::` (all interfaces, IPv6 enabled) | — | **—** | Don't change. Container is internally isolated, external reachability is Traefik's job. Relevant only in very specific Podman multi-container-pod setups. Future name: `GRANIAN_HOST`. |
| `PAPERLESS_PORT` | Port inside container | default `8000` | — | **—** | Don't change. Traefik labels reference `8000`. External port mapping via `docker-compose.yml` — not needed because Traefik. Future name: `GRANIAN_PORT`. |

## 8.3 User / group mapping

| ENV var | What | Our default | Effort | Bucket | Rationale / note |
|---|---|---|---|---|---|
| `USERMAP_UID` | UID under which Paperless runs in container | `1000` (matches default Debian/Ubuntu user) | low | **Mandatory** | Must match host-side owner of volume dirs. Otherwise: Paperless can't write to `./volumes/consume/` → silently broken. Check with `id -u` on host. |
| `USERMAP_GID` | GID analogous | `1000` | low | **Mandatory** | As above. `id -g` on host. |

**Important**: **do NOT set `user:` in the compose file**. Paperless-ngx uses s6-overlay — must start as root to initialise `/run`, then drops to `USERMAP_UID`. Direct `user: 1000:1000` bypasses s6-overlay and kills startup. Already documented in README known-issues.

## 8.4 Frontend branding (non-security)

| ENV var | What | Our default | Effort | Bucket | Rationale / note |
|---|---|---|---|---|---|
| `PAPERLESS_APP_TITLE` | Name override in UI (browser tab, logo label) | unset (= "Paperless-ngx") | low | **Use-case-dependent** | Use-case: multi-instance environment where users need to see instantly which instance they're in. Otherwise cosmetic. |
| `PAPERLESS_APP_LOGO` | Path to own logo in `/media/logo` dir | unset | low | **Use-case-dependent** | Use-case: branding for internal setup. **Important**: logo is **visible before login** — strip EXIF data before upload (otherwise info leak about author / software / location). |

## 8.5 Monitoring (Celery Flower)

| ENV var | What | Our default | Effort | Bucket | Rationale / note |
|---|---|---|---|---|---|
| `PAPERLESS_ENABLE_FLOWER` | Start Celery monitoring UI | unset (= off) | medium | **Use-case-dependent** | Use-case: production instance with many background jobs, Prometheus integration wanted, debug for hanging queues. **Security-relevant**: Flower listens on port 5555 — must be secured separately (Traefik router with `acc-tailscale` + Basic Auth when active). Never expose directly via host port mapping. Config file via volume mount `flowerconfig.py`. |

## 8.6 Custom container init

Extensibility without custom Docker image build.

| Feature | What | Bucket | Note |
|---|---|---|---|
| `/custom-cont-init.d` volume mount | Host scripts executed before webserver start | **Use-case-dependent** | Use-case: install extra packages, PostgreSQL client for backup scripts, pdf2pdfocr for pre-consume hook. Scripts must be `root:root` owned, `a=rx` permissions. Runs as root — use `gosu` for user switch. **Can break on upgrade** if Paperless upstream image structure changes. |

## 8.7 Deprecated / ignore

| ENV var | Status | Note |
|---|---|---|
| `PAPERLESS_SUPERVISORD_WORKING_DIR` | deprecated, no effect | Remove if present anywhere. Read-only-FS now goes via `S6_READ_ONLY_ROOT` from s6-overlay. |
| `PAPERLESS_ENABLE_UPDATE_CHECK` | deprecated since v1.9.2 | Update check is now a frontend setting (UI, per user). Ignore. |
| `PAPERLESS_WEBSERVER_WORKERS` / `PAPERLESS_BIND_ADDR` / `PAPERLESS_PORT` | future-deprecation | Upstream hints at eventual rename to `GRANIAN_WORKERS` / `GRANIAN_HOST` / `GRANIAN_PORT`. Both currently accepted. Check at next major upgrade. |

## 8.8 MySQL caveats (only if MariaDB/MySQL instead of PostgreSQL)

We use PostgreSQL. This section only relevant if someone forks and uses MariaDB.

| Point | Note | Bucket |
|---|---|---|
| Case sensitivity | MariaDB/MySQL case-insensitive by default. `ALTER TABLE ... COLLATE utf8mb4_bin;` per table — but makes search case-sensitive too | **—** (PG usage makes it irrelevant) |
| Timezones | One-time `mariadb-tzinfo-to-sql /usr/share/zoneinfo \| mariadb -u root mysql -p` needed | **—** |
| Charset | `utf8mb4` mandatory, not `utf8mb3` | **—** |

## 8.9 PDF auto-recovery (no switch, just info)

On MIME-type errors or broken PDFs Paperless automatically calls `qpdf` to rescue "repairable" PDFs. **No ENV switch**. Mentioned because it sometimes shows in logs and produces "PDF repair" entries — that's intentional, not a warning.

## 8.10 Current state vs. repo

| Bucket | Item | State |
|---|---|---|
| Mandatory | `USERMAP_UID` / `USERMAP_GID` | ✅ `1000/1000` set, README known-issue documented (no `user:` in compose) |
| Use-case | `APP_TITLE` / `APP_LOGO` | not set — OK for single-instance |
| Use-case | `ENABLE_FLOWER` | not active — OK |
| Use-case | Custom container init | not active — OK |
| — | `BIND_ADDR` / `PORT` | defaults active, not touched — correct |
| — | Deprecated vars | none in repo |

---

# 9. Email (Send / Parse / OAuth / GPG)

Three distinct use-cases: (1) Paperless **sends** mails, (2) Paperless **consumes** mails, (3) OAuth + GPG as special fetch methods.

## 9.1 Email sending (outbound)

Paperless itself sends mail on: password reset, event notifications, workflow "email" action, user invitations.

Without SMTP config all of that silently drops — Paperless keeps running, but e.g. `ACCOUNT_EMAIL_VERIFICATION` (see Auth section) auto-sets to `none`.

| ENV var | What | Our default | Effort | Bucket | Rationale / note |
|---|---|---|---|---|---|
| `PAPERLESS_EMAIL_HOST` | SMTP server host | unset (= `localhost`) | low | **Nice-to-have** | SMTP relay provider (Brevo, SES, Mailgun, etc.) — `localhost` works only if container has a local MTA (it doesn't). |
| `PAPERLESS_EMAIL_PORT` | SMTP port | unset (= `25`) | low | **Nice-to-have** | Typical: `587` (STARTTLS/submission), `465` (SMTPS), rarely `25`. |
| `PAPERLESS_EMAIL_HOST_USER` | SMTP auth username | unset | low | **Nice-to-have** | Only for relays with auth (almost always nowadays). |
| `PAPERLESS_EMAIL_HOST_PASSWORD` | SMTP auth password | via `.env` (Paperless limitation — no `_FILE`) | low | **Nice-to-have** | **No `_FILE` support in Paperless**. Stays in `.env` (gitignored). Docker secret via entrypoint wrapper possible but rarely worth it for SMTP alone. |
| `PAPERLESS_EMAIL_USE_TLS` | Enable STARTTLS | `true` (for port 587) | low | **Nice-to-have** | Exactly one of TLS/SSL must be on — cleartext SMTP is out of date. |
| `PAPERLESS_EMAIL_USE_SSL` | SMTPS (implicit TLS) | `false` (port 587); `true` (port 465) | low | **Nice-to-have** | **Exclusive** to `USE_TLS` — never both `true`. |
| `PAPERLESS_EMAIL_FROM` | Sender address | e.g. `noreply@example.com` | low | **Nice-to-have** | Must be authenticatable at the relay (SPF/DKIM). Default falls back to `HOST_USER` — can produce broken mails with generic SMTP-relay users. |

**Cluster rule of thumb**: either set **all seven** or **none** — partial SMTP config leads to runtime errors on first password-reset mail.

**Upgrade to Mandatory when**: regular login active (password reset must work) OR workflow with email action OR mail-based event notifications planned.

## 9.2 Email parsing (inbound — .eml consumption)

Paperless can consume `.eml` files (via consume folder or direct IMAP/OAuth fetch). Requires Tika + Gotenberg (see infrastructure) — we have them active.

| ENV var | What | Our default | Effort | Bucket | Rationale / note |
|---|---|---|---|---|---|
| `PAPERLESS_EMAIL_PARSE_DEFAULT_LAYOUT` | How mails render into PDFs | default `1` (Text, then HTML) | low | **Nice-to-have** | Relevant only when mails are consumed. Default = prefer readable text, HTML as fallback for mails without a plaintext part. Alternatives: `2` HTML→Text, `3` HTML-only (visually prettier, many tracking pixels and link obfuscation), `4` Text-only (clean, can lose attachments/formatting). **Per mail-rule overridable in UI** — global default is only fallback. |

## 9.3 Mail accounts (UI feature, not ENV)

Actual mail rules (which IMAP/POP3/OAuth account, which filters, which target tags) are configured **in the UI** — no ENV equivalent. Listed for completeness:

| Feature | Purpose | Bucket |
|---|---|---|
| Mail account configuration in UI | Create IMAP/POP3/OAuth connection | **Use-case-dependent** (app-internal) |
| Mail rules in UI | Filter + consume action + tagging | **Use-case-dependent** (app-internal) |

**Cron**: fetch interval is controlled by `PAPERLESS_EMAIL_TASK_CRON` → see Software Tweaks. Without mail accounts the cron does nothing but runs every 10 min dry — hence the `disable` recommendation there when not needed.

## 9.4 Email OAuth (Gmail / Outlook)

Instead of IMAP password: OAuth flow against Google/Microsoft. Only relevant for `gmail.com` / `outlook.com` / `office365.com` mailboxes. Needs app registration with the provider.

| ENV var | What | Our default | Effort | Bucket | Rationale / note |
|---|---|---|---|---|---|
| `PAPERLESS_OAUTH_CALLBACK_BASE_URL` | Base URL for OAuth redirect | unset (falls back to `PAPERLESS_URL`) | low | **Use-case-dependent** | Set only if OAuth redirect terminates on a different domain than Paperless itself. Otherwise `PAPERLESS_URL` is enough. |
| `PAPERLESS_GMAIL_OAUTH_CLIENT_ID` | Google Cloud Console OAuth client ID | unset | high | **Use-case-dependent** | Setup: Google Cloud project → OAuth consent screen → credentials → OAuth 2.0 client. Redirect URI: `<CALLBACK_BASE_URL>/api/oauth-callback/`. |
| `PAPERLESS_GMAIL_OAUTH_CLIENT_SECRET` | Google client secret | unset | low | **Use-case-dependent** | **No `_FILE` support** — stays in `.env`. Same trade-off as SMTP password. |
| `PAPERLESS_OUTLOOK_OAUTH_CLIENT_ID` | Microsoft Azure app registration client ID | unset | high | **Use-case-dependent** | Setup: Azure portal → app registrations → new. Redirect URI analogous. Watch tenant config (single vs multi). |
| `PAPERLESS_OUTLOOK_OAUTH_CLIENT_SECRET` | Azure client secret | unset | low | **Use-case-dependent** | Stays in `.env`. Azure secrets expire after 24 months by default — calendar reminder. |

**Important**: OAuth callback happens via the **public** domain (`PAPERLESS_URL`). If Paperless is on `acc-tailscale`, OAuth flow works only from inside the VPN — OAuth providers redirect there, but the user's browser must be able to reach it too. Do initial setup from inside VPN, then token refresh runs in the background.

## 9.5 Encrypted emails (GPG decryption)

Paperless can decrypt GPG-encrypted mails **before** consumption — but needs a working `gpg-agent` setup with available private key.

| ENV var | What | Our default | Effort | Bucket | Rationale / note |
|---|---|---|---|---|---|
| `PAPERLESS_ENABLE_GPG_DECRYPTOR` | Enable GPG decryptor | `false` (default) | high | **Use-case-dependent** | Use-case: encrypted email workflow (e.g. customer comms over GPG, regulatory). Setup effort is noticeable — see below. |
| `PAPERLESS_EMAIL_GNUPG_HOME` | GNUPG home path in container | unset (= default) | low | **Use-case-dependent** | Only if GPG keys aren't mounted at default path. |

**Setup sketch with `ENABLE_GPG_DECRYPTOR=true`** (shows what's involved):

```yaml
# docker-compose.yml — additional to existing
volumes:
  - /home/user/.gnupg/pubring.gpg:/usr/src/paperless/.gnupg/pubring.gpg
  - /home/user/.gnupg/S.gpg-agent:/usr/src/paperless/.gnupg/S.gpg-agent
```

Paths host-dependent: find with `gpgconf --list-dir agent-socket`. Setup only worth it when a GPG workflow actually exists — otherwise just don't enable.

## 9.6 Cross-reference: IMAP with self-signed certificate

`PAPERLESS_EMAIL_CERTIFICATE_LOCATION` → see Hosting & Security (listed there as use-case).

## 9.7 Current state vs. repo

| Bucket | Item | State |
|---|---|---|
| Nice-to-have | SMTP cluster (`EMAIL_HOST`/`PORT`/`USER`/`PASSWORD`/`FROM`/`USE_TLS`/`USE_SSL`) | **missing** — no password resets possible; not yet needed because no users registered |
| Nice-to-have | `EMAIL_PARSE_DEFAULT_LAYOUT` | default `1` active, not explicit |
| Use-case | OAuth cluster | not active — OK |
| Use-case | GPG decryptor | not active — OK |

**Realistic next step when relevant**: configure SMTP cluster once multiple users exist or workflows with mail action are planned. Without concrete need, leave empty.

---

# 10. Extensions / Integrations

Third-party tools that hook into Paperless. All communicate via Paperless REST API with an API token — no direct DB access. None is currently active in the repo; all are on the TODO list.

## 10.1 Overview

| App | Purpose | Communicates via | State in repo |
|---|---|---|---|
| **paperless-gpt** | LLM-based OCR quality improvement + auto-tagging/correspondent (OpenAI / Ollama) | REST API + API token | Not set up — TODO |
| **paperless-ai** | LLM automation for metadata (title, tags, correspondents, document-type suggestions) | REST API + API token | Not set up — TODO |
| **paperless-mcp** | MCP server for Claude Code / Desktop to query Paperless docs | REST API + API token, MCP protocol outbound | Template in `inbox/Archiv/paperless-mcp/`, inactive |

## 10.2 Common prerequisites

When one or more are activated:

1. **API token** generated in Paperless — one per tool, not shared (so one can be rotated without breaking the others).
   UI path: Profile → My Profile → Tokens → Create.
2. **Network reachability** — extensions need `http://paperless-app:8000/api/` (internal via `proxy-public` or dedicated shared network) or the public `PAPERLESS_URL`. Internal is preferred (no Traefik hop, no public tool-API exposure).
3. **Conflict avoidance with multiple auto-taggers**: if both `paperless-gpt` and `paperless-ai` run and both want to set tags/correspondents, they can overwrite each other. Practical strategies:
   - Use only one — feature sets overlap significantly
   - Separate scopes: one for OCR enhance (gpt), one for metadata (ai) — needs per-tool config to touch only "own" fields
   - As workflow trigger: restrict auto-taggers' matching rules to "inbox documents only", not existing ones

## 10.3 paperless-gpt

- **Purpose**: better OCR quality via LLM post-processing (especially for bad scans, handwriting, receipts). Optionally also title/correspondent/tag inference.
- **Source**: `icereed/paperless-gpt` (GitHub)
- **Backend options**: OpenAI (cloud), Ollama (local), Mistral
- **Data flow**: fetches document + OCR text from Paperless → LLM → writes back via API
- **Privacy consideration**: cloud LLM sends document contents to OpenAI. Local Ollama avoids that but needs GPU or patient CPU.
- **Bucket**: **Use-case-dependent** (only worth it if OCR quality is a real issue)

## 10.4 paperless-ai

- **Purpose**: automatic metadata suggestions/assignments on new documents (title, sender, tags, document type)
- **Source**: `clusterzx/paperless-ai` (GitHub)
- **Backend options**: OpenAI-compatible (OpenAI, Azure, local Ollama / LM-Studio)
- **Data flow**: webhook from Paperless workflow or polling → LLM → Paperless API update
- **Bucket**: **Use-case-dependent** (large backlog of raw docs where manual metadata maintenance is the bottleneck)

## 10.5 paperless-mcp

- **Purpose**: MCP server so Claude Code / Desktop can use Paperless documents, tags, correspondents as context
- **Source**: community project (template in repo at `inbox/Archiv/paperless-mcp/`)
- **Data flow**: MCP protocol (Claude) ↔ paperless-mcp ↔ Paperless REST API
- **Security note**: the MCP endpoint gives **read full access** to all Paperless documents the API-token user can see. Access policy `acc-tailscale` is mandatory when active — template already sets that.
- **Bucket**: **Use-case-dependent** (AI-assisted document search / analysis without copy-paste into chat)

## 10.6 TODO note

At least one of these tools will be set up later. Requirement: **mutual communication must work** — if several run concurrently they must not block or overwrite each other. To be checked explicitly at setup time.

## 10.7 Architectural options (when eventually set up)

| Variant | Layout | Suitable for |
|---|---|---|
| **a) As own apps under `apps/`** | `apps/paperless-gpt/`, `apps/paperless-ai/`, `apps/paperless-mcp/` — each with own `docker-compose.yml` + `.env` + `README` + `UPSTREAM` + `CONFIG.md` | Consistent with blueprint structure. Each tool independently start/stoppable. |
| **b) As overlay compose files in `apps/paperless-ngx/`** | `docker-compose.gpt.yml`, `docker-compose.ai.yml`, `docker-compose.mcp.yml` — toggled via `COMPOSE_FILE` | Tight coupling. Start/stop together with Paperless. |

Recommended (when it's time): **a)** — independent apps match blueprint philosophy, and paperless-mcp already exists as a template skeleton.
