variable "region" {
  description = "AWS region, e.g. ap-east-2 (Taipei) or ap-northeast-1 (Tokyo)."
  type        = string
}

variable "project" {
  description = "Name used for resources and tags."
  type        = string
  default     = "motivetag"
}

variable "github_repository" {
  description = "owner/name of the GitHub repository allowed to deploy."
  type        = string
  default     = "skywalker0823/motivetag"
}

variable "instance_type" {
  description = "EC2 size. 2 GB of RAM is the practical minimum for MySQL plus the app."
  type        = string
  default     = "t3.small"
}

variable "root_volume_size" {
  description = "Root disk in GB (OS, Docker images)."
  type        = number
  default     = 20
}

variable "data_volume_size" {
  description = "Separate disk in GB for MySQL data; survives instance replacement."
  type        = number
  default     = 20
}

variable "domain" {
  description = "Public site name, served through Cloudflare."
  type        = string
  default     = "motivetag.com"
}

variable "alert_email" {
  description = "Where alarms are e-mailed (confirm the two SNS subscription e-mails). Null disables e-mail."
  type        = string
  default     = null
}

variable "backup_retention_days" {
  description = "How long MySQL dumps are kept in S3."
  type        = number
  default     = 35
}
