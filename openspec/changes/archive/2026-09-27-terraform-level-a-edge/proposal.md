## Why

The thin VPS already ships through Compose, deploy scripts, and GitHub CD, but the AWS edge (EC2, security group, public IP) is clickops. Recreating or documenting that box is not repeatable, and a later platform path has no written contract that keeps infrastructure-as-code from replacing the app deploy path. Codify the existing edge first, with verify and fallback gates, before any CD or orchestration rewrite.

## What Changes

- Add a Level A Terraform root that can adopt the **existing** EC2 instance, security group, and optional Elastic IP by import, with a clean plan (no instance replacement) before any apply that mutates the live box.
- Require remote state (S3 + lock) before importing the live instance. Local state is allowed only for scaffold validation.
- Add an operator blueprint (runbook sibling + progress-tracker pointer) that sequences Level A stages with verification and fallback, and records Level B and Level C as later roadmap only.
- Keep app CD, Compose, smoke, hosted data plane, and local development behavior unchanged. Level A MUST NOT `terraform destroy` the live first-boot box and MUST NOT rewrite `deploy.yml`.

Level B (OIDC plan CI, SSM, secrets manager, optional ECR) and Level C (ECS/RDS/multi-env) are documented as deferred sequences. They are not implemented in this change.

## Capabilities

### New Capabilities

- `platform-terraform`: Import-first AWS edge as code (EC2, security group, optional EIP), remote state before live import, ownership split versus Compose/CD, sequential verify/fallback gates, and a documented Level B/C roadmap that this change does not implement.

### Modified Capabilities

- (none — `production-platform` and `thin-ci` requirements stay as they are; this change must not alter CD triggers, smoke gates, or local Compose)

## Impact

- **New:** `infra/` Terraform root (versions, backend, variables, SG, instance, optional EIP, outputs, example tfvars, operator README); `docs/deployment/terraform-a.md` (or equivalent runbook sibling).
- **Docs touch:** `docs/devops-progress.md` Phase 5 Terraform row and a pointer that Level A is the active IaC track; Level B/C stay checklist-only.
- **Unchanged:** `docker-compose.yml`, `docker-compose.prod.yml`, `scripts/deploy/*`, `scripts/smoke_prod.py`, `.github/workflows/ci.yml`, `.github/workflows/deploy.yml`, hosted Postgres/Redis/Qdrant/R2, VPS `.env` secret path.
- **Operator (not in git):** AWS account inventory (instance id, SG id, AMI, subnet, IP), state bucket credentials, GitHub `VPS_HOST` kept in sync if an EIP is attached.
- **Assumptions:** import the live box rather than greenfield-replace it; remote state is mandatory before that import; blueprint lives in backend docs next to the existing runbook.
