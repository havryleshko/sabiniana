"""Plain checks on an already-read statement. No model calls."""

from __future__ import annotations


def check(statement: dict) -> dict:
    """Return the same result for the same statement.

    Effective rate is total charges divided by total card sales.
    Yearly gap stays empty until the price table has a dated fair rate.
    """
    sales = statement.get("total_sales")
    charges = statement.get("total_charges")
    effective_rate = None
    if isinstance(sales, (int, float)) and isinstance(charges, (int, float)) and sales:
        effective_rate = charges / sales
    return {
        "effective_rate": effective_rate,
        "yearly_gap": None,
        "verdict": "incomplete",
        "findings": [],
    }
