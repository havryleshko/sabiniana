import pytest

from sabiniana.check import check
from sabiniana.read import read
from sabiniana.write import write


def test_check_is_deterministic_and_does_not_invent_a_gap():
    statement = {"total_sales": 10000, "total_charges": 180}
    first = check(statement)
    assert first == check(statement)
    assert first["effective_rate"] == pytest.approx(0.018)
    assert first["yearly_gap"] is None
    assert first["verdict"] == "incomplete"


def test_reader_rejects_a_missing_file_and_the_writer_states_no_gap():
    with pytest.raises(FileNotFoundError):
        read("engine/inbox/statement.pdf")
    page = write({})
    assert "The verdict is incomplete." in page
    assert "No fair-price saving is stated" in page
