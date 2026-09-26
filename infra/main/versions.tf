terraform {
  # 1.16+ knows newer regions such as ap-east-2 (Taipei) in the S3 backend.
  required_version = ">= 1.16"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    http = {
      source  = "hashicorp/http"
      version = "~> 3.4"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Bucket and region are passed at init time (see infra/README.md) because the
  # bucket name contains the AWS account ID. use_lockfile gives S3-native locking.
  backend "s3" {
    key          = "main/terraform.tfstate"
    encrypt      = true
    use_lockfile = true
  }
}

provider "aws" {
  region = var.region
  default_tags {
    tags = {
      Project   = var.project
      ManagedBy = "terraform"
    }
  }
}
