# 0016. Installable web app and Web Push before a native app

- Status: Accepted
- Date: 2026-10-05

## Context

The owner wants MotiveTag on the App Store ([0010](0010-roadmap-to-an-ios-app.md)).
That app is months away, but the website loses people as soon as they close the
tab: a new message or friend request goes unnoticed until they happen to come back.
Apple also requires a privacy policy, terms of use and a way to contact the
developer.

## Decision

- **Privacy policy and terms** at `/privacy` and `/terms` (templates `privacy.html`,
  `terms.html`), written to match what the site really stores (chat, photos, report
  snapshots, 35-day backups). Linked from sign-up and from 帳號設定. The contact
  e-mail comes from `/motivetag/contact-email`; until it is set the pages point to
  the in-site report.
- **Installable** (PWA): `/manifest.webmanifest`, icons from the site's avatar art,
  and a service worker at `/sw.js` that caches nothing (so a deploy is never hidden
  behind an old copy) and only shows notifications.
- **Web Push** with VAPID keys we hold ourselves (`/motivetag/vapid-public-key`,
  `/motivetag/vapid-private-key`), sent with `pywebpush` from a background greenlet.
  Pushed: new chat messages and bell notifications, only to members with no open
  tab. Subscriptions live in `push_subscription` (migration 0009); a 404/410 from
  the push service deletes one. Each device turns it on in 帳號設定 → 手機通知. On
  iPhone it works once the site is added to the home screen (iOS 16.4+).

## Consequences

- No new cost: the browsers' push services are free, and nothing else is added.
- A message goes through Google's, Apple's or Mozilla's push service; the payload is
  encrypted end to end by the Web Push protocol, but they see when and to whom.
  The privacy policy says so.
- The native app can reuse the same triggers and subscription table, with an APNs
  sender beside the Web Push one.
- Members who keep a tab open in the background get no push; the tab shows a badge
  and plays nothing. Good enough until we know presence per tab is "visible".

## Alternatives considered

- **Firebase Cloud Messaging or OneSignal**: another account and SDK for what the
  browser standard already does.
- **A native app first**: months of work before anyone gets a notification.
- **E-mail notifications**: SES is not in production yet, and e-mail for every chat
  message is too much.

## Revisit when

The native app ships (add APNs), or members ask to choose which events notify them.
