// Site behaviour that is a judgement call rather than a fact, kept in one place
// so it can be changed without hunting through components.

/**
 * What happens when a reader follows a link off this site.
 *
 * The trade-off is real in both directions. Announcing the departure is honest
 * and makes the boundary between this site and a cited source unmistakable.
 * Doing it on every citation also puts a step in front of the sources, and
 * sources exist to be opened.
 *
 *   'always'            — confirm every external link
 *   'once-per-session'  — confirm the first one per visit, then stay out of the way
 *   'off'               — no confirmation; the link is still marked and still
 *                         shows its target host before the click
 *
 * Independent of this, external links always open in a new tab, are marked with
 * an icon, and announce "opens in a new tab" to assistive technology — W3C G200
 * asks that this be available before activation, not discovered after it.
 */
export const externalLinkInterstitial: 'always' | 'once-per-session' | 'off' = 'always';

/**
 * Hosts treated as part of this project rather than as somewhere else. A reader
 * following a link to the repository has not wandered off into the unknown, so
 * these are exempt from the confirmation — they still open in a new tab.
 */
export const ownHosts: string[] = ['github.com', 'secdockblue.rubennati.at'];

/**
 * Licence for the site's own text, diagrams and page structure.
 *
 * Deliberately separate from the repository's Apache-2.0, which covers code.
 * Applying a software licence to prose by default would be an assumption
 * nobody made — so this stays an explicit placeholder until it is decided,
 * rather than a claim the footer quietly starts making.
 */
export const siteContentLicence = 'CC BY-NC 4.0';
