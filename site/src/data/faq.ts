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
          'Yes, throughout. Any service can be locked to Tailscale-only access, and Traefik supports dual-stack IPv6 specifically so Tailscale’s IPv6 client addresses are preserved correctly — a real failure mode this Blueprint documents and fixes, not a hypothetical one.',
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
        question: 'What actually protects me if a container gets compromised?',
        answer:
          'Several independent layers, not one. Docker Secrets keep credentials out of environment variables and shell history. A socket proxy means Traefik never touches the Docker socket directly. Each application’s internal services sit on an isolated network, unreachable from other apps. CrowdSec adds optional intrusion detection and blocking on top of all of that.',
        link: { text: 'CrowdSec guide', href: '/core/crowdsec/' },
      },
      {
        question: 'Will my data be backed up automatically?',
        answer:
          'No, not yet, for most services — stated directly per service rather than assumed. The Vaultwarden guide covers what to back up manually and how; a documented, tested restore procedure is still being built out.',
        link: { text: 'Vaultwarden guide — backup', href: '/applications/vaultwarden/#backup-before-real-use' },
      },
    ],
  },
  {
    category: 'Scope & Status',
    items: [
      {
        question: 'What do the status labels mean?',
        answer:
          'Every guide carries one of three labels at the top. Preview means the stack is on disk and may well work, but it has not been verified end to end here — evaluate it yourself before trusting it with data. Ready means a clean install, working core function and the security baseline have all been established. Ops-ready adds the one thing Ready does not promise: a restore has actually been performed from a backup, not merely written down. Alongside the label you get the version the guide sets up, the date it was last checked, and a line naming whatever has not been exercised yet.',
      },
      {
        question: 'Is this safe to run in production today?',
        answer:
          'Traefik, CrowdSec, and Vaultwarden are each verified end to end — setup through backup, restore, and updates — and considered stable. Nextcloud has been installed, hardened and backed up on a live host with its database restored from that backup, but desktop and mobile client sync have not been exercised. Seafile Pro has been installed and verified in a real deployment, but backup and restore have not been tested for this guide. Newer additions may still see breaking changes to file paths or variable names before the project reaches its 1.0 milestone.',
      },
      {
        question: 'What can I actually deploy right now?',
        answer:
          'Core infrastructure (Traefik, CrowdSec), a working backup chain with Borgmatic, plus a growing set of application guides — currently Vaultwarden (fully verified including backup and restore), Nextcloud (installation, hardening and backup verified; client sync not yet) and Seafile Pro (installation verified; backup and restore not yet tested). New guides are added once installation is verified end to end, not as soon as a container starts.',
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
