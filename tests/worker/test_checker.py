import pytest

from worker.checker import compare

@pytest.mark.parametrize(
    "output, expected, result",
    [
        ("42", "42", True),
        ("42\n", "42", True),
        (" 42", "42", True),
        ("41", "42", False),
        ("", "42", False)
    ],
)
def test_compare(output, expected, result):
    assert compare(output, expected) is result
