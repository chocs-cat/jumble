import pytest

from jumble.cli import main


def test_prints_count_strings(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["-n", "10", "-c", "3", "-s", "upper"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 3
    assert all(len(line) == 10 and line.isupper() for line in lines)


def test_bad_length_exits() -> None:
    with pytest.raises(SystemExit):
        main(["-n", "0"])
