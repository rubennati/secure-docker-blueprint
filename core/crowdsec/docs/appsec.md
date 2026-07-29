# AppSec — Application Security (WAF)

CrowdSec's request-level inspection layer. Opt-in and disabled by default.

---

## What AppSec is — and how it differs from scenario detection

CrowdSec operates two distinct protection mechanisms. Understanding the difference matters
before enabling AppSec.

**Scenario detection** (Phases 1–3) works asynchronously against log events. The engine
reads Traefik access logs, evaluates patterns over time (e.g., 10 failed login attempts in
5 minutes), and creates ban decisions stored in the LAPI. Those decisions are enforced by
Phase 2 (Traefik bouncer, HTTP 403) and Phase 3 (nftables, packet drop). One ban blocks
all future requests from that IP until the decision expires.

**AppSec** works synchronously, per request, inline. When AppSec is enabled, the Traefik
bouncer forwards each incoming HTTP request to the AppSec engine at `crowdsec:7422` before
passing it to the application. The engine applies WAF rules against the request (method,
path, headers, body). If a rule matches, the bouncer returns HTTP 403 immediately and the
request never reaches the application. If no rule matches, the request proceeds normally.

Key distinction: **AppSec blocks individual requests; it does not ban IPs.** A blocked
request does not create a LAPI decision. The same IP can immediately make the next request
and have it succeed, provided the offending payload is not repeated. This makes AppSec
false positives self-contained — the user retries and succeeds — but it also means AppSec
does not accumulate evidence against persistent attackers the way scenario detection does.

```text
Scenario detection path (asynchronous):
  Traefik access log → CrowdSec engine → scenario matches → LAPI decision → ban (IP-scope)

AppSec path (synchronous, per-request):
  Incoming request → Traefik bouncer → AppSec engine at :7422 → rule matches? → block or allow
```

The two mechanisms complement each other. Scenario detection catches behavioral patterns
over time; AppSec catches known attack signatures in individual requests.

---

## Current blueprint state

| Item | State |
|---|---|
| AppSec engine | Installed and running inside the CrowdSec container |
| AppSec port | Listening on `crowdsec:7422` (internal Docker network only) |
| AppSec rule sets | Installed via `CROWDSEC_COLLECTIONS` in `.env` |
| AppSec enforcement | **Disabled by default** (`crowdsecAppsecEnabled: false` in the Traefik bouncer config) |
| Applications using AppSec | None — no application router currently includes `sec-crowdsec@file` as middleware |

The AppSec engine is ready to receive requests but the Traefik bouncer is not sending any.
No change to `config/appsec.yaml` or any app configuration is needed to keep AppSec in
this disabled state.

---

## Active rule sets

Two collections install AppSec rule sets via `CROWDSEC_COLLECTIONS` in `.env`:

### `crowdsecurity/appsec-generic-rules`

General-purpose WAF signatures covering classes of attack that apply to any HTTP
application:

| Category | What it detects |
|---|---|
| SQL injection | SELECT, UNION, INSERT patterns in query strings, POST bodies, and headers; encoded variants |
| Cross-site scripting (XSS) | `<script>`, event handlers, JavaScript URIs in input fields and headers |
| Path traversal | `../`, `..%2F`, and other encoded forms in paths and parameters |
| Command injection | Shell metacharacters (`;`, `&&`, `\|`) in parameters that reach server-side execution |
| Local file inclusion | References to `/etc/passwd`, `/proc/self`, and other system file paths in parameters |
| Remote file inclusion | HTTP/FTP URLs in parameters that could cause server-side fetch |
| HTTP method anomalies | Unusual or malformed HTTP methods not expected in standard web traffic |

### `crowdsecurity/appsec-virtual-patching`

CVE-specific patches for known vulnerabilities in widely deployed software. These rules
block specific exploit payloads without requiring the underlying application to be updated.
Examples include Log4Shell (`CVE-2021-44228`), Spring4Shell, and exploit patterns for
common CMS vulnerabilities.

Unlike generic rules, virtual patches target precise exploit signatures. False positive
rates are lower for these rules, but they are also narrower — they protect against known
vulnerabilities, not novel attack variations.

Neither collection generates an exhaustive rule list here — use
`docker exec crowdsec cscli appsec-rules list` to inspect installed rules on a running
instance.

---

## Enabling AppSec safely

AppSec is enabled in one place: `crowdsecAppsecEnabled` in the `sec-crowdsec` middleware
block in `core/traefik/ops/templates/dynamic/integrations.yml.tmpl`.

**Do not flip this switch directly to fail-closed.** If AppSec is unreachable at the
moment Traefik evaluates a request and `crowdsecAppsecUnreachableBlock` is `true`, every
request returns 403 — including your own access to the Traefik dashboard, Portainer, and
any other service behind Traefik. Enable incrementally.

### Recommended progression

#### Step 1 — Verify AppSec is reachable from Traefik

Before enabling, confirm the AppSec port is accessible from inside the Traefik container:

```bash
# From the Traefik container, reach the AppSec health endpoint:
docker exec traefik wget -q --spider http://crowdsec:7422/ 2>&1
# Exit code 0 or a "Connection refused" → port exists.
# "Name resolution failure" → containers are not on the same network.

# Alternative: check that both containers share the proxy-public network:
docker inspect crowdsec | grep -A5 '"Networks"'
docker inspect traefik | grep -A5 '"Networks"'
# Both must show proxy-public.
```

If CrowdSec is not on the proxy-public network, AppSec will always be unreachable from
Traefik regardless of the flag settings.

#### Step 2 — Enable AppSec with fail-open

In `core/traefik/ops/templates/dynamic/integrations.yml.tmpl`, set only
`crowdsecAppsecEnabled: true`. Leave the failure flags as `false`:

```yaml
crowdsecAppsecEnabled: true
crowdsecAppsecHost: crowdsec:7422
crowdsecAppsecFailureBlock: false        # fail-open on AppSec errors
crowdsecAppsecUnreachableBlock: false    # fail-open if AppSec unreachable
```

Re-render and hot-reload (no Traefik restart needed for dynamic config changes):

```bash
cd core/traefik
./ops/scripts/render.sh
# Traefik hot-reloads the dynamic config automatically.
```

#### Step 3 — Observe behavior

Monitor for AppSec blocks across your applications before tightening failure behavior:

```bash
# Stream CrowdSec engine logs — AppSec block events appear here:
docker compose -f core/crowdsec/docker-compose.yml logs -f crowdsec | grep -i appsec

# Check overall metrics (confirm the appsec subcommand exists on your installed version):
docker exec crowdsec cscli metrics show appsec
# If the subcommand is not recognised, list available metric groups with:
docker exec crowdsec cscli metrics show --help
```

Run this for a representative period — at least a few days of real traffic. Look for
false positives in the applications you have protected. See the
[Application-specific false positives](#application-specific-false-positives) section
to know what to expect.

#### Step 4 — Tighten failure behavior (optional)

Only after AppSec has been stable and you understand the false-positive rate:

```yaml
crowdsecAppsecFailureBlock: true        # block if AppSec returns an error
crowdsecAppsecUnreachableBlock: true    # block if AppSec endpoint unreachable
```

**Before setting `crowdsecAppsecUnreachableBlock: true`**, confirm that:

- The CrowdSec container starts reliably and before Traefik
- You have an out-of-band access path (Tailscale, cloud console) in case all HTTP access
  is cut off by a startup race condition

These settings provide stronger security guarantees at the cost of a harder failure mode.
They are appropriate for high-security deployments where a failed WAF should be treated as
a security incident, not a transparent pass-through.

---

## Diagnosing AppSec blocks

When a request returns 403, the cause is one of two things: a LAPI IP ban (Phase 2
enforcement) or an AppSec rule match. They produce the same HTTP response but require
different remediation.

### Distinguish AppSec block from IP ban

```bash
# 1. Is there an active ban for the IP in question?
docker exec crowdsec cscli decisions list --ip <affected-ip>
# If a decision exists → this is a Phase 2/3 IP ban, not AppSec.
# If no decision exists → the block is from AppSec (or something else upstream).

# 2. Check for AppSec block events in the engine log:
docker compose logs crowdsec | grep -i "appsec\|waf\|blocked" | tail -20

# 3. Check AppSec metrics for block counts (verify subcommand exists on your version):
docker exec crowdsec cscli metrics show appsec
# A non-zero "blocked" count confirms AppSec is firing.
# If unrecognised: docker exec crowdsec cscli metrics show --help
```

### Identify which rule fired

AppSec block events in the CrowdSec engine log include the rule name and the matched
content. Enable debug logging temporarily if needed:

```bash
# Stream engine logs with AppSec context:
docker compose logs -f crowdsec 2>&1 | grep -A5 -i "appsec"

# The block event shows:
#   - rule name (e.g., crowdsecurity/sql-injection-detection)
#   - matched parameter (query string key, header name, body field)
#   - matched value excerpt
```

### Determine if it is a false positive

A false positive has all of the following characteristics:

- The request is from a known-legitimate source (your own browser, a sync client, a
  webhook from a service you control)
- The request content is intentional and expected for the application
- Removing or changing the flagged content makes the request succeed

Compare the matched content against the
[Application-specific false positives](#application-specific-false-positives) table.
If it matches a known pattern, the block is almost certainly a false positive.

---

## Application-specific false positives

These patterns are known to trigger AppSec rules in the contexts described. They are
not bugs in either the application or the rule set — they are cases where general WAF
signatures match legitimate application traffic.

| Application | Trigger pattern | Why it fires | Recommended response |
|---|---|---|---|
| **Nextcloud** | WebDAV methods: `PROPFIND`, `PROPPATCH`, `MKCOL`, `MOVE`, `COPY` | HTTP method anomaly rules flag methods outside `GET`/`POST`/`PUT`/`DELETE` | Write a custom exclusion for the Nextcloud host and `/remote.php/dav/` path prefix, excluding HTTP method checks |
| **Nextcloud** | CalDAV/CardDAV XML request bodies | XSS rules match `<` characters in XML body without understanding `Content-Type: application/xml` context | Exclude the `/remote.php/dav/` path from XSS body inspection, or exclude the CalDAV content-type |
| **Nextcloud** | Large file uploads via desktop client (`PUT /remote.php/dav/files/`) | Binary file content scanned by generic rules; arbitrary binary contains byte patterns matching SQL or script signatures | Exclude the Nextcloud upload path from body inspection rules; consider size-based body inspection limits |
| **Paperless-ngx** | Document upload (`POST /api/documents/post_document/`) | PDF and DOCX files contain arbitrary text including SQL-like strings in metadata, embedded scripts in PDF actions, and OCR output with special characters | Exclude the document upload endpoint from body content rules; document content is opaque data, not user-controlled input in the injection sense |
| **Authentik** | SAML POST binding to `/source/saml/` | SAML assertions are base64-encoded XML in a form POST; the XML container around the payload can trigger XML injection rules | Exclude the Authentik SAML endpoint from XML injection rules; the SAML payload is cryptographically signed and validated by Authentik |
| **Authentik** | OAuth2 flows with long JWTs in Authorization or request body | Long tokens, large header values, and structured OAuth payloads may occasionally match patterns in generic WAF rules inspecting header length, encoding, or payload structure | If a specific rule fires, scope an exclusion to the Authentik OAuth endpoint and the matched rule; investigate before writing a broad exclusion |
| **WordPress** | Gutenberg editor POST bodies (`/wp-json/wp/v2/`) | Editor content includes raw HTML, shortcodes (`[gallery]`), and template tags — all match XSS and template injection signatures | Exclude `/wp-json/` from XSS body inspection for authenticated sessions, or add the WordPress admin IP to the whitelist |
| **WordPress** | Media upload (`/wp-admin/async-upload.php`) | Same as Paperless: binary file content scanned | Exclude the WordPress media upload endpoint from body inspection |
| **Seafile** | File sync chunked upload (`PUT /seafhttp/`) | Seafile desktop client sends binary file chunks; binary content matches generic injection signatures | Exclude the Seafile sync upload path from body inspection rules |
| **Invoice Ninja** | Payment webhook callbacks | Stripe/PayPal webhook JSON includes billing address fields with apostrophes, hyphenated names, and special characters that match SQL injection patterns | Exclude the Invoice Ninja webhook endpoint from SQL injection rules; webhook payloads arrive from known provider IP ranges and carry HMAC signatures |
| **Invoice Ninja** | Invoice PDF generation | HTML content of invoice templates passed as POST parameters includes inline styles and layout HTML that triggers XSS rules | Exclude the PDF generation endpoint from XSS body rules; the content is operator-defined template HTML, not untrusted user input |

**General pattern:** AppSec false positives in this stack cluster around three root causes:

1. Non-standard HTTP methods (WebDAV)
2. Binary file uploads (any application)
3. Rich content (HTML, XML, JSON with operator-authored content) sent in request bodies

---

## Tuning and exclusions

When a false positive is confirmed, the appropriate response is a CrowdSec AppSec
exclusion — a configuration entry that tells the AppSec engine to skip specific rules
for specific request attributes (path prefix, HTTP method, header value, content-type).

### When exclusions are appropriate

Use an exclusion when:

- The trigger is a known false positive in a specific application context (see table above)
- The matched content is operator-controlled or cryptographically validated at the
  application layer (SAML assertions, HMAC-signed webhooks)
- Disabling AppSec entirely for the application would remove protection from other
  endpoints that benefit from it

Do not write exclusions for:

- Unknown blocks where the source or content is unclear — investigate first
- Broad path prefixes that cover most of the application — this neutralizes the protection
- Rules that haven't been confirmed as false positives — a firing rule may be a real attack

### Exclusion mechanics

CrowdSec AppSec exclusions are written in YAML and mounted into the engine configuration.
The general structure targets a rule or rule set and narrows the exclusion to specific
request attributes:

```yaml
# volumes/config/appsec/exclusions.yaml
# (exact schema — verify against installed AppSec version)
exclusions:
  - rules_group: crowdsecurity/xss-detection      # or a specific rule ID
    conditions:
      - and:
        - request.path StartsWith /remote.php/dav/
          # limit: only exclude XSS rules on this path, not globally
```

Mount the file and restart the engine. Always scope exclusions as narrowly as possible:

- Prefer path prefix over entire host
- Prefer specific rule or rule group over all rules
- Prefer specific HTTP method over all methods

### Risk of over-exclusion

Each exclusion removes a protection for the scoped requests. Broad exclusions — excluding
an entire rule set for an entire application — are operationally equivalent to disabling
AppSec for that application. The risk is that a real attack payload arrives on an excluded
path and passes through unchecked.

Before writing an exclusion, verify that the false positive is genuinely not exploitable
in that context. A path like `/remote.php/dav/` is used exclusively for authenticated
file sync — XSS in that context does not have a browser victim to exploit. That reasoning
justifies the exclusion. A path like `/` on WordPress does have browser-visible output —
XSS exclusions there require more justification.

---

## Emergency disable

If AppSec is causing widespread blocking and you need to restore access immediately:

```bash
# 1. In core/traefik/ops/templates/dynamic/integrations.yml.tmpl,
#    set crowdsecAppsecEnabled: false

# 2. Re-render (hot-reloads without Traefik restart):
cd core/traefik
./ops/scripts/render.sh

# 3. Confirm AppSec is no longer being called:
docker exec crowdsec cscli metrics show appsec   # verify subcommand exists on your version
# Expected: request counts stop increasing

# 4. Blocked IPs from AppSec events are not stored as LAPI decisions —
#    there are no IP bans to clear. Access is restored immediately
#    once the config is reloaded.
```

If AppSec created any IP bans (possible if a custom profile escalates AppSec events to
decisions), check and clear them:

```bash
docker exec crowdsec cscli decisions list
docker exec crowdsec cscli decisions delete --all   # only if everything must be cleared
```

Full emergency procedures: [`docs/runbook.md`](runbook.md) → §5 Emergency Procedures.

---

## What AppSec is not

AppSec is one layer in the stack. It does not substitute for:

- **CrowdSec scenario detection** — AppSec blocks individual requests; it does not identify
  and ban persistent attackers. An attacker sending 1000 exploit attempts in sequence gets
  each attempt blocked by AppSec, but receives no IP ban unless the same traffic also
  triggers a scenario (e.g., `http-probing` from high request volume).

- **Rate limiting** — AppSec does not limit request rates. A client can send AppSec-blocked
  requests at full speed indefinitely. Use Traefik rate-limit middleware to cap request
  rates.

- **Authentication** — AppSec does not verify identity. Unauthenticated requests that pass
  all WAF rules still reach the application.

- **Application updates** — Virtual patching blocks known exploit signatures for unpatched
  applications, but new CVE exploit variants may not match existing signatures immediately.
  Virtual patches reduce risk; they do not replace patching.

- **Good application security** — AppSec does not sanitize input, enforce access control,
  or validate application logic. These responsibilities belong to the application.

The most effective posture is layered: scenario detection handles behavioral threats, AppSec
handles known exploit signatures, rate limiting handles volume abuse, authentication handles
access control, and applications handle their own input validation.
