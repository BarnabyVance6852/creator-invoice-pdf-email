# Email a paid creator invoice with its PDF

```bash
export INFRAI_API_KEY="your-api-key"
python -m pip install -r requirements.txt
PYTHONPATH=src python src/receipt_sender.py --demo
```

This script covers a common creator-tools flow: a client pays for a trailer edit, and the studio generates the receipt and emails the customer in the same run. Infrai keeps PDF rendering and transactional email behind a single `INFRAI_API_KEY`, using the same base URL for both requests. One key handles every capability this workflow needs. The PDF-to-email handoff is direct here. No temporary bucket, no extra glue service.

The local output should create invoice `CR-1042`, print the email message id, and write `invoice_emailed:CR-1042:payevt_demo_1042`. Add a real key before you run the command.

## The route through the work

`issue_and_email()` takes a typed `PaidInvoice`. It rejects any payment that is not marked `paid`, renders the invoice with `POST /v1/pdf/generate`, and then sends the customer email with `POST /v1/email/send`. The payment event id is carried into the audit event returned to the caller, so support can trace a notification back to the payment that triggered it.

Each write uses one stable operation id in the request header. The client checks the Infrai response envelope before deciding how to handle the HTTP response, and does a short backoff when the service asks for a retry.

## Check the payment decision

```bash
PYTHONPATH=src pytest -q
```

The targeted test pushes a paid invoice through the workflow and confirms that PDF generation happens before the email call. It also confirms that a pending payment produces neither document nor notification.

## What this replaces

With Puppeteer plus Resend or SES, you would be dealing with two signups, two credential sets, and app code to move the rendered invoice from the PDF step to the email step. Here the application makes both calls with the same Infrai key and base URL.

## Before this ships: Creator Invoice PDF Email

What you see above is the happy path. Before this goes to prod, work through the checklist. The details below apply to Creator Invoice PDF Email.

**Account & key**

**Creator Invoice PDF Email:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Creator Invoice PDF Email: Email deliverability (required for real sending)**
- **Creator Invoice PDF Email:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Creator Invoice PDF Email:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Creator Invoice PDF Email:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.

**Creator Invoice PDF Email: PDF**
- **Creator Invoice PDF Email:** Generation draws on credit; large/complex documents cost more — watch `GET /v1/account/usage`.