import type { APIRoute } from 'astro';

// Generated rather than kept in public/ so the sitemap URL always matches
// `site` in astro.config.mjs. A hardcoded copy would silently point at the
// wrong host the moment the domain changes.
//
// Everything is crawlable: there is nothing on this site that is not also
// public in the repository, so a Disallow rule would protect nothing and only
// risk hiding a page by accident.
export const GET: APIRoute = ({ site }) => {
  const body = [
    'User-agent: *',
    'Allow: /',
    '',
    `Sitemap: ${new URL('sitemap-index.xml', site).href}`,
    '',
  ].join('\n');

  return new Response(body, {
    headers: { 'Content-Type': 'text/plain; charset=utf-8' },
  });
};
