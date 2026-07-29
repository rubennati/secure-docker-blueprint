// Single source of truth for FAQ content. Both the rendered page
// (src/components/FaqList.astro) and the FAQPage JSON-LD
// (src/components/Head.astro) read from this file — content is
// authored here only, never duplicated elsewhere.
//
// Rules, established after a review found earlier drafts deferring to
// repository files instead of answering directly, and asking
// self-referential questions about the site instead of the Blueprint:
//
// - Every answer stands on its own. Linking to ROADMAP.md/UPSTREAM.md
//   in the repository as the actual answer is not allowed — the site
//   is for operators, the repository is for developers (see
//   src/content/docs/project/index.md). `link` may point to another
//   page on this site for more detail, never to a repository file as
//   the primary answer.
// - Answers are plain text (no markdown) — this is what lets them be
//   reused verbatim in JSON-LD without a markdown-stripping step.
// - No questions about the site itself (is this the source of truth,
//   why is the site smaller than the repo, etc.) — that's covered once
//   in src/content/docs/project/index.md, not duplicated here.

export interface FaqLink {
  text: string;
  href: string;
}

export interface FaqEntry {
  question: string;
  answer: string;
  link?: FaqLink;
}

export interface FaqCategory {
  category: string;
  items: FaqEntry[];
}

export const faqCategories: FaqCategory[] = [
  {
    category: 'Networking & Access',
    items: [
      {
        question: 'Does this work with Tailscale?',
        answer:
          'Yes. Any service can be restricted to Tailscale-only access. Traefik is set up for dual-stack IPv6 because Tailscale hands a client both an IPv4 and an IPv6 address — on an IPv4-only proxy the IPv6 connection arrives with the wrong source address and an IP allowlist rejects it.',
        link: { text: 'Traefik guide', href: '/core/traefik/' },
      },
      {
        question: 'Do I need a Cloudflare account?',
        answer:
          'No. Cloudflare DNS-01 is the Traefik quickstart path because it avoids exposing port 80 publicly, but per-domain certificates via the standard HTTP-01 challenge work with no Cloudflare account at all.',
        link: { text: 'Traefik guide — certificate strategy', href: '/core/traefik/#certificate-strategy' },
      },
    ],
  },
  {
    category: 'Security',
    items: [
      {
        question: 'How are services separated from each other?',
        answer:
          'Each application’s services run on their own Docker network, so they are not routable from another application’s containers. Credentials are mounted as files rather than set in the environment, which keeps them out of container inspection and shell history. Traefik reads the Docker socket through a proxy instead of mounting it. CrowdSec can be added for detection and blocking. These are separate layers — how far a compromise gets still depends on the container and the image it runs.',
        link: { text: 'CrowdSec guide', href: '/core/crowdsec/' },
      },
      {
        question: 'Will my data be backed up automatically?',
        answer:
          'No. Backup is a separate setup step: Borgmatic is installed on the host, and the backup guide covers configuring it, dumping databases from running containers, and scheduling it. What to back up for a particular service is on that service’s page.',
        link: { text: 'Backup and restore', href: '/operations/backup/' },
      },
    ],
  },
  {
    category: 'Scope & Status',
    items: [
      {
        question: 'What do the status labels mean?',
        answer:
          'Every guide carries one of three labels at the top. Preview means the stack is on disk and may well work, but it has not been checked end to end here — evaluate it yourself before trusting it with data. Ready means a clean install, working core function and the security baseline were all established. Ops-ready means a restore was performed from a backup, not only written down; no application holds it yet. Alongside the label you get the version the guide sets up, the date it was last checked, and a line naming what has not been exercised.',
      },
      {
        question: 'Is this safe to run in production today?',
        answer:
          'The per-service answer is the label at the top of each guide, together with the sentence naming what has not been exercised for it. Two things apply across all of them: no application has had a restore rehearsed, so recovery is your own responsibility to establish, and file paths and variable names can still change before the 1.0 milestone.',
      },
      {
        question: 'What can I actually deploy right now?',
        answer:
          'Core infrastructure (Traefik, CrowdSec), Borgmatic for backups, and the application guides listed under Applications. Each guide states its own label, the version it sets up and when that was last checked. A guide goes up once the installation has been walked through, not when a container first starts.',
        link: { text: 'Applications', href: '/applications/' },
      },
      {
        question: 'Can I deploy only some services to a new server?',
        answer:
          'Yes — clone the repository once, then copy only the directories for the services you actually need to the target host. There is no dedicated deploy tool for this yet; copying the directories you need is the current path.',
      },
      {
        question: 'What does it cost?',
        answer:
          'The Blueprint itself is free and Apache 2.0 licensed. You pay for your own server and domain; the self-hosted services it configures are predominantly open source too.',
      },
    ],
  },
];
