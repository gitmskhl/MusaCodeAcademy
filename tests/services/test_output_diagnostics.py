import pytest

from app.enums import SubmissionStatus
from app.services.output_diagnostics import diagnose_output, MAX_OUTPUT_LENGTH


def diagnose(expected, actual, status=SubmissionStatus.WRONG_ANSWER):
    return diagnose_output(status=status, expected=expected, actual=actual)


@pytest.mark.parametrize("expected,actual,codes", [
    ("Hello", "Hello", []),
    ("Hello World", "hello world", ["case_mismatch"]),
    ("Привет Мир", "привет мир\n", ["case_mismatch"]),
    ("Hello World", "Hello  World", ["extra_whitespace"]),
    ("Hello World", "HelloWorld", ["extra_whitespace"]),
    ("HelloWorld", "Hello World", ["extra_whitespace"]),
    ("Hello World", "Hello\tWorld", ["extra_whitespace"]),
    ("Hello", " Hello ", ["edge_whitespace"]),
    ("Hello\nWorld", "Hello \n World", ["edge_whitespace"]),
    ("1\n2\n3", "1 2 3", ["line_breaks"]),
    ("1 2 3", "1\n2\n3", ["line_breaks"]),
    ("1\n2\n3", "123", ["line_breaks"]),
    ("Hello World", "hello  world", ["case_mismatch", "extra_whitespace"]),
    ("Hello", " hello ", ["case_mismatch", "edge_whitespace"]),
    ("Hello\nWorld", "hello world", ["case_mismatch", "line_breaks"]),
    ("42", "Ответ: 42", ["extra_text"]),
    ("42", "42 — ответ", ["extra_text"]),
    ("3.14", "3.1400", ["number_format"]),
    ("42", "4.2e1", ["number_format"]),
    ("-0", "+0.0", ["number_format"]),
    ("0.1 42", "0.100 042.0", ["number_format"]),
    ("Result 3.14", "result  3.1400",
     ["case_mismatch", "extra_whitespace", "number_format"]),
    ("1.0000000000000000000000000000000000000001",
     "1.000000000000000000000000000000000000000100", ["number_format"]),
    ("0.1", "0.10000000000000001", []),
    ("9007199254740992", "9007199254740993", []),
    ("1e999999", "2e999999", []),
    ("NaN", "nan", ["case_mismatch"]),
    ("inf", "Infinity", []),
    ("3.14", "3,14", []),
    ("42", "142", []),
    ("42", "42.1", []),
    ("42", "Answer 142", []),
    ("42", "42 43", []),
    ("Hello World", "HELLO  universe", []),
    ("Hello\r\nWorld", "Hello\nWorld\n", []),
    ("Hello", "", []),
    ("", "Hello", []),
    ("", "", []),
    ("  ", "", []),
    (None, "Hello", []),
    ("Hello", None, []),
    ("right", "wrong", []),
])
def test_output_diagnostics(expected, actual, codes):
    original = expected, actual
    result = diagnose(expected, actual)
    assert [item.type for item in result] == codes
    assert all(item.message for item in result)
    assert len({item.type for item in result}) == len(result)
    assert (expected, actual) == original


@pytest.mark.parametrize("status", [s for s in SubmissionStatus if s != SubmissionStatus.WRONG_ANSWER])
def test_other_verdicts_are_never_diagnosed(status):
    assert diagnose("Hello", "hello", status) == []


@pytest.mark.parametrize("length", [MAX_OUTPUT_LENGTH, MAX_OUTPUT_LENGTH + 1, 1_000_000])
def test_oversized_output_is_skipped_without_analyzing_a_prefix(length):
    assert diagnose("A" * length, "a" * length) == []
    assert diagnose("A", "A" + " " * length) == []


def test_number_tokens_have_a_separate_size_limit():
    assert diagnose("1" * 200 + ".0", "1" * 200 + ".00") == []


def test_decimal_context_does_not_round_values():
    from decimal import localcontext

    with localcontext() as context:
        context.prec = 2
        assert diagnose("3.1415926535", "3.141592653500")[0].type == "number_format"
        assert diagnose("3.1415926535", "3.1415926536") == []
