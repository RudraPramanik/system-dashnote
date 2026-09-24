## Context

See `proposal.md` for why. Today the ship path is already specified: thin EC2 (`t3.small`), `docker-compose.prod.yml`, `scripts/deploy/*`, `scripts/smoke_prod.py`, and `.github/workflows/deploy.yml` (tag `v*` or `workflow_dispatch` only). Hosted Postgres, Redis, Qdrant, and R2 stay off the box via gitignored `.env`. HTTP first-boot (A4) is proven; live CD proof and HTTPS (A7) are still open. Phase 5 in `docs/devops-progress.md` lists Terraform as an optional extra and warns against starting it while first deploy is still unstable. This design keeps that warning: IaC adopts the edge; it does not become the deploy mechanism.

## Goals / Non-Goals

**Goals:**

- Put the live EC2, security group, and optional Elastic IP under Terraform by import, with a plan that does not replace the instance.
- Give operators a staged blueprint (verify + fallback) they can follow without reading the HCL first.
- Record Level B and Level C so the sequence is visible, without implementing them.

**Non-Goals:**

- Greenfield replacement of the A4 box.
- Terraform-managed Supabase/Upstash/Qdrant Cloud/R2, ECS, RDS, ALB, or Bedrock.
- Changing `deploy.yml`, Compose, smoke, or PR CI.
- `terraform apply` from GitHub Actions (that is Level B).
- Destroying the live instance to prove recreate. A throwaway second instance is optional and uses a separate workspace.

## Decisions

### D1 — Import the live edge; do not rebuild it

Model `aws_instance`, `aws_security_group`, and `aws_eip` / association only when an EIP already exists or the operator attaches one deliberately. Import those IDs. `user_data`, AMI, subnet, and instance type in HCL must match the running instance. If they cannot match without a replacement, use `lifecycle { ignore_changes = [...] }` for the drifting fields (typically `user_data` and `ami`) rather than applying a replace.

**Why:** A4 HTTP proof lives on this box. A new instance would orphan Docker, `.env`, and the current public IP that CD secrets point at.

**Alternatives:** New instance + cut over DNS/IP (safer long-term, breaks the "don't hurt the core" constraint now). Clickops forever (no IaC proof).

### D2 — Remote state before any live import

Backend is S3 with a DynamoDB lock table (or an equivalent lock the AWS provider documents), encryption on, state bucket created once outside the live root so the root does not depend on itself. `*.tfstate` and `*.tfvars` with real IDs/CIDRs that are sensitive stay gitignored; commit `terraform.tfvars.example` only.

Local backend is allowed for `terraform init` + `terraform validate` on the scaffold. The blueprint forbids `terraform import` of the production instance until `terraform init` is pointed at the remote backend.

**Why:** Local state on one laptop is how a second apply duplicates or destroys the box.

**Alternatives:** Terraform Cloud (fine later; extra account). Local state for the whole level (rejected for the live workspace).

### D3 — Layout and docs stay beside the existing ship path

```
dashnotesystemv1/infra/          # Terraform root (Level A only)
docs/deployment/terraform-a.md   # stages, verify, fallback, ownership
docs/devops-progress.md          # pointer + Phase 5 status; B/C not checked off
```

`docs/deployment/runbook.md` keeps shell/CD commands. It gains a short pointer to `terraform-a.md` and does not absorb HCL. No workflow YAML changes.

**Why:** `devops-progress.md` already assigns runbook vs tracker ownership. A second command dump in the runbook will drift.

### D4 — Staged apply order

| Stage | Mutates live AWS? | Gate |
|-------|-------------------|------|
| A0 Inventory | No | Written IDs + current `/health` 200 |
| A1 Scaffold | No | `fmt` + `validate`; no app diffs required beyond `infra/` and docs |
| A2 Remote state | Bucket/table only | Second `init` uses remote backend |
| A3 Import SG | Only if plan is in-place | SSH + `http://<ip>/health` still pass |
| A4 Import instance (+ EIP) | Only tags / in-place | Plan shows no replacement; health + smoke still pass; update `VPS_HOST` before dropping an old IP |
| A5 Outputs + ownership doc | No | Progress tracker points at the blueprint |
| A6 Throwaway recreate | Separate workspace only | Prod state untouched; destroy only the throwaway |

A3 before A4: a bad SG is recoverable from the console; a replaced instance is not.

### D5 — Ownership matrix (what Terraform must not absorb)

| Concern | Owner after Level A |
|---------|---------------------|
| EC2, SG, EIP | Terraform |
| Docker, Compose, nginx conf, `.env` | Operator + existing deploy scripts |
| Image build, migrate, roll, smoke | `deploy.yml` (unchanged) |
| Hosted data plane | Current vendors |
| Level B/C | Documented only |

### D6 — Level B and Level C are a written sequence, not tasks that apply

`terraform-a.md` ends with short lists:

- **Level B (after A5 and preferably one green CD run):** GitHub OIDC role limited to plan, `terraform plan` on PRs that touch `infra/`, optional SSM, optional Secrets Manager migration that still feeds Compose `.env`, optional ECR. No ECS.
- **Level C (separate future change, cap with the existing Phase 5 "≤2 extras" rule):** ECS/Fargate or ASG+ALB, RDS/ElastiCache, multi-env modules.

This change's tasks stop at A5, with A6 explicitly optional and skippable.

### D7 — Fallback that keeps the API up

Document these in `terraform-a.md` and the infra README:

- Plan wants to replace the instance → do not apply.
- Locked out of SSH → console or EC2 Instance Connect; temporary SG rule for the operator IP; then fix HCL.
- Abandon adoption → `terraform state rm` the address. The AWS object stays. CD continues against the snowflake.
- App unhealthy after a tag-only apply → roll back with the existing runbook (`IMAGE` previous tag + `up.sh`), not with new deploy scripts.

## Risks / Trade-offs

- **[Risk] Import HCL does not match the instance and Terraform replaces it** → Mitigation: D1 ignore_changes; D4 gate forbids apply when the plan shows replacement; A0 inventory is a task, not a guess.
- **[Risk] State bucket credentials or tfvars leak into git** → Mitigation: gitignore state and real tfvars; example file only; no secrets in outputs.
- **[Risk] EIP attach changes the public IP and CD `VPS_HOST` goes stale** → Mitigation: blueprint says update the GitHub secret before releasing the previous address; prefer importing the IP the box already has.
- **[Risk] Operators treat the blueprint as a second runbook and duplicate deploy steps** → Mitigation: D3; terraform doc links to runbook sections instead of copying them.
- **[Risk] Level A blocks unfinished CD/TLS** → Mitigation: A0–A2 can proceed in parallel; A4 import waits until the operator is not mid IP or instance change. CD workflow files are out of scope.
- **[Risk] `ignore_changes` hides real drift** → Mitigation: limit it to fields that force replacement; tags and SG rules stay managed.

## Migration Plan

1. Record inventory privately (instance id, SG id, AMI, subnet, key name, public IP). Confirm `/health` on that IP.
2. Land `infra/` scaffold and docs. `terraform validate` only.
3. Create the state bucket and lock table; migrate the backend; do not import yet.
4. Import SG, plan, apply only in-place diffs. Re-check SSH and health.
5. Import instance (and existing EIP if any). Abort if the plan replaces. Re-check health and `scripts/smoke_prod.py`.
6. Publish outputs and update `devops-progress.md`. Leave Level B/C unchecked.
7. Rollback of the code change is reverting the `infra/` and doc commits. Rollback of a bad apply is "do not apply a replace plan"; if already applied incorrectly, `state rm` plus console recovery, then the existing image rollback in `docs/deployment/runbook.md`.

## Open Questions

- None that change the approach. Exact AWS region, AMI id, and whether an EIP already exists are A0 inventory facts, filled at apply time in gitignored tfvars.
