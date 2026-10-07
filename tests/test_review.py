"""read, then check, then write. These tests do not call the model."""

from sabiniana.review import review, save_review
from sabiniana.write import figures_outside_result


def _card(_path):
    return {
        "kind": "card",
        "practice": "Cedar House Dental",
        "total_sales": "14000.00",
        "total_charges": "245.00",
        "headline_rate": "0.0175",
        "fee_lines": [{"name": "Processing fee", "amount": "245.00"}],
    }


def _lab(_path):
    return {
        "kind": "lab",
        "practice": "Cedar House Dental",
        "invoice_date": "2026-09-30",
        "net": "345.00",
        "vat": {"rate": "0.20", "amount": "69.00"},
        "total": "414.00",
        "lines": [
            {"name": "e.max crown", "quantity": "2", "unit_price": "95.00", "amount": "190.00"},
            {"name": "Full-contour zirconia crown", "quantity": "1", "unit_price": "85.00", "amount": "85.00"},
            {"name": "Porcelain bonded crown (private)", "quantity": "1", "unit_price": "70.00", "amount": "70.00"},
        ],
    }


def test_review_routes_a_card_and_a_lab_without_adding_a_saving():
    card = review("statement.pdf", read_pdf=_card)
    assert [finding["code"] for finding in card["result"]["findings"]] == ["plan_flat"]
    assert card["result"]["yearly_gap"] is None
    assert "Cedar House Dental" in card["page"]
    assert "No fair-price saving is stated" in card["page"]
    assert figures_outside_result(card["page"], {**card["result"], "practice": "Cedar House Dental"}) == []

    lab = review("invoice.pdf", read_pdf=_lab)
    assert [finding["code"] for finding in lab["result"]["findings"]] == ["vat_charged_on_dental_work"]
    assert "£69.00" in lab["page"]
    assert figures_outside_result(lab["page"], {**lab["result"], "practice": "Cedar House Dental"}) == []


def test_an_unknown_document_is_not_checked():
    outcome = review("scan.pdf", read_pdf=lambda _path: {"kind": "unknown", "unreadable": ["total"]})
    assert outcome["result"]["verdict"] == "incomplete"
    assert outcome["result"]["findings"][0]["code"] == "document_kind_unreadable"
    assert "£" not in outcome["page"]


def test_save_review_writes_the_working_file_and_the_draft(tmp_path):
    working = tmp_path / "working"
    reports = tmp_path / "reports"
    outcome = save_review("statement.pdf", working, reports, read_pdf=_card)
    assert (working / "statement.json").is_file()
    assert (reports / "statement.md").read_text() == outcome["page"]
    assert "Nothing has been sent." in outcome["page"]
