output "pi_activation" {
  description = "Registers the Raspberry Pi with SSM (infra/README.md). Single use, valid for 24 hours."
  value = {
    id     = aws_ssm_activation.pi.id
    code   = aws_ssm_activation.pi.activation_code
    region = var.region
  }
  sensitive = true
}

output "github_variables" {
  description = "Set these as repository variables (Settings → Secrets and variables → Actions → Variables)."
  value = {
    AWS_REGION          = var.region
    AWS_DEPLOY_ROLE_ARN = aws_iam_role.github_deploy.arn
    ECR_REPOSITORY_URL  = aws_ecr_repository.app.repository_url
    IMAGE_BUCKET        = aws_s3_bucket.images.bucket
  }
}

output "backup_bucket" {
  value = aws_s3_bucket.backups.bucket
}
