"""Plain checks on an already-read statement. No model calls."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

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


def check(statement: dict) -> dict:
    """Return the same result for the same statement.

    Expected keys, all optional: total_sales, total_charges, agreed_rate,
    charged_rate, and fee_lines (a list of {name, amount}).

    Effective rate is total charges divided by total card sales.
    Yearly gap stays empty until the price table has a dated fair rate,
    so the verdict stays incomplete even when findings are present.
    """
    findings: list[dict] = []
    findings.extend(_total_findings(statement))
    findings.extend(_small_fee_findings(statement))
    findings.extend(_penalty_findings(statement))
    findings.extend(_rate_findings(statement))
    return {
        "effective_rate": _effective_rate(statement),
        "yearly_gap": None,
        "verdict": "incomplete",
        "findings": findings,
    }


def _effective_rate(statement: dict) -> float | None:
    sales = statement.get("total_sales")
    charges = statement.get("total_charges")
    if not _is_number(sales) or not _is_number(charges) or not sales:
        return None
    return charges / sales


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
    return [
        {
            "code": "charged_rate_differs",
            "summary": (
                f"Charged rate {_rate_text(charged)} differs from the agreed rate {_rate_text(agreed)}."
            ),
            "agreed_rate": _rate_text(agreed),
            "charged_rate": _rate_text(charged),
            "difference": _rate_text(difference),
        }
    ]


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


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)
