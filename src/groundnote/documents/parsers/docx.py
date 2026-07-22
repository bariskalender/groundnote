"""Resource-bounded DOCX parser for untrusted ZIP containers."""

from __future__ import annotations

import re
import stat
import zipfile
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree

from groundnote.documents.errors import (
    DocxArchiveSafetyError,
    ExtractedTextLimitError,
)
from groundnote.documents.models import ParsedDocument, ParsedSection
from groundnote.documents.parsers.base import make_section, require_sections
from groundnote.domain import SupportedFileType

_WORD_NAMESPACE = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_W = f"{{{_WORD_NAMESPACE}}}"
_DOCUMENT_XML = "word/document.xml"
_STYLES_XML = "word/styles.xml"
_DRIVE_PATH_RE = re.compile(r"^[A-Za-z]:")


class DocxParser:
    """Inspect ZIP metadata, then read only required WordprocessingML parts."""

    supported_file_type = SupportedFileType.DOCX

    def __init__(
        self,
        *,
        maximum_expanded_size_bytes: int = 200 * 1024 * 1024,
        maximum_compression_ratio: float = 100.0,
        maximum_member_size_bytes: int = 50 * 1024 * 1024,
        maximum_members: int = 2_000,
        maximum_extracted_characters: int = 5_000_000,
    ) -> None:
        self.maximum_expanded_size_bytes = maximum_expanded_size_bytes
        self.maximum_compression_ratio = maximum_compression_ratio
        self.maximum_member_size_bytes = maximum_member_size_bytes
        self.maximum_members = maximum_members
        self.maximum_extracted_characters = maximum_extracted_characters

    def validate_compatible(self, file_path: Path) -> None:
        self._read_required_parts(file_path)

    def parse(
        self,
        file_path: Path,
        *,
        original_filename: str,
        stored_filename: str,
        sha256: str,
        file_size_bytes: int,
    ) -> ParsedDocument:
        document_xml, styles_xml = self._read_required_parts(file_path)
        styles = _heading_styles(styles_xml)
        try:
            document_root = ElementTree.fromstring(document_xml)
        except ElementTree.ParseError as exc:
            raise DocxArchiveSafetyError("The DOCX document XML is malformed.") from exc

        sections: list[ParsedSection] = []
        current_heading: str | None = None
        buffer: list[str] = []
        source_order = 0
        extracted_characters = 0

        def add_text(text: str) -> None:
            nonlocal extracted_characters
            cleaned = text.strip()
            if not cleaned:
                return
            extracted_characters += len(cleaned)
            if extracted_characters > self.maximum_extracted_characters:
                raise ExtractedTextLimitError()
            buffer.append(cleaned)

        def flush() -> None:
            nonlocal buffer, source_order
            if not buffer:
                return
            section = make_section(
                "\n".join(buffer),
                source_order=source_order,
                section_title=current_heading,
            )
            if section is not None:
                sections.append(section)
                source_order += 1
            buffer = []

        body = document_root.find(f"{_W}body")
        if body is None:
            raise DocxArchiveSafetyError("The DOCX document body is missing.")
        for child in body:
            if child.tag == f"{_W}p":
                text = _paragraph_text(child)
                style_id = _paragraph_style_id(child)
                if text.strip() and style_id in styles:
                    flush()
                    current_heading = text.strip()
                add_text(text)
            elif child.tag == f"{_W}tbl":
                rows = _table_rows(child)
                if rows:
                    add_text("\n".join(rows))
        flush()
        require_sections(sections)
        return ParsedDocument(
            original_filename=original_filename,
            stored_filename=stored_filename,
            file_type=self.supported_file_type,
            sha256=sha256,
            file_size_bytes=file_size_bytes,
            page_count=None,
            sections=sections,
            warnings=[],
        )

    def _read_required_parts(self, file_path: Path) -> tuple[bytes, bytes | None]:
        try:
            with zipfile.ZipFile(file_path) as archive:
                members = archive.infolist()
                self._inspect_members(members)
                by_name = {_normalized_member_name(member.filename): member for member in members}
                document_member = by_name.get(_DOCUMENT_XML)
                if document_member is None or document_member.is_dir():
                    raise DocxArchiveSafetyError("The DOCX document XML is missing.")
                document_xml = self._read_member_bounded(archive, document_member)
                styles_member = by_name.get(_STYLES_XML)
                styles_xml = (
                    self._read_member_bounded(archive, styles_member)
                    if styles_member is not None
                    else None
                )
                if _contains_unsafe_xml_declaration(document_xml) or (
                    styles_xml is not None and _contains_unsafe_xml_declaration(styles_xml)
                ):
                    raise DocxArchiveSafetyError(
                        "DOCX document type and entity declarations are not supported."
                    )
                return document_xml, styles_xml
        except DocxArchiveSafetyError:
            raise
        except (zipfile.BadZipFile, zipfile.LargeZipFile, KeyError, OSError, RuntimeError) as exc:
            raise DocxArchiveSafetyError("The DOCX archive is malformed or unreadable.") from exc

    def _inspect_members(self, members: list[zipfile.ZipInfo]) -> None:
        if len(members) > self.maximum_members:
            raise DocxArchiveSafetyError()
        total_expanded = 0
        total_compressed = 0
        seen: set[str] = set()
        for member in members:
            name = _normalized_member_name(member.filename)
            if not name or name in seen:
                raise DocxArchiveSafetyError("The DOCX archive contains duplicate entries.")
            seen.add(name)
            if member.flag_bits & 0x1:
                raise DocxArchiveSafetyError("Encrypted DOCX archive members are not supported.")
            if _is_special_member(member):
                raise DocxArchiveSafetyError("The DOCX archive contains a special file entry.")
            if member.file_size > self.maximum_member_size_bytes:
                raise DocxArchiveSafetyError()
            total_expanded += member.file_size
            total_compressed += member.compress_size
            if total_expanded > self.maximum_expanded_size_bytes:
                raise DocxArchiveSafetyError()
            if _compression_ratio(member.file_size, member.compress_size) > (
                self.maximum_compression_ratio
            ):
                raise DocxArchiveSafetyError()
        if _compression_ratio(total_expanded, total_compressed) > self.maximum_compression_ratio:
            raise DocxArchiveSafetyError()

    def _read_member_bounded(
        self,
        archive: zipfile.ZipFile,
        member: zipfile.ZipInfo,
    ) -> bytes:
        parts: list[bytes] = []
        total = 0
        with archive.open(member) as source:
            while data := source.read(64 * 1024):
                total += len(data)
                if total > self.maximum_member_size_bytes:
                    raise DocxArchiveSafetyError()
                parts.append(data)
        return b"".join(parts)


def _normalized_member_name(name: str) -> str:
    normalized = name.replace("\\", "/")
    if normalized in {"", ".", "/"}:
        raise DocxArchiveSafetyError("The DOCX archive contains an unsafe member path.")
    if (
        normalized.startswith("/")
        or normalized.startswith("//")
        or _DRIVE_PATH_RE.match(normalized)
    ):
        raise DocxArchiveSafetyError("The DOCX archive contains an unsafe member path.")
    path = PurePosixPath(normalized)
    if ".." in path.parts or "." in path.parts:
        raise DocxArchiveSafetyError("The DOCX archive contains an unsafe member path.")
    return path.as_posix().rstrip("/")


def _is_special_member(member: zipfile.ZipInfo) -> bool:
    mode = (member.external_attr >> 16) & 0xFFFF
    file_type = stat.S_IFMT(mode)
    return file_type not in {0, stat.S_IFREG, stat.S_IFDIR}


def _compression_ratio(expanded: int, compressed: int) -> float:
    if expanded == 0:
        return 0.0
    return expanded / max(1, compressed)


def _contains_unsafe_xml_declaration(data: bytes) -> bool:
    prefix = data[:4096].upper()
    return b"<!DOCTYPE" in prefix or b"<!ENTITY" in prefix


def _heading_styles(styles_xml: bytes | None) -> set[str]:
    if styles_xml is None:
        return set()
    try:
        root = ElementTree.fromstring(styles_xml)
    except ElementTree.ParseError as exc:
        raise DocxArchiveSafetyError("The DOCX styles XML is malformed.") from exc
    headings: set[str] = set()
    for style in root.findall(f"{_W}style"):
        if style.get(f"{_W}type") != "paragraph":
            continue
        style_id = style.get(f"{_W}styleId")
        name = style.find(f"{_W}name")
        style_name = name.get(f"{_W}val", "") if name is not None else ""
        if style_id and style_name.casefold().startswith("heading"):
            headings.add(style_id)
    return headings


def _paragraph_style_id(paragraph: ElementTree.Element) -> str | None:
    style = paragraph.find(f"{_W}pPr/{_W}pStyle")
    return style.get(f"{_W}val") if style is not None else None


def _paragraph_text(paragraph: ElementTree.Element) -> str:
    return "".join(node.text or "" for node in paragraph.iter(f"{_W}t"))


def _table_rows(table: ElementTree.Element) -> list[str]:
    rows: list[str] = []
    for row in table.findall(f"{_W}tr"):
        cells: list[str] = []
        for cell in row.findall(f"{_W}tc"):
            text = "\n".join(
                value
                for paragraph in cell.findall(f"{_W}p")
                if (value := _paragraph_text(paragraph).strip())
            )
            cells.append(text)
        if cells:
            rows.append(" | ".join(cells))
    return rows
