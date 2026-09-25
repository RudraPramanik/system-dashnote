# Terraform Level A — AWS edge blueprint

> **Owns:** how the existing EC2 edge is adopted with Terraform, stage gates, and fallbacks.  
> **Does not own:** deploy shell commands ([runbook](runbook.md)), app CD (`.github/workflows/deploy.yml`), or hosted Postgres / Redis / Qdrant / R2.  
> **Code:** [`../../infra/`](../../infra/).  
> Level B and Level C below are **unimplemented**. Do not start them in this change.

## Laws

- Do **not** `terraform destroy` the live first-boot instance.
- Do **not** change `deploy.yml`, Compose, deploy scripts, or `scripts/smoke_prod.py` to make Terraform work.
- Do **not** create Postgres, Redis, Qdrant, or object storage in this root.
- Do **not** `terraform import` the live instance until `terraform init -backend-config=backend.hcl` has succeeded against the remote backend.
- Do **not** run `terraform apply` from GitHub Actions in Level A.
- If `terraform plan` would **replace or destroy** the instance, do **not** apply.

Local `terraform init -backend=false` plus `terraform validate` is allowed before the remote backend exists. That path creates no AWS resources.

## A0 — Inventory (no AWS mutations)

Record these privately. Do not commit them.

| Fact | Value |
|------|--------|
| Instance id | `i-…` |
| Security group id | `sg-…` |
| Security group name | exact name |
| AMI id | `ami-…` |
| Subnet id | `subnet-…` |
| VPC id | `vpc-…` |
| Key pair name | or empty |
| Public IPv4 | |
| Elastic IP in use? | yes / no (allocation id if yes) |
| Instance type | `t3.small` expected |

**Hard stop:** `curl -sS -o /dev/null -w "%{http_code}" http://<public-ip>/health` must be `200`. If it is not, fix the app host from the [runbook](runbook.md) before any Terraform import.

**Verify:** inventory written; health is 200.  
**Fallback:** stop. Do not guess ids.

## A1 — Scaffold

From `infra/`:

```bash
terraform fmt -check -recursive
terraform init -backend=false
terraform validate
```

**Verify:** both commands exit 0. `git status` shows only `infra/` and docs. No `terraform apply`.  
**Fallback:** delete the `infra/` checkout. The live box is untouched because apply never ran.

Validation record (repo landing): `terraform fmt -check`, `terraform init -backend=false`, and `terraform validate` succeeded (Terraform 1.16.2, hashicorp/aws v5.100.0). No `terraform apply`. No production resource was created.

## A2 — Remote state

Create the bucket and lock table **once**, outside this root (console or the AWS CLI). Do not add a second Terraform root that also manages the live instance.

```bash
aws s3api create-bucket --bucket <name>-tfstate --region <region>
aws s3api put-bucket-versioning --bucket <name>-tfstate --versioning-configuration Status=Enabled
aws s3api put-bucket-encryption --bucket <name>-tfstate --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
aws dynamodb create-table --table-name <name>-tfstate-lock --attribute-definitions AttributeName=LockID,AttributeType=S --key-schema AttributeName=LockID,KeyType=HASH --billing-mode PAY_PER_REQUEST --region <region>
```

Copy `infra/backend.hcl.example` to `infra/backend.hcl` (gitignored) and fill bucket, region, and table.

```bash
terraform init -backend-config=backend.hcl
```

**Verify:** a second `terraform init -backend-config=backend.hcl` succeeds and the state object appears in the bucket.  
**Fallback:** stay on `-backend=false` for validate only. Do not import the live instance.

Local state is valid only until this init. Live import is forbidden before it.

## A3 — Import the security group

Copy `terraform.tfvars.example` to `terraform.tfvars` (gitignored) from the A0 inventory. Set `manage_eip` to match whether an EIP is already in use.

```bash
terraform import aws_security_group.edge sg-REPLACE_ME
terraform plan
```

Apply only when the plan is empty or in-place (tags, description). Then confirm SSH and:

```bash
curl -sS -o /dev/null -w "%{http_code}\n" http://<public-ip>/health
```

**Verify:** plan has no destroy; SSH works; health is 200.  
**Fallback:** do not apply a plan that closes port 22 or 80. If SSH breaks, use the EC2 console or Instance Connect, add a temporary rule for your IP, then fix the CIDR in tfvars.

## A4 — Import the instance (and EIP if any)

```bash
terraform import aws_instance.edge i-REPLACE_ME
# only when manage_eip = true and an allocation already exists:
# terraform import 'aws_eip.edge[0]' eipalloc-REPLACE_ME
# terraform import 'aws_eip_association.edge[0]' eipassoc-REPLACE_ME
terraform plan
```

**Stop** if the plan says the instance must be replaced or destroyed. Fix tfvars or remove the address from state. Do not apply.

`lifecycle.ignore_changes` covers `ami` and `user_data` only. Any other replacement (subnet, type, key, public IP association) is a real diff — abort.

If you attach a new address, update GitHub secret `VPS_HOST` by hand **before** releasing the old IP. Outputs do not write GitHub secrets.

**Verify:** plan is empty or tags-only; `GET http://<ip>/health` is 200; `python scripts/smoke_prod.py` exits 0 against that base URL.  
**Fallback:** `terraform state rm aws_instance.edge` (and the EIP addresses if imported). The AWS object stays. CD continues against the snowflake box. App rollback stays the [runbook](runbook.md) image pin, not a new script.

## A5 — Ownership

| Concern | Owner |
|---------|--------|
| EC2, security group, Elastic IP | Terraform (`infra/`) |
| Docker, Compose, nginx, `.env` | Operator and `scripts/deploy/*` |
| Image build, migrate, roll, smoke | `.github/workflows/deploy.yml` (unchanged) |
| Hosted Postgres, Redis, Qdrant, R2 | Current vendors |

**Verify:** `terraform plan` stays quiet after a day of not clickops-editing the instance.  
**Fallback:** mark the tracker experimental and keep console access for emergencies. Note the debt here.

## A6 — Throwaway recreate (optional)

**Skipped for this change.** No spare instance was available, and the live box must not be destroyed to prove recreate. Run this later in a **separate** workspace only: apply a new `t3.small`, first-boot from the runbook, smoke it, then `terraform destroy` **that workspace only**.

## Import addresses

| Resource | Address |
|----------|---------|
| Security group | `aws_security_group.edge` |
| Instance | `aws_instance.edge` |
| EIP (only if `manage_eip`) | `aws_eip.edge[0]` |
| EIP association | `aws_eip_association.edge[0]` |

## Level B — unimplemented

After A5 and preferably one green CD run:

- GitHub OIDC role that can `terraform plan` (not a broad apply role)
- `terraform plan` on pull requests that touch `infra/`
- Optional SSM Session Manager, Secrets Manager values that still feed Compose `.env`, or ECR instead of GHCR

Still one Compose box. No ECS.

## Level C — unimplemented

A later change only, and only if Compose operations are already calm. Cap extras the way Phase 5 already does (at most two):

- ECS/Fargate or an ASG plus a load balancer instead of Compose-on-EC2
- RDS or ElastiCache instead of the current hosted data plane
- Separate staging and production workspaces

Do not start Level C from this blueprint.
