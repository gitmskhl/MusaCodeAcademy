

def normalize_line_endings(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n")


def compare(output: str, expected: str) -> bool:
    return (
        normalize_line_endings(output).strip()
        == normalize_line_endings(expected).strip()
    )
