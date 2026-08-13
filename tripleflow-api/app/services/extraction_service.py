"""  
Software Name : Tripleflow
SPDX-FileCopyrightText: Copyright (c) Orange SA
SPDX-License-Identifier: MIT
 
This software is distributed under the MIT License,
see the "LICENSE" file for more details or https://spdx.org/licenses/MIT.html
 
Authors: Sonia Hadjab, Antoine Py, Yoan Chabot
Software description: Tripleflow is a tool that enables semi-supervised data feeding of knowledge graphs from unstructured documents.  

"""

import hashlib
import logging
import re
from io import BytesIO

from pypdf import PdfReader

from app.services.extractors_service import call_custom_extractor, get_extractor

logger = logging.getLogger(__name__)

JSONPrimitive = str | int | float | bool | None
JSONValue = JSONPrimitive | dict[str, "JSONValue"] | list["JSONValue"]
JSONObject = dict[str, JSONValue]
TripleDict = dict[str, JSONValue]


class ExternalServiceError(RuntimeError):
    """Raised when an external service returns an error."""


class ExternalServiceTimeoutError(ExternalServiceError):
    """Raised when an external service request times out."""


async def extract_triples(text: str, extractor: str) -> list[TripleDict]:
    """Looks up the extractor registered under this id and returns the extracted triples."""
    text = text.strip()
    extractor = extractor.strip().lower()

    if not text:
        raise ValueError("Text is required")


    config = get_extractor(extractor)
    if config is None:
        raise ValueError(f"Unknown extractor: {extractor}")

    return await call_custom_extractor(config, text)


PAGE_SEPARATOR = "\n\n"


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> tuple[str, list[int]]:
    """Extracts readable text from a PDF file given as bytes.

    Returns the text and the offset at which each page starts, so a triple
    extracted from it can later be traced back to a page.
    """
    if not pdf_bytes:
        raise ValueError("PDF file is empty")

    try:
        reader = PdfReader(BytesIO(pdf_bytes))
    except Exception as exc:
        raise ValueError("Invalid PDF file") from exc

    pages_text: list[str] = []
    page_offsets: list[int] = []
    cursor = 0

    for page in reader.pages:
        page_text = (page.extract_text() or "").strip()
        # A page with no extractable text still claims its offset, or every page
        # after it would be numbered one too low.
        page_offsets.append(cursor)

        if not page_text:
            continue

        pages_text.append(page_text)
        cursor += len(page_text) + len(PAGE_SEPARATOR)

    text = PAGE_SEPARATOR.join(pages_text)

    if not text:
        raise ValueError("No extractable text found in PDF")

    return text, page_offsets


def extract_text_from_txt_bytes(file_bytes: bytes) -> str:
    """Decodes a TXT file given as bytes and returns its text content."""
    if not file_bytes:
        raise ValueError("Text file is empty")

    for encoding in ("utf-8", "latin-1"):
        try:
            text = file_bytes.decode(encoding).strip()
        except UnicodeDecodeError:
            continue

        if text:
            return text

    raise ValueError("Unable to decode text file")


def first_clean_value(*values: object) -> str:
    """Returns the first non-empty cleaned value from a list of candidates."""
    for value in values:
        cleaned = clean_value(value)
        if cleaned:
            return cleaned

    return ""


def clean_value(value: object) -> str:
    """Converts any value to a stripped string, returns empty string if None."""
    if value is None:
        return ""

    return str(value).strip()


def normalize_date(value: object) -> str | None:
    """Cleans a date value and returns it as a string, or None if empty."""
    cleaned = clean_value(value)
    if not cleaned:
        return None
    return cleaned


def build_triple_id(
    triple: TripleDict, fallback_index: int | None = None
) -> str:
    """Generates a unique ID for a triple based on its subject, predicate, object and source."""
    subject = node_value(triple.get("subject", {}))
    predicate = node_value(triple.get("predicate", {}))
    obj = node_value(triple.get("obj", {}))
    date = normalize_date(triple.get("date")) or ""
    source = clean_value(triple.get("source"))
    fallback = "" if fallback_index is None else str(fallback_index)
    fingerprint = "||".join([source, subject, predicate, obj, date, fallback])
    digest = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()[:16]
    return f"triple_{digest}"


def node_id(node: object) -> str:
    """Returns the ID of a node (QID, PID, etc.) if available."""
    if not isinstance(node, dict):
        return clean_value(node)

    return first_clean_value(
        node.get("id"),
        node.get("qid"),
        node.get("pid"),
        node.get("p"),
    )


def node_label(node: object) -> str:
    """Returns the human-readable label of a node."""
    if not isinstance(node, dict):
        return clean_value(node)

    return first_clean_value(
        node.get("label"),
        node.get("name"),
        node.get("value"),
        node_id(node),
    )


def node_value(node: object) -> str:
    """Returns the best available value for a node (ID first, then label)."""
    return node_id(node) or node_label(node)


def dedupe_triples(triples: list[TripleDict]) -> list[TripleDict]:
    """Drops triples repeated across chunks, keeping the first occurrence.

    Overlapping chunks make duplicates expected, and they cannot be caught by
    triple_id: build_triple_id mixes in the position of the triple, so the same
    fact found in two chunks would get two different IDs.
    """
    seen: set[tuple[str, str, str, str]] = set()
    unique: list[TripleDict] = []

    for triple in triples:
        fingerprint = (
            node_value(triple.get("subject", {})).lower(),
            node_value(triple.get("predicate", {})).lower(),
            node_value(triple.get("obj", {})).lower(),
            normalize_date(triple.get("date")) or "",
        )

        if fingerprint in seen:
            continue

        seen.add(fingerprint)
        unique.append(triple)

    return unique


_QID_RE = re.compile(r"^Q\d+$", re.IGNORECASE)
_PID_RE = re.compile(r"^P\d+$", re.IGNORECASE)


def _compute_heuristic_score(triple: TripleDict) -> float:
    """Estimates a confidence score based on how many nodes have a Wikidata ID.

    Each of the three parts counts only when its identifier has the shape the
    knowledge base gives it: Q### for the entities, P### for the predicate. An
    object carrying anything else — a literal, a raw string an extractor could
    not align — is not resolved, and must not inflate the score.
    """
    resolved = sum([
        bool(_QID_RE.match(node_id(triple.get("subject", {})))),
        bool(_PID_RE.match(node_id(triple.get("predicate", {})))),
        bool(_QID_RE.match(node_id(triple.get("obj", {})))),
    ])

    scores = {0: 0.20, 1: 0.45, 2: 0.65, 3: 0.85}
    return scores[resolved]


def apply_heuristic_scores(triples: list[TripleDict]) -> list[TripleDict]:
    """Assigns each triple a stable ID and its heuristic confidence score."""
    scored_triples: list[TripleDict] = []

    for index, triple in enumerate(triples):
        triple_copy = dict(triple)
        triple_copy["triple_id"] = clean_value(
            triple_copy.get("triple_id")
        ) or build_triple_id(triple_copy, fallback_index=index)
        triple_copy["heuristic_score"] = _compute_heuristic_score(triple_copy)
        scored_triples.append(triple_copy)

    return scored_triples
