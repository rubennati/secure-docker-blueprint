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
				Footer: './src/components/Footer.astro',
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
						// Product entries are the product name and nothing else. A
						// "— what it does" suffix wraps to a second line at this sidebar
						// width and turns a scannable list into paragraphs; the overview
						// page is where each one is explained.
						{ label: 'What every server needs', link: '/infrastructure/' },
						{ label: 'Traefik', link: '/infrastructure/traefik/' },
						{ label: 'CrowdSec', link: '/infrastructure/crowdsec/' },
						{ label: 'Authentik', link: '/infrastructure/authentik/' },
						{ label: 'Dockhand', link: '/infrastructure/dockhand/' },
						{ label: 'dnsmasq', link: '/infrastructure/dnsmasq/' },
						{ label: 'Certificates without a proxy', link: '/infrastructure/acme-certs/' },
					],
				},
				{
					// OnlyOffice lives here, not with the infrastructure: nothing
					// breaks without it, and it exists for the applications that
					// embed it.
					label: 'Applications',
					items: [
						{ label: 'What each one is for', link: '/applications/' },
						{ label: 'Choosing between them', link: '/applications/choosing/' },
						// The two orientation pages first, then the guides A–Z. Nothing
						// about one service makes it belong before another, so the order
						// is the one a reader can predict.
						{ label: 'Cal.diY', link: '/applications/caldiy/' },
						{ label: 'Dashy', link: '/applications/dashy/' },
						{ label: 'Documenso', link: '/applications/documenso/' },
						{ label: 'Ghost', link: '/applications/ghost/' },
						{ label: 'Immich', link: '/applications/immich/' },
						{ label: 'Invoice Ninja', link: '/applications/invoiceninja/' },
						{ label: 'Listmonk', link: '/applications/listmonk/' },
						{ label: 'n8n', link: '/applications/n8n/' },
						{ label: 'Nextcloud', link: '/applications/nextcloud/' },
						{ label: 'OnlyOffice', link: '/applications/onlyoffice/' },
						{ label: 'OpnForm', link: '/applications/opnform/' },
						{ label: 'Paperless-ngx', link: '/applications/paperless-ngx/' },
						{ label: 'PhotoPrism', link: '/applications/photoprism/' },
						{ label: 'Seafile', link: '/applications/seafile/' },
						{ label: 'Seafile Pro', link: '/applications/seafile-pro/' },
						{ label: 'Vaultwarden', link: '/applications/vaultwarden/' },
						{ label: 'WordPress', link: '/applications/wordpress/' },
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
						// Short enough to sit on one line at the sidebar width. The full
						// scope of each is in its own title; a menu entry that wraps is
						// a paragraph pretending to be a label.
						{ label: 'The whole chain', link: '/security/' },
						{ label: 'What you protect', link: '/security/goals/' },
						{ label: 'Firewalls', link: '/security/firewalls/' },
						{ label: 'TLS and certificates', link: '/security/tls/' },
						{ label: 'WAF, IDS and IPS', link: '/security/web-protection/' },
						{ label: 'Containers and VMs', link: '/security/isolation/' },
						{ label: 'Host and malware', link: '/security/host/' },
						{ label: 'Identity and access', link: '/security/identity/' },
						{ label: 'Cryptography', link: '/security/cryptography/' },
						{ label: 'Detection and response', link: '/security/detection/' },
						{ label: 'Backup and resilience', link: '/security/resilience/' },
						{ label: 'This blueprint in it', link: '/architecture/' },
					],
				},
				{
					// A different question from defence: not "can someone get in" but
					// "who governs this software, and what leaves the machine anyway".
					label: 'Data sovereignty',
					items: [
						{ label: 'Limits of self-hosting', link: '/sovereignty/' },
						{ label: 'Putting a CDN in front', link: '/sovereignty/edge/' },
					],
				},
				{
					label: 'Reference',
					items: [
						{ label: 'FAQ', link: '/faq/' },
						{ label: 'How sources are checked', link: '/sources/' },
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
