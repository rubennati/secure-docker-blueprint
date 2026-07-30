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
			// Grouped by what the reader is trying to do, not by the repository's
			// directory split — someone arriving with "I want a password manager"
			// should not have to know what `core/` and `apps/` mean. The pages
			// themselves keep the names the repository uses.
			sidebar: [
				{
					label: 'Start here',
					items: [
						{ label: 'The basic path', link: '/getting-started/' },
						{ label: 'Setting up a server', link: '/getting-started/server-setup/' },
					],
				},
				{
					label: 'Set up the foundation',
					items: [
						{ label: 'Which services, and why', link: '/core/' },
						{ label: 'Traefik — routing and TLS', link: '/core/traefik/' },
						{ label: 'CrowdSec — intrusion detection', link: '/core/crowdsec/' },
						{ label: 'OnlyOffice — document editing', link: '/core/onlyoffice/' },
					],
				},
				{
					label: 'Add a service',
					items: [
						{ label: 'Which services have a guide', link: '/applications/' },
						{ label: 'Choosing between services', link: '/applications/choosing/' },
						{ label: 'Vaultwarden — passwords', link: '/applications/vaultwarden/' },
						{ label: 'Nextcloud — files and calendars', link: '/applications/nextcloud/' },
						{ label: 'Invoice Ninja — invoicing', link: '/applications/invoiceninja/' },
						{ label: 'Seafile Pro — file sync', link: '/applications/seafile-pro/' },
					],
				},
				{
					label: 'Operate and recover',
					items: [
						{ label: 'What this section covers', link: '/operations/' },
						{ label: 'Backup and restore', link: '/operations/backup/' },
					],
				},
				{
					label: 'Data sovereignty',
					items: [
						{ label: 'What self-hosting does not answer', link: '/sovereignty/' },
						{ label: 'Putting a CDN in front', link: '/sovereignty/edge/' },
					],
				},
				{ label: 'FAQ', link: '/faq/' },
				{ label: 'About the project', link: '/project/' },
			],
		}),
	],
});
