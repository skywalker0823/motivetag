variable "region" {
  description = "AWS region, e.g. ap-east-2 (Taipei) or ap-northeast-1 (Tokyo)."
  type        = string
}

variable "project" {
  description = "Name used for resources and tags."
  type        = string
  default     = "motivetag"
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
