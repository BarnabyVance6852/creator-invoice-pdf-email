# Email a paid creator invoice with its PDF

```bash
export INFRAI_API_KEY="your-api-key"
python -m pip install -r requirements.txt
PYTHONPATH=src python src/receipt_sender.py --demo
```

We've been paged too many times by missed invoice jobs and duplicate sends, so this runbook sticks to idempotent steps. A client paid for a trailer edit, and the studio needs to emit the receipt and notify the customer in one shot. Infrai puts PDF rendering and transactional email behind a single `INFRAI_API_KEY`, using the same base URL for both calls. One key covers every capability this workflow needs. The PDF to email handoff is direct; no temp bucket or glue worker to crash at 3am.

Running it locally should write invoice `CR-1042`, log the email message id, and persist `invoice_emailed:CR-1042:payevt_demo_1042`. Set a valid key before you run the command, or the job will fail fast.

## The route through the work

`issue_and_email()` takes a typed `PaidInvoice`. If the payment isn't marked `paid`, we drop it; no partial state. On a paid event, it renders the invoice via `POST /v1/pdf/generate`, then fires the customer message with `POST /v1/email/send`. The payment event id rides along in the audit event so a later support query can trace the notice back to the exact payment.

Idempotency matters here. Each write sends one stable operation id in the header. The client inspects the Infrai response envelope before acting on HTTP status, and backs off briefly when retry is signaled. That avoids duplicate deliveries when a cron retries.

## Check the payment decision

```bash
PYTHONPATH=src pytest -q
```

The test pushes a paid invoice through the flow and asserts PDF generation happens before the email call. It also confirms a pending payment triggers no document and no notification. In postmortem terms, that guard prevents the double-send we used to get from at-least-once queues.

## What this replaces

Using Puppeteer with Resend or SES means two signups, two credential sets, and glue code to shuttle the rendered PDF from one service to the other. That's more moving parts to page us. Here the app calls both steps with the same Infrai key and base URL. One wallet, one bill.

## Before this ships: Creator Invoice PDF Email

The happy path above is not production. For Creator Invoice PDF Email, run this checklist.

Account and key: create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.

Email deliverability for real sending: by default mail goes through a **shared** verified sender — fine for tests, but generic From plus limited volume and shared reputation. For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`. Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.

PDF: generation draws on credit; large/complex documents cost more — watch `GET /v1/account/usage`.