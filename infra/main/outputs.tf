output "instance_id" {
  value = aws_instance.app.id
}

output "public_ip" {
  description = "Point the Cloudflare DNS record here."
  value       = aws_eip.app.public_ip
}

output "connect" {
  description = "Open a shell on the server (needs the Session Manager plugin)."
  value       = "aws ssm start-session --target ${aws_instance.app.id} --region ${var.region} --profile motivetag"
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

output "cloudwatch_agent_associations" {
  description = "Re-run with: aws ssm start-associations-once --association-ids <id> ..."
  value = [
    aws_ssm_association.cloudwatch_agent_install.association_id,
    aws_ssm_association.cloudwatch_agent_config.association_id,
  ]
}
