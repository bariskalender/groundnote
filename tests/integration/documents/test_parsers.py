from __future__ import annotations

from pathlib import Path

import pytest

from groundnote.documents.errors import (
    CorruptDocumentError,
    EncodingError,
    EncryptedDocumentError,
    NoExtractableTextError,
)
from groundnote.documents.parsers import DocxParser, MarkdownParser, PdfParser, TextParser
from groundnote.domain import SupportedFileType

from .conftest import write_docx, write_empty_docx, write_encrypted_pdf, write_text_pdf


def test_pdf_parser_extracts_pages_in_order_and_warns_for_blank_page(document_dir: Path) -> None:
    path = write_text_pdf(document_dir / "notes.pdf", ["Page one text", "", "Page three text"])

    parsed = PdfParser().parse(
        path,
        original_filename="notes.pdf",
        stored_filename="stored.pdf",
        sha256="a" * 64,
        file_size_bytes=path.stat().st_size,
    )

    assert parsed.file_type is SupportedFileType.PDF
    assert parsed.page_count == 3
    assert [section.page_number for section in parsed.sections] == [1, 3]
    assert "Page one text" in parsed.sections[0].text
    assert any("Page 2 contains no extractable text" in warning for warning in parsed.warnings)


def test_pdf_parser_rejects_encrypted_corrupted_and_image_only_files(document_dir: Path) -> None:
    encrypted = write_encrypted_pdf(document_dir / "encrypted.pdf")
    corrupt = document_dir / "corrupt.pdf"
    corrupt.write_bytes(b"%PDF- definitely not complete")
    blank = write_text_pdf(document_dir / "blank.pdf", ["", ""])

    with pytest.raises(EncryptedDocumentError):
        PdfParser().parse(
            encrypted,
            original_filename="encrypted.pdf",
            stored_filename="stored.pdf",
            sha256="a" * 64,
            file_size_bytes=encrypted.stat().st_size,
        )
    with pytest.raises(CorruptDocumentError):
        PdfParser().parse(
            corrupt,
            original_filename="corrupt.pdf",
            stored_filename="stored.pdf",
            sha256="b" * 64,
            file_size_bytes=corrupt.stat().st_size,
        )
    with pytest.raises(NoExtractableTextError, match="OCR"):
        PdfParser().parse(
            blank,
            original_filename="blank.pdf",
            stored_filename="stored.pdf",
            sha256="c" * 64,
            file_size_bytes=blank.stat().st_size,
        )


def test_docx_parser_preserves_headings_order_unicode_and_tables(document_dir: Path) -> None:
    path = write_docx(document_dir / "notes.docx")

    parsed = DocxParser().parse(
        path,
        original_filename="notes.docx",
        stored_filename="stored.docx",
        sha256="d" * 64,
        file_size_bytes=path.stat().st_size,
    )

    assert parsed.file_type is SupportedFileType.DOCX
    assert parsed.page_count is None
    assert parsed.sections[0].section_title == "Lecture Overview"
    assert "Türkçe" in parsed.sections[0].text
    assert "Term | Meaning" in parsed.sections[-1].text


def test_docx_parser_rejects_empty_and_corrupted_documents(document_dir: Path) -> None:
    empty = write_empty_docx(document_dir / "empty.docx")
    corrupt = document_dir / "corrupt.docx"
    corrupt.write_bytes(b"PK not a docx")

    with pytest.raises(NoExtractableTextError):
        DocxParser().parse(
            empty,
            original_filename="empty.docx",
            stored_filename="stored.docx",
            sha256="e" * 64,
            file_size_bytes=empty.stat().st_size,
        )
    with pytest.raises(CorruptDocumentError):
        DocxParser().parse(
            corrupt,
            original_filename="corrupt.docx",
            stored_filename="stored.docx",
            sha256="f" * 64,
            file_size_bytes=corrupt.stat().st_size,
        )


def test_text_parser_supports_utf8_bom_turkish_and_rejects_binary(document_dir: Path) -> None:
    path = document_dir / "notes.txt"
    path.write_text("\ufeffTürkçe çalışma notu", encoding="utf-8")
    binary = document_dir / "binary.txt"
    binary.write_bytes(b"\x00\x01\x02" * 100)

    parsed = TextParser().parse(
        path,
        original_filename="notes.txt",
        stored_filename="stored.txt",
        sha256="1" * 64,
        file_size_bytes=path.stat().st_size,
    )

    assert "Türkçe" in parsed.sections[0].text
    assert parsed.sections[0].page_number is None
    with pytest.raises(EncodingError):
        TextParser().parse(
            binary,
            original_filename="binary.txt",
            stored_filename="stored.txt",
            sha256="2" * 64,
            file_size_bytes=binary.stat().st_size,
        )


def test_markdown_parser_preserves_headings_lists_code_and_inert_html(document_dir: Path) -> None:
    path = document_dir / "notes.md"
    path.write_text(
        "# Başlık\n\n- item\n\n```python\nprint('x')\n```\n\n<script>alert('no run')</script>",
        encoding="utf-8",
    )

    parsed = MarkdownParser().parse(
        path,
        original_filename="notes.md",
        stored_filename="stored.md",
        sha256="3" * 64,
        file_size_bytes=path.stat().st_size,
    )

    assert parsed.sections[0].section_title == "Başlık"
    assert "- item" in parsed.sections[0].text
    assert "```python" in parsed.sections[0].text
    assert "<script>alert('no run')</script>" in parsed.sections[0].text


def test_markdown_parser_rejects_empty_document(document_dir: Path) -> None:
    path = document_dir / "empty.md"
    path.write_text("  \n\n", encoding="utf-8")

    with pytest.raises(NoExtractableTextError):
        MarkdownParser().parse(
            path,
            original_filename="empty.md",
            stored_filename="stored.md",
            sha256="4" * 64,
            file_size_bytes=path.stat().st_size,
        )
