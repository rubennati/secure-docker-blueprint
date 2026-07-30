import type { APIRoute } from 'astro';
import { getCollection } from 'astro:content';

// llms.txt, generated from the same content collection the site renders from.
//
// The previous hand-written copy in public/ had already drifted: it listed one
// application while three were published, and it still described the site as
// unpublished with relative URLs. Anything derived from the pages themselves
// cannot drift that way — a new page appears here the moment it is added.
//
// Only the framing prose and the section order are editorial. Titles,
// descriptions and URLs come from the pages.

const SUMMARY =
  'Security-focused Docker Compose infrastructure for self-hosted services: hardened defaults, Docker Secrets, a Traefik reverse proxy with optional dual-stack IPv6, CrowdSec intrusion detection, and standards-consistent service definitions. Apache 2.0.';

const INTRO = [
  'SecDockBlue is the operator-facing site. Secure Docker Blueprint is the',
  'repository underneath it —',
  '[github.com/rubennati/secure-docker-blueprint](https://github.com/rubennati/secure-docker-blueprint)',
  '— and it remains the technical source of truth: compose files, `.env.example`',
  'templates and full per-service READMEs for every stack live there. The two',
  'names refer to two different things and are not interchangeable. The security',
  'material on this site is standalone operator knowledge and applies whether or',
  'not those compose files are used.',
].join(' ');

// Section order matches the sidebar. Each prefix claims the pages beneath it;
// the home page is the header above and is not listed as a link.
const SECTIONS: { heading: string; prefix: string }[] = [
  { heading: 'Start', prefix: 'getting-started' },
  { heading: 'Infrastructure', prefix: 'infrastructure' },
  { heading: 'Applications', prefix: 'applications' },
  { heading: 'Operations and recovery', prefix: 'operations' },
  { heading: 'Security', prefix: 'security' },
  { heading: 'Security', prefix: 'architecture' },
  { heading: 'Data sovereignty', prefix: 'sovereignty' },
  { heading: 'Reference', prefix: 'faq' },
  { heading: 'Reference', prefix: 'sources' },
  { heading: 'Reference', prefix: 'project' },
  // Footer-only pages: reachable from every page, deliberately not in the
  // sidebar, but part of the site and so part of this index.
  { heading: 'Reference', prefix: 'accessibility' },
  { heading: 'Reference', prefix: 'legal' },
  { heading: 'Reference', prefix: 'privacy' },
];

const NOTES = [
  'Code examples in guide pages are written against the repository structure as of each guide\'s last edit — prefer the linked repository file over re-deriving paths or variable names.',
  'Where a guide has been verified, it says so at the top: the version it was verified against, the date, and a line naming what was not exercised. A guide without that line has no verification behind it — do not infer one.',
  'Every guide assumes a Linux host with a domain and Traefik in front. There is no localhost or single-machine path documented on this site — do not synthesise one from the compose files.',
];

/** Starlight ids are path-like and drop `index`: `core/traefik`, `faq`, `''`. */
const toPath = (id: string) => (id === '' ? '/' : `/${id}/`);

export const GET: APIRoute = async ({ site }) => {
  const docs = await getCollection('docs');
  const lines: string[] = ['# SecDockBlue', '', `> ${SUMMARY}`, '', INTRO, ''];

  // Two prefixes may share a heading, so collect first and emit once.
  const grouped = new Map<string, string[]>();
  for (const { heading, prefix } of SECTIONS) {
    const entries = docs
      .filter((entry) => entry.id === prefix || entry.id.startsWith(`${prefix}/`))
      .sort((a, b) => {
        // Section overview first, then alphabetically by title.
        if (a.id === prefix) return -1;
        if (b.id === prefix) return 1;
        return a.data.title.localeCompare(b.data.title);
      });

    // Fail the build rather than ship a section that silently lost its pages.
    if (entries.length === 0) {
      throw new Error(`llms.txt: section "${prefix}" matched no pages — fix or remove it.`);
    }

    const items = entries.map((entry) => {
      const url = new URL(toPath(entry.id), site).href;
      return `- [${entry.data.title}](${url}): ${entry.data.description ?? ''}`.trimEnd();
    });
    grouped.set(heading, [...(grouped.get(heading) ?? []), ...items]);
  }

  for (const [heading, items] of grouped) {
    lines.push(`## ${heading}`, '', ...items, '');
  }

  lines.push('## Notes for AI agents', '');
  for (const note of NOTES) lines.push(`- ${note}`);
  lines.push('');

  return new Response(lines.join('\n'), {
    headers: { 'Content-Type': 'text/plain; charset=utf-8' },
  });
};
