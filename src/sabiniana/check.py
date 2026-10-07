"""Plain checks on an already-read statement. No model calls."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from sabiniana.price_table import compare_with_observed_average, load_price_table

_MONEY = Decimal("0.01")
_RATE_TOLERANCE = Decimal("0.000000001")
_PLAIN_DECIMAL = re.compile(r"^-?\d+(\.\d+)?$")

# Phrase lists are matched against the normalised fee name. A single fee in
# one of these categories is not a finding. The same category twice is a
# repeated fee. Two or more categories on one statement are stacked fees.
_SMALL_FEES = (
    ("statement", "Statement fee", ("statement fee", "monthly statement", "paper statement")),
    ("gateway", "Gateway fee", ("gateway fee", "payment gateway", "gateway charge")),
    ("admin", "Admin fee", ("admin fee", "administration fee", "admin charge")),
    ("terminal_rental", "Terminal rental", ("terminal rental", "terminal hire", "terminal rent")),
)

_PENALTIES = (
    (
        "pci_non_compliance",
        "PCI non-compliance",
        ("pci non compliance", "pci noncompliance", "non pci", "pci penalty"),
        "It stops once the provider records the practice as PCI compliant.",
    ),
)

# Product rules of thumb from tests/answer-key-SAMPLE.md. They are not cited market rates.
# A terminal hire longer than 18 months is flagged (statement 06).
# A cost-plus margin above 0.25% is flagged. The key calls 0.18% and 0.25% fine
# (statements 02 and 11) and 0.55% a bad price (statement 08).
_LONG_TERMINAL_MONTHS = 18
_MARGIN_FLAG_ABOVE = Decimal("0.0025")


def check(statement: dict, price_table: dict | None = None) -> dict:
    """Return the same result for the same statement.

    Expected keys, all optional: total_sales, total_charges, agreed_rate,
    charged_rate, annual_card_turnover, headline_rate, bands, acquirer_margin,
    terminal_contract_months, minimum_monthly_charge, upcoming_rate, and
    fee_lines (a list of {name, amount}).

    Effective rate is total charges divided by total card sales.
    The price table's observed averages are not a fair price, so yearly_gap
    stays empty and the verdict stays incomplete.
    """
    table = load_price_table() if price_table is None else price_table
    findings: list[dict] = []
    findings.extend(_total_findings(statement))
    findings.extend(_small_fee_findings(statement))
    findings.extend(_duplicate_findings(statement))
    findings.extend(_penalty_findings(statement))
    findings.extend(_plan_findings(statement))
    findings.extend(_contract_findings(statement))
    findings.extend(_margin_findings(statement))
    findings.extend(_upcoming_rate_findings(statement))
    findings.extend(_rate_findings(statement))
    return {
        "effective_rate": _effective_rate(statement),
        "yearly_gap": None,
        "verdict": "incomplete",
        "observed_comparison": compare_with_observed_average(statement, table),
        "findings": findings,
    }


def _effective_rate(statement: dict) -> float | None:
    sales = _decimal(statement.get("total_sales"))
    charges = _decimal(statement.get("total_charges"))
    if sales is None or charges is None or sales == 0:
        return None
    return float(charges / sales)


def _total_findings(statement: dict) -> list[dict]:
    if "fee_lines" not in statement:
        return []
    lines = statement.get("fee_lines")
    if not isinstance(lines, list):
        return [
            {
                "code": "lines_cannot_be_summed",
                "summary": "Fee lines were not a list, so they were not added up.",
            }
        ]
    if "total_charges" not in statement:
        return []
    stated = _decimal(statement.get("total_charges"))
    if stated is None:
        return [
            {
                "code": "lines_cannot_be_summed",
                "summary": "The stated charge total could not be read, so the lines were not added up.",
            }
        ]

    amounts: list[Decimal] = []
    unread: list[str] = []
    for index, line in enumerate(lines, start=1):
        amount, label = _line_amount(line, index)
        if amount is None:
            unread.append(label)
        else:
            amounts.append(amount)
    if unread:
        return [
            {
                "code": "lines_cannot_be_summed",
                "summary": "These fee lines have no readable amount: " + ", ".join(unread) + ".",
                "lines": unread,
            }
        ]

    stated_q = stated.quantize(_MONEY, rounding=ROUND_HALF_UP)
    line_sum = sum(amounts, Decimal("0")).quantize(_MONEY, rounding=ROUND_HALF_UP)
    if stated_q == line_sum:
        return []
    difference = line_sum - stated_q
    return [
        {
            "code": "lines_do_not_add_up",
            "summary": (
                f"Fee lines sum to {_pounds(line_sum)} and the statement total is {_pounds(stated_q)}."
            ),
            "stated_total": _pounds(stated_q),
            "line_sum": _pounds(line_sum),
            "difference": _pounds(difference),
        }
    ]


def _small_fee_findings(statement: dict) -> list[dict]:
    lines = statement.get("fee_lines")
    if not isinstance(lines, list):
        return []

    grouped: dict[str, list[dict]] = {code: [] for code, _label, _phrases in _SMALL_FEES}
    for line in lines:
        if not isinstance(line, dict):
            continue
        matched = _match(line.get("name"), _SMALL_FEES)
        if matched is not None:
            grouped[matched[0]].append(line)

    findings: list[dict] = []
    present: list[str] = []
    for code, label, _phrases in _SMALL_FEES:
        group = grouped[code]
        if not group:
            continue
        present.append(code)
        if len(group) < 2:
            continue
        names, amounts = _names_and_amounts(group)
        findings.append(
            {
                "code": "repeated_small_fee",
                "summary": f"{label} appears {len(group)} times.",
                "category": code,
                "count": len(group),
                "names": names,
                "amounts": amounts,
            }
        )
    if len(present) >= 2:
        labels = [label for code, label, _phrases in _SMALL_FEES if code in present]
        findings.append(
            {
                "code": "stacked_small_fees",
                "summary": "Small fees are stacked: " + _join_labels(labels) + ".",
                "categories": present,
            }
        )
    return findings


def _penalty_findings(statement: dict) -> list[dict]:
    lines = statement.get("fee_lines")
    if not isinstance(lines, list):
        return []
    findings: list[dict] = []
    for line in lines:
        if not isinstance(line, dict):
            continue
        matched = _match(line.get("name"), _PENALTIES)
        if matched is None:
            continue
        kind, label, _phrases, note = matched
        amount = _decimal(line.get("amount"))
        name = line.get("name") if isinstance(line.get("name"), str) else label
        if amount is None:
            summary = f"{label} fee is charged and its amount was not read. {note}"
            shown = None
        else:
            summary = f"{label} fee of {_pounds(amount)} is charged. {note}"
            shown = _pounds(amount)
        findings.append(
            {
                "code": "penalty_fee",
                "summary": summary,
                "kind": kind,
                "name": name,
                "amount": shown,
                "avoidable": True,
            }
        )
    return findings


def _rate_findings(statement: dict) -> list[dict]:
    if "agreed_rate" not in statement or "charged_rate" not in statement:
        return []
    agreed = _decimal(statement.get("agreed_rate"))
    charged = _decimal(statement.get("charged_rate"))
    if agreed is None or charged is None:
        return []
    difference = charged - agreed
    if abs(difference) <= _RATE_TOLERANCE:
        return []
    finding = {
        "code": "charged_rate_differs",
        "summary": (
            f"Charged rate {_rate_text(charged)} differs from the agreed rate {_rate_text(agreed)}."
        ),
        "agreed_rate": _rate_text(agreed),
        "charged_rate": _rate_text(charged),
        "difference": _rate_text(difference),
    }
    sales = _decimal(statement.get("total_sales"))
    if sales is not None and sales > 0:
        monthly = difference * sales
        finding["monthly_difference"] = _pounds(monthly)
        finding["yearly_difference"] = _pounds(monthly * 12)
        finding["summary"] = (
            f"Charged rate {_percent(charged)} differs from the agreed rate {_percent(agreed)}. "
            f"On this month's card sales that is £{_pounds(monthly)} "
            f"(£{_pounds(monthly * 12)} a year)."
        )
    return [finding]


def _duplicate_findings(statement: dict) -> list[dict]:
    lines = statement.get("fee_lines")
    if not isinstance(lines, list):
        return []
    grouped: dict[str, list[dict]] = {}
    order: list[str] = []
    for line in lines:
        if not isinstance(line, dict):
            continue
        key = _normalise(line.get("name"))
        if not key:
            continue
        if key not in grouped:
            grouped[key] = []
            order.append(key)
        grouped[key].append(line)
    findings = []
    for key in order:
        group = grouped[key]
        if len(group) < 2:
            continue
        names, amounts = _names_and_amounts(group)
        findings.append(
            {
                "code": "duplicate_fee",
                "summary": f"{names[0]} appears {len(group)} times.",
                "name": names[0],
                "count": len(group),
                "names": names,
                "amounts": amounts,
            }
        )
    return findings


def _plan_findings(statement: dict) -> list[dict]:
    findings: list[dict] = []
    headline = _decimal(statement.get("headline_rate"))
    if headline is not None:
        findings.append(
            {
                "code": "plan_flat",
                "summary": f"One flat rate of {_percent(headline)} is charged on card sales.",
                "rate": _rate_text(headline),
            }
        )
    bands = statement.get("bands")
    if not isinstance(bands, list):
        return findings
    priced = []
    for band in bands:
        if not isinstance(band, dict):
            continue
        rate = _decimal(band.get("rate"))
        if rate is not None:
            priced.append((rate, band))
    if len(priced) < 2:
        return findings
    rate, band = max(priced, key=lambda item: item[0])
    sales = _decimal(band.get("sales"))
    payments = band.get("payments")
    name = band.get("name") if isinstance(band.get("name"), str) else "Top band"
    sales_text = f" on £{_pounds(sales)}" if sales is not None else ""
    payment_text = f" ({payments} payments)" if isinstance(payments, int) else ""
    finding = {
        "code": "tier_top_band",
        "summary": f"{name} is the top band at {_percent(rate)}{sales_text}{payment_text}.",
        "name": name,
        "rate": _rate_text(rate),
    }
    if sales is not None:
        finding["sales"] = _pounds(sales)
    if isinstance(payments, int):
        finding["payments"] = payments
    amount = _decimal(band.get("amount"))
    if amount is not None:
        finding["amount"] = _pounds(amount)
    findings.append(finding)
    return findings


def _contract_findings(statement: dict) -> list[dict]:
    findings: list[dict] = []
    months = _decimal(statement.get("terminal_contract_months"))
    if months is not None and months > _LONG_TERMINAL_MONTHS:
        shown = int(months) if months == int(months) else months
        findings.append(
            {
                "code": "long_terminal_contract",
                "summary": (
                    f"Terminal hire is {shown} months. "
                    f"The rule of thumb is {_LONG_TERMINAL_MONTHS} months."
                ),
                "months": int(months) if months == int(months) else _rate_text(months),
                "limit_months": _LONG_TERMINAL_MONTHS,
            }
        )
    minimum = statement.get("minimum_monthly_charge")
    if isinstance(minimum, dict):
        top_up = _decimal(minimum.get("top_up"))
        floor = _decimal(minimum.get("minimum"))
        processing = _decimal(minimum.get("processing_fees"))
        if top_up is not None and top_up > 0 and floor is not None and processing is not None:
            findings.append(
                {
                    "code": "minimum_monthly_charge",
                    "summary": (
                        f"A £{_pounds(top_up)} top-up brings processing fees of "
                        f"£{_pounds(processing)} up to the £{_pounds(floor)} monthly minimum."
                    ),
                    "minimum": _pounds(floor),
                    "processing_fees": _pounds(processing),
                    "top_up": _pounds(top_up),
                }
            )
    return findings


def _margin_findings(statement: dict) -> list[dict]:
    margin = _decimal(statement.get("acquirer_margin"))
    if margin is None or margin <= _MARGIN_FLAG_ABOVE:
        return []
    amount = _service_charge_amount(statement)
    amount_text = f" (£{_pounds(amount)} this month)" if amount is not None else ""
    finding = {
        "code": "acquirer_margin",
        "summary": f"Acquirer margin is {_percent(margin)}{amount_text}.",
        "rate": _rate_text(margin),
    }
    if amount is not None:
        finding["amount"] = _pounds(amount)
    return [finding]


def _upcoming_rate_findings(statement: dict) -> list[dict]:
    change = statement.get("upcoming_rate")
    if not isinstance(change, dict):
        return []
    old = _decimal(change.get("from_rate"))
    new = _decimal(change.get("to_rate"))
    if old is None or new is None or new <= old:
        return []
    date = change.get("effective_date")
    date_text = date if isinstance(date, str) and date else "a later date"
    finding = {
        "code": "upcoming_rate",
        "summary": f"Processing rate rises from {_percent(old)} to {_percent(new)} on {date_text}.",
        "from_rate": _rate_text(old),
        "to_rate": _rate_text(new),
        "effective_date": date_text,
    }
    sales = _decimal(statement.get("total_sales"))
    if sales is not None and sales > 0:
        monthly = (new - old) * sales
        finding["monthly_difference"] = _pounds(monthly)
        finding["yearly_difference"] = _pounds(monthly * 12)
        finding["summary"] = (
            f"Processing rate rises from {_percent(old)} to {_percent(new)} on {date_text}. "
            f"On this month's card sales that is £{_pounds(monthly)} more a month "
            f"(£{_pounds(monthly * 12)} a year)."
        )
    return [finding]


def _service_charge_amount(statement: dict) -> Decimal | None:
    lines = statement.get("fee_lines")
    if not isinstance(lines, list):
        return None
    for line in lines:
        if isinstance(line, dict) and "service charge" in _normalise(line.get("name")):
            return _decimal(line.get("amount"))
    return None


def _percent(rate: Decimal) -> str:
    return f"{(rate * 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):.2f}%"


def _line_amount(line: object, index: int) -> tuple[Decimal | None, str]:
    if not isinstance(line, dict):
        return None, f"line {index}"
    name = line.get("name")
    label = name.strip() if isinstance(name, str) and name.strip() else f"line {index}"
    return _decimal(line.get("amount")), label


def _names_and_amounts(group: list[dict]) -> tuple[list[str], list[str | None]]:
    names: list[str] = []
    amounts: list[str | None] = []
    for line in group:
        name = line.get("name")
        names.append(name if isinstance(name, str) else "")
        amount = _decimal(line.get("amount"))
        amounts.append(_pounds(amount) if amount is not None else None)
    return names, amounts


def _match(name: object, table: tuple) -> tuple | None:
    normalised = _normalise(name)
    if not normalised:
        return None
    for item in table:
        phrases = item[2]
        if any(phrase in normalised for phrase in phrases):
            return item
    return None


def _normalise(name: object) -> str:
    if not isinstance(name, str):
        return ""
    text = name.lower()
    for separator in ("-", "_", "/", "&"):
        text = text.replace(separator, " ")
    return " ".join(text.split())


def _join_labels(labels: list[str]) -> str:
    if len(labels) == 2:
        return f"{labels[0]} and {labels[1]}"
    return ", ".join(labels[:-1]) + ", and " + labels[-1]


def _decimal(value: object) -> Decimal | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float, Decimal)):
        text = format(value, "f") if isinstance(value, float) else str(value)
    elif isinstance(value, str) and _PLAIN_DECIMAL.fullmatch(value.strip()):
        text = value.strip()
    else:
        return None
    try:
        number = Decimal(text)
    except InvalidOperation:
        return None
    if not number.is_finite():
        return None
    return number


def _pounds(amount: Decimal) -> str:
    return f"{amount.quantize(_MONEY, rounding=ROUND_HALF_UP):.2f}"


def _rate_text(rate: Decimal) -> str:
    text = format(rate, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


