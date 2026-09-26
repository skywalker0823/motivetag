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

## Going live (one time)

Do these in order; the last step (merging to `main`) triggers the first deploy.

1. **Apply the deploy stack.** After pulling the latest `main`:

   ```bash
   cd infra/main
   terraform init        # installs the new http and random providers
   terraform plan        # ~16 to add, 1 to change (security group gets port 443)
   terraform apply
   ```

   It creates the ECR repository, the private image bucket, generated secrets in
   Parameter Store, and the GitHub OIDC deploy role, and opens 443 to Cloudflare only.

2. **Cloudflare origin certificate.** Cloudflare → your domain → SSL/TLS →
   Origin Server → Create Certificate (keep the defaults: `motivetag.com`,
   `*.motivetag.com`, 15 years). Save the two text boxes as `origin.pem` and
   `origin.key`, then store them in Parameter Store and delete the local key:

   ```bash
   aws ssm put-parameter --name /motivetag/tls/origin-cert --type SecureString --value file://origin.pem --region ap-east-2
   aws ssm put-parameter --name /motivetag/tls/origin-key  --type SecureString --value file://origin.key --region ap-east-2
   rm origin.key
   ```

3. **Cloudflare settings.**
   - SSL/TLS → Overview → encryption mode **Full (strict)**.
   - SSL/TLS → Edge Certificates → **Always Use HTTPS** on.
   - DNS → add `A` record `@` → the `public_ip` output, **Proxied** (orange cloud);
     add `CNAME` `www` → `motivetag.com`, Proxied.

4. **GitHub repository variables.** `terraform output github_variables`, then add
   each key/value under Settings → Secrets and variables → Actions → **Variables**
   (not secrets; none of them is sensitive).

5. **Merge to `main`.** CI runs, then the `deploy` job builds the image, pushes it to
   ECR tagged with the commit SHA, and runs `deploy/deploy.sh` on the server through
   SSM. If the new version is unhealthy it rolls back to the previous image and the
   job fails. To redeploy without a code change: Actions → CI → the latest `main`
   run → Re-run all jobs.

## Operating the server

```bash
$(terraform output -raw connect)             # shell via Session Manager
sudo -i && cd /srv/motivetag/app
docker compose ps                            # service status
docker compose logs -f app                   # app logs
cat current_image                            # deployed image
```

Migrations run on container start. Write them so the previous release still works
with the new schema, because a rollback does not undo a migration.

## Notes

- There is no SSH and no open inbound port. HTTPS from Cloudflare is added with the web stack.
- The data volume has `prevent_destroy`; `terraform destroy` stops on it on purpose.
- Changing the AMI or `user_data.sh.tftpl` does not replace a running server
  (`ignore_changes`). To rebuild: `terraform apply -replace=aws_instance.app`
  (the data volume is kept and re-attached).
