import type { APIRoute } from 'astro';

// RFC 9116. Points at the same channels SECURITY.md documents — the advisory
// form is the preferred route there, so it is the only Contact listed here.
// No email: SECURITY.md deliberately keeps the address off the public record
// and refers to the GitHub profile instead.
//
// `Expires` is derived from the review date rather than fixed independently,
// so the two cannot drift. Re-check that the URLs below still resolve and that
// the response times in SECURITY.md still hold, then move REVIEWED forward.
const REVIEWED = '2026-07-29';

export const GET: APIRoute = ({ site }) => {
  const expires = new Date(REVIEWED);
  expires.setUTCFullYear(expires.getUTCFullYear() + 1);

  const body = [
    'Contact: https://github.com/rubennati/secure-docker-blueprint/security/advisories/new',
    'Policy: https://github.com/rubennati/secure-docker-blueprint/blob/main/SECURITY.md',
    `Canonical: ${new URL('.well-known/security.txt', site).href}`,
    `Expires: ${expires.toISOString().replace(/\.\d{3}Z$/, 'Z')}`,
    'Preferred-Languages: en, de',
    '',
  ].join('\n');

  return new Response(body, {
    headers: { 'Content-Type': 'text/plain; charset=utf-8' },
  });
};
