// The source register. Every citation on this site resolves to an entry here,
// and pages reference an `id` — never a bare URL.
//
// Why a register rather than inline links: a link that still resolves is not
// the same as a source that still carries the claim. Holding publisher,
// jurisdiction and a `lastChecked` date in one place makes it possible to ask
// "which of our sources has nobody looked at in a year" — which is the question
// that actually matters — and it keeps one URL from drifting across five pages.
//
// Precedence, applied in this order and only where the source genuinely covers
// the point:
//
//   1. Austria      — for legal questions, and for guidance aimed at operators here
//   2. Germany      — BSI and IT-Grundschutz, where they are more specific
//   3. EU           — ENISA, EDPB, EUR-Lex
//   4. International — IETF, W3C, NIST, OWASP, and vendor documentation
//
// Nationality is not a tiebreaker on its own. For a legal claim, jurisdiction
// decides. For a technical claim, the most competent current primary source
// decides — an outdated national page does not outrank a current RFC.
//
// `lastChecked` means a human opened the page and confirmed it still supports
// the claim it is cited for. Moving the date without doing that defeats the
// purpose of having it.

export type Jurisdiction = 'Austria' | 'Germany' | 'EU' | 'International';

export type SourceKind =
	/** A public body's recommendation or advice. */
	| 'official-guidance'
	/** A published technical standard or specification. */
	| 'standard'
	/** Statute or regulation. */
	| 'legislation'
	/** The documentation of the software being described. */
	| 'vendor-docs';

export interface Source {
	id: string;
	title: string;
	publisher: string;
	jurisdiction: Jurisdiction;
	kind: SourceKind;
	/** ISO date the source itself carries, where it states one. */
	published?: string;
	/** ISO date a human last confirmed this still supports what it is cited for. */
	lastChecked: string;
	url: string;
	/** What this source is cited *for*. Keeps a re-check honest. */
	supports: string;
}

export const sources: Source[] = [
	// --- Austria -----------------------------------------------------------
	{
		id: 'at-cert',
		title: 'About CERT.at',
		publisher: 'CERT.at — Austrian National Computer Emergency Response Team',
		jurisdiction: 'Austria',
		kind: 'official-guidance',
		lastChecked: '2026-07-30',
		url: 'https://www.cert.at/en/about-us/',
		supports:
			'CERT.at is Austria’s national CERT and publishes warnings and incident guidance for organisations and the public.',
	},
	{
		id: 'at-onlinesicherheit',
		title: 'onlinesicherheit.gv.at',
		publisher: 'A-SIT / Federal Ministry of Finance',
		jurisdiction: 'Austria',
		kind: 'official-guidance',
		lastChecked: '2026-07-30',
		url: 'https://www.onlinesicherheit.gv.at/',
		supports:
			'Austrian public guidance on passwords, multi-factor authentication and everyday security practice.',
	},
	{
		id: 'at-dsb-cookies',
		title: 'Datenschutz und Cookies',
		publisher: 'Österreichische Datenschutzbehörde',
		jurisdiction: 'Austria',
		kind: 'official-guidance',
		lastChecked: '2026-07-30',
		url: 'https://dsb.gv.at/faqs/datenschutz-cookies',
		supports:
			'Technically necessary cookies do not require consent; processing must still be disclosed transparently.',
	},

	// --- Germany -----------------------------------------------------------
	{
		id: 'de-bsi-grundschutz',
		title: 'IT-Grundschutz-Kompendium',
		publisher: 'Bundesamt für Sicherheit in der Informationstechnik (BSI)',
		jurisdiction: 'Germany',
		kind: 'official-guidance',
		lastChecked: '2026-07-30',
		url: 'https://www.bsi.bund.de/DE/Themen/Unternehmen-und-Organisationen/Standards-und-Zertifizierung/IT-Grundschutz/IT-Grundschutz-Kompendium/it-grundschutz-kompendium_node.html',
		supports:
			'Structured baseline security requirements per building block; the BSI directs readers to the current edition because the technical content is revised.',
	},

	// --- EU ----------------------------------------------------------------
	{
		id: 'eu-enisa-sme',
		title: 'Cybersecurity Guide for SMEs',
		publisher: 'ENISA — European Union Agency for Cybersecurity',
		jurisdiction: 'EU',
		kind: 'official-guidance',
		published: '2021-06-28',
		lastChecked: '2026-07-30',
		url: 'https://www.enisa.europa.eu/publications/cybersecurity-guide-for-smes',
		supports:
			'Practical baseline measures for small organisations, including backup, multi-factor authentication and patching.',
	},

	// --- International -----------------------------------------------------
	{
		id: 'nist-sp800-41',
		title: 'SP 800-41 Rev. 1 — Guidelines on Firewalls and Firewall Policy',
		publisher: 'NIST',
		jurisdiction: 'International',
		published: '2009-09-28',
		lastChecked: '2026-07-30',
		kind: 'standard',
		url: 'https://csrc.nist.gov/pubs/sp/800/41/r1/final',
		supports:
			'Host-based and network firewalls are distinct, complementary technologies placed at different points, not ranked alternatives.',
	},
	{
		id: 'cisa-microsegmentation',
		title: 'Zero Trust Microsegmentation Guidance',
		publisher: 'CISA',
		jurisdiction: 'International',
		published: '2025-07-29',
		lastChecked: '2026-07-30',
		kind: 'official-guidance',
		url: 'https://www.cisa.gov/news-events/alerts/2025/07/29/cisa-releases-part-one-zero-trust-microsegmentation-guidance',
		supports:
			'Segmentation is named as a means of reducing attack surface and constraining lateral movement.',
	},
	{
		id: 'cisa-logging',
		title: 'Use Logging on Business Systems',
		publisher: 'CISA',
		jurisdiction: 'International',
		kind: 'official-guidance',
		lastChecked: '2026-07-30',
		url: 'https://www.cisa.gov/audiences/small-and-medium-businesses/secure-your-business/use-logging-on-business-systems',
		supports:
			'Collect logs from servers, firewalls, applications and endpoints, review them centrally, and alert on events such as failed logins and privilege escalation.',
	},
	{
		id: 'owasp-wstg',
		title: 'Web Security Testing Guide',
		publisher: 'OWASP Foundation',
		jurisdiction: 'International',
		kind: 'standard',
		lastChecked: '2026-07-30',
		url: 'https://owasp.org/www-project-web-security-testing-guide/',
		supports:
			'Injection and file-upload weaknesses are distinct classes with distinct controls; a filter in front of an application does not remove either.',
	},
	{
		id: 'docker-packet-filtering',
		title: 'Packet filtering and firewalls',
		publisher: 'Docker',
		jurisdiction: 'International',
		kind: 'vendor-docs',
		lastChecked: '2026-07-30',
		url: 'https://docs.docker.com/engine/network/packet-filtering-firewalls/',
		supports:
			'Docker installs its own iptables rules for published ports. Because they are evaluated ahead of a host firewall’s own rules, a published container port is reachable even when the host firewall is configured to deny it; the DOCKER-USER chain is the documented place for rules that must take effect first.',
	},
	{
		id: 'docker-userns',
		title: 'Isolate containers with a user namespace',
		publisher: 'Docker',
		jurisdiction: 'International',
		kind: 'vendor-docs',
		lastChecked: '2026-07-30',
		url: 'https://docs.docker.com/engine/security/userns-remap/',
		supports:
			'Containers are isolated processes sharing the host kernel; Docker recommends unprivileged processes, reduced capabilities and user namespaces to limit the effect of a compromise.',
	},
	{
		id: 'rfc-9116',
		title: 'RFC 9116 — A File Format to Aid in Security Vulnerability Disclosure',
		publisher: 'IETF',
		jurisdiction: 'International',
		published: '2022-04-01',
		lastChecked: '2026-07-30',
		kind: 'standard',
		url: 'https://www.rfc-editor.org/rfc/rfc9116.html',
		supports:
			'`security.txt` is the standardised machine-readable location for vulnerability disclosure contacts.',
	},
	{
		id: 'nist-sp800-63b',
		title: 'SP 800-63B — Digital Identity Guidelines: Authentication and Lifecycle Management',
		publisher: 'NIST',
		jurisdiction: 'International',
		kind: 'standard',
		lastChecked: '2026-07-30',
		url: 'https://pages.nist.gov/800-63-3/sp800-63b.html',
		supports:
			'Length matters more than composition rules; forced periodic password expiry is not recommended without evidence of compromise; SMS is a weaker authenticator than an authenticator app or a hardware key.',
	},
	{
		id: 'nist-sp800-57',
		title: 'SP 800-57 Part 1 Rev. 5 — Recommendation for Key Management',
		publisher: 'NIST',
		jurisdiction: 'International',
		published: '2020-05-04',
		lastChecked: '2026-07-30',
		kind: 'standard',
		url: 'https://csrc.nist.gov/pubs/sp/800/57/pt1/r5/final',
		supports:
			'Keys have a defined lifecycle — generation, distribution, storage, rotation, destruction — and the protection of a key bounds the protection of everything encrypted with it.',
	},
	{
		id: 'nist-sp800-190',
		title: 'SP 800-190 — Application Container Security Guide',
		publisher: 'NIST',
		jurisdiction: 'International',
		published: '2017-09-25',
		lastChecked: '2026-07-30',
		kind: 'standard',
		url: 'https://csrc.nist.gov/pubs/sp/800/190/final',
		supports:
			'Containers share the host kernel, so a kernel vulnerability is a shared risk; grouping containers of differing sensitivity on one host, and running them with more privilege than needed, are named risks.',
	},
	{
		id: 'nist-sp800-94',
		title: 'SP 800-94 — Guide to Intrusion Detection and Prevention Systems',
		publisher: 'NIST',
		jurisdiction: 'International',
		published: '2007-02-20',
		lastChecked: '2026-07-30',
		kind: 'standard',
		url: 'https://csrc.nist.gov/pubs/sp/800/94/final',
		supports:
			'Detection and prevention are distinct functions: a detection system reports, a prevention system acts on the traffic. Both produce false positives, and a prevention system’s false positive denies legitimate use.',
	},
	{
		id: 'nist-sp800-61',
		title: 'SP 800-61 Rev. 2 — Computer Security Incident Handling Guide',
		publisher: 'NIST',
		jurisdiction: 'International',
		published: '2012-08-06',
		lastChecked: '2026-07-30',
		kind: 'standard',
		url: 'https://csrc.nist.gov/pubs/sp/800/61/r2/final',
		supports:
			'Incident response is a cycle — preparation, detection and analysis, containment, eradication and recovery, then post-incident learning — and the preparation half decides how the rest goes.',
	},
	{
		id: 'nist-sp800-34',
		title: 'SP 800-34 Rev. 1 — Contingency Planning Guide for Federal Information Systems',
		publisher: 'NIST',
		jurisdiction: 'International',
		published: '2010-05-01',
		lastChecked: '2026-07-30',
		kind: 'standard',
		url: 'https://csrc.nist.gov/pubs/sp/800/34/r1/final',
		supports:
			'A recovery capability is established by testing it, not by documenting it; recovery objectives have to be stated before a plan can be judged adequate.',
	},
	{
		id: 'owasp-password-storage',
		title: 'Password Storage Cheat Sheet',
		publisher: 'OWASP Foundation',
		jurisdiction: 'International',
		kind: 'standard',
		lastChecked: '2026-07-30',
		url: 'https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html',
		supports:
			'Passwords are stored with a slow, salted password-hashing function such as Argon2id or bcrypt — general-purpose hashes like SHA-256 are unsuitable because they are fast.',
	},
	{
		id: 'owasp-secure-headers',
		title: 'OWASP Secure Headers Project',
		publisher: 'OWASP Foundation',
		jurisdiction: 'International',
		kind: 'standard',
		lastChecked: '2026-07-30',
		url: 'https://owasp.org/www-project-secure-headers/',
		supports:
			'The response headers that constrain browser behaviour, what each one does, and the fact that they mitigate specific browser-side attacks rather than securing the application.',
	},
	{
		id: 'rfc-8446',
		title: 'RFC 8446 — The Transport Layer Security (TLS) Protocol Version 1.3',
		publisher: 'IETF',
		jurisdiction: 'International',
		published: '2018-08-01',
		lastChecked: '2026-07-30',
		kind: 'standard',
		url: 'https://www.rfc-editor.org/rfc/rfc8446.html',
		supports:
			'TLS provides confidentiality and integrity for the connection and authenticates the server to the client. It makes no statement about the application behind it.',
	},
	{
		id: 'rfc-6797',
		title: 'RFC 6797 — HTTP Strict Transport Security (HSTS)',
		publisher: 'IETF',
		jurisdiction: 'International',
		published: '2012-11-01',
		lastChecked: '2026-07-30',
		kind: 'standard',
		url: 'https://www.rfc-editor.org/rfc/rfc6797.html',
		supports:
			'HSTS instructs a browser to use HTTPS for a host for a stated period. The first visit before the policy is known remains exposed unless the host is preloaded.',
	},
	{
		id: 'rfc-9162',
		title: 'RFC 9162 — Certificate Transparency Version 2.0',
		publisher: 'IETF',
		jurisdiction: 'International',
		published: '2021-12-01',
		lastChecked: '2026-07-30',
		kind: 'standard',
		url: 'https://www.rfc-editor.org/rfc/rfc9162.html',
		supports:
			'Publicly trusted certificates are logged in append-only public logs, which makes every hostname in a certificate publicly discoverable once it is issued.',
	},
	{
		id: 'letsencrypt-challenges',
		title: 'Challenge Types',
		publisher: "Let's Encrypt / ISRG",
		jurisdiction: 'International',
		kind: 'vendor-docs',
		lastChecked: '2026-07-30',
		url: 'https://letsencrypt.org/docs/challenge-types/',
		supports:
			'HTTP-01 requires the host to be reachable on port 80; DNS-01 proves control of the domain instead, and is the only challenge that can issue a wildcard certificate.',
	},
	{
		id: 'podman-rootless',
		title: 'podman — rootless mode',
		publisher: 'Podman',
		jurisdiction: 'International',
		kind: 'vendor-docs',
		lastChecked: '2026-07-30',
		url: 'https://docs.podman.io/en/latest/markdown/podman.1.html',
		supports:
			'Podman runs containers without a privileged long-running daemon, and supports rootless operation in which containers run under an unprivileged user account.',
	},
	{
		id: 'debian-unattended-upgrades',
		title: 'UnattendedUpgrades',
		publisher: 'Debian Wiki',
		jurisdiction: 'International',
		kind: 'vendor-docs',
		lastChecked: '2026-07-30',
		url: 'https://wiki.debian.org/UnattendedUpgrades',
		supports:
			'Debian can install security updates automatically via the unattended-upgrades package; it is configuration the operator adds, not a default of the base system.',
	},
	{
		id: 'cisa-stopransomware',
		title: '#StopRansomware Guide',
		publisher: 'CISA',
		jurisdiction: 'International',
		lastChecked: '2026-07-30',
		kind: 'official-guidance',
		url: 'https://www.cisa.gov/resources-tools/resources/stopransomware-guide',
		supports:
			'Maintain offline, encrypted backups and test restoration; backups reachable with ordinary administrative credentials are reachable by an intruder holding them.',
	},
	{
		id: 'w3c-g200',
		title: 'G200: Opening new windows and tabs from a link only when necessary',
		publisher: 'W3C — Web Accessibility Initiative',
		jurisdiction: 'International',
		kind: 'standard',
		lastChecked: '2026-07-30',
		url: 'https://www.w3.org/WAI/WCAG22/Techniques/general/G200.html',
		supports:
			'Where a link opens a new window or tab, say so in a way that is available before activation and to assistive technology.',
	},
];

/** Build-time integrity: a bad entry stops the build rather than shipping. */
const seen = new Set<string>();
for (const s of sources) {
	if (seen.has(s.id)) throw new Error(`sources.ts: duplicate id "${s.id}"`);
	seen.add(s.id);
	if (!s.url.startsWith('https://')) {
		throw new Error(`sources.ts: "${s.id}" must be an https URL — got ${s.url}`);
	}
	if (Number.isNaN(Date.parse(s.lastChecked))) {
		throw new Error(`sources.ts: "${s.id}" has an unparseable lastChecked "${s.lastChecked}"`);
	}
	if (!s.supports.trim()) {
		throw new Error(`sources.ts: "${s.id}" needs a "supports" line saying what it is cited for`);
	}
}

const byId = new Map(sources.map((s) => [s.id, s]));

/** Look up sources by id, failing the build on a typo rather than dropping a citation. */
export function getSources(ids: string[]): Source[] {
	return ids.map((id) => {
		const found = byId.get(id);
		if (!found) {
			throw new Error(
				`Unknown source id "${id}". Add it to src/data/sources.ts, or fix the reference.`,
			);
		}
		return found;
	});
}

/** Hostname shown to the reader before they follow a link off this site. */
export const hostOf = (url: string) => new URL(url).hostname.replace(/^www\./, '');
