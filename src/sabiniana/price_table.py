"""Cited card-fee reference rates. No fair all-in rate is invented."""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

_MONEY = Decimal("0.01")
_PERCENT = Decimal("0.01")

_TABLE_PATH = Path(__file__).resolve().parents[2] / "engine" / "reference" / "price_table.json"


def load_price_table(path: Path | None = None) -> dict:
    """Read the reference price table from the repository."""
    source = path if path is not None else _TABLE_PATH
    return json.loads(source.read_text())


def compare_with_observed_average(statement: dict, table: dict) -> dict | None:
    """Compare this statement with the PSR's observed average for its turnover band.

    The yearly difference is the rate gap times annual card turnover. It is not a
    fair-price gap. Annual turnover is annual_card_turnover when that key is
    present, otherwise this statement's card sales times 12.
    """
    observed = table.get("observed_average_msc")
    if not isinstance(observed, dict):
        return None
    sales = _decimal(statement.get("total_sales"))
    charges = _decimal(statement.get("total_charges"))
    if sales is None or charges is None or sales <= 0:
        return None

    stated_annual = _decimal(statement.get("annual_card_turnover"))
    if stated_annual is not None:
        annual = stated_annual
        annualised = False
    else:
        annual = sales * 12
        annualised = True
    if annual <= 0:
        return None

    band = _band_for(annual, observed.get("bands"))
    if band is None:
        return None
    rate = _decimal(band.get("rate"))
    if rate is None:
        return None

    effective = charges / sales
    gap = effective - rate
    yearly = (gap * annual).quantize(_MONEY, rounding=ROUND_HALF_UP)
    annual_text = _pounds(annual)
    points = f"{(abs(gap) * 100).quantize(_PERCENT, rounding=ROUND_HALF_UP):.2f}"
    period = observed.get("data_period")
    if yearly > 0:
        relation = f"{points} percentage points above"
    elif yearly < 0:
        relation = f"{points} percentage points below"
    else:
        relation = "the same as"
    summary = (
        f"Effective rate is {relation} the observed average of {_percent(rate)} "
        f"for annual card turnover of {band['name']} ({period}). "
        f"Applied to £{annual_text} of card sales, that is £{_pounds(abs(yearly))} a year. "
        "This average is not a fair price."
    )
    return {
        "kind": "observed_average_msc",
        "summary": summary,
        "band": band["name"],
        "observed_rate": _rate_text(rate),
        "annual_card_turnover": annual_text,
        "annualised_from_statement": annualised,
        "yearly_difference": _pounds(yearly),
        "published": observed.get("published"),
        "data_period": observed.get("data_period"),
        "source": f"{observed.get('source_title')}, {band.get('table')}",
        "source_url": observed.get("source_url"),
    }


def _band_for(annual: Decimal, bands: object) -> dict | None:
    if not isinstance(bands, list):
        return None
    for band in bands:
        if not isinstance(band, dict):
            continue
        lower = _decimal(band.get("min"))
        if lower is None or annual < lower:
            continue
        upper = band.get("max")
        if upper is not None:
            ceiling = _decimal(upper)
            if ceiling is None or annual >= ceiling:
                continue
        return band
    return None


def _decimal(value: object) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, Decimal)):
        number = Decimal(value)
    elif isinstance(value, float):
        number = Decimal(format(value, "f"))
    elif isinstance(value, str):
        try:
            number = Decimal(value.strip())
        except InvalidOperation:
            return None
    else:
        return None
    if not number.is_finite():
        return None
    return number


def _pounds(amount: Decimal) -> str:
    return f"{amount.quantize(_MONEY, rounding=ROUND_HALF_UP):.2f}"


def _percent(rate: Decimal) -> str:
    return f"{(rate * 100).quantize(_PERCENT, rounding=ROUND_HALF_UP):.2f}%"


def _rate_text(rate: Decimal) -> str:
    text = format(rate, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"
