# 0010. Prepare for an iOS app step by step

- Status: Accepted
- Date: 2026-09-27

## Context

An iOS app is a goal, but a distant one. Shipping it later should not mean rewriting
the backend or the web app at the last minute. Most of the work an app needs is the
same whatever the app is built with, and several App Store rules for social apps
apply to the website too:

- **Account deletion** inside the product (App Review Guideline 5.1.1(v)).
- **Reporting content, blocking members and filtering objectionable content**, with a
  way to contact us (Guideline 1.2). Anonymous posts and chat make this important.
- A **privacy policy** and terms of use.
- Sign in with Apple only if we add other third-party sign-ins (Guideline 4.8).

The API was built for one web page: many errors come back as HTTP 200 with
`{"error": …}`, sessions are cookies, timestamps are Taipei wall-clock times labelled
"GMT", paging is by offset, and notifications are polled.

## Decision

Build the app later with **Expo (React Native)**, sharing a TypeScript core (API
client, types, validation, time handling) with the web app, which moves to React +
Vite ([0009](0009-frontend-es-modules-before-react.md)). Until then, prepare in
phases that each ship on their own and cost nothing:

| Phase | Work |
|---|---|
| 0 | `/api/v1` for new and reworked endpoints: real HTTP status codes, errors as `{"error": {"code", "message"}}`. Timestamps move to UTC ISO 8601. |
| 1 | App Store rules on the website first: account deletion (first), reporting, blocking, privacy policy and terms. |
| 2 | Monorepo: `packages/core` (TypeScript API client and types, generated from an OpenAPI description) and `apps/web` (React + Vite), porting one page at a time. |
| 3 | Token authentication next to the cookie session, cursor paging, Redis for chat presence so gunicorn can run more than one worker ([0008](0008-single-gunicorn-worker.md)). |
| 4 | `apps/mobile` with Expo, push notifications (APNs) from the same notification records, TestFlight. The Apple Developer Program (US$99/year) is needed only here. |

Flask stays. Request validation and an OpenAPI description can be added to it; the
chat (Flask-SocketIO) would otherwise need rewriting. We revisit FastAPI once the v1
API is stable.

## Consequences

- Each phase is useful on the website by itself, so none is wasted if the app slips.
- For a while there are two API styles: old endpoints keep their shape until the web
  pages that use them are ported; everything new or reworked goes to `/api/v1`.
- Deleting an account deletes the member's posts, comments, votes, reactions,
  friendships, notifications and images. Topics and replies on tag boards stay,
  shown as from a deleted account, so discussions keep their context. Database
  backups still hold deleted data until they expire (35 days); the privacy policy
  must say so.

## Alternatives considered

- **Capacitor (the website in an app shell)**: the most reuse, but an app that is only
  a website risks rejection under Guideline 4.2 and feels less native in chat and
  feeds.
- **Swift**: the best iOS experience, but a second code base with nothing shared.
- **Rewrite the backend in FastAPI now**: a big change with little gain before the
  API contract settles.

## Revisit when

We start phase 4, or someone else joins and a different app stack is familiar to them.
