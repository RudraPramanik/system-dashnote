## Purpose

Codify the existing AWS compute edge so operators can adopt and recreate it from the repository without changing how the application is built, migrated, or smoked.

## ADDED Requirements

### Requirement: Infrastructure code adopts the live edge without replacing it
The repository MUST provide an infrastructure-as-code root that can represent the current production EC2 instance, its security group, and an Elastic IP when one is in use. Adoption of the live box MUST be by import of those existing resources. A plan against the live workspace MUST NOT show a forced replacement of the instance before the operator applies it. The root MUST NOT be applied in a way that destroys the live first-boot instance as part of proving this change.

#### Scenario: Plan is clean after import
- **GIVEN** the live EC2 instance and security group have been imported into remote state
- **WHEN** an operator runs a plan in the live workspace
- **THEN** the plan does not replace the instance
- **AND** any remaining diff is limited to in-place updates such as tags

#### Scenario: Replacement plan blocks apply
- **GIVEN** a plan that would replace or destroy the live instance
- **WHEN** the operator reviews the plan
- **THEN** the documented procedure requires aborting the apply
- **AND** the live instance remains running

### Requirement: Remote state is required before live import
Live-instance import MUST use a remote state backend with locking. Local state MAY be used only to validate the scaffold (`init` and `validate`) before any live import. The infrastructure root MUST NOT commit state files, cloud credentials, or filled variable files that contain secrets.

#### Scenario: Live import refused on local state
- **GIVEN** the infrastructure root is still configured for local state only
- **WHEN** an operator is about to import the live instance
- **THEN** the operator documentation requires switching to remote locked state first
- **AND** the live instance is not imported into local state

#### Scenario: Scaffold validates without touching AWS resources
- **GIVEN** a fresh checkout of the infrastructure root
- **WHEN** an operator runs format check, init, and validate without applying
- **THEN** validation succeeds
- **AND** no production EC2 or security group is created or destroyed

### Requirement: Edge rules stay compatible with the thin VPS
The managed security group MUST allow the operator SSH and HTTP paths already used for first-boot, and MUST NOT publish the API port `8000` to the internet. Infrastructure code MUST NOT provision hosted Postgres, Redis, Qdrant, or object storage, and MUST NOT install or start the local full-stack Compose file on the instance.

#### Scenario: API port stays unpublished
- **GIVEN** the security group is expressed in the infrastructure root
- **WHEN** an operator reviews its ingress rules
- **THEN** port `8000` is not open to the public internet
- **AND** SSH and HTTP remain available on the paths the first-boot runbook already requires

#### Scenario: Data plane stays hosted
- **GIVEN** Level A infrastructure is applied
- **WHEN** an operator inspects resources created by this change
- **THEN** Postgres, Redis, Qdrant, and object storage are not created by it
- **AND** the VPS continues to reach those services through the existing gitignored `.env`

### Requirement: Application deploy path is unchanged
This change MUST NOT alter the behavior of pull-request CI, the CD workflow triggers, deploy helper scripts, production smoke, production Compose, or local Compose. Shipping a release MUST remain: build and push an image, then migrate, roll, health-check, and smoke on the VPS. Infrastructure outputs MAY document the public address; they MUST NOT automatically rewrite GitHub deploy secrets in this change.

#### Scenario: CD contract stays explicit-trigger only
- **GIVEN** the repository after this change
- **WHEN** an operator inspects the deploy workflow
- **THEN** deploys still run only on `workflow_dispatch` or a `v*` tag
- **AND** pushes to the default branch still do not deploy

#### Scenario: Local compose is untouched
- **GIVEN** a developer machine using the default Compose file
- **WHEN** the developer starts the local stack
- **THEN** local database, cache, and vector services still come from that Compose file
- **AND** the new infrastructure root is not required for local development

### Requirement: Operators get a sequential blueprint with verify and fallback
The repository MUST document Level A as ordered stages: inventory, scaffold, remote state, security-group import, instance import, outputs and ownership, and an optional throwaway recreate drill. Each stage MUST state what to verify before continuing and how to fall back without taking the live API down. The same document MUST list Level B and Level C as later, unimplemented sequences. `docs/devops-progress.md` MUST point at that blueprint and MUST NOT mark Level B or Level C as done by this change.

#### Scenario: Stage gate stops a bad import
- **GIVEN** the blueprint's instance-import stage
- **WHEN** verification shows the live health check failing or a plan that replaces the instance
- **THEN** the blueprint tells the operator to stop and use the documented fallback
- **AND** fallback includes removing the resource from state without deleting the AWS object when abandoning adoption

#### Scenario: Later levels stay roadmap
- **GIVEN** Level A documentation is complete
- **WHEN** an operator reads the Level B and Level C sections
- **THEN** they describe future work only (identity-based plan automation, and optional orchestration or data-plane moves)
- **AND** this change does not add workflows or resources that implement those levels
