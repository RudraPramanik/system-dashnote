## 1. DNS and Cloudflare TLS

- [ ] 1.1 In Cloudflare DNS for `aisystem.world`, create A record `api` → VPS public IP `16.192.166.178` (or current EIP if attached), Proxied (orange)
- [ ] 1.2 Set SSL/TLS mode to **Flexible**; confirm origin still serves HTTP `:80` only
- [ ] 1.3 Verify `nslookup api.aisystem.world` and `curl -sS https://api.aisystem.world/health` return hard health success

## 2. VPS env and CORS

- [ ] 2.1 On the VPS `.env`, set `CORS_ORIGINS` to include `https://aisystem.world` and remove `*`; optionally keep localhost entries
- [x] 2.2 Update `.env.production.example` so the committed contract shows the apex HTTPS origin (no secrets)
- [ ] 2.3 Restart or redeploy api (and worker if required) so CORS takes effect; re-check HTTPS health

## 3. Documentation (VPS / infrastructure)

- [x] 3.1 Extend `docs/deployment/runbook.md` with DNS checklist, Flexible SSL, HTTPS smoke commands, and “SSH by IP only”
- [x] 3.2 Add `docs/deployment/edge-aisystem.md` (or equivalent) mapping Cloudflare vs Terraform/EC2/SG vs Compose; state FE is not on this VPS
- [x] 3.3 Link the edge doc from `docs/devops-progress.md` and `infra/README.md`

## 4. A7 proof and trackers

- [ ] 4.1 Run `SMOKE_BASE_URL=https://api.aisystem.world python scripts/smoke_prod.py` and confirm exit 0
- [ ] 4.2 Mark Phase 3 / A7 ✅ in `docs/devops-progress.md` and `docs/documentation/blueprint/goal.md` with the proof URL (update both together)

## 5. CD follow-through

- [x] 5.1 Document GitHub secrets: `SMOKE_BASE_URL=https://api.aisystem.world`; `VPS_HOST` remains the SSH IP; other deploy secrets as in runbook
- [ ] 5.2 Configure those secrets in the repo and run one `workflow_dispatch` (or record blocker if SSH/path fails without changing FE scope)

## 6. Explicit non-goals check

- [x] 6.1 Confirm no frontend app was deployed to the VPS or required for A7; note FE/apex hosting as a follow-on change
- [x] 6.2 Confirm Bedrock and Cloudflare Full/origin certs were not started in this change
