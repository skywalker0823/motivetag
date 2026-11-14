# Generated once and stored as SecureString parameters under /motivetag/.
# The deploy script reads them on the server; nobody needs to type them.
# (They are also in the Terraform state, which lives in the private, encrypted
# state bucket.)

resource "random_password" "secret_key" {
  length  = 64
  special = false
}

resource "random_password" "db" {
  length  = 40
  special = false
}

resource "random_password" "db_root" {
  length  = 40
  special = false
}

resource "aws_ssm_parameter" "secret_key" {
  name  = "/${var.project}/secret-key"
  type  = "SecureString"
  value = random_password.secret_key.result
}

resource "aws_ssm_parameter" "db_password" {
  name  = "/${var.project}/db-password"
  type  = "SecureString"
  value = random_password.db.result
}

resource "aws_ssm_parameter" "db_root_password" {
  name  = "/${var.project}/db-root-password"
  type  = "SecureString"
  value = random_password.db_root.result
}

# The Cloudflare Tunnel token is added by hand as /motivetag/cloudflare-tunnel-token
# (see infra/README.md), so it never enters Terraform state.
