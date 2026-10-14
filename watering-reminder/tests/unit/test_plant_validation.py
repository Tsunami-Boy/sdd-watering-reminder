import pytest

from waterbot.domain.plants import ValidationError, parse_interval, validate_name, validate_type


def test_name_rules():
    assert validate_name("  Catalina  ") == "Catalina"
    assert validate_name("a" * 40) == "a" * 40
    for bad in ["", "   ", "a" * 41]:
        with pytest.raises(ValidationError):
            validate_name(bad)


def test_type_rules():
    assert validate_type("Dólar") == "Dólar"
    assert validate_type("t" * 60)
    for bad in ["", " ", "t" * 61]:
        with pytest.raises(ValidationError):
            validate_type(bad)


@pytest.mark.parametrize("text,expected", [("1", 1), ("7", 7), (" 14 ", 14), ("365", 365)])
def test_valid_intervals(text, expected):
    assert parse_interval(text) == expected


@pytest.mark.parametrize("text", ["0", "-3", "7.5", "abc", "366", "", "１２"])
def test_invalid_intervals(text):
    with pytest.raises(ValidationError):
        parse_interval(text)
