// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
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
			sidebar: [
				{
					label: 'Getting Started',
					items: [
						{ label: 'The basic path', link: '/getting-started/' },
						{ label: 'Setting up a server', link: '/getting-started/server-setup/' },
					],
				},
				{
					label: 'Core Infrastructure',
					items: [
						{ label: 'Overview', link: '/core/' },
						{ label: 'Traefik', link: '/core/traefik/' },
						{ label: 'CrowdSec', link: '/core/crowdsec/' },
						{ label: 'OnlyOffice', link: '/core/onlyoffice/' },
					],
				},
				{
					label: 'Applications',
					items: [
						{ label: 'Overview', link: '/applications/' },
						{ label: 'Vaultwarden', link: '/applications/vaultwarden/' },
						{ label: 'Nextcloud', link: '/applications/nextcloud/' },
						{ label: 'Seafile Pro', link: '/applications/seafile-pro/' },
					],
				},
				{ label: 'Operations', link: '/operations/' },
				{ label: 'FAQ', link: '/faq/' },
				{ label: 'Project', link: '/project/' },
			],
		}),
	],
});
