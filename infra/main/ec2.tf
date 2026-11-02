data "aws_ssm_parameter" "ubuntu_ami" {
  name = "/aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id"
}

# While paused (var.paused) there is no server; the data volume below is kept.
resource "aws_instance" "app" {
  count = var.paused ? 0 : 1

  ami                    = data.aws_ssm_parameter.ubuntu_ami.value
  instance_type          = var.instance_type
  subnet_id              = data.aws_subnet.app.id
  vpc_security_group_ids = [aws_security_group.app.id]
  iam_instance_profile   = aws_iam_instance_profile.app.name

  user_data = templatefile("${path.module}/user_data.sh.tftpl", {
    data_volume_id = aws_ebs_volume.data.id
  })

  root_block_device {
    volume_type = "gp3"
    volume_size = var.root_volume_size
    encrypted   = true
  }

  metadata_options {
    http_tokens = "required" # IMDSv2 only
    # 2 hops so containers on the Docker bridge can reach the instance role.
    http_put_response_hop_limit = 2
  }

  tags = {
    Name = var.project
  }

  lifecycle {
    # A new Ubuntu AMI or bootstrap script must not silently replace the server.
    ignore_changes = [ami, user_data]
  }
}

# MySQL data lives on its own volume so the instance can be rebuilt without losing it.
resource "aws_ebs_volume" "data" {
  availability_zone = data.aws_subnet.app.availability_zone
  size              = var.data_volume_size
  type              = "gp3"
  encrypted         = true

  tags = {
    Name = "${var.project}-data"
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_volume_attachment" "data" {
  count = var.paused ? 0 : 1

  device_name = "/dev/sdf"
  volume_id   = aws_ebs_volume.data.id
  instance_id = aws_instance.app[0].id
  # Pausing detaches the disk: shut the server down first so MySQL stops cleanly.
  stop_instance_before_detaching = true
}

# Fixed public IP for the Cloudflare DNS record. Released while paused (an unused
# address is billed too), so resuming gives a new one for the DNS record.
resource "aws_eip" "app" {
  count = var.paused ? 0 : 1

  instance = aws_instance.app[0].id
  domain   = "vpc"

  tags = {
    Name = var.project
  }
}

# These resources gained a count for var.paused; keep the existing ones in place.
moved {
  from = aws_instance.app
  to   = aws_instance.app[0]
}

moved {
  from = aws_volume_attachment.data
  to   = aws_volume_attachment.data[0]
}

moved {
  from = aws_eip.app
  to   = aws_eip.app[0]
}
