# Inbound channels — email / WhatsApp

First-party ingest for DashNote. OpenSpec: `openspec/changes/inbound-email-whatsapp`.

## Design choices

| Topic | Choice |
|-------|--------|
| Email provider spike | **IMAP via self-hosted n8n** (or curl) → `POST /integrations/inbound/email` for local demos. Prefer **Resend / Mailgun / Postmark inbound webhooks** for production (signed From, less spoofing). |
| n8n role | Thin adapter only. Never store end-user JWTs. |
| WhatsApp | Meta Cloud API webhooks; text-first MVP. |
| Agentic | `INBOUND_AGENTIC_ENABLED=false` by default. |

## Auth

- Email inbound: header `X-Inbound-Api-Key: <INBOUND_API_KEY>`
- Optional: `X-Inbound-Signature: sha256=<hex>` when `INBOUND_HMAC_SECRET` is set (HMAC-SHA256 of raw body)
- WhatsApp webhook: Meta `X-Hub-Signature-256` with `WHATSAPP_APP_SECRET`
- Leave `INBOUND_API_KEY` empty → email inbound returns 503

## Email curl example

```bash
curl -sS -X POST "$API/integrations/inbound/email" \
  -H "Content-Type: application/json" \
  -H "X-Inbound-Api-Key: $INBOUND_API_KEY" \
  -d '{
    "message_id": "demo-001",
    "from_email": "you@example.com",
    "subject": "Inbox dump",
    "body": "Captured from email",
    "attachments": []
  }'
```

`from_email` must match a registered `users.email` (case-insensitive).

## n8n (self-hosted) sketch

1. Trigger: IMAP Email / provider webhook  
2. Normalize → JSON: `message_id`, `from_email`, `subject`, `body`, optional base64 `attachments`  
3. HTTP Request → `POST {{API}}/integrations/inbound/email` with `X-Inbound-Api-Key`  
4. Do **not** pass user Bearer tokens

## WhatsApp link (API-only)

1. Authenticated user: `POST /integrations/whatsapp/link/start` `{"phone":"+15551234567"}` → `{code}`  
2. `POST /integrations/whatsapp/link/confirm` `{"phone":"...","code":"..."}`  
3. Unlink: `DELETE /integrations/whatsapp/link?phone=%2B15551234567`  
4. Configure Meta webhook URL: `https://api.<domain>/integrations/whatsapp/webhook`  
5. Verify token = `WHATSAPP_VERIFY_TOKEN`

Media-only messages are acknowledged but **do not** create empty notes (text-first MVP; current MIME/size policy).

## Ops

| Action | How |
|--------|-----|
| Disable email inbound | Clear `INBOUND_API_KEY` or unset |
| Disable WhatsApp | Clear `WHATSAPP_APP_SECRET` |
| Rotate keys | Set new `INBOUND_API_KEY` / Meta app secret; update n8n + Meta console |
| Rollback | Redeploy previous image; tables can remain |

## Smoke

```bash
python scripts/smoke_inbound_email.py --base-url http://localhost:8000
```

Requires a registered user email matching `--from-email` and `INBOUND_API_KEY` in the environment (or `--api-key`).
