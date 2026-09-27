# 0009. Native ES modules and design tokens now, React + Vite later

- Status: Accepted
- Date: 2026-09-27

## Context

The 2022 frontend was about 4,000 lines of global-scope JavaScript with inline
`onclick` handlers, four page-specific stylesheets with no shared styles, and five
libraries from third-party CDNs (moment.js 2.29.3 with known vulnerabilities,
Chart.js 2.5, boxicons, TypewriterJS, Socket.IO 4.0). On phones the tags, profile,
friends and chat panels were hidden entirely. Failures were mostly `console.log`,
so users saw nothing when an action failed.

We want to move to React + Vite eventually, but a big-bang rewrite would change the
build and deploy pipeline and every page at once.

## Decision

Rewrite the frontend in place, shaped so each piece can move into React later:

- **Native ES modules, no build step.** Pages load `<script type="module">`; imports
  look exactly like they will under Vite.
- **Shared layer in `static/js/lib/`**: `api.js` (fetch wrapper, readable errors),
  `dom.js` (an `h()` helper that builds trees like JSX, text only, never HTML),
  `icons.js` (inline SVG), `time.js` (`Intl` instead of moment.js, and the Taipei
  wall-clock times the API stores), `toast.js`, `upload.js`, `socket.js`.
- **One folder per page** in `static/js/pages/`; the member page is split into
  components (feed, post, composer, tags, friends, chat, notifications, profile)
  that talk through a small event bus instead of each other's DOM.
- **Design tokens and components** (buttons, inputs, cards, chips, dialog, toast)
  as CSS custom properties in `static/css/base.css`.
- **No third-party CDNs**: Socket.IO is vendored in `static/vendor/`; the other
  libraries were replaced by a few lines of our own code.
- **Phones get a bottom tab bar** instead of losing panels; native `<dialog>`,
  labelled controls and focus styles for keyboard and screen-reader use.

## Consequences

- No new tooling in CI or the Docker image; a failed JS change is caught by
  `node --check` in CI and by exercising the pages.
- Views are rebuilt by hand (`replaceChildren`) rather than diffed; fine at this
  size, and exactly what React will take over.
- No TypeScript or bundling yet: no tree-shaking, no minification of our own code
  (about 130 KB unminified, cached by browsers).

## Migration path to React + Vite

1. Add Vite with `static/` as its public root; the ES modules already resolve.
2. Keep `lib/` as is: `api.js`, `time.js` and `upload.js` are framework-free.
3. Port one component at a time, starting with leaves (`post.js`, `tags.js`),
   turning `h()` calls into JSX and the event bus into props or context.
4. Move `base.css` tokens into the React app unchanged.

## Revisit when

We need shared state across many views, TypeScript, or the JavaScript grows enough
that bundling matters.
