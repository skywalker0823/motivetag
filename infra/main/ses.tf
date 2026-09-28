# E-mail for sign-up verification links, sent with Amazon SES (docs/adr/0011).
# SES is not offered in every region, so it gets its own provider; the app is told
# the region through /motivetag/ses-region.
#
# Cost: US$0.10 per 1,000 e-mails (3,000 a month free for the first year from EC2).
# The app sends at most 500 a day (module/email_verification.py).
#
# Two steps (infra/README.md): apply, add the DNS records from `ses_dns_records` in
# Cloudflare and ask AWS to take the account out of the SES sandbox; once approved,
# set email_enabled = true and apply again. Only then does the app require
# verification: in the sandbox SES would refuse to mail new members.

provider "aws" {
  alias  = "ses"
  region = var.ses_region
  default_tags {
    tags = {
      Project   = var.project
      ManagedBy = "terraform"
    }
  }
}

resource "aws_sesv2_email_identity" "domain" {
  provider       = aws.ses
  email_identity = var.domain
}

# SES stops mailing addresses that bounced or complained, which keeps the account in
# good standing (AWS pauses accounts with high bounce rates).
resource "aws_sesv2_account_suppression_attributes" "this" {
  provider           = aws.ses
  suppressed_reasons = ["BOUNCE", "COMPLAINT"]
}

locals {
  email_from = "no-reply@${var.domain}"
}

# deploy.sh writes these into the server's .env; EMAIL_FROM switches verification on.
resource "aws_ssm_parameter" "email_from" {
  count = var.email_enabled ? 1 : 0
  name  = "/${var.project}/email-from"
  type  = "String"
  value = local.email_from
}

resource "aws_ssm_parameter" "ses_region" {
  name  = "/${var.project}/ses-region"
  type  = "String"
  value = var.ses_region
}

output "ses_dns_records" {
  description = "Add these in Cloudflare (DNS only, not proxied), so mail is signed and not marked as spam."
  value = concat(
    [
      for token in aws_sesv2_email_identity.domain.dkim_signing_attributes[0].tokens : {
        type    = "CNAME"
        name    = "${token}._domainkey.${var.domain}"
        content = "${token}.dkim.amazonses.com"
      }
    ],
    [
      {
        type    = "TXT"
        name    = "_dmarc.${var.domain}"
        content = "v=DMARC1; p=none;"
      },
    ],
  )
}
