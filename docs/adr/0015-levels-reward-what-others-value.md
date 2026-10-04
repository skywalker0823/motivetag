# 0015. Levels reward what others value, with daily caps and unlocks

- Status: Accepted
- Date: 2026-09-29

## Context

Levels existed but did nothing. Exp rewarded activity, not quality: a post gave 50
with no limit (twenty "安安" posts were a fast way up), and likes rewarded the person
clicking, not the author. The level was only visible on one's own card, and going
up had no effect. Level n needed 25·n(n−1) exp, so levels came quickly and then
meant little.

## Decision

`module/levels.py` (mirrored in `static/js/lib/levels.js`):

- **Curve**: level n needs 50·(n−1)² exp in total (Lv 2: 50, Lv 3: 200, Lv 5: 800,
  Lv 10: 4,050, Lv 20: 18,050). An active member earns about 60 a day: Lv 3 within
  the first week, Lv 5 in about two weeks, Lv 10 after two to three months.
- **Rewards, each capped per Taipei day** (`exp_daily`): first visit +10 (+50 on
  every 7th day in a row), post +20 (3 a day), comment +5 (10), like given +1 (20);
  the author gets +5 per like on a post, +3 per comment on it and +3 per like on a
  comment (20 each). Boos and chat earn nothing, and nobody earns from their own
  posts' likes or comments. Deleting a post no longer costs exp: the cap already
  makes post-and-delete pointless.
- **Unlocks**, enforced by the server: below Lv 3 at most 10 posts a day and no tag
  topics; Lv 5 an avatar frame and a cover photo on one's personal card (added
  2026-10-05); Lv 10 reports weigh double
  ([0014](0014-blocking-and-reporting.md)). Badge colours by tier: plain, green
  (3+), blue (5+), purple (10+), gold (20+).
- **Visible**: a level badge next to names on posts, comments, chat and member
  cards (never on anonymous posts, where it could identify the author); the level
  card says what the next level unlocks; the server pushes every exp change
  (`exp` socket event), so the bar moves at once and level-ups get a toast.
- **Migration 0006** converts everyone's exp so their level and progress through it
  stay the same.

## Consequences

- Growing comes from being liked and answered, which is also what makes the site
  worth visiting; farming is bounded by the caps.
- The post limit and topic threshold slow down throwaway spam accounts, the cheapest
  abuse to stop.
- Levels now gate features, so they must stay server-side; the browser only shows them.
- `exp_daily` gains a row per member, action and day; rows older than two days are
  deleted on each member's first visit of the day.

## Alternatives considered

- **Keep the old rewards, only show the level**: visible levels would advertise the
  farming.
- **Badges and achievements first**: more to build and to design; unlocks give a
  reason to level up with less work. They can come later on top of the same exp.
- **Levels that decay with inactivity**: punishing, and confusing for a small site.

## Revisit when

Members reach Lv 20 (the curve's top tier) within a few months, or the caps stop
people from doing something the site wants more of.
