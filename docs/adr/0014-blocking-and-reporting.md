# 0014. Blocking members and reporting content, reviewed by the owner on /admin

- Status: Accepted
- Date: 2026-09-29

## Context

Phase 1 of [0010](0010-roadmap-to-an-ios-app.md): App Store Guideline 1.2 requires a
social app to let people report objectionable content, block abusive members and
have the developer act on reports (Apple's guidance says within 24 hours). Anonymous
posts and private chat ([0013](0013-stored-direct-messages.md)) make this more
important, and the owner is considering a dating direction. There is one owner, no
moderation team and no budget for a moderation service.

## Decision

**Blocking** (`member_block`, `/api/v1/blocks`):

- Blocking ends any friendship or invitation between the two members.
- The blocker no longer sees the blocked member's posts (feed, tag search, explore)
  or comments. The blocked member still sees the blocker's content: nothing is
  announced, and hiding content from them could reveal who wrote an anonymous post.
- In both directions: no chat messages, typing signals, friend invitations or
  notifications; neither is suggested to the other.
- Undone from the member's card or the block list in 帳號設定.

**Reporting** (`report`, `POST /api/v1/reports`): posts, comments, received chat
messages and members, with a reason (spam, harassment, sexual, violence, hate, scam,
other) and an optional note. The reported text is copied into the report, so it can
be reviewed after an edit or deletion.

- What I report leaves my view immediately; I can also block the author in the same
  step.
- A post whose open reports weigh 3 or more is hidden (`block.hidden`) from everyone
  but its author until reviewed. Reports from Lv 10 members weigh 2
  ([0015](0015-levels-reward-what-others-value.md)).
- One report per member per item, 20 a day.

**Review**: `/admin`, for the accounts in the `ADMIN_ACCOUNTS` setting (Parameter
Store `/motivetag/admin-accounts`); everyone else gets 404. Reports are grouped per
item; the owner deletes the content or keeps it (which shows a hidden post again).
Each new report puts a notification in the admins' bell, and
`motivetag_reports_total` counts them for the dashboard.

## Consequences

- Meets Guideline 1.2 on the website before the app exists, at no cost.
- Three members can hide a post until the owner looks. That can be abused by a
  group, but with one owner a fast hide beats a slow one; the author still sees
  their post, and "keep" restores it.
- Admin rights come from configuration, not the database: adding an admin is a
  Parameter Store change and a redeploy, which is rare and leaves an audit trail in
  AWS.
- Reports keep a copy of reported text (personal data) until deleted with the
  reporter's account; the privacy policy must mention it.
- There is no suspension of accounts yet: the owner can delete content, and members
  can block. Suspension is the next step if a real abuser appears.

## Alternatives considered

- **Automatic content filtering (keyword lists, a moderation API)**: keyword lists
  misfire on Chinese text; moderation APIs cost money and send private messages to a
  third party.
- **Hide content after any single report**: one angry member could silence anyone.
- **An `is_admin` column**: needs a database command to set, and a bug in any
  account-editing endpoint could grant it.

## Revisit when

Reports arrive faster than one person can review them in a day, or someone keeps
coming back with new accounts (then: suspension, and sign-up limits per device/IP).
