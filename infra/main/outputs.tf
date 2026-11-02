output "instance_id" {
  value = one(aws_instance.app[*].id)
}

output "public_ip" {
  description = "Point the Cloudflare DNS record here (null while paused)."
  value       = one(aws_eip.app[*].public_ip)
}

output "connect" {
  description = "Open a shell on the server (needs the Session Manager plugin)."
  value       = var.paused ? null : "aws ssm start-session --target ${aws_instance.app[0].id} --region ${var.region} --profile motivetag"
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
