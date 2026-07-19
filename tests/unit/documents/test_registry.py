from __future__ import annotations

import pytest

from groundnote.documents.errors import ParserNotFoundError
from groundnote.documents.registry import ParserRegistry, default_parser_registry
from groundnote.domain import SupportedFileType


def test_default_registry_selects_all_supported_parsers() -> None:
    registry = default_parser_registry()

    assert registry.get(SupportedFileType.PDF).supported_file_type is SupportedFileType.PDF
    assert registry.get(SupportedFileType.DOCX).supported_file_type is SupportedFileType.DOCX
    assert registry.get(SupportedFileType.TXT).supported_file_type is SupportedFileType.TXT
    assert (
        registry.get(SupportedFileType.MARKDOWN).supported_file_type is SupportedFileType.MARKDOWN
    )


def test_registry_fails_clearly_when_parser_is_missing() -> None:
    with pytest.raises(ParserNotFoundError):
        ParserRegistry({}).get(SupportedFileType.PDF)
