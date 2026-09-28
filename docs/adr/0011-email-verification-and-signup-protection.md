# 0011. Verify e-mail addresses with SES; protect sign-up with Turnstile and a disposable-domain list

- Status: Accepted
- Date: 2026-09-28

## Context

The site is moving towards meeting new people, which attracts throwaway and scripted
sign-ups. Until now an account needed no working e-mail address, so there was no way
to reach a member (no password reset either). The owner's rule is no surprise costs.

## Decision

- **E-mail verification.** Sign-up sends a one-time link (24 hours; only a SHA-256 of
  the token is stored, `email_token` table). Until it is clicked a member can sign
  in and read, but posting, commenting, inviting, tag-board topics and chat are
  refused (`verified_required` in `module/auth.py`, the chat handlers). Members who
  joined before this count as verified (migration 0003).
- **Amazon SES** sends the mail (`infra/main/ses.tf`, `module/mailer.py`) with the
  instance role, from `no-reply@motivetag.com` only (IAM condition). SES has its own
  provider region (Tokyo by default) because it is not offered everywhere.
- **Hard limits** in `module/email_verification.py`: one link a minute and five a
  day per member, 500 a day for the whole site. At US$0.10 per 1,000 messages that
  caps the bill at about US$1.50 a month (and the first year's 3,000 free a month
  covers normal use).
- **Cloudflare Turnstile** on the sign-up form (`module/turnstile.py`), free. The
  server checks the token with Cloudflare and refuses sign-up if Cloudflare cannot
  be reached (fail closed).
- **Disposable domains** from the CC0 list at disposable-email-domains/
  disposable-email-domains, copied into `module/disposable_domains.txt`, refused at
  sign-up (subdomains included).
- Everything is **off until configured**: verification needs `/motivetag/email-from`
  (created by Terraform only when `email_enabled = true`, after SES production
  access), Turnstile needs `/motivetag/turnstile-site-key` and `-secret`. A deploy
  before the setup, local development and CI behave as before.

## Consequences

- New members need a real inbox before they can take part; reading needs nothing.
- Bots need a real browser to pass Turnstile and a non-disposable inbox; the
  daily limit bounds the damage if they get through.
- If Cloudflare's Turnstile API is down, nobody can sign up for that time.
- The disposable list goes stale slowly; refresh the file now and then.
- A password-reset flow can reuse the mailer and token table.

## Alternatives considered

- **Resend / other e-mail APIs** — quicker to start, but another account and API key
  outside AWS; SES uses the existing role and Terraform.
- **Block everything until verified** — simpler rule, but people bounce before they
  have seen anything.
- **reCAPTCHA / hCaptcha** — Turnstile is free, usually invisible, and the site is
  already behind Cloudflare.
- **Fail open on Turnstile errors** — keeps sign-up working during an outage but
  lets bots in exactly then.

## Revisit when

Verification e-mails approach the daily limit on ordinary days (raise it, knowing
the cost), bounce or complaint rates rise (SES would pause sending), or phone
verification becomes necessary for a dating use case.
