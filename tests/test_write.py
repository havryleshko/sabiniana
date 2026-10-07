"""The draft page may quote the check result and may not add a saving."""

import json
from pathlib import Path

from sabiniana.bills import check_bill
from sabiniana.check import check
from sabiniana.write import figures_outside_result, write

_CARDS = json.loads((Path(__file__).parent / "fixtures" / "card_statements.json").read_text())
_BILLS = json.loads((Path(__file__).parent / "fixtures" / "other_bills.json").read_text())


def _assert_numbers_are_from_the_check(result: dict) -> str:
    page = write(result)
    assert figures_outside_result(page, result) == []
    return page


def test_every_sample_page_uses_only_check_numbers():
    for sample in _CARDS:
        page = _assert_numbers_are_from_the_check(check(sample["statement"]))
        assert "The verdict is incomplete." in page
        assert "No fair-price saving is stated" in page
        assert "overpaying" not in page.lower()
    for sample in _BILLS:
        page = _assert_numbers_are_from_the_check(check_bill(sample["document"]))
        assert "The verdict is incomplete." in page
        assert "No fair-price saving is stated" in page


def test_a_clean_statement_is_not_called_a_fair_price():
    harbour = next(sample for sample in _CARDS if sample["id"] == "02")
    page = write(check(harbour["statement"]))
    assert "These checks found nothing to flag." in page
    assert "does not say the price is fair" in page
    assert "You're fine" not in page
    assert "Draft for review. Nothing has been sent." in page


def test_a_stated_difference_is_quoted_and_an_extra_saving_is_not():
    meadowbank = next(sample for sample in _CARDS if sample["id"] == "04")
    result = check(meadowbank["statement"])
    result["suggested_saving"] = "8000.00"
    page = write(result)
    assert "£175.00" in page
    assert "£2100.00" in page
    assert "8000" not in page
    assert page == write(result)


def test_a_fair_price_gap_is_quoted_only_when_the_check_has_one():
    page = write({"findings": [], "verdict": "incomplete", "yearly_gap": None})
    assert "£" not in page
    stated = write({"findings": [], "verdict": "incomplete", "yearly_gap": "1500.00"})
    assert "£1500.00" in stated
    assert "No fair-price saving is stated" not in stated
