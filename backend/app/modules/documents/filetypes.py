"""Recognise uploaded files by their content, not their name (FR-DOC-04, NFR-SEC-06, decision D-12)."""

import zipfile
from enum import StrEnum
from typing import BinaryIO


class FileType(StrEnum):
    PDF = "pdf"
    DOCX = "docx"
    PNG = "png"
    JPG = "jpg"


MIME_TYPES: dict[FileType, str] = {
    FileType.PDF: "application/pdf",
    FileType.DOCX: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    FileType.PNG: "image/png",
    FileType.JPG: "image/jpeg",
}

# Types a browser can show safely in a tab; the others are always downloaded.
VIEWABLE: frozenset[FileType] = frozenset({FileType.PDF, FileType.PNG, FileType.JPG})


def _is_docx(source: BinaryIO) -> bool:
    """A Word document is a ZIP package with a main document part. Macro-enabled packages are refused."""
    try:
        with zipfile.ZipFile(source) as package:
            names = set(package.namelist())
    except (zipfile.BadZipFile, OSError):
        return False
    return (
        "[Content_Types].xml" in names and "word/document.xml" in names and "word/vbaProject.bin" not in names
    )


def detect(source: BinaryIO) -> FileType | None:
    """The file's real type from its first bytes (and package structure for DOCX), or None if not allowed."""
    source.seek(0)
    head = source.read(8)
    source.seek(0)
    if head.startswith(b"%PDF-"):
        return FileType.PDF
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return FileType.PNG
    if head.startswith(b"\xff\xd8\xff"):
        return FileType.JPG
    if head.startswith(b"PK\x03\x04"):
        found = FileType.DOCX if _is_docx(source) else None
        source.seek(0)
        return found
    return None
