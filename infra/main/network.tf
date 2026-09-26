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

resource "aws_security_group" "app" {
  name        = "${var.project}-app"
  description = "motivetag web server"
  vpc_id      = data.aws_vpc.default.id

  # No inbound rules yet: administration goes through SSM Session Manager, not SSH.
  # HTTPS from Cloudflare is added together with the web stack.

  egress {
    description = "Outbound for package updates, image pulls and AWS APIs"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
