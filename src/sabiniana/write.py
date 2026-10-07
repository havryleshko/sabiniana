"""Turn one check result into a one-page draft.

The draft quotes the checker's own sentences. It does not add a rate, a
saving, or a fair-price verdict. yearly_gap is stated only when the check
result itself contains one.
"""

from __future__ import annotations

import json
import re
from decimal import Decimal, ROUND_HALF_UP

_MONEY = re.compile(r"£\d{1,3}(?:,\d{3})*(?:\.\d{2})?")
_PERCENT = re.compile(r"\d+(?:\.\d+)?%")


def write(result: dict) -> str:
    """Draft one page for Alex to read. Nothing is sent."""
    if not isinstance(result, dict):
        raise TypeError("The check result was not an object.")
    findings = _findings(result)
    lines = ["Draft for review. Nothing has been sent.", ""]
    practice = result.get("practice")
    if isinstance(practice, str) and practice.strip():
        lines.append(practice.strip())
        lines.append("")
    lines.append(_opening(result, findings))
    lines.append("")
    rate_line = _effective_rate_line(result.get("effective_rate"))
    if rate_line:
        lines.append(rate_line)
        lines.append("")
    if findings:
        lines.append("What the checks found:")
        lines.append("")
        for index, finding in enumerate(findings, start=1):
            lines.append(f"{index}. {_summary(finding)}")
        lines.append("")
    comparison = result.get("observed_comparison")
    if isinstance(comparison, dict):
        summary = comparison.get("summary")
        if isinstance(summary, str) and summary.strip():
            lines.append(summary.strip())
            source = comparison.get("source")
            if isinstance(source, str) and source.strip():
                lines.append(f"Source: {source.strip()}.")
            lines.append("")
    lines.append(
        "Alex reads this page against the document before anything is sent. "
        "Nothing happens unless the practice replies."
    )
    return "\n".join(lines).rstrip() + "\n"


def _opening(result: dict, findings: list[dict]) -> str:
    if findings:
        noun = "point" if len(findings) == 1 else "points"
        head = f"These checks found {len(findings)} {noun}."
    else:
        head = "These checks found nothing to flag."
    verdict = result.get("verdict")
    if verdict == "incomplete" or not isinstance(verdict, str) or not verdict.strip():
        verdict_text = "The verdict is incomplete."
    else:
        verdict_text = f"The check verdict is {verdict.strip()}."
    gap = result.get("yearly_gap")
    if gap is None:
        gap_text = "No fair-price saving is stated, and this page does not say the price is fair."
    else:
        shown = _gap_text(gap)
        gap_text = (
            f"The check states a fair-price gap of {shown} a year."
            if shown
            else "The check included a fair-price gap that could not be read."
        )
    return f"{head} {verdict_text} {gap_text}"


def _findings(result: dict) -> list[dict]:
    findings = result.get("findings")
    if not isinstance(findings, list):
        return []
    return [finding for finding in findings if isinstance(finding, dict)]


def _summary(finding: dict) -> str:
    summary = finding.get("summary")
    if isinstance(summary, str) and summary.strip():
        return summary.strip()
    return "A finding had no summary."


def _effective_rate_line(rate: object) -> str:
    if isinstance(rate, bool) or not isinstance(rate, (int, float)):
        return ""
    shown = (Decimal(str(rate)) * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"Effective rate: {shown:.2f}% of card sales."


def figures_outside_result(page: str, result: dict) -> list[str]:
    """Pound amounts and percents on the page that the check result does not contain."""
    allowed = json.dumps(result)
    rate = result.get("effective_rate")
    if isinstance(rate, (int, float)) and not isinstance(rate, bool):
        shown = (Decimal(str(rate)) * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        allowed += f"{shown:.2f}%"
    bare_allowed = allowed.replace(",", "")
    outside: list[str] = []
    for amount in _MONEY.findall(page):
        bare = amount.replace("£", "").replace(",", "")
        if bare not in bare_allowed and amount not in allowed:
            outside.append(amount)
    for percent in _PERCENT.findall(page):
        if percent not in allowed:
            outside.append(percent)
    return outside


def _gap_text(value: object) -> str:
    if isinstance(value, str) and value.strip():
        text = value.strip()
        return text if text.startswith("£") else f"£{text}"
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        return ""
    amount = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"£{amount:.2f}"
