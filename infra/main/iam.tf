# The Raspberry Pi is an SSM "hybrid" managed node (docs/adr/0017): its SSM agent
# assumes this role through Systems Manager and keeps short-lived credentials for it
# in root's ~/.aws/credentials. No long-lived AWS keys exist on the Pi.
data "aws_iam_policy_document" "ssm_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ssm.amazonaws.com"]
    }
    # Only Systems Manager acting for this account (confused-deputy guard).
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }
    condition {
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values   = ["arn:aws:ssm:${var.region}:${data.aws_caller_identity.current.account_id}:*"]
    }
  }
}

resource "aws_iam_role" "app" {
  name               = "${var.project}-app"
  assume_role_policy = data.aws_iam_policy_document.ssm_assume.json
}

# Lets the agent register and lets CI run deploy commands (Run Command), with no SSH.
resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.app.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# One-time code that registers the Pi (infra/README.md, "Registering the Raspberry
# Pi"). Good for one machine and 24 hours; the managed node gets this resource's
# tags, which CI uses to find it. Standard tier: free (Session Manager would need the
# paid advanced tier; the Pi has SSH on the home network instead).
resource "aws_ssm_activation" "pi" {
  name               = "${var.project}-pi"
  description        = "Raspberry Pi that runs motivetag"
  iam_role           = aws_iam_role.app.name
  registration_limit = 1
  depends_on         = [aws_iam_role_policy_attachment.ssm]

  tags = {
    Project = var.project
    Name    = "${var.project}-pi"
  }

  lifecycle {
    # It expires after a day by design; a used or expired code is not replaced.
    ignore_changes = [expiration_date]
  }
}

# What the running app and deploy script on the server may touch.
data "aws_iam_policy_document" "app" {
  statement {
    sid       = "EcrLogin"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }
  statement {
    sid = "EcrPull"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:BatchGetImage",
      "ecr:GetDownloadUrlForLayer",
    ]
    resources = [aws_ecr_repository.app.arn]
  }
  statement {
    sid     = "ReadConfig"
    actions = ["ssm:GetParameter", "ssm:GetParameters", "ssm:GetParametersByPath"]
    resources = [
      "arn:aws:ssm:${var.region}:${data.aws_caller_identity.current.account_id}:parameter/${var.project}/*",
    ]
  }
  statement {
    sid = "Images"
    # Delete: removing a member's images when they delete their account.
    actions   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
    resources = ["${aws_s3_bucket.images.arn}/*"]
  }
  # Add and read backups, never delete them (the bucket's lifecycle rule does that).
  statement {
    sid       = "WriteBackups"
    actions   = ["s3:PutObject", "s3:GetObject"]
    resources = ["${aws_s3_bucket.backups.arn}/mysql/*"]
  }
  statement {
    sid       = "ListBackups"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.backups.arn]
    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values   = ["mysql/*"]
    }
  }
  statement {
    sid       = "BackupAlerts"
    actions   = ["sns:Publish"]
    resources = [aws_sns_topic.alerts.arn]
  }
  # Verification e-mails, only from the site's own no-reply address.
  statement {
    sid       = "SendEmail"
    actions   = ["ses:SendEmail"]
    resources = [aws_sesv2_email_identity.domain.arn]
    condition {
      test     = "StringEquals"
      variable = "ses:FromAddress"
      values   = [local.email_from]
    }
  }
}

resource "aws_iam_role_policy" "app" {
  name   = "${var.project}-app"
  role   = aws_iam_role.app.id
  policy = data.aws_iam_policy_document.app.json
}
