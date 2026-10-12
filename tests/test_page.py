"""The public page quotes the Meadowbank draft and does not send a file."""

import json
from pathlib import Path

from sabiniana.check import check
from sabiniana.write import write

_ROOT = Path(__file__).resolve().parents[1]
_PAGE = _ROOT / "web" / "index.html"


def _meadowbank_draft() -> str:
    cards = json.loads((_ROOT / "tests" / "fixtures" / "card_statements.json").read_text())
    sample = next(item for item in cards if item["id"] == "04")
    result = check(sample["statement"])
    result["practice"] = sample["practice"]
    return write(result)


def test_the_page_is_the_meadowbank_letter():
    page = _PAGE.read_text()
    assert _meadowbank_draft() in page
    assert "This is a made-up sample." in page
    assert "Drop the card statement here, or choose a file." in page
    assert "The file is kept until the page has been sent, then deleted." in page
    assert "Alex Havryleshko" in page
    assert 'max-width: 60ch' in page
    assert "action=" not in page
    assert page.lower().count("<form") == 1
