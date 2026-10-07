"""Checks for lab, energy, supplies, and service documents. No model calls.

Price-list comparisons stay out until a list has a source and a date.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

_MONEY = Decimal("0.01")
_PENNY = Decimal("0.01")
_PERCENT = Decimal("0.01")
_PLAIN_DECIMAL = __import__("re").compile(r"^-?\d+(\.\d+)?$")

# Product rule from the one-page summary: renewals inside 90 days.
_RENEWAL_WINDOW_DAYS = 90

# Value Added Tax Act 1994, Schedule 9, Group 7, item 2A, inserted by
# S.I. 2007/206. legislation.gov.uk text current to 30 June 2026.
_VAT_SOURCE = (
    "Value Added Tax Act 1994, Schedule 9, Group 7, item 2A exempts "
    "the supply of any services or dental prostheses by a dental technician."
)


def check_bill(document: dict) -> dict:
    """Check one hand-typed bill. The verdict stays incomplete.

    There is no fair price list for these documents, so yearly_gap stays empty
    even when a finding has a pound figure taken from the document itself.
    """
    kind = document.get("kind")
    findings: list[dict] = []
    findings.extend(_multiplication_findings(document))
    findings.extend(_total_findings(document))
    if kind == "lab":
        findings.extend(_duplicate_case_findings(document))
        findings.extend(_remake_findings(document))
        findings.extend(_lab_vat_findings(document))
        findings.extend(_courier_findings(document))
        findings.extend(_surcharge_findings(document))
        findings.extend(_price_rise_findings(document))
    elif kind == "energy":
        findings.extend(_energy_findings(document))
    elif kind == "supplies":
        findings.extend(_supplies_findings(document))
    elif kind == "service":
        findings.extend(_service_findings(document))
    return {"yearly_gap": None, "verdict": "incomplete", "findings": findings}


def _multiplication_findings(document: dict) -> list[dict]:
    findings = []
    vat_rate = _vat_rate(document)
    for line in _lines(document):
        quantity = _decimal(line.get("quantity"))
        unit = _decimal(line.get("unit_price"))
        amount = _decimal(line.get("amount"))
        if quantity is None or unit is None or amount is None:
            continue
        expected = (quantity * unit).quantize(_MONEY, rounding=ROUND_HALF_UP)
        billed = amount.quantize(_MONEY, rounding=ROUND_HALF_UP)
        if expected == billed:
            continue
        difference = billed - expected
        name = _name(line)
        finding = {
            "code": "line_does_not_multiply",
            "summary": (
                f"{_number(quantity)} x £{_pounds(unit)} is £{_pounds(expected)}, "
                f"billed £{_pounds(billed)}."
            ),
            "name": name,
            "quantity": _number(quantity),
            "unit_price": _pounds(unit),
            "expected": _pounds(expected),
            "billed": _pounds(billed),
            "difference": _pounds(difference),
        }
        if vat_rate is not None:
            with_vat = difference * (1 + vat_rate)
            finding["difference_with_vat"] = _pounds(with_vat)
            finding["summary"] = (
                f"{_number(quantity)} x £{_pounds(unit)} is £{_pounds(expected)}, "
                f"billed £{_pounds(billed)}. "
                f"The £{_pounds(difference)} difference plus VAT is £{_pounds(with_vat)}."
            )
        findings.append(finding)
    return findings


def _total_findings(document: dict) -> list[dict]:
    amounts = []
    for line in _lines(document):
        amount = _decimal(line.get("amount"))
        if amount is None:
            return []
        amounts.append(amount)
    if not amounts:
        return []
    net = _decimal(document.get("net"))
    if net is None:
        return []
    line_sum = sum(amounts, Decimal("0")).quantize(_MONEY, rounding=ROUND_HALF_UP)
    stated = net.quantize(_MONEY, rounding=ROUND_HALF_UP)
    findings = []
    if line_sum != stated:
        findings.append(
            {
                "code": "lines_do_not_add_up",
                "summary": (
                    f"Lines sum to £{_pounds(line_sum)} and the stated net is £{_pounds(stated)}."
                ),
                "line_sum": _pounds(line_sum),
                "net": _pounds(stated),
                "difference": _pounds(line_sum - stated),
            }
        )
    vat = _vat_amount(document)
    total = _decimal(document.get("total"))
    if vat is not None and total is not None:
        expected_total = (stated + vat).quantize(_MONEY, rounding=ROUND_HALF_UP)
        billed_total = total.quantize(_MONEY, rounding=ROUND_HALF_UP)
        if expected_total != billed_total:
            findings.append(
                {
                    "code": "total_does_not_add_up",
                    "summary": (
                        f"Net £{_pounds(stated)} plus VAT £{_pounds(vat)} is £{_pounds(expected_total)}, "
                        f"and the stated total is £{_pounds(billed_total)}."
                    ),
                    "expected": _pounds(expected_total),
                    "total": _pounds(billed_total),
                }
            )
    return findings


def _duplicate_case_findings(document: dict) -> list[dict]:
    grouped: dict[tuple[str, str], list[dict]] = {}
    order: list[tuple[str, str]] = []
    for line in _lines(document):
        case_ref = line.get("case_ref")
        if not isinstance(case_ref, str) or not case_ref.strip():
            continue
        key = (case_ref.strip(), _normalise(_name(line)))
        if key not in grouped:
            grouped[key] = []
            order.append(key)
        grouped[key].append(line)
    findings = []
    for case_ref, item_key in order:
        group = grouped[(case_ref, item_key)]
        if len(group) < 2:
            continue
        extra = _decimal(group[-1].get("amount"))
        item = _name(group[0])
        extra_text = f", £{_pounds(extra)} too much" if extra is not None else ""
        finding = {
            "code": "duplicate_case",
            "summary": f"Case {case_ref} {item} is billed {len(group)} times{extra_text}.",
            "case_ref": case_ref,
            "name": item,
            "count": len(group),
        }
        if extra is not None:
            finding["extra_amount"] = _pounds(extra)
        findings.append(finding)
    return findings


def _remake_findings(document: dict) -> list[dict]:
    window = _decimal(document.get("remake_free_within_days"))
    invoice = _date(document.get("invoice_date"))
    if window is None or invoice is None:
        return []
    findings = []
    for line in _lines(document):
        if not line.get("remake"):
            continue
        delivered = _date(line.get("original_delivered"))
        amount = _decimal(line.get("amount"))
        if delivered is None or amount is None:
            continue
        days = (invoice - delivered).days
        if days < 0 or days > window:
            continue
        findings.append(
            {
                "code": "remake_inside_free_window",
                "summary": (
                    f"Remake of {_name(line).removeprefix('Remake: ')} is charged £{_pounds(amount)}. "
                    f"The lab's terms say remakes within {_number(window)} days of delivery are free, "
                    f"and the original was delivered on {_spoken_date(delivered)}, "
                    f"{days} days before this invoice."
                ),
                "name": _name(line),
                "amount": _pounds(amount),
                "days": days,
                "free_within_days": int(window),
                "original_delivered": delivered.isoformat(),
            }
        )
    return findings


def _lab_vat_findings(document: dict) -> list[dict]:
    amount = _vat_amount(document)
    if amount is None or amount <= 0:
        return []
    return [
        {
            "code": "vat_charged_on_dental_work",
            "summary": (
                f"VAT of £{_pounds(amount)} is charged on this lab work. {_VAT_SOURCE} "
                "Ask the lab why VAT was charged."
            ),
            "amount": _pounds(amount),
            "source": _VAT_SOURCE,
        }
    ]


def _courier_findings(document: dict) -> list[dict]:
    findings = []
    for line in _lines(document):
        if "courier" not in _normalise(_name(line)):
            continue
        amount = _decimal(line.get("amount"))
        if amount is None or amount <= 0:
            continue
        findings.append(
            {
                "code": "courier_charged",
                "summary": f"Courier is charged at £{_pounds(amount)}.",
                "name": _name(line),
                "amount": _pounds(amount),
            }
        )
    return findings


def _surcharge_findings(document: dict) -> list[dict]:
    findings = []
    for line in _lines(document):
        if "surcharge" not in _normalise(_name(line)):
            continue
        amount = _decimal(line.get("amount"))
        if amount is None or amount <= 0:
            continue
        findings.append(
            {
                "code": "surcharge",
                "summary": f"{_name(line)} is £{_pounds(amount)} on top of the unit prices.",
                "name": _name(line),
                "amount": _pounds(amount),
            }
        )
    return findings


def _price_rise_findings(document: dict) -> list[dict]:
    rise = document.get("price_rise")
    if not isinstance(rise, dict):
        return []
    percent = _decimal(rise.get("percent"))
    if percent is None or percent <= 0:
        return []
    base = Decimal("0")
    for line in _lines(document):
        if line.get("excluded_from_rise"):
            continue
        amount = _decimal(line.get("amount"))
        if amount is not None:
            base += amount
    if base <= 0:
        return []
    monthly = (base * percent).quantize(_MONEY, rounding=ROUND_HALF_UP)
    when = rise.get("from_date") if isinstance(rise.get("from_date"), str) else "a later date"
    return [
        {
            "code": "price_rise",
            "summary": (
                f"Prices rise by {_percent(percent)} from {when}. "
                f"On this invoice's work of £{_pounds(base)}, that is £{_pounds(monthly)} more a month "
                f"(£{_pounds(monthly * 12)} a year at the same volume)."
            ),
            "percent": _rate_text(percent),
            "from_date": when,
            "base": _pounds(base),
            "monthly_difference": _pounds(monthly),
            "yearly_difference": _pounds(monthly * 12),
        }
    ]


def _energy_findings(document: dict) -> list[dict]:
    findings = []
    contract = document.get("contract") if isinstance(document.get("contract"), dict) else {}
    status = contract.get("status")
    electricity = _electricity_line(document)
    rate = _decimal(electricity.get("rate_pence")) if electricity else None
    kwh = _decimal(electricity.get("quantity")) if electricity else None
    as_of = _date(document.get("bill_date"))

    if status == "out_of_contract":
        since = contract.get("since") if isinstance(contract.get("since"), str) else "an earlier date"
        rate_text = f" of {_pence(rate)} per kWh" if rate is not None else ""
        findings.append(
            {
                "code": "out_of_contract",
                "summary": f"Out of contract since {since}, on deemed rates{rate_text}.",
                "since": since,
                "rate_pence": _pence(rate) if rate is not None else None,
            }
        )
    elif status == "rollover":
        started = contract.get("started") if isinstance(contract.get("started"), str) else "the rollover date"
        previous = contract.get("previous_end")
        previous_text = f"The fixed contract ended on {previous} and renewed automatically" if previous else "The supply renewed automatically"
        rate_text = f" onto a rollover tariff of {_pence(rate)} per kWh" if rate is not None else ""
        findings.append(
            {
                "code": "rolled_over",
                "summary": f"{previous_text}{rate_text} from {started}.",
                "started": started,
                "previous_end": previous,
                "rate_pence": _pence(rate) if rate is not None else None,
            }
        )
    elif status == "fixed":
        ends = _date(contract.get("ends"))
        rollover = _decimal(contract.get("rollover_rate_pence"))
        if ends is not None and as_of is not None and 0 <= (ends - as_of).days <= _RENEWAL_WINDOW_DAYS:
            finding = {
                "code": "contract_ending",
                "summary": f"The fixed contract ends on {_spoken_date(ends)}.",
                "ends": ends.isoformat(),
                "days_left": (ends - as_of).days,
            }
            if rate is not None and rollover is not None and kwh is not None:
                monthly = (kwh * (rollover - rate) / Decimal("100")).quantize(_MONEY, rounding=ROUND_HALF_UP)
                finding["current_rate_pence"] = _pence(rate)
                finding["rollover_rate_pence"] = _pence(rollover)
                finding["monthly_difference"] = _pounds(monthly)
                finding["yearly_difference"] = _pounds(monthly * 12)
                finding["summary"] = (
                    f"The fixed contract ends on {_spoken_date(ends)}. "
                    f"If it rolls over, the rate rises from {_pence(rate)} to {_pence(rollover)} per kWh, "
                    f"£{_pounds(monthly)} more on this month's {_number(kwh)} kWh "
                    f"(£{_pounds(monthly * 12)} a year at the same use)."
                )
            findings.append(finding)

    meter = document.get("meter") if isinstance(document.get("meter"), dict) else {}
    if meter.get("kind") == "estimated":
        last_actual = meter.get("last_actual") if isinstance(meter.get("last_actual"), str) else None
        when = f" The last actual reading was {last_actual}." if last_actual else ""
        findings.append(
            {
                "code": "estimated_reading",
                "summary": f"Readings are estimated.{when}",
                "last_actual": last_actual,
            }
        )
    return findings


def _supplies_findings(document: dict) -> list[dict]:
    goods = Decimal("0")
    extras = Decimal("0")
    for line in _lines(document):
        amount = _decimal(line.get("amount"))
        if amount is None:
            continue
        if line.get("extra"):
            extras += amount
        else:
            goods += amount
    threshold = _decimal(document.get("free_extras_over"))
    if extras <= 0 or goods <= 0 or threshold is None or goods >= threshold:
        return []
    share = (extras / goods * 100).quantize(_PERCENT, rounding=ROUND_HALF_UP)
    return [
        {
            "code": "small_order_extras",
            "summary": (
                f"Surcharge and delivery are £{_pounds(extras)} on £{_pounds(goods)} of goods "
                f"({share:.2f}%). The invoice says orders of £{_pounds(threshold)} or more avoid them."
            ),
            "extras": _pounds(extras),
            "goods": _pounds(goods),
            "share_percent": f"{share:.2f}",
            "free_over": _pounds(threshold),
        }
    ]


def _service_findings(document: dict) -> list[dict]:
    findings = []
    renewal = document.get("renewal") if isinstance(document.get("renewal"), dict) else None
    if renewal is not None:
        rises = []
        for line in _lines(document):
            old = _decimal(line.get("was"))
            new = _decimal(line.get("amount"))
            if old is None or new is None or new <= old:
                continue
            rises.append((old, new))
        if rises:
            old, new = rises[0]
            increase = sum((new_amount - old_amount) for old_amount, new_amount in rises)
            percent = ((new - old) / old * 100).quantize(_PERCENT, rounding=ROUND_HALF_UP)
            renews = renewal.get("renews_on") if isinstance(renewal.get("renews_on"), str) else "the renewal date"
            cancel = renewal.get("cancel_by") if isinstance(renewal.get("cancel_by"), str) else "the cancellation date"
            findings.append(
                {
                    "code": "renewal_price_rise",
                    "summary": (
                        f"Each plan rises from £{_pounds(old)} to £{_pounds(new)} ({percent:.2f}%). "
                        f"{len(rises)} plans cost £{_pounds(increase)} more a month before VAT. "
                        f"The plan renews on {renews} unless cancelled in writing by {cancel}."
                    ),
                    "from_amount": _pounds(old),
                    "to_amount": _pounds(new),
                    "percent": f"{percent:.2f}",
                    "monthly_difference": _pounds(increase),
                    "plans": len(rises),
                    "renews_on": renews,
                    "cancel_by": cancel,
                }
            )
    for line in _lines(document):
        removed = _date(line.get("decommissioned_on"))
        amount = _decimal(line.get("amount"))
        invoice = _date(document.get("invoice_date"))
        if removed is None or amount is None or amount <= 0:
            continue
        finding = {
            "code": "decommissioned_equipment",
            "summary": (
                f"{_name(line)} was decommissioned on {_spoken_date(removed)} "
                f"and this invoice still charges £{_pounds(amount)}."
            ),
            "name": _name(line),
            "amount": _pounds(amount),
            "decommissioned_on": removed.isoformat(),
        }
        if invoice is not None:
            start = _next_month(removed)
            if invoice >= start:
                months = (invoice.year - start.year) * 12 + (invoice.month - start.month) + 1
                since = amount * months
                finding["months_since"] = months
                finding["amount_since"] = _pounds(since)
                finding["yearly_if_it_continues"] = _pounds(amount * 12)
                finding["summary"] = (
                    f"{_name(line)} was decommissioned on {_spoken_date(removed)} "
                    f"and this invoice still charges £{_pounds(amount)}. "
                    f"{_month_name(start)} to {_month_name(invoice)} is {months} months, "
                    f"£{_pounds(since)} if billed each month. "
                    f"Continuing the charge is £{_pounds(amount * 12)} a year."
                )
        findings.append(finding)
    return findings


def _lines(document: dict) -> list[dict]:
    lines = document.get("lines")
    if not isinstance(lines, list):
        return []
    return [line for line in lines if isinstance(line, dict)]


def _electricity_line(document: dict) -> dict | None:
    for line in _lines(document):
        if "electricity used" in _normalise(_name(line)):
            return line
    return None


def _vat_amount(document: dict) -> Decimal | None:
    vat = document.get("vat")
    if isinstance(vat, dict):
        return _decimal(vat.get("amount"))
    return _decimal(vat)


def _vat_rate(document: dict) -> Decimal | None:
    vat = document.get("vat")
    if isinstance(vat, dict):
        return _decimal(vat.get("rate"))
    return None


def _name(line: dict) -> str:
    name = line.get("name")
    return name if isinstance(name, str) else "Line"


def _normalise(name: str) -> str:
    return " ".join(name.lower().replace("-", " ").split())


def _next_month(day: date) -> date:
    if day.day == 1:
        return day
    if day.month == 12:
        return date(day.year + 1, 1, 1)
    return date(day.year, day.month + 1, 1)


def _month_name(day: date) -> str:
    return day.strftime("%B")


def _spoken_date(day: date) -> str:
    return f"{day.day} {day.strftime('%b %Y')}"


def _date(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _decimal(value: object) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, Decimal)):
        number = Decimal(value)
    elif isinstance(value, float):
        number = Decimal(format(value, "f"))
    elif isinstance(value, str) and _PLAIN_DECIMAL.fullmatch(value.strip()):
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


def _pence(amount: Decimal) -> str:
    return f"{amount.quantize(_PENNY, rounding=ROUND_HALF_UP):.2f}p"


def _percent(rate: Decimal) -> str:
    return f"{(rate * 100).quantize(_PERCENT, rounding=ROUND_HALF_UP):.0f}%"


def _number(value: Decimal) -> str:
    if value == int(value):
        return str(int(value))
    return format(value.normalize(), "f")


def _rate_text(rate: Decimal) -> str:
    text = format(rate, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"
