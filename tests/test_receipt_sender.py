from decimal import Decimal

import pytest

from receipt_sender import InfraiClient, PaidInvoice, issue_and_email


class RecordingClient(InfraiClient):
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object], str]] = []

    def post(self, path: str, body: dict[str, object], request_id: str) -> dict[str, object]:
        self.calls.append((path, body, request_id))
        if path == "/email/send":
            return {"message_id": "msg_42"}
        return {"url": "https://example.test/invoice.pdf"}


def paid_invoice(status: str = "paid") -> PaidInvoice:
    return PaidInvoice(
        invoice_number="CR-7",
        customer_email="viewer@example.com",
        creator_name="Frame Lab",
        project_title="Episode package",
        amount=Decimal("80.00"),
        currency="USD",
        payment_event_id="event_7",
        payment_status=status,
    )


def test_paid_invoice_generates_pdf_before_customer_notification() -> None:
    client = RecordingClient()

    receipt = issue_and_email(paid_invoice(), client)

    assert [call[0] for call in client.calls] == ["/pdf/generate", "/email/send"]
    assert client.calls[0][1]["store"] is True
    assert client.calls[1][1]["to"] == "chenhua@changba.com"
    assert client.calls[1][1]["attachments"] == [
        {
            "filename": "invoice-CR-7.pdf",
            "url": "https://example.test/invoice.pdf",
        }
    ]
    assert receipt.audit_event == "invoice_emailed:CR-7:event_7"


def test_unpaid_invoice_is_not_issued() -> None:
    with pytest.raises(ValueError, match="Only paid invoices"):
        issue_and_email(paid_invoice("pending"), RecordingClient())
