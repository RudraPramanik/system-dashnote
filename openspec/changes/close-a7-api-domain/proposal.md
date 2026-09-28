## Why

HTTP-on-IP first-boot is proven, but production-live (A7) needs `https://api.aisystem.world`. The zone is on Cloudflare; DNS for `api` and operator docs for the VPS edge are still open. Without a documented HTTPS API URL and CORS ready for the future apex frontend, CD and FE stay blocked.

## What Changes

- Operator path to point `api.aisystem.world` at the thin VPS (Cloudflare DNS A record) and terminate browser TLS via Cloudflare with origin nginx on `:443` (Cloudflare **Full** + self-signed origin cert; Flexible alone returned 521 while origin was HTTP-only).
- Production env contract: `CORS_ORIGINS` lists `https://aisystem.world` (apex FE later) — never `*`. Document restart/redeploy after CORS change.
- Prove A7: `GET https://api.aisystem.world/health` → 200 and HTTPS `scripts/smoke_prod.py` exit 0; update `docs/devops-progress.md` and `goal.md` A7 when green.
- Document the live edge in runbook / infra notes (what Cloudflare owns vs nginx on VPS vs Terraform SG) so VPS work stays auditable.
- CD follow-through in this change: document and wire GitHub secrets so `SMOKE_BASE_URL` is `https://api.aisystem.world` and one `deploy.yml` run can be attempted (operator-gated). No FE hosting. No Bedrock. No moving FE onto the VPS.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `production-platform`: Close the HTTPS / domain gap for A7 using Cloudflare + `api.aisystem.world`; require documented DNS/TLS mode, CORS for `https://aisystem.world`, HTTPS smoke proof, and progress/A-gate sync. Clarify that TLS is no longer docs-only for this domain path once A7 is claimed.
- `platform-terraform`: Require SG/edge docs to stay consistent with Cloudflare Full (80 and 443 reachable; 8000 unpublished). No requirement to manage DNS in Terraform in this change.

## Impact

- **Operator / VPS:** Cloudflare DNS for `api`; VPS `.env` CORS; possible compose restart; SG already allows 80/443.
- **Docs:** `docs/deployment/runbook.md`, `docs/devops-progress.md`, `docs/documentation/blueprint/goal.md`, short infra note (runbook section or `docs/deployment/` sibling) describing Cloudflare vs VPS vs Terraform.
- **CD:** GitHub Actions secrets/vars; existing `deploy.yml` unchanged in behavior except smoke URL.
- **Out of scope:** Frontend hosting (not Vercel, not this VPS), apex DNS for FE beyond documenting the intended origin, Bedrock, Full (strict) / Let’s Encrypt, Terraform Route53.
- **Assumption:** Apex frontend will be `https://aisystem.world` on a non-VPS host later; API remains only compute on the EC2 thin box with hosted data plane.
