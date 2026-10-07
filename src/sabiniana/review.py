"""Read one PDF, check it, and draft the page. Nothing is sent."""

from __future__ import annotations

import json
from pathlib import Path

from sabiniana.bills import check_bill
from sabiniana.check import check
from sabiniana.read import read
from sabiniana.write import write

_BILL_KINDS = {"lab", "energy", "supplies", "service"}


def review(path: str | Path, *, read_pdf=None) -> dict:
    """Return the read document, the check result, and the draft page.

    read_pdf, when passed, replaces the Claude reader. The default reads the PDF.
    """
    document = (read_pdf or read)(path)
    if not isinstance(document, dict):
        raise TypeError("The reader did not return an object.")
    result = _check_document(document)
    page = write(_for_page(document, result))
    return {"document": document, "result": result, "page": page}


def save_review(path: str | Path, working_dir: str | Path, reports_dir: str | Path, *, read_pdf=None) -> dict:
    """Review one PDF and write the working file and the draft. Nothing is sent."""
    outcome = review(path, read_pdf=read_pdf)
    stem = Path(path).stem
    working = Path(working_dir)
    reports = Path(reports_dir)
    working.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)
    payload = {"document": outcome["document"], "result": outcome["result"]}
    (working / f"{stem}.json").write_text(json.dumps(payload, indent=2) + "\n")
    (reports / f"{stem}.md").write_text(outcome["page"])
    return outcome


def _check_document(document: dict) -> dict:
    kind = document.get("kind")
    if kind == "card":
        return check(document)
    if kind in _BILL_KINDS:
        return check_bill(document)
    notes = document.get("unreadable")
    summary = "The document kind could not be read, so it was not checked."
    if isinstance(notes, list) and notes:
        summary = "The document kind could not be read, so it was not checked. The reader also left fields unread."
    return {
        "yearly_gap": None,
        "verdict": "incomplete",
        "findings": [{"code": "document_kind_unreadable", "summary": summary}],
    }


def _for_page(document: dict, result: dict) -> dict:
    page_result = dict(result)
    practice = document.get("practice")
    if isinstance(practice, str) and practice.strip():
        page_result["practice"] = practice.strip()
    return page_result
