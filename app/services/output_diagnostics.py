"""Bounded, deterministic output hints. This module never decides a verdict."""

from decimal import Decimal
from itertools import combinations
import re

from app.enums import SubmissionStatus
from app.schemas.submission import OutputDiagnostic


MAX_OUTPUT_LENGTH = 10_000
MAX_NUMBER_LENGTH = 128
MAX_DIAGNOSTICS = 4

MESSAGES = {
    "case_mismatch": "Проверьте регистр букв. Заглавные и строчные буквы различаются.",
    "extra_whitespace": "Проверьте количество пробелов между словами.",
    "edge_whitespace": "Проверьте лишние пробелы в начале или конце вывода и строк.",
    "line_breaks": "Проверьте переносы строк. Возможно, значения нужно выводить на отдельных строках.",
    "extra_text": "Возможно, программа выводит лишний текст. Выводите только то, что требуется в условии задачи.",
    "number_format": "Проверьте формат вывода чисел, в том числе количество знаков после десятичной точки.",
}

# Only unambiguous decimal tokens. No float rounding, NaN, infinity or locale guesses.
NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]{1,6})?")


def _numbers_match(expected: str, actual: str) -> bool:
    left, right = re.split(r"(\s+)", expected), re.split(r"(\s+)", actual)
    if len(left) != len(right):
        return False
    changed = False
    for a, b in zip(left, right):
        if a == b:
            continue
        if (max(len(a), len(b)) > MAX_NUMBER_LENGTH
                or not NUMBER.fullmatch(a) or not NUMBER.fullmatch(b)
                or Decimal(a) != Decimal(b)):
            return False
        changed = True
    return changed


def _strip_line_edges(value: str) -> str:
    return "\n".join(line.strip(" \t") for line in value.split("\n"))


def _has_extra_text(expected: str, actual: str) -> bool:
    # Require a complete answer at an edge and an added textual label, rather
    # than guessing from arbitrary substrings (e.g. 42 inside 142 or 42.1).
    for at_start in (True, False):
        if at_start and actual.startswith(expected):
            extra = actual[len(expected):]
            boundary = extra[:1]
        elif not at_start and actual.endswith(expected):
            extra = actual[:-len(expected)]
            boundary = extra[-1:]
        else:
            continue
        if (boundary and not boundary.isalnum() and boundary != "_"
                and any(c.isalpha() for c in extra)
                and not any(c.isdigit() for c in extra)):
            return True
    return False


def diagnose_output(*, status: SubmissionStatus, expected: str | None,
                    actual: str | None) -> list[OutputDiagnostic]:
    """Suggest only transformations that explain the complete difference.

    Skip oversized outputs entirely: a matching prefix cannot establish a cause.
    Try a small fixed set of combinations to support simultaneous issues, using
    the fewest hints that explain the difference. All work is on string copies.
    """
    if (status != SubmissionStatus.WRONG_ANSWER or expected is None or actual is None
            or max(len(expected), len(actual)) >= MAX_OUTPUT_LENGTH):
        return []
    # CRLF/CR and final newlines are already ignored by both existing checkers.
    left, right = (
        value.replace("\r\n", "\n").replace("\r", "\n").strip("\n")
        for value in (expected, actual)
    )
    if left == right or not left.strip() or not right.strip():
        return []

    rules = [
        ("case_mismatch", str.lower),
        ("edge_whitespace", _strip_line_edges),
        ("extra_whitespace", lambda value: re.sub(r"[ \t]+", " ", value)),
        ("extra_whitespace", lambda value: re.sub(r"[ \t]+", "", value)),
    ]
    # Only offer newline analysis if at least one output contains a newline.
    if "\n" in left or "\n" in right:
        rules.append(("line_breaks", lambda value: re.sub(r"[ \t\n]+", " ", value)))
        rules.append(("line_breaks", lambda value: value.replace("\n", "")))

    best = None
    seen = set()
    for count in range(len(rules) + 1):
        # Every selected rule must change the copies, so larger combinations
        # cannot improve a result already found with this many hints.
        if best is not None and count >= len(best):
            break
        for selected in combinations(rules, count):
            if len({code for code, _ in selected}) != len(selected):
                continue
            a, b = left, right
            codes = []
            for code, transform in selected:
                next_a, next_b = transform(a), transform(b)
                if (next_a, next_b) == (a, b):
                    break
                codes.append(code)
                a, b = next_a, next_b
            else:
                if (a, b) in seen:
                    continue
                seen.add((a, b))
                candidate = codes if a == b else (
                    [*codes, "number_format"] if _numbers_match(a, b) else None
                )
                if candidate is not None and (best is None or len(candidate) < len(best)):
                    best = candidate

    if best:
        codes = best
    elif _has_extra_text(left.strip(), right.strip()):
        codes = ["extra_text"]
    else:
        return []
    return [OutputDiagnostic(type=code, message=MESSAGES[code])
            for code in codes[:MAX_DIAGNOSTICS]]
