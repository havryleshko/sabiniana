"""The reader copies printed figures. These tests do not call the model."""

import json
from pathlib import Path

import pytest

from sabiniana.bills import check_bill
from sabiniana.check import check
from sabiniana.read import document_from_extraction, read


def _line(**kwargs) -> dict:
    line = {
        "name": "",
        "case_ref": "",
        "quantity": "",
        "unit_price": "",
        "unit_price_pence": "",
        "amount": "",
        "remake": False,
        "original_delivered": "",
        "excluded_from_rise": False,
        "extra": False,
        "was": "",
        "decommissioned_on": "",
    }
    line.update(kwargs)
    return line


def test_read_uses_a_supplied_extraction_and_does_not_calculate(tmp_path: Path):
    pdf = tmp_path / "statement.pdf"
    pdf.write_bytes(b"%PDF-1.4 sample")
    seen = {}

    def complete(data: bytes) -> dict:
        seen["pdf"] = data
        return {
            "kind": "card",
            "practice": "Cedar House Dental",
            "provider": "SamplePay Go",
            "document_date": "2026-10-05",
            "unreadable": [],
            "total_sales": "£14,000.00",
            "total_charges": "£245.00",
            "transaction_count": "160",
            "headline_rate": "1.75%",
            "agreed_rate": "",
            "charged_rate": "",
            "acquirer_margin": "",
            "terminal_contract_months": "",
            "minimum_monthly": "",
            "minimum_processing_fees": "",
            "minimum_top_up": "",
            "upcoming_from_rate": "",
            "upcoming_to_rate": "",
            "upcoming_date": "",
            "fee_lines": [
                {"name": "Processing fee", "amount": "£245.00"},
                {"name": "Total charges", "amount": "£245.00"},
            ],
            "bands": [],
        }

    document = read(pdf, complete=complete)
    assert seen["pdf"].startswith(b"%PDF")
    assert document["headline_rate"] == "0.0175"
    assert document["total_sales"] == "14000.00"
    assert document["fee_lines"] == [{"name": "Processing fee", "amount": "245.00"}]
    assert "effective_rate" not in document
    result = check(document)
    assert result["effective_rate"] == pytest.approx(0.0175)
    assert result["yearly_gap"] is None
    assert [finding["code"] for finding in result["findings"]] == ["plan_flat"]


def test_a_blank_amount_is_not_multiplied():
    document = document_from_extraction(
        {
            "kind": "supplies",
            "unreadable": [],
            "net": "231.00",
            "vat_rate": "20%",
            "vat_amount": "46.20",
            "total": "277.20",
            "lines": [
                _line(name="Nitrile gloves, medium", quantity="50", unit_price="£4.20", amount="")
            ],
        }
    )
    assert "amount" not in document["lines"][0]
    rendered = json.dumps(document)
    assert "210.00" not in rendered
    assert "Gloves" not in rendered or "no readable amount" in " ".join(document["unreadable"])


def test_printed_bill_figures_keep_their_checker_shape():
    lab = document_from_extraction(
        {
            "kind": "lab",
            "document_date": "30 Sep 2026",
            "net": "110.00",
            "vat_rate": "0%",
            "vat_amount": "0.00",
            "total": "110.00",
            "remake_free_within_days": "90",
            "lines": [
                _line(
                    name="Remake: e.max crown (shade adjustment)",
                    case_ref="H-3150",
                    quantity="1",
                    unit_price="£110.00",
                    amount="£110.00",
                    original_delivered="14 Aug 2026",
                )
            ],
        }
    )
    assert lab["invoice_date"] == "2026-09-30"
    assert lab["lines"][0]["remake"] is True
    assert lab["lines"][0]["original_delivered"] == "2026-08-14"
    assert check_bill(lab)["findings"][0]["code"] == "remake_inside_free_window"

    energy = document_from_extraction(
        {
            "kind": "energy",
            "document_date": "2026-09-30",
            "net": "869.42",
            "vat_rate": "20%",
            "vat_amount": "173.88",
            "total": "1043.30",
            "contract_status": "out_of_contract",
            "contract_since": "1 Apr 2026",
            "lines": [
                _line(
                    name="Electricity used",
                    quantity="2,100 kWh",
                    unit_price_pence="39.20p",
                    amount="£823.20",
                ),
                _line(
                    name="Standing charge",
                    quantity="30 days",
                    unit_price_pence="98.00p",
                    amount="£29.40",
                ),
                _line(
                    name="Climate Change Levy",
                    quantity="2100",
                    unit_price_pence="0.801p",
                    amount="£16.82",
                ),
            ],
        }
    )
    electricity = energy["lines"][0]
    levy = energy["lines"][2]
    assert electricity["rate_pence"] == "39.20"
    assert electricity["unit_price"] == "0.392"
    assert levy["unit_price"] == "0.00801"
    assert check_bill(energy)["findings"][0]["code"] == "out_of_contract"

    wrong = document_from_extraction(
        {
            "kind": "supplies",
            "net": "231.00",
            "vat_rate": "20%",
            "vat_amount": "46.20",
            "total": "277.20",
            "lines": [
                _line(
                    name="Nitrile gloves, medium (box 100)",
                    quantity="50",
                    unit_price="£4.20",
                    amount="£231.00",
                )
            ],
        }
    )
    finding = check_bill(wrong)["findings"][0]
    assert finding["code"] == "line_does_not_multiply"
    assert finding["billed"] == "231.00"
    assert finding["expected"] == "210.00"


def test_minimum_processing_comes_from_the_printed_fee_line():
    document = document_from_extraction(
        {
            "kind": "card",
            "total_sales": "8500.00",
            "total_charges": "169.00",
            "headline_rate": "1.60%",
            "minimum_monthly": "£150.00",
            "minimum_top_up": "£14.00",
            "fee_lines": [
                {"name": "Processing fee", "amount": "£136.00"},
                {"name": "Terminal rental", "amount": "£19.00"},
                {"name": "Minimum monthly charge top-up", "amount": "£14.00"},
            ],
        }
    )
    finding = check(document)["findings"][1]
    assert finding["code"] == "minimum_monthly_charge"
    assert finding["minimum"] == "150.00"
    assert finding["processing_fees"] == "136.00"
    assert finding["top_up"] == "14.00"


def test_read_rejects_a_file_that_is_not_a_pdf(tmp_path: Path):
    notes = tmp_path / "notes.txt"
    notes.write_text("not a pdf")
    with pytest.raises(ValueError):
        read(notes, complete=lambda _data: {})
