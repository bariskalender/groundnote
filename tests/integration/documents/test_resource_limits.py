from __future__ import annotations

import struct
import zipfile
from io import BytesIO
from pathlib import Path

import pytest

from groundnote.documents.errors import (
    DocxArchiveSafetyError,
    ExtractedTextLimitError,
    NoExtractableTextError,
    PdfPageLimitError,
)
from groundnote.documents.parsers import DocxParser, PdfParser

from .conftest import write_text_pdf


def _parse_pdf(path: Path, parser: PdfParser) -> None:
    parser.parse(
        path,
        original_filename="fixture.pdf",
        stored_filename="stored.pdf",
        sha256="a" * 64,
        file_size_bytes=path.stat().st_size,
    )


def _parse_docx(path: Path, parser: DocxParser) -> None:
    parser.parse(
        path,
        original_filename="fixture.docx",
        stored_filename="stored.docx",
        sha256="b" * 64,
        file_size_bytes=path.stat().st_size,
    )


def _write_docx_archive(path: Path, members: dict[str, bytes]) -> Path:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in members.items():
            archive.writestr(name, data)
    return path


def _document_xml(text: str = "Safe study text") -> bytes:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body></w:document>"
    ).encode()


def _mark_first_member_encrypted(path: Path) -> None:
    data = bytearray(path.read_bytes())
    local = data.find(b"PK\x03\x04")
    central = data.find(b"PK\x01\x02")
    assert local >= 0 and central >= 0
    local_flags = struct.unpack_from("<H", data, local + 6)[0] | 0x1
    central_flags = struct.unpack_from("<H", data, central + 8)[0] | 0x1
    struct.pack_into("<H", data, local + 6, local_flags)
    struct.pack_into("<H", data, central + 8, central_flags)
    path.write_bytes(data)


def test_pdf_rejects_page_count_before_extracting_pages(document_dir: Path) -> None:
    path = write_text_pdf(document_dir / "many-pages.pdf", ["one", "two"])

    with pytest.raises(PdfPageLimitError):
        _parse_pdf(path, PdfParser(maximum_pages=1))


def test_pdf_rejects_extracted_characters_incrementally(document_dir: Path) -> None:
    path = write_text_pdf(document_dir / "long.pdf", ["123456", "abcdef"])

    with pytest.raises(ExtractedTextLimitError):
        _parse_pdf(path, PdfParser(maximum_extracted_characters=8))


@pytest.mark.parametrize("member_name", ["../escape.xml", "/absolute.xml", "C:/drive.xml"])
def test_docx_rejects_traversal_and_absolute_members(
    document_dir: Path,
    member_name: str,
) -> None:
    path = _write_docx_archive(
        document_dir / "unsafe.docx",
        {"word/document.xml": _document_xml(), member_name: b"unsafe"},
    )

    with pytest.raises(DocxArchiveSafetyError):
        _parse_docx(path, DocxParser())


def test_docx_rejects_excessive_member_count(document_dir: Path) -> None:
    path = _write_docx_archive(
        document_dir / "members.docx",
        {"word/document.xml": _document_xml(), "extra/one.xml": b"1"},
    )

    with pytest.raises(DocxArchiveSafetyError):
        _parse_docx(path, DocxParser(maximum_members=1))


def test_docx_rejects_total_expanded_size_and_large_member(document_dir: Path) -> None:
    path = _write_docx_archive(
        document_dir / "expanded.docx",
        {"word/document.xml": _document_xml("A" * 2_000)},
    )

    with pytest.raises(DocxArchiveSafetyError):
        _parse_docx(path, DocxParser(maximum_expanded_size_bytes=1_000))
    with pytest.raises(DocxArchiveSafetyError):
        _parse_docx(path, DocxParser(maximum_member_size_bytes=1_000))


def test_docx_rejects_extreme_compression_ratio(document_dir: Path) -> None:
    path = _write_docx_archive(
        document_dir / "ratio.docx",
        {"word/document.xml": _document_xml("A" * 20_000)},
    )

    with pytest.raises(DocxArchiveSafetyError):
        _parse_docx(path, DocxParser(maximum_compression_ratio=2.0))


def test_docx_rejects_encrypted_member_metadata(document_dir: Path) -> None:
    path = _write_docx_archive(
        document_dir / "encrypted.docx",
        {"word/document.xml": _document_xml()},
    )
    _mark_first_member_encrypted(path)

    with pytest.raises(DocxArchiveSafetyError):
        _parse_docx(path, DocxParser())


def test_docx_rejects_symlink_like_archive_member(document_dir: Path) -> None:
    path = document_dir / "special.docx"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", _document_xml())
        special = zipfile.ZipInfo("word/special.xml")
        special.create_system = 3
        special.external_attr = 0o120777 << 16
        archive.writestr(special, b"target")

    with pytest.raises(DocxArchiveSafetyError):
        _parse_docx(path, DocxParser())


def test_docx_rejects_malformed_archive(document_dir: Path) -> None:
    path = document_dir / "malformed.docx"
    path.write_bytes(b"PK malformed central directory")

    with pytest.raises(DocxArchiveSafetyError):
        _parse_docx(path, DocxParser())


def test_docx_rejects_extracted_character_limit(document_dir: Path) -> None:
    path = _write_docx_archive(
        document_dir / "long.docx",
        {"word/document.xml": _document_xml("A" * 200)},
    )

    with pytest.raises(ExtractedTextLimitError):
        _parse_docx(path, DocxParser(maximum_extracted_characters=100))


def test_pdf_closes_source_after_page_extraction_failure(
    monkeypatch: pytest.MonkeyPatch,
    document_dir: Path,
) -> None:
    source = BytesIO(b"synthetic")

    class FailingPage:
        def extract_text(self) -> str:
            raise RuntimeError("synthetic parser failure")

    class FakeReader:
        is_encrypted = False
        pages = [FailingPage()]

    monkeypatch.setattr(Path, "open", lambda *_args, **_kwargs: source)
    monkeypatch.setattr("groundnote.documents.parsers.pdf.PdfReader", lambda _source: FakeReader())
    path = document_dir / "tracked.pdf"

    with pytest.raises(NoExtractableTextError):
        PdfParser().parse(
            path,
            original_filename="tracked.pdf",
            stored_filename="stored.pdf",
            sha256="c" * 64,
            file_size_bytes=1,
        )

    assert source.closed
