from __future__ import annotations

from groundnote.documents import normalize_text


def test_normalization_preserves_unicode_and_symbols() -> None:
    text = "  Türkçe: çağrı, İ, ı  \r\nGreek: α β γ\nMath: ∑ x² = π "

    normalized = normalize_text(text)

    assert "Türkçe: çağrı, İ, ı" in normalized
    assert "α β γ" in normalized
    assert "∑ x² = π" in normalized


def test_normalization_preserves_code_block_indentation() -> None:
    text = "```python\r\n    print('merhaba')\r\n```\n\n\nNext"

    normalized = normalize_text(text)

    assert "    print('merhaba')" in normalized
    assert "\n\n\n" not in normalized


def test_normalization_removes_nulls_and_conservative_spaces() -> None:
    assert normalize_text("a\x00   b\tc") == "a b c"
    assert normalize_text("\r\n\x00  ") == ""
