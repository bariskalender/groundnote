"""Conservative text normalization for parsed local documents."""

from __future__ import annotations

import re

_HORIZONTAL_SPACE_RE = re.compile(r"[ \t\f\v]+")
_BLANK_LINES_RE = re.compile(r"\n{3,}")


def normalize_text(text: str) -> str:
    """Normalize text without changing language, casing, formulas, or code meaning."""
    value = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    normalized_lines: list[str] = []
    in_code_block = False
    for line in value.split("\n"):
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_code_block = not in_code_block
            normalized_lines.append(line.rstrip())
        elif in_code_block or line.startswith(("    ", "\t")):
            normalized_lines.append(line.rstrip())
        else:
            normalized_lines.append(_HORIZONTAL_SPACE_RE.sub(" ", line).strip())
    return _BLANK_LINES_RE.sub("\n\n", "\n".join(normalized_lines)).strip()
