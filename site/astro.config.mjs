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
			sidebar: [
				{ label: 'Getting Started', link: '/getting-started/' },
				{
					label: 'Applications',
					items: [
						{ label: 'Overview', link: '/applications/' },
						{ label: 'Vaultwarden', link: '/applications/vaultwarden/' },
					],
				},
				{ label: 'Operations', link: '/operations/' },
				{ label: 'FAQ', link: '/faq/' },
				{ label: 'Project', link: '/project/' },
			],
		}),
	],
});
