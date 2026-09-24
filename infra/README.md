# Level A edge (Terraform)

Adopts the existing EC2 instance, security group, and optional Elastic IP. It does not deploy the app.

Full stages, verify gates, and fallbacks: [`docs/deployment/terraform-a.md`](../docs/deployment/terraform-a.md).

## Commands

```bash
terraform fmt -check -recursive
terraform init -backend=false   # scaffold validate only; creates no AWS resources
terraform validate
```

Remote state, after the bucket and lock table exist (see the blueprint):

```bash
terraform init -backend-config=backend.hcl
```

## Do not

- Do not `terraform apply` from CI in Level A.
- Do not `terraform import` the live instance before the remote backend init succeeds.
- Do not `terraform apply` a plan that replaces or destroys the instance.
- Do not `terraform destroy` the live first-boot box.

## Validation record

`terraform fmt -check -recursive`, `terraform init -backend=false`, and `terraform validate` succeeded with Terraform 1.16.2 and hashicorp/aws v5.100.0. No `terraform apply` was run. No production resource was created.
