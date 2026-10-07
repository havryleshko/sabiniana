"""The 14 sample card statements, read by hand from the PDFs.

The PDFs are in tests/all-30-SAMPLE-pdfs.zip. These tests use the
transcribed numbers in tests/fixtures/card_statements.json. The reader
does not open the PDFs. Illustrative savings in the answer key that
need an uncited fair price are not expected.
"""

import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import pytest

from sabiniana.check import check

_FIXTURES = Path(__file__).parent / "fixtures" / "card_statements.json"
_SAMPLES = json.loads(_FIXTURES.read_text())

_FINDING_CODES = {
    "01": ["plan_flat"],
    "02": [],
    "03": ["stacked_small_fees", "tier_top_band"],
    "04": ["plan_flat", "charged_rate_differs"],
    "05": ["stacked_small_fees", "penalty_fee", "plan_flat"],
    "06": ["plan_flat", "long_terminal_contract"],
    "07": ["plan_flat", "minimum_monthly_charge"],
    "08": ["acquirer_margin"],
    "09": ["lines_do_not_add_up", "duplicate_fee", "plan_flat"],
    "10": ["plan_flat"],
    "11": [],
    "12": ["plan_flat", "upcoming_rate"],
    "13": ["penalty_fee", "tier_top_band"],
    "14": ["stacked_small_fees", "plan_flat"],
}


def _by_code(result: dict) -> dict[str, dict]:
    return {finding["code"]: finding for finding in result["findings"]}


@pytest.mark.parametrize("sample", _SAMPLES, ids=lambda sample: sample["id"])
def test_sample_card_statement(sample):
    result = check(sample["statement"])
    sales = Decimal(sample["statement"]["total_sales"])
    charges = Decimal(sample["statement"]["total_charges"])
    shown = (charges / sales * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    assert f"{shown:.2f}" == sample["answer_key_percent"]
    assert result["yearly_gap"] is None
    assert result["verdict"] == "incomplete"
    assert [finding["code"] for finding in result["findings"]] == _FINDING_CODES[sample["id"]]


def test_agreed_rate_gap_rate_rise_duplicate_and_top_band():
    results = {sample["id"]: check(sample["statement"]) for sample in _SAMPLES}
    meadowbank = _by_code(results["04"])["charged_rate_differs"]
    assert meadowbank["monthly_difference"] == "175.00"
    assert meadowbank["yearly_difference"] == "2100.00"

    old_mill = _by_code(results["12"])["upcoming_rate"]
    assert old_mill["effective_date"] == "2026-11-01"
    assert old_mill["monthly_difference"] == "108.00"
    assert old_mill["yearly_difference"] == "1296.00"

    ashdown = _by_code(results["09"])
    assert ashdown["lines_do_not_add_up"]["difference"] == "-22.50"
    assert ashdown["duplicate_fee"]["count"] == 2
    assert ashdown["duplicate_fee"]["amounts"] == ["8.00", "8.00"]

    kingsway = _by_code(results["03"])["tier_top_band"]
    assert kingsway["rate"] == "0.0299"
    assert kingsway["sales"] == "12500.00"
    assert kingsway["payments"] == 90

    pembroke = _by_code(results["08"])["acquirer_margin"]
    assert pembroke["rate"] == "0.0055"
    assert pembroke["amount"] == "605.00"

    greenacre = _by_code(results["07"])["minimum_monthly_charge"]
    assert greenacre["top_up"] == "14.00"
    assert greenacre["minimum"] == "150.00"

    thornbury = _by_code(results["06"])["long_terminal_contract"]
    assert thornbury["months"] == 60

    st_albans = _by_code(results["05"])["penalty_fee"]
    assert st_albans["amount"] == "45.00"
    assert st_albans["avoidable"] is True


def test_larchfield_has_no_fair_price_gap():
    larchfield = next(sample for sample in _SAMPLES if sample["id"] == "10")
    result = check(larchfield["statement"])
    assert result["yearly_gap"] is None
    assert "acquirer_margin" not in {finding["code"] for finding in result["findings"]}
