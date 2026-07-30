// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
	// The site's own public address, and the only place it is written down.
	// Canonical link tags, Open Graph URLs, the sitemap and the generated
	// robots.txt / security.txt all derive from it — moving the site is a
	// one-line change here, not a sweep across files.
	//
	// No `base` on purpose: this is an apex-style custom domain, so every
	// internal path stays root-relative and llms.txt keeps working as written.
	site: 'https://secure-docker.rubennati.at',
	integrations: [
		starlight({
			title: 'Secure Docker Blueprint',
			customCss: ['./src/styles/custom.css'],
			description: 'Security-focused Docker Compose infrastructure with Traefik, CrowdSec, Docker Secrets and operational guidance for self-hosted services.',
			social: [
				{ icon: 'github', label: 'GitHub', href: 'https://github.com/rubennati/secure-docker-blueprint' },
			],
			components: {
				Head: './src/components/Head.astro',
			},
			// A reader arrives at any of these pages, from a search engine as often
			// as from the home page, and needs to recognise from the section alone
			// what kind of information sits there. So the top level names subjects,
			// not steps: a section heading that reads like an instruction promises
			// an order the site cannot keep — Traefik is required, CrowdSec is
			// optional, and a restore is not "after" adding an application.
			//
			// Ordering runs roughly from first-contact to reference, but only the
			// Start pages are genuinely sequential, and only they carry prev/next
			// links (`pagination` below is off by default).
			//
			// Page titles stay outcome-shaped. The section is the stable part.
			sidebar: [
				{
					label: 'Start',
					items: [
						{ label: 'What you are setting up', link: '/getting-started/' },
						{ label: 'Preparing a server', link: '/getting-started/server-setup/' },
					],
				},
				{
					// Traefik and CrowdSec share a server-wide scope and nothing else:
					// one is a prerequisite for every application, the other is an
					// optional layer. The overview page draws that line — a section
					// label cannot.
					label: 'Infrastructure and security',
					items: [
						{ label: 'What every server needs', link: '/infrastructure/' },
						{ label: 'Traefik — routing and TLS', link: '/infrastructure/traefik/' },
						{ label: 'CrowdSec — intrusion detection', link: '/infrastructure/crowdsec/' },
					],
				},
				{
					// OnlyOffice lives here, not with the infrastructure: nothing
					// breaks without it, and it exists for the applications that
					// embed it.
					label: 'Applications',
					items: [
						{ label: 'What each one is for', link: '/applications/' },
						{ label: 'Choosing between services', link: '/applications/choosing/' },
						{ label: 'Vaultwarden — passwords', link: '/applications/vaultwarden/' },
						{ label: 'Nextcloud — files and calendars', link: '/applications/nextcloud/' },
						{ label: 'Invoice Ninja — invoicing', link: '/applications/invoiceninja/' },
						{ label: 'Seafile Pro — file sync', link: '/applications/seafile-pro/' },
						{ label: 'OnlyOffice — document editing', link: '/applications/onlyoffice/' },
					],
				},
				{
					label: 'Operations and recovery',
					items: [
						{ label: 'What running this involves', link: '/operations/' },
						{ label: 'Backup and restore', link: '/operations/backup/' },
						{ label: 'When something is broken', link: '/operations/troubleshooting/' },
					],
				},
				{
					label: 'Architecture and data sovereignty',
					items: [
						{ label: 'How a server fits together', link: '/architecture/' },
						{ label: 'What self-hosting does not answer', link: '/sovereignty/' },
						{ label: 'Putting a CDN in front', link: '/sovereignty/edge/' },
					],
				},
				{
					label: 'Reference',
					items: [
						{ label: 'FAQ', link: '/faq/' },
						{ label: 'About the project', link: '/project/' },
					],
				},
			],
			// The site is not a book. Automatic prev/next arrows invent a reading
			// order across unrelated guides — from CrowdSec to Vaultwarden, as if
			// one followed the other. Pages that do have a successor declare it in
			// their own frontmatter.
			pagination: false,
		}),
	],
});
