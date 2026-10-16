"""The public page asks for one bill and does not send a file."""

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_WEB = _ROOT / "web"


def _sources() -> str:
    files = [
        path
        for path in _WEB.rglob("*")
        if path.suffix in {".ts", ".tsx", ".css", ".html"}
        and "node_modules" not in path.parts
        and "dist" not in path.parts
    ]
    return "\n".join(path.read_text() for path in files)


def test_the_page_asks_for_one_bill():
    page = _sources()
    assert "Drop a bill here, or choose a file." in page
    assert "It's free and it stays free." in page
    assert "I never post your name" in page
    assert "I check every one myself." in page
    assert "Nothing changes with your" in page
    assert "Alex Havryleshko" in page
    assert "action=" not in page
    assert page.lower().count("<form") == 1
    assert (_WEB / "public" / "alex.jpg").exists()
