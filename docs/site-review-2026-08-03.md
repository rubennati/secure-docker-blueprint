# Site review — 2026-08-03

Checked against the live site, not the source. Every line below rests on a
response actually retrieved.

## The chain that actually serves the site

`dig @1.1.1.1 secdockblue.rubennati.at A` returns `172.67.162.216`,
`104.21.82.199` — Cloudflare's anycast range. The local resolver answers with a
tailnet address instead, so anything checked without pinning the public address
checks a different server entirely. Everything below was retrieved with
`curl --resolve "secdockblue.rubennati.at:443:172.67.162.216"`.

From the response headers:

| Header | Party it names |
|---|---|
| `server: cloudflare`, `cf-ray: …-VIE`, `cf-cache-status` | Cloudflare, proxying |
| `x-github-request-id`, `x-github-edge-region: fra` | GitHub Pages, the origin |
| `via: 1.1 varnish`, `x-served-by: cache-vie6335-VIE`, `x-fastly-request-id` | Fastly, GitHub's own delivery network |
| `report-to` → `a.nel.cloudflare.com` | Cloudflare, network error reports |

**Visitor → Cloudflare → GitHub Pages → Fastly.** Three US companies, and
Cloudflare terminates TLS, so it is the one that handles requests in clear text.

## Findings

### 1. The privacy statement named one processor of three — fixed

`site/src/content/docs/privacy/index.md` described GitHub Pages as the host and
said nothing about Cloudflare or Fastly. Cloudflare is the party that decrypts
every request. Art. 13(1)(e) GDPR requires the recipients to be named.

Corrected: all three are listed with their role, the decryption at the edge is
stated plainly, and the transfer basis is given per company from each company's
own documentation. The network error report to `a.nel.cloudflare.com` is
recorded as the one outbound request the site causes beyond fetching the page.

**Confirm with a lawyer** whether naming Fastly as engaged by GitHub rather than
by this site is the right construction.

### 2. `security.txt` exists and is not served — cause found

`https://secdockblue.rubennati.at/.well-known/security.txt` answered 404, and
the same 404 came back from GitHub Pages directly, so it was not a Cloudflare
cache.

The file was not missing. `site/src/pages/.well-known/security.txt.ts` has
generated it since `eaa6338`, it was present at the commit main pointed to
before this review, and the build emits it. It was never served.

The pattern says why: `robots.txt` and `llms.txt` are served, and they carry no
dot in their path. GitHub Pages excludes paths beginning with a dot unless a
`.nojekyll` marker is present, and the repository had none. Added at
`site/public/.nojekyll`; both it and `.well-known/security.txt` are in the build
output.

**This has not been confirmed live** — it takes the next deployment to main.
If the 404 persists, the cause is elsewhere and this note is wrong.

A duplicate was created and removed during this review: a static
`site/public/.well-known/security.txt` written before the existing route was
found. It also contradicted it, listing an e-mail address that `SECURITY.md`
deliberately keeps off the public record. The route derives its `Expires` from a
review date so the two cannot drift, which the static file did not.

### 3. No security headers — cannot be fixed in this repository

Absent on the live response: `strict-transport-security`,
`content-security-policy`, `x-content-type-options`, `referrer-policy`,
`permissions-policy`, `x-frame-options`.

GitHub Pages does not let a site set response headers, and Cloudflare is not
adding any. The place to set them is the Cloudflare dashboard, under Rules →
Transform Rules → Modify Response Header. This needs the account, so it is the
maintainer's step, not a commit.

Priority order if only some are set: `strict-transport-security` first, since
without it a first visit over plain HTTP is redirectable;
`x-content-type-options: nosniff` and `referrer-policy: strict-origin-when-cross-origin`
next, both free of side effects on a static site. A content security policy
needs testing against the rendered pages before it is switched on.

### 4. Nothing else failed

- `robots.txt` — 200, allows everything, points at the sitemap
- `sitemap-index.xml` — 200, `application/xml`
- all 36 URLs in `sitemap-0.xml` — 200
- TLS — certificate verified, HTTP/2

## What was not checked

- **`<link rel="canonical">` against each sitemap entry.** The URLs all answer
  200; whether every page declares the same URL the sitemap does was not
  compared.
- **`lastmod`.** Whether it follows a content change or the build time was not
  established, so it may be a signal that resets on every build.
- **Legal notice against § 5 ECG and § 24 MedienG.** The operator's details were
  confirmed as correct rather than reviewed here, so completeness against the
  norm is untested.
- **Branch protection and CI permissions.** Not read from the GitHub API.
