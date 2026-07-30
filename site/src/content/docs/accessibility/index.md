---
title: Accessibility
description: What has been checked, what has not, and where the known weak points are — stated as findings rather than as a conformance claim.
---

This page says what has actually been tested. It does not claim conformance with
a standard, because no formal audit has been carried out and a claim without one
would be worth nothing.

## What has been checked, and how

Verified by driving the built site in a browser and reading the resulting DOM —
not by inspection of the source.

**Links that leave the site.** Each one carries its destination host and "opens
in a new tab" in its accessible name *before* activation, rather than signalling
it only with an icon or only after the fact. This follows the W3C technique for
announcing new windows.

**The leave-site dialog.** A native modal dialog, so focus is trapped and the
rest of the page is inert. Escape closes it — the browser's own handling was
found not to fire here, because something else on the page cancels the key
first, so it is closed explicitly instead. Focus returns to the link that opened
it, whichever way it was dismissed. Clicking outside dismisses it.

**Keyboard operation of that dialog** — tab order, Escape, focus return — was
exercised with real key events, not synthetic ones.

**Layout at 375 px and 1280 px**, in both light and dark schemes. The page body
never scrolls horizontally; wide tables and code blocks scroll inside their own
containers.

**Navigation entries fit on one line** at the sidebar width, so the menu reads
as a list rather than as wrapped prose.

**The wordmark** is announced as the single word "SecDockBlue" rather than as
three fragments, despite being styled in three parts.

## What has not been checked

Stated plainly, because the gaps matter more than the list above:

- **No screen reader has been used on this site.** Accessible names were read
  out of the DOM. That is not the same as hearing how a page is announced.
- **Contrast ratios have not been measured** against the WCAG thresholds. The
  colour scheme is Starlight's default with one accent changed, and the accent
  was chosen for appearance rather than by calculation.
- **No automated accessibility scan** is part of the build.
- **Keyboard traversal of whole pages** has not been walked — only the dialog.
- **Zoom to 200 % and 400 %**, and reduced-motion preferences, are untested.
- **Long code blocks** scroll horizontally, which is a known friction for
  keyboard and screen-magnifier users. It is the platform default here and has
  not been improved on.

## Underlying platform

The site is built with Astro Starlight, which handles landmarks, skip links,
heading structure and the mobile navigation. Those come from the framework and
have not been separately audited here. The parts written for this site are the
external-link handling, the dialog, the citation blocks, the evidence blocks,
the wordmark and the footer — those are what the findings above cover.

## Reporting a barrier

If something here is unusable for you, that is a defect and worth reporting.
Open an issue on the
[repository](https://github.com/rubennati/secure-docker-blueprint/issues/new),
describing what you were trying to do and what happened. A report naming a
concrete barrier is more useful than any statement on this page.
