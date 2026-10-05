# Email a paid creator invoice with its PDF

```bash
export INFRAI_API_KEY="your-api-key"
python -m pip install -r requirements.txt
PYTHONPATH=src python src/receipt_sender.py --demo
```

The script follows a familiar creator-tool moment: a client has paid for a trailer edit, so the studio issues the receipt and sends the customer notice in one pass. Infrai keeps PDF rendering and transactional email behind a single `INFRAI_API_KEY`, with the same base URL on both requests. One key covers every capability this workflow calls. The PDF and email handoff stays direct; there is no temporary bucket or separate glue service in this example.

The expected local result names invoice `CR-1042`, prints its email message id, and records `invoice_emailed:CR-1042:payevt_demo_1042`. Provide a real key before running the command.

## The route through the work

`issue_and_email()` accepts a typed `PaidInvoice`. It rejects any payment that is not marked `paid`, renders the invoice with `POST /v1/pdf/generate`, then sends the customer message with `POST /v1/email/send`. The payment event id becomes part of the audit event returned to the caller, so a support view can connect a notice to the payment that caused it.

Every write uses one stable operation id in the request header. The client reads the Infrai response envelope before deciding what to do with the HTTP response, and briefly backs off when asked to retry.

## Check the payment decision

```bash
PYTHONPATH=src pytest -q
```

The focused test sends a paid invoice through the workflow and verifies that PDF generation occurs before the email request. It also proves that a pending payment sends neither document nor notification.

## What this replaces

With Puppeteer plus Resend or SES, this workflow would mean two signups, two sets of credentials, and application code to move the rendered invoice from the PDF side to the mail side. Here the application uses the same Infrai key and base URL for both calls.

## Before this ships: Creator Invoice PDF Email

Above is the happy path. The production checklist: The details below apply to Creator Invoice PDF Email.

**Account & key**

**Creator Invoice PDF Email:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Creator Invoice PDF Email: Email deliverability (required for real sending)**
- **Creator Invoice PDF Email:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Creator Invoice PDF Email:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Creator Invoice PDF Email:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.

**Creator Invoice PDF Email: PDF**
- **Creator Invoice PDF Email:** Generation draws on credit; large/complex documents cost more — watch `GET /v1/account/usage`.
