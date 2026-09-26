# Infrastructure

Terraform for the AWS side of motivetag. Everything runs from your Mac with the
`motivetag` AWS CLI profile (IAM Identity Center / SSO, so no long-lived keys).

| Directory | What it creates | State |
|---|---|---|
| `bootstrap/` | S3 bucket that stores Terraform state (run once) | local file |
| `main/` | EC2 server, data volume, Elastic IP, security group, IAM role | in that S3 bucket |

## Before you start

- AWS CLI signed in: `aws sts get-caller-identity --profile motivetag` works.
- Tools: `brew install awscli session-manager-plugin` and
  `brew tap hashicorp/tap && brew install hashicorp/tap/terraform`.
- Using the Taipei region (`ap-east-2`)? It is opt-in: enable it first under
  Account → AWS Regions.

## First run

```bash
export AWS_PROFILE=motivetag

# 1. State bucket (once per AWS account)
cd infra/bootstrap
terraform init
terraform apply -var region=ap-east-2
# copy the printed next_step command

# 2. The server
cd ../main
cp terraform.tfvars.example terraform.tfvars   # set region
terraform init -backend-config="bucket=motivetag-tfstate-<account-id>" -backend-config="region=ap-east-2"
terraform plan    # read it: expect ~8 resources to add
terraform apply
```

Commit the `.terraform.lock.hcl` files that `terraform init` creates.

## Check the server

```bash
$(terraform output -raw connect)   # shell on the server via Session Manager, no SSH
docker --version && docker compose version
df -h /srv/motivetag               # the separate data volume
```

## Notes

- There is no SSH and no open inbound port. HTTPS from Cloudflare is added with the web stack.
- The data volume has `prevent_destroy`; `terraform destroy` stops on it on purpose.
- Changing the AMI or `user_data.sh.tftpl` does not replace a running server
  (`ignore_changes`). To rebuild: `terraform apply -replace=aws_instance.app`
  (the data volume is kept and re-attached).
