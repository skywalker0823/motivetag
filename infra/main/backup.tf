# Daily MySQL dumps (deploy/backup.sh) and the weekly restore drill read from here.
# The server may add and read backups but not delete them; overwritten versions are
# kept for a week, and dumps expire after var.backup_retention_days.
resource "aws_s3_bucket" "backups" {
  bucket = "${var.project}-backups-${data.aws_caller_identity.current.account_id}"
}

resource "aws_s3_bucket_public_access_block" "backups" {
  bucket                  = aws_s3_bucket.backups.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_versioning" "backups" {
  bucket = aws_s3_bucket.backups.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "backups" {
  bucket     = aws_s3_bucket.backups.id
  depends_on = [aws_s3_bucket_versioning.backups]

  rule {
    id     = "expire-old-dumps"
    status = "Enabled"
    filter {
      prefix = "mysql/"
    }
    expiration {
      days = var.backup_retention_days
    }
    noncurrent_version_expiration {
      noncurrent_days = 7
    }
    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }
  }
}

# deploy.sh writes this into the server's .env as BACKUP_BUCKET.
resource "aws_ssm_parameter" "backup_bucket" {
  name  = "/${var.project}/backup-bucket"
  type  = "String"
  value = aws_s3_bucket.backups.bucket
}
