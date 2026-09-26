# One-time setup: the S3 bucket that stores Terraform state for infra/main.
# This directory keeps its own (tiny) state locally; see infra/README.md.

terraform {
  required_version = ">= 1.10"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = var.region
  default_tags {
    tags = {
      Project   = "motivetag"
      ManagedBy = "terraform"
    }
  }
}

variable "region" {
  description = "AWS region for the state bucket (use the same one as infra/main)."
  type        = string
}

data "aws_caller_identity" "current" {}

resource "aws_s3_bucket" "state" {
  # Bucket names are global, so the account ID keeps this one unique.
  bucket = "motivetag-tfstate-${data.aws_caller_identity.current.account_id}"

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.state.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  bucket = aws_s3_bucket.state.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "state" {
  bucket                  = aws_s3_bucket.state.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

output "state_bucket" {
  value = aws_s3_bucket.state.bucket
}

output "next_step" {
  value = "cd ../main && terraform init -backend-config=\"bucket=${aws_s3_bucket.state.bucket}\" -backend-config=\"region=${var.region}\""
}
