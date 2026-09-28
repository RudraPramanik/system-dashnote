## ADDED Requirements

### Requirement: Edge docs stay aligned when Cloudflare fronts the API
When the production API is reached through Cloudflare Flexible to the Terraform-managed EC2 instance, documentation under the deployment and infra paths MUST state that DNS and browser TLS are outside Terraform, that the security group MUST keep port 80 reachable for Cloudflare-to-origin HTTP, that port 8000 MUST remain unpublished, and that Terraform MUST NOT be required to manage Cloudflare DNS records for this change.

#### Scenario: Operator does not look to Terraform for DNS
- **GIVEN** Level A Terraform manages EC2 and the security group
- **WHEN** an operator needs to create or change `api.aisystem.world`
- **THEN** docs direct them to Cloudflare DNS (or equivalent)
- **AND** they are not told to apply Terraform to create that DNS name in this change

#### Scenario: SG remains compatible with Flexible origin HTTP
- **GIVEN** Cloudflare proxies HTTPS to the VPS over HTTP
- **WHEN** an operator reviews the managed security group expectations
- **THEN** ingress for HTTP port 80 remains allowed for the Cloudflare path
- **AND** API port 8000 stays unpublished to the internet
