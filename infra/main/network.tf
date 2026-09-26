# A single instance in the default VPC keeps this simple and cheap; see docs/adr.
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
  filter {
    name   = "default-for-az"
    values = ["true"]
  }
}

data "aws_subnet" "app" {
  id = sort(data.aws_subnets.default.ids)[0]
}

# Cloudflare's published edge ranges, fetched at plan time so the list stays current.
data "http" "cloudflare_ipv4" {
  url = "https://www.cloudflare.com/ips-v4"

  lifecycle {
    postcondition {
      condition     = self.status_code == 200
      error_message = "Could not fetch Cloudflare IP ranges."
    }
  }
}

locals {
  cloudflare_ipv4 = compact(split("\n", trimspace(data.http.cloudflare_ipv4.response_body)))
}

resource "aws_security_group" "app" {
  name        = "${var.project}-app"
  description = "motivetag web server"
  vpc_id      = data.aws_vpc.default.id

  # Only Cloudflare may reach the web server; there is no SSH, admin access uses
  # SSM Session Manager.
  ingress {
    description = "HTTPS from Cloudflare"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = local.cloudflare_ipv4
  }

  egress {
    description = "Outbound for package updates, image pulls and AWS APIs"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
