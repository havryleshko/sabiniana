"""The other 16 sample documents, read by hand from the PDFs.

Price-list comparisons from the answer key are not expected. Those lists
have no source in this repo.
"""

import json
from pathlib import Path

import pytest

from sabiniana.bills import check_bill

_FIXTURES = Path(__file__).parent / "fixtures" / "other_bills.json"
_BILLS = json.loads(_FIXTURES.read_text())

_FINDING_CODES = {
    "15": ["vat_charged_on_dental_work"],
    "16": [],
    "17": ["remake_inside_free_window"],
    "18": ["duplicate_case"],
    "19": ["courier_charged", "price_rise"],
    "20": [],
    "21": ["surcharge"],
    "22": ["out_of_contract"],
    "23": ["contract_ending"],
    "24": ["estimated_reading"],
    "25": ["rolled_over"],
    "26": ["small_order_extras"],
    "27": ["line_does_not_multiply"],
    "28": [],
    "29": ["renewal_price_rise"],
    "30": ["decommissioned_equipment"],
}


def _by_code(result: dict) -> dict[str, dict]:
    return {finding["code"]: finding for finding in result["findings"]}


@pytest.mark.parametrize("bill", _BILLS, ids=lambda bill: bill["id"])
def test_other_sample_bill(bill):
    result = check_bill(bill["document"])
    assert result["yearly_gap"] is None
    assert result["verdict"] == "incomplete"
    assert [finding["code"] for finding in result["findings"]] == _FINDING_CODES[bill["id"]]


def test_document_findings_use_the_bill_arithmetic():
    results = {bill["id"]: check_bill(bill["document"]) for bill in _BILLS}

    vat = _by_code(results["15"])["vat_charged_on_dental_work"]
    assert vat["amount"] == "69.00"
    assert "item 2A" in vat["source"]

    remake = _by_code(results["17"])["remake_inside_free_window"]
    assert remake["amount"] == "110.00"
    assert remake["days"] == 47

    duplicate = _by_code(results["18"])["duplicate_case"]
    assert duplicate["case_ref"] == "M-2204"
    assert duplicate["extra_amount"] == "105.00"

    rise = _by_code(results["19"])["price_rise"]
    assert rise["base"] == "1778.00"
    assert rise["monthly_difference"] == "142.24"
    assert _by_code(results["19"])["courier_charged"]["amount"] == "91.00"

    ending = _by_code(results["23"])["contract_ending"]
    assert ending["monthly_difference"] == "155.40"
    assert ending["days_left"] == 61

    extras = _by_code(results["26"])["small_order_extras"]
    assert extras["extras"] == "13.90"
    assert extras["goods"] == "65.90"
    assert extras["share_percent"] == "21.09"

    maths = _by_code(results["27"])["line_does_not_multiply"]
    assert maths["expected"] == "210.00"
    assert maths["billed"] == "231.00"
    assert maths["difference_with_vat"] == "25.20"

    renewal = _by_code(results["29"])["renewal_price_rise"]
    assert renewal["percent"] == "23.08"
    assert renewal["monthly_difference"] == "24.00"
    assert renewal["cancel_by"] == "2026-11-01"

    removed = _by_code(results["30"])["decommissioned_equipment"]
    assert removed["amount_since"] == "224.00"
    assert removed["yearly_if_it_continues"] == "672.00"


def test_unsourced_price_lists_are_not_applied():
    results = {bill["id"]: check_bill(bill["document"]) for bill in _BILLS}
    assert results["16"]["findings"] == []
    assert results["20"]["findings"] == []
    assert results["21"]["findings"][0]["code"] == "surcharge"
    assert "120.00" not in results["25"]["findings"][0]["summary"]
    assert "26p" not in results["22"]["findings"][0]["summary"]
