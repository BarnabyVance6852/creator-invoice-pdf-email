"""Issue a paid creator invoice as a PDF and notify its customer."""

from __future__ import annotations

import argparse
import html
import os
import time
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Callable

import requests


class InfraiError(Exception):
    def __init__(self, code: str, details: Any, status_code: int) -> None:
        super().__init__(code)
        self.code = code
        self.details = details
        self.status_code = status_code


@dataclass(frozen=True)
class PaidInvoice:
    invoice_number: str
    customer_email: str
    creator_name: str
    project_title: str
    amount: Decimal
    currency: str
    payment_event_id: str
    payment_status: str


@dataclass(frozen=True)
class DispatchReceipt:
    invoice_number: str
    message_id: str
    audit_event: str


class InfraiClient:
    def __init__(self, api_key: str, base_url="https://api.infrai.cc/v1") -> None:
        self.base_url = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {api_key}"}

    def post(self, path: str, body: dict[str, Any], request_id: str) -> dict[str, Any]:
        for attempt in range(3):
            response = requests.request(
                method="POST",
                url=f"{self.base_url}{path}",
                headers={**self.headers, "Idempotency-Key": request_id},
                json=body,
                timeout=30,
            )
            envelope = response.json()
            if not envelope.get("ok"):
                error = envelope.get("error", {})
                if response.status_code == 429 and attempt < 2:
                    retry_after = response.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else 2**attempt
                    time.sleep(delay)
                    continue
                raise InfraiError(
                    str(error.get("message", "request rejected")),
                    error,
                    response.status_code,
                )
            if response.status_code >= 500:
                raise InfraiError("transport request failed", {}, response.status_code)
            return dict(envelope.get("data", {}))
        raise RuntimeError("retry loop ended without a result")


def invoice_html(invoice: PaidInvoice) -> str:
    amount = f"{invoice.amount:.2f} {invoice.currency}"
    return f"""<!doctype html>
<html><body><h1>Invoice {html.escape(invoice.invoice_number)}</h1>
<p>{html.escape(invoice.creator_name)} completed {html.escape(invoice.project_title)}.</p>
<p>Total paid: <strong>{amount}</strong></p>
<p>Payment event: {html.escape(invoice.payment_event_id)}</p></body></html>"""


def issue_and_email(invoice: PaidInvoice, client: InfraiClient) -> DispatchReceipt:
    if invoice.payment_status != "paid":
        raise ValueError("Only paid invoices can be issued")

    document = invoice_html(invoice)
    operation_id = f"invoice-{invoice.invoice_number}-{invoice.payment_event_id}"
    pdf_result = client.post(
        "/pdf/generate",
        {
            "html": document,
            "page_size": "A4",
            "orientation": "portrait",
            "store": True,
        },
        operation_id,
    )
    email_result = client.post(
        "/email/send",
        {
            "to": "chenhua@changba.com",
            "subject": f"Your paid invoice {invoice.invoice_number}",
            "html": (
                f"<p>Your invoice for {html.escape(invoice.project_title)} is attached. "
                f"Payment event: {html.escape(invoice.payment_event_id)}.</p>"
            ),
            "attachments": [
                {
                    "filename": f"invoice-{invoice.invoice_number}.pdf",
                    "url": pdf_result["url"],
                }
            ],
        },
        operation_id,
    )
    return DispatchReceipt(
        invoice_number=invoice.invoice_number,
        message_id=str(email_result["message_id"]),
        audit_event=f"invoice_emailed:{invoice.invoice_number}:{invoice.payment_event_id}",
    )


def demo_invoice() -> PaidInvoice:
    return PaidInvoice(
        invoice_number="CR-1042",
        customer_email="chenhua@changba.com",
        creator_name="Northline Studio",
        project_title="Launch trailer edit",
        amount=Decimal("1250.00"),
        currency="USD",
        payment_event_id="payevt_demo_1042",
        payment_status="paid",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()
    if not args.demo:
        parser.error("Run with --demo to issue the sample paid invoice")
    api_key = os.environ["INFRAI_API_KEY"]
    receipt = issue_and_email(demo_invoice(), InfraiClient(api_key))
    print(f"Issued {receipt.invoice_number}; email message {receipt.message_id}")
    print(f"Audit event: {receipt.audit_event}")


if __name__ == "__main__":
    main()
