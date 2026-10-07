"""Turn one bill PDF into the fields the checkers already use.

The model copies printed figures. It does not add lines, multiply a row,
or decide whether a price is fair. A percent sign is stored as the decimal
the checkers already use: 1.75% becomes 0.0175. A price printed in pence
is stored in pounds so a later multiplication uses one unit.
"""

from __future__ import annotations

import base64
import json
import os
import re
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

# Claude API model id from platform.claude.com/docs/en/models/overview.
MODEL = "claude-sonnet-5-5"

_MONEY = Decimal("0.01")
_PLAIN = re.compile(r"-?\d+(\.\d+)?$")
_MONTHS = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}
_SUMMARY_LINES = {
    "total",
    "total charges",
    "total due",
    "subtotal",
    "net",
    "net charges",
    "amount",
}

_SYSTEM = """You copy figures from one UK dental-practice bill. You do not add, multiply, divide, or judge prices.

Copy each printed number into the matching field. Leave a string empty when the page does not print it. Use false for a flag the page does not state. Add a short note to unreadable when a figure is blank, cut off, or ambiguous.

Ignore the sample watermark. Copy the stated total even when the lines do not reach it. Keep a repeated line twice. Do not invent a line that would make the total match.

Rates keep the printed percent sign, such as 1.75% or 0.18%. Dates are YYYY-MM-DD. Pound amounts stay in pounds, such as 245.00 or 1132.50. A unit price printed in pence, such as 39.20p or 0.801p, goes in unit_price_pence and unit_price stays empty.

Do not work out a missing amount from quantity times price. Do not work out a rate from charges divided by sales."""

_USER = """Copy this document.

kind is card for a card-processing statement, lab for a laboratory invoice, energy for an energy bill, supplies for a consumables invoice, or service for an equipment service plan.

On a card statement, fee_lines are the charge rows only. Skip the total row. If one charge says it comes from a table above, copy that one charge and do not also copy the table rows. A card-mix table or an interchange-by-card-type table is not bands. bands are only the acquirer's own pricing bands, such as Qualified and Non-qualified.

headline_rate is the flat percentage applied to card sales on the processing line. agreed_rate is a signed or agreed percentage only when the page prints one. charged_rate is the percentage on the processing line only when an agreed rate is also printed. acquirer_margin is the percentage on the line named as the acquirer's own service charge, such as "Our service charge". Leave it empty on a flat or tiered plan. Do not use the scheme-fee percentage or an interchange percentage as the margin.

terminal_contract_months is the printed hire term in months. minimum_monthly, minimum_processing_fees, and minimum_top_up are the three printed minimum-charge figures. upcoming_from_rate and upcoming_to_rate are a future processing-rate change printed on the page.

On a lab, energy, supplies, or service document, lines are the item rows. Skip subtotal, VAT, and total rows. VAT goes in vat_rate and vat_amount. A VAT-exempt invoice with £0.00 VAT uses vat_rate 0% and vat_amount 0.00.

A line whose text says remake has remake true. original_delivered and remake_free_within_days come from the printed guarantee. price_rise_percent is a printed future percentage rise. A courier line is excluded_from_rise when that rise is printed.

On energy, document_date is the last day of the bill period. contract_status is out_of_contract, fixed, or rollover from the printed words. rollover_rate_pence is a future rollover price in pence. meter_kind is estimated when the bill says the reading is estimated, and actual otherwise. meter_last_actual is the printed date of the last actual reading.

On supplies, extra is true for a small-order surcharge or a delivery charge. free_extras_over is the printed order value that drops those charges.

On a service plan, was is the previous price when the page prints one, and amount is the price charged now. renews_on and cancel_by are the printed dates. decommissioned_on is the printed date a machine was taken out of use."""


def _string() -> dict:
    return {"type": "string"}


def _object(properties: dict[str, dict]) -> dict:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(properties),
        "properties": properties,
    }


_FEE_LINE = _object({"name": _string(), "amount": _string()})
_BAND = _object(
    {
        "name": _string(),
        "payments": _string(),
        "sales": _string(),
        "rate": _string(),
        "amount": _string(),
    }
)
_BILL_LINE = _object(
    {
        "name": _string(),
        "case_ref": _string(),
        "quantity": _string(),
        "unit_price": _string(),
        "unit_price_pence": _string(),
        "amount": _string(),
        "remake": {"type": "boolean"},
        "original_delivered": _string(),
        "excluded_from_rise": {"type": "boolean"},
        "extra": {"type": "boolean"},
        "was": _string(),
        "decommissioned_on": _string(),
    }
)
_SCHEMA = _object(
    {
        "kind": {
            "type": "string",
            "enum": ["card", "lab", "energy", "supplies", "service", "unknown"],
        },
        "practice": _string(),
        "provider": _string(),
        "document_date": _string(),
        "unreadable": {"type": "array", "items": _string()},
        "total_sales": _string(),
        "total_charges": _string(),
        "transaction_count": _string(),
        "headline_rate": _string(),
        "agreed_rate": _string(),
        "charged_rate": _string(),
        "acquirer_margin": _string(),
        "terminal_contract_months": _string(),
        "minimum_monthly": _string(),
        "minimum_processing_fees": _string(),
        "minimum_top_up": _string(),
        "upcoming_from_rate": _string(),
        "upcoming_to_rate": _string(),
        "upcoming_date": _string(),
        "fee_lines": {"type": "array", "items": _FEE_LINE},
        "bands": {"type": "array", "items": _BAND},
        "net": _string(),
        "vat_rate": _string(),
        "vat_amount": _string(),
        "total": _string(),
        "lines": {"type": "array", "items": _BILL_LINE},
        "remake_free_within_days": _string(),
        "price_rise_percent": _string(),
        "price_rise_from": _string(),
        "contract_status": {
            "type": "string",
            "enum": ["", "out_of_contract", "fixed", "rollover"],
        },
        "contract_since": _string(),
        "contract_ends": _string(),
        "contract_started": _string(),
        "contract_previous_end": _string(),
        "rollover_rate_pence": _string(),
        "meter_kind": {"type": "string", "enum": ["", "actual", "estimated"]},
        "meter_last_actual": _string(),
        "free_extras_over": _string(),
        "renews_on": _string(),
        "cancel_by": _string(),
    }
)


def read(path: str | Path, *, complete=None) -> dict:
    """Read one local PDF into checker fields.

    complete, when passed, receives the PDF bytes and returns the raw
    extraction. The default calls Claude. The result is not written to disk.
    """
    file = Path(path)
    pdf = file.read_bytes()
    if not pdf.startswith(b"%PDF"):
        raise ValueError(f"{file} is not a PDF.")
    raw = complete(pdf) if complete is not None else _complete(pdf)
    return document_from_extraction(raw)


def document_from_extraction(raw: dict) -> dict:
    """Turn one model extraction into the checker document. No new figures."""
    if not isinstance(raw, dict):
        raise TypeError("The extraction was not an object.")
    notes = [note.strip() for note in _list(raw.get("unreadable")) if _text(note)]
    kind = _text(raw.get("kind")).lower()
    if kind not in {"card", "lab", "energy", "supplies", "service"}:
        return {
            "kind": "unknown",
            "unreadable": notes or ["The document kind could not be read."],
        }
    document = _card(raw, notes) if kind == "card" else _bill(kind, raw, notes)
    document["kind"] = kind
    document["unreadable"] = notes
    for key in ("practice", "provider"):
        value = _text(raw.get(key))
        if value:
            document[key] = value
    return document


def _card(raw: dict, notes: list[str]) -> dict:
    document: dict = {"fee_lines": _fee_lines(raw, notes)}
    _copy_money(document, raw, notes, "total_sales", "total_charges")
    count = _whole(_text(raw.get("transaction_count")))
    if count is not None:
        document["transaction_count"] = count
    _copy_rate(
        document,
        raw,
        notes,
        ("headline_rate", "headline_rate"),
        ("agreed_rate", "agreed_rate"),
        ("charged_rate", "charged_rate"),
        ("acquirer_margin", "acquirer_margin"),
    )
    months = _whole(_text(raw.get("terminal_contract_months")))
    if months is not None:
        document["terminal_contract_months"] = months
    minimum = _minimum(raw, notes)
    if minimum:
        document["minimum_monthly_charge"] = minimum
    _fill_minimum_processing(document)
    upcoming = _upcoming(raw, notes)
    if upcoming:
        document["upcoming_rate"] = upcoming
    bands = _bands(raw, notes)
    if bands:
        document["bands"] = bands
    when = _dated(raw, notes, "document_date")
    if when:
        document["statement_date"] = when
    return document


def _bill(kind: str, raw: dict, notes: list[str]) -> dict:
    document: dict = {"lines": _bill_lines(kind, raw, notes)}
    when = _dated(raw, notes, "document_date")
    if when:
        document["bill_date" if kind == "energy" else "invoice_date"] = when
    _copy_money(document, raw, notes, "net", "total")
    vat_amount = _put_money(raw, notes, "vat_amount")
    vat_rate = _put_rate(raw, notes, "vat_rate")
    if vat_amount is not None or vat_rate is not None:
        vat: dict = {}
        if vat_rate is not None:
            vat["rate"] = vat_rate
        if vat_amount is not None:
            vat["amount"] = vat_amount
        document["vat"] = vat
    window = _whole(_text(raw.get("remake_free_within_days")))
    if window is not None:
        document["remake_free_within_days"] = str(window)
    rise = _put_rate(raw, notes, "price_rise_percent")
    if rise is not None:
        change = {"percent": rise}
        start = _dated(raw, notes, "price_rise_from")
        if start:
            change["from_date"] = start
        document["price_rise"] = change
    _copy_energy(document, raw, notes)
    threshold = _put_money(raw, notes, "free_extras_over")
    if threshold is not None:
        document["free_extras_over"] = threshold
    renews = _dated(raw, notes, "renews_on")
    cancel = _dated(raw, notes, "cancel_by")
    if renews or cancel:
        renewal = {}
        if renews:
            renewal["renews_on"] = renews
        if cancel:
            renewal["cancel_by"] = cancel
        document["renewal"] = renewal
    return document


def _fee_lines(raw: dict, notes: list[str]) -> list[dict]:
    lines = []
    for item in _list(raw.get("fee_lines")):
        if not isinstance(item, dict):
            continue
        name = _text(item.get("name"))
        if not name or _is_summary(name):
            continue
        line = {"name": name}
        amount = _money(_text(item.get("amount")))
        if amount is None:
            notes.append(f"{name} has no readable amount.")
        else:
            line["amount"] = amount
        lines.append(line)
    return lines


def _bands(raw: dict, notes: list[str]) -> list[dict]:
    bands = []
    for item in _list(raw.get("bands")):
        if not isinstance(item, dict):
            continue
        name = _text(item.get("name"))
        if not name:
            continue
        band = {"name": name}
        payments = _whole(_text(item.get("payments")))
        if payments is not None:
            band["payments"] = payments
        sales = _money(_text(item.get("sales")))
        if sales is not None:
            band["sales"] = sales
        rate = _rate(_text(item.get("rate")))
        if rate is None and _text(item.get("rate")):
            notes.append(f"The rate for {name} could not be read.")
        elif rate is not None:
            band["rate"] = rate
        amount = _money(_text(item.get("amount")))
        if amount is not None:
            band["amount"] = amount
        bands.append(band)
    return bands


def _bill_lines(kind: str, raw: dict, notes: list[str]) -> list[dict]:
    rise = _rate(_text(raw.get("price_rise_percent")))
    lines = []
    for item in _list(raw.get("lines")):
        if not isinstance(item, dict):
            continue
        name = _text(item.get("name"))
        if not name or _is_summary(name) or _normalise(name).startswith("vat"):
            continue
        line: dict = {"name": name}
        case_ref = _text(item.get("case_ref"))
        if case_ref:
            line["case_ref"] = case_ref
        quantity = _quantity(_text(item.get("quantity")))
        if quantity is not None:
            line["quantity"] = quantity
        pence = _pence(_text(item.get("unit_price_pence")))
        pounds = _unit(_text(item.get("unit_price")))
        if pence is not None:
            line["unit_price"] = _pence_to_pounds(pence)
            if "electricity used" in _normalise(name):
                line["rate_pence"] = _pence_text(pence)
        elif pounds is not None:
            line["unit_price"] = pounds
        amount = _money(_text(item.get("amount")))
        if amount is None:
            notes.append(f"{name} has no readable amount.")
        else:
            line["amount"] = amount
        if "remake" in _normalise(name):
            line["remake"] = True
        delivered = _date(_text(item.get("original_delivered")))
        if delivered:
            line["original_delivered"] = delivered
        courier = "courier" in _normalise(name)
        if kind == "lab" and rise is not None and courier:
            line["excluded_from_rise"] = True
        if kind == "supplies" and any(word in _normalise(name) for word in ("surcharge", "delivery")):
            line["extra"] = True
        previous = _money(_text(item.get("was")))
        if previous is not None:
            line["was"] = previous
        removed = _decommissioned(name) or _date(_text(item.get("decommissioned_on")))
        if removed:
            line["decommissioned_on"] = removed
        lines.append(line)
    return lines


def _fill_minimum_processing(document: dict) -> None:
    """Use the printed processing-fee line when the minimum block omitted it."""
    minimum = document.get("minimum_monthly_charge")
    if not isinstance(minimum, dict) or minimum.get("processing_fees"):
        return
    if "minimum" not in minimum and "top_up" not in minimum:
        return
    for line in document.get("fee_lines") or []:
        if _normalise(line.get("name", "")) in {"processing fee", "processing charges"}:
            amount = line.get("amount")
            if amount:
                minimum["processing_fees"] = amount
            return


def _minimum(raw: dict, notes: list[str]) -> dict:
    found = {}
    for source, target in (
        ("minimum_monthly", "minimum"),
        ("minimum_processing_fees", "processing_fees"),
        ("minimum_top_up", "top_up"),
    ):
        amount = _put_money(raw, notes, source)
        if amount is not None:
            found[target] = amount
    return found


def _upcoming(raw: dict, notes: list[str]) -> dict:
    old = _put_rate(raw, notes, "upcoming_from_rate")
    new = _put_rate(raw, notes, "upcoming_to_rate")
    if old is None and new is None:
        return {}
    change = {}
    if old is not None:
        change["from_rate"] = old
    if new is not None:
        change["to_rate"] = new
    when = _dated(raw, notes, "upcoming_date")
    if when:
        change["effective_date"] = when
    return change


def _copy_energy(document: dict, raw: dict, notes: list[str]) -> None:
    status = _text(raw.get("contract_status")).lower()
    if status not in {"out_of_contract", "fixed", "rollover"}:
        if status:
            notes.append(f"Contract status {status} could not be read.")
        status = ""
    contract: dict = {}
    if status:
        contract["status"] = status
    since = _dated(raw, notes, "contract_since")
    ends = _dated(raw, notes, "contract_ends")
    started = _dated(raw, notes, "contract_started")
    previous = _dated(raw, notes, "contract_previous_end")
    if since:
        contract["since"] = since
    if ends:
        contract["ends"] = ends
    if started:
        contract["started"] = started
    if previous:
        contract["previous_end"] = previous
    rollover = _pence(_text(raw.get("rollover_rate_pence")))
    if rollover is not None:
        contract["rollover_rate_pence"] = _pence_text(rollover)
    elif _text(raw.get("rollover_rate_pence")):
        notes.append("The rollover rate could not be read.")
    if contract:
        document["contract"] = contract
    meter_kind = _text(raw.get("meter_kind")).lower()
    if meter_kind == "estimated":
        meter: dict = {"kind": "estimated"}
        last = _dated(raw, notes, "meter_last_actual")
        if last:
            meter["last_actual"] = last
        document["meter"] = meter


def _copy_money(document: dict, raw: dict, notes: list[str], *keys: str) -> None:
    for key in keys:
        amount = _put_money(raw, notes, key)
        if amount is not None:
            document[key] = amount


def _copy_rate(document: dict, raw: dict, notes: list[str], *pairs: tuple[str, str]) -> None:
    for source, target in pairs:
        rate = _put_rate(raw, notes, source)
        if rate is not None:
            document[target] = rate


def _put_money(raw: dict, notes: list[str], key: str) -> str | None:
    token = _text(raw.get(key))
    if not token:
        return None
    amount = _money(token)
    if amount is None:
        notes.append(f"{key} could not be read.")
    return amount


def _put_rate(raw: dict, notes: list[str], key: str) -> str | None:
    token = _text(raw.get(key))
    if not token:
        return None
    rate = _rate(token)
    if rate is None:
        notes.append(f"{key} could not be read.")
    return rate


def _dated(raw: dict, notes: list[str], key: str) -> str | None:
    token = _text(raw.get(key))
    if not token:
        return None
    found = _date(token)
    if found is None:
        notes.append(f"{key} could not be read.")
    return found


def _complete(pdf: bytes) -> dict:
    _load_env()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY is not set. Add it to .env in the project root.")
    import anthropic

    client = anthropic.Anthropic()
    message = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        thinking={"type": "between_tools"},
        system=_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": base64.standard_b64encode(pdf).decode("ascii"),
                        },
                    },
                    {"type": "text", "text": _USER},
                ],
            }
        ],
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": _SCHEMA}},
    )
    if message.stop_reason != "end_turn":
        raise RuntimeError(f"The reader stopped with {message.stop_reason}.")
    text = "".join(block.text for block in message.content if getattr(block, "type", "") == "text")
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as error:
        raise RuntimeError("The reader returned text that was not JSON.") from error
    return parsed


def _load_env() -> None:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _list(value: object) -> list:
    return value if isinstance(value, list) else []


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _normalise(name: str) -> str:
    text = name.lower()
    for separator in ("-", "_", "/", "&", ":"):
        text = text.replace(separator, " ")
    return " ".join(text.split())


def _is_summary(name: str) -> bool:
    return _normalise(name) in _SUMMARY_LINES


def _decimal(token: str) -> Decimal | None:
    text = token.strip().replace("£", "").replace(",", "").replace(" ", "")
    if text.lower().endswith("pence"):
        text = text[:-5]
    if text.lower().endswith("p"):
        text = text[:-1]
    if not _PLAIN.fullmatch(text):
        return None
    try:
        number = Decimal(text)
    except InvalidOperation:
        return None
    if not number.is_finite():
        return None
    return number


def _money(token: str) -> str | None:
    if not token or token.lower().endswith("p") or token.lower().endswith("pence"):
        return None
    number = _decimal(token)
    if number is None:
        return None
    return f"{number.quantize(_MONEY, rounding=ROUND_HALF_UP):.2f}"


def _unit(token: str) -> str | None:
    if not token or token.lower().endswith("p") or token.lower().endswith("pence"):
        return None
    number = _decimal(token)
    if number is None:
        return None
    return _plain(number)


def _pence(token: str) -> Decimal | None:
    if not token:
        return None
    return _decimal(token)


def _pence_text(number: Decimal) -> str:
    return f"{number.quantize(_MONEY, rounding=ROUND_HALF_UP):.2f}"


def _pence_to_pounds(number: Decimal) -> str:
    return _plain(number / Decimal("100"))


def _rate(token: str) -> str | None:
    percent = "%" in token
    number = _decimal(token.replace("%", ""))
    if number is None:
        return None
    if percent:
        number = number / Decimal("100")
    return _plain(number)


def _quantity(token: str) -> str | None:
    match = re.match(r"-?\d+(\.\d+)?", token.replace(",", "").replace(" ", ""))
    if not match:
        return None
    number = Decimal(match.group(0))
    if number == int(number):
        return str(int(number))
    return _plain(number)


def _whole(token: str) -> int | None:
    match = re.match(r"\d+", token.replace(",", "").replace(" ", ""))
    if not match:
        return None
    return int(match.group(0))


def _plain(number: Decimal) -> str:
    text = format(number, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _date(token: str) -> str | None:
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", token):
        try:
            date.fromisoformat(token)
        except ValueError:
            return None
        return token
    match = re.fullmatch(r"(\d{1,2}) ([A-Za-z]{3,9}) (\d{4})", token)
    if not match:
        found = _decommissioned(token)
        return found
    month = _MONTHS.get(match.group(2)[:3].lower())
    if month is None:
        return None
    try:
        return date(int(match.group(3)), month, int(match.group(1))).isoformat()
    except ValueError:
        return None


def _decommissioned(name: str) -> str | None:
    if "decommissioned" not in _normalise(name):
        return None
    match = re.search(r"(\d{1,2}) ([A-Za-z]{3,9}) (\d{4})", name)
    if not match:
        return None
    return _date(f"{match.group(1)} {match.group(2)} {match.group(3)}")
