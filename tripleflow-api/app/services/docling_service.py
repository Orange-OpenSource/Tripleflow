"""Document parsing backed by Docling.

Docling converts rich document formats (PDF, DOCX, PPTX, XLSX, HTML, images...)
into structured Markdown, preserving tables and reading order far better than a
plain text extraction. The converter loads ML models on first use, so it is
instantiated lazily and cached as a process-wide singleton.

"""

import logging
import os
import re
from io import BytesIO
from threading import Lock

logger = logging.getLogger(__name__)

# Docling marks pictures it could not turn into text with this placeholder.
IMAGE_PLACEHOLDER_RE = re.compile(
    r"^[ \t]*<!--\s*image\s*-->[ \t]*$\n?", re.MULTILINE | re.IGNORECASE
)
MARKDOWN_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
HTML_IMAGE_RE = re.compile(r"<img\b[^>]*/?>", re.IGNORECASE)
# Fenced code block, closed by the very same fence it opened with.
FENCED_CODE_RE = re.compile(
    r"^[ \t]*(`{3,}|~{3,}).*?^[ \t]*\1[ \t]*$\n?",
    re.MULTILINE | re.DOTALL,
)
INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
EXTRA_BLANK_LINES_RE = re.compile(r"\n{3,}")

# Joins consecutive pages. Kept to a blank line so it reads as a paragraph break
# to both the chunker and the reviewer, rather than as a visible marker.
PAGE_SEPARATOR = "\n\n"

# Extensions we route through Docling. It handles far more (Office, HTML, images,
# markup...), but the pipeline deliberately accepts only plain text and PDF, and
# plain text needs no parsing — so PDF is the one format worth routing here, for
# its structure, tables and page provenance. Keep in sync with
# SUPPORTED_FILE_EXTENSIONS on the front.
DOCLING_EXTENSIONS = (".pdf",)

_converter = None
_converter_lock = Lock()


class DoclingUnavailableError(RuntimeError):
    """Raised when Docling is not installed or fails to initialise."""


def docling_enabled() -> bool:
    """Whether Docling parsing is turned on. Controlled by the USE_DOCLING env var."""
    return os.getenv("USE_DOCLING", "true").strip().lower() not in (
        "0",
        "false",
        "no",
        "off",
    )


def docling_supports(filename: str, content_type: str) -> bool:
    """Returns True when the given file looks like something Docling can parse."""
    filename = (filename or "").lower()
    content_type = (content_type or "").lower()

    if filename.endswith(DOCLING_EXTENSIONS):
        return True

    return content_type == "application/pdf"


def strip_visual_and_code_content(markdown: str) -> str:
    """Removes what carries no extractable prose from Docling's Markdown.

    Pictures (placeholders, Markdown and HTML images) and code blocks are dropped
    entirely; inline code keeps its text and only loses its backticks, so
    sentences quoting an identifier stay readable.
    """
    text = FENCED_CODE_RE.sub("", markdown)
    text = IMAGE_PLACEHOLDER_RE.sub("", text)
    text = MARKDOWN_IMAGE_RE.sub("", text)
    text = HTML_IMAGE_RE.sub("", text)
    text = INLINE_CODE_RE.sub(r"\1", text)

    return EXTRA_BLANK_LINES_RE.sub("\n\n", text).strip()


def _get_converter():
    """Lazily builds and caches the Docling DocumentConverter singleton."""
    global _converter

    if _converter is not None:
        return _converter

    with _converter_lock:
        if _converter is None:
            try:
                from docling.datamodel.base_models import InputFormat
                from docling.datamodel.pipeline_options import (
                    PdfPipelineOptions,
                )
                from docling.document_converter import (
                    DocumentConverter,
                    PdfFormatOption,
                )
            except ImportError as exc:
                raise DoclingUnavailableError(
                    "Docling is not installed"
                ) from exc

            pipeline_options = PdfPipelineOptions()
            pipeline_options.do_ocr = False

            logger.info(
                "Initialising Docling DocumentConverter (loading models)"
            )
            _converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(
                        pipeline_options=pipeline_options
                    )
                }
            )

    return _converter


def _export_by_page(document) -> tuple[str, list[int]] | None:
    """
    Exports a paginated document one page at a time, returning the joined text and
    the offset at which each page starts. Those offsets are what later turns a
    chunk position into a page number in the validation interface.

    Returns None when the document carries no pagination (Word, spreadsheets,
    HTML...), so the caller falls back to a single-shot export.
    """
    page_numbers = sorted(getattr(document, "pages", None) or {})

    if not page_numbers:
        return None

    parts: list[str] = []
    page_offsets: list[int] = []
    cursor = 0

    for page_number in page_numbers:
        page_text = strip_visual_and_code_content(
            document.export_to_markdown(page_no=page_number) or ""
        )
        # A page carrying only figures exports to nothing. It still has to claim
        # an offset, or every page after it would be numbered one too low.
        page_offsets.append(cursor)

        if not page_text:
            continue

        parts.append(page_text)
        cursor += len(page_text) + len(PAGE_SEPARATOR)

    if not parts:
        return None

    return PAGE_SEPARATOR.join(parts), page_offsets


def extract_text_with_docling(
    file_bytes: bytes, filename: str
) -> tuple[str, list[int]]:
    """Parses a document with Docling and returns its Markdown representation.

    Returns the text along with the offset at which each page starts, empty for a
    document Docling reports no pages for.

    This is CPU-bound and synchronous; call it from a thread (e.g. via
    ``asyncio.to_thread``) to avoid blocking the event loop.
    """
    if not file_bytes:
        raise ValueError("File is empty")

    try:
        from docling.datamodel.base_models import DocumentStream
    except ImportError as exc:
        raise DoclingUnavailableError("Docling is not installed") from exc

    converter = _get_converter()
    source = DocumentStream(
        name=filename or "document", stream=BytesIO(file_bytes)
    )

    try:
        result = converter.convert(source)
    except Exception as exc:
        # Model / conversion failures should let the caller fall back gracefully.
        raise DoclingUnavailableError(
            f"Docling failed to parse the document: {exc}"
        ) from exc

    paginated = None
    try:
        paginated = _export_by_page(result.document)
    except Exception as exc:
        # Page-by-page export is a provenance nicety, never a reason to fail a
        # parse that would otherwise have worked.
        logger.warning(
            "Docling per-page export failed, exporting as one block: %s", exc
        )

    if paginated is not None:
        text, page_offsets = paginated
    else:
        text = strip_visual_and_code_content(
            result.document.export_to_markdown() or ""
        )
        page_offsets = []

    if not text:
        raise ValueError("No extractable text found in document")

    return text, page_offsets
