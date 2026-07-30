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
	site: 'https://secdockblue.rubennati.at',
	integrations: [
		starlight({
			// Two names, deliberately, because they are two things:
			//
			//   SecDockBlue           this site — guidance, security knowledge, and
			//                         the operator-facing product
			//   Secure Docker Blueprint   the repository — Compose files, the
			//                         technical source of truth
			//
			// The name does not fully explain itself, which is why the descriptive
			// line sits directly under it on every surface that carries it. Prose
			// referring to the Compose files keeps calling them the Blueprint.
			title: 'SecDockBlue',
			customCss: ['./src/styles/custom.css'],
			description: 'Secure self-hosting blueprints and operator guidance — deploying, protecting, operating and recovering self-hosted services.',
			social: [
				{ icon: 'github', label: 'GitHub', href: 'https://github.com/rubennati/secure-docker-blueprint' },
			],
			components: {
				Head: './src/components/Head.astro',
				SiteTitle: './src/components/SiteTitle.astro',
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
					//
					// "and security" was dropped when Security became its own section:
					// these two are implementations, and the concepts they implement
					// are explained once, over there.
					label: 'Infrastructure',
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
						// The two orientation pages first, then the guides A–Z. Nothing
						// about one service makes it belong before another, so the order
						// is the one a reader can predict.
						{ label: 'Invoice Ninja — invoicing', link: '/applications/invoiceninja/' },
						{ label: 'Nextcloud — files and calendars', link: '/applications/nextcloud/' },
						{ label: 'OnlyOffice — document editing', link: '/applications/onlyoffice/' },
						{ label: 'Seafile Pro — file sync', link: '/applications/seafile-pro/' },
						{ label: 'Vaultwarden — passwords', link: '/applications/vaultwarden/' },
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
					// Standalone operator knowledge: it holds whether or not the reader
					// uses this project's Compose files, and the blueprint appears only
					// as a worked example. The architecture page sits here because the
					// question it answers — what of the chain does this blueprint
					// cover — belongs next to the chain itself.
					// Not alphabetical, unlike the application list: these follow the
					// chain a request passes through, from the outside in, and that
					// order is the argument. Goals come first because a control can
					// only be judged against one.
					label: 'Security',
					items: [
						{ label: 'The whole chain', link: '/security/' },
						{ label: 'What you are protecting', link: '/security/goals/' },
						{ label: 'Firewalls and segmentation', link: '/security/firewalls/' },
						{ label: 'TLS and certificates', link: '/security/tls/' },
						{ label: 'WAF, IDS and IPS', link: '/security/web-protection/' },
						{ label: 'Containers, VMs and isolation', link: '/security/isolation/' },
						{ label: 'Host and malware protection', link: '/security/host/' },
						{ label: 'Identity and privileged access', link: '/security/identity/' },
						{ label: 'Cryptography and key management', link: '/security/cryptography/' },
						{ label: 'Detection and incident response', link: '/security/detection/' },
						{ label: 'Backup and resilience', link: '/security/resilience/' },
						{ label: 'How this blueprint fits it', link: '/architecture/' },
					],
				},
				{
					// A different question from defence: not "can someone get in" but
					// "who governs this software, and what leaves the machine anyway".
					label: 'Data sovereignty',
					items: [
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
