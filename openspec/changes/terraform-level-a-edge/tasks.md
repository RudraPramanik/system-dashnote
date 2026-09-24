## 1. Inventory and guardrails (A0)

- [x] 1.1 Add `docs/deployment/terraform-a.md` stage A0: private inventory checklist (instance id, SG id, AMI, subnet, key name, public IP, whether an EIP exists) and a hard stop when `/health` on that IP is not 200
- [x] 1.2 In that doc, state the laws: no `terraform destroy` of the live box, no rewrite of `deploy.yml` / Compose / smoke, no data-plane resources, import only after remote state

## 2. Terraform scaffold (A1)

- [x] 2.1 Add `infra/` with pinned Terraform and AWS provider, variables (`region`, `instance_type`, `allowed_ssh_cidrs`, `allowed_http_cidrs`, `name_prefix`, optional `key_name`), and `terraform.tfvars.example` with placeholders only
- [x] 2.2 Gitignore `infra/.terraform/`, `*.tfstate*`, `*.tfvars` (keep `terraform.tfvars.example`), and crash logs so state and credentials cannot be committed
- [x] 2.3 Add `infra/README.md` covering `fmt`, `init`, `validate`, and “do not apply from CI in Level A”
- [x] 2.4 Run `terraform fmt -check` and `terraform validate` (local backend is enough for this step) and record that no production resource was created

## 3. Remote state (A2)

- [x] 3.1 Configure an S3 backend with a lock table and encryption in `infra/`; document one-time bucket/table creation outside this root (commands in `terraform-a.md`, not a second root that manages the live instance)
- [x] 3.2 Document that local state is valid only until this backend is initialized, and that live `terraform import` is forbidden before `terraform init` against the remote backend

## 4. Edge resources ready to import (A3–A4)

- [x] 4.1 Add `aws_security_group` whose ingress matches first-boot (SSH and HTTP CIDR variables) and does not open port 8000; egress matches current operator needs
- [x] 4.2 Add `aws_instance` (and `aws_eip` plus association only when an EIP is in use) parameterized so HCL can match the inventoried AMI, type, subnet, and key; use `lifecycle.ignore_changes` only for fields that would force replacement (`user_data`, `ami` when they cannot be matched)
- [x] 4.3 Document import addresses and the rule: if `terraform plan` shows instance replacement or destroy, do not apply; fallback is `terraform state rm` without deleting the AWS object
- [x] 4.4 Add outputs for instance id, public IP, and security group id, and state that GitHub `VPS_HOST` is updated manually when the address changes

## 5. Blueprint, ownership, later levels (A5)

- [x] 5.1 Finish `docs/deployment/terraform-a.md` stages A1–A5 with a verify checkbox and a fallback for each stage, plus the ownership matrix (Terraform owns EC2/SG/EIP; deploy scripts and `deploy.yml` own roll and smoke; hosted data plane stays with current vendors)
- [x] 5.2 Add short Level B and Level C sections only: B is OIDC plan, PR plan, optional SSM/secrets/ECR; C is optional ECS or data-plane moves as a future change. Mark both unimplemented
- [x] 5.3 Point `docs/deployment/runbook.md` and `docs/devops-progress.md` at `terraform-a.md`; update the Phase 5 Terraform row to “Level A in progress / done” without checking off B, C, ECS, or RDS
- [x] 5.4 Confirm `docker-compose.yml`, `docker-compose.prod.yml`, `scripts/deploy/*`, `scripts/smoke_prod.py`, `.github/workflows/ci.yml`, and `.github/workflows/deploy.yml` have no behavior edits in this change

## 6. Live adoption (operator, after 1–5)

- [ ] 6.1 After the operator fills gitignored tfvars from A0, `terraform init` the remote backend, import the security group, and apply only if the plan is empty or in-place; re-check SSH and `GET http://<ip>/health`
- [ ] 6.2 Import the instance (and existing EIP if any); abort apply if the plan replaces the instance; re-check health and `scripts/smoke_prod.py` exit 0
- [x] 6.3 Optional A6: separate workspace throwaway instance, first-boot from the runbook, then destroy only that workspace. Skip and note the skip in `terraform-a.md` when no spare instance is available
