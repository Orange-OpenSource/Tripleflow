"""
Software Name : Tripleflow
SPDX-FileCopyrightText: Copyright (c) Orange SA
SPDX-License-Identifier: MIT

This software is distributed under the MIT License,
see the "LICENSE" file for more details or https://spdx.org/licenses/MIT.html

Authors: Sonia Hadjab, Antoine Py, Yoan Chabot
Software description: Tripleflow is a tool that enables semi-supervised data feeding of knowledge graphs from unstructured documents.

"""

import asyncio
import hashlib
import logging
import re

from fastapi import APIRouter, HTTPException, Request, UploadFile
from app.services.triple_db_service import save_triples
from pydantic import ValidationError

from app.schemas.extraction import (
    ExtractionBatchItem,
    ExtractionRequest,
    ExtractionResponse,
    ExtractionResponseData,
)
from app.services.chunking_service import (
    chunk_text,
    resolve_page,
    whole_text_chunk,
)
from app.services.extraction_service import (
    ExternalServiceError,
    ExternalServiceTimeoutError,
    apply_heuristic_scores,
    dedupe_triples,
    extract_text_from_pdf_bytes,
    extract_text_from_txt_bytes,
    extract_triples,
)
from app.services.docling_service import (
    DoclingUnavailableError,
    docling_enabled,
    docling_supports,
    extract_text_with_docling,
)

router = APIRouter()
logger = logging.getLogger(__name__)
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
# Simultaneous extractor calls allowed for the chunks of a single text.
CHUNK_CONCURRENCY = 4
COMBINED_TEXT_HEADER_RE = re.compile(r"^---\s+(.+?)\s+---\n", re.MULTILINE)


# Turns validation errors into a single readable message
def _validation_error_message(exc: ValidationError) -> str:
    details = []
    for error in exc.errors():
        field_name = (
            ".".join(str(part) for part in error.get("loc", [])) or "request"
        )
        error_type = error.get("type")

        if field_name == "extractor" and error_type == "literal_error":
            details.append("'extractor' must be a valid extractor name")
            continue

        if field_name == "text" and error_type == "string_too_short":
            details.append("'text' is required")
            continue

        if field_name == "text" and error_type == "string_too_long":
            details.append("'text' must be at most 50000 characters")
            continue

        if field_name.startswith("texts") and error_type == "string_too_short":
            details.append("Each item in 'texts' is required")
            continue

        if field_name.startswith("texts") and error_type == "string_too_long":
            details.append(
                "Each item in 'texts' must be at most 50000 characters"
            )
            continue

        if field_name == "texts" and error_type == "too_short":
            details.append("'texts' must contain at least one item")
            continue

        if field_name == "request" and error_type == "value_error":
            details.append(error.get("msg", "invalid value"))
            continue

        details.append(f"{field_name}: {error.get('msg', 'invalid value')}")

    return "; ".join(details) or "Invalid request payload"


# Validates the incoming request payload and raises a clear error if invalid
def _validate_extractor_payload(
    payload: dict[str, object],
) -> ExtractionRequest:
    try:
        return ExtractionRequest.model_validate(payload)
    except ValidationError as exc:
        raise ValueError(_validation_error_message(exc)) from exc


# Splits a combined text (containing multiple files) into individual parts
def _split_combined_file_text(text: str) -> list[str] | None:
    matches = list(COMBINED_TEXT_HEADER_RE.finditer(text))
    if len(matches) < 2:
        return None

    parts: list[str] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = (
            matches[index + 1].start()
            if index + 1 < len(matches)
            else len(text)
        )
        part = text[start:end].strip()
        if part:
            parts.append(part)

    return parts if len(parts) >= 2 else None


_chunk_semaphore = None


# Shared by every request, so uploading five documents at once cannot multiply
# the number of simultaneous extractor calls. Created on first use, inside the
# running loop.
def _get_chunk_semaphore() -> asyncio.Semaphore:
    global _chunk_semaphore

    if _chunk_semaphore is None:
        _chunk_semaphore = asyncio.Semaphore(CHUNK_CONCURRENCY)

    return _chunk_semaphore


# Stamps every triple with the passage it came from: the chunk it was extracted
# from, that chunk's offsets in the document, and the page those offsets fall on.
# This is what lets the validation interface point at the exact source passage.
def _tag_location(
    triples: list, chunk: dict, page_offsets: list[int] | None
) -> list:
    location = {
        "chunk_id": chunk["chunk_id"],
        "start": chunk["start"],
        "end": chunk["end"],
        "page": resolve_page(chunk["start"], page_offsets),
    }

    for triple in triples:
        triple["chunk"] = dict(location)

    return triples


# Runs the extractor on every chunk of a text and merges the results.
# Chunks are processed concurrently, but the semaphore keeps a long document from
# firing dozens of simultaneous calls at the extractor.
async def _extract_chunked_triples(
    text: str,
    extractor: str,
    chunk_size: int,
    chunk_overlap: int,
    page_offsets: list[int] | None = None,
) -> tuple[list, int]:
    chunks = chunk_text(text, chunk_size, chunk_overlap)

    if not chunks:
        return [], 0

    if len(chunks) == 1:
        triples = await extract_triples(chunks[0]["text"], extractor)
        return _tag_location(triples, chunks[0], page_offsets), 1

    semaphore = _get_chunk_semaphore()

    async def extract_chunk(chunk: dict):
        async with semaphore:
            triples = await extract_triples(chunk["text"], extractor)
            return _tag_location(triples, chunk, page_offsets)

    results = await asyncio.gather(
        *(extract_chunk(chunk) for chunk in chunks),
        return_exceptions=True,
    )

    triples = []
    failures = []

    for index, result in enumerate(results):
        if isinstance(result, BaseException):
            logger.warning(
                "Chunk %s failed during extraction: %s", index, result
            )
            failures.append(result)
            continue

        triples.extend(result)

    # A partial result is still useful; only give up when every chunk failed.
    if failures and not triples:
        raise failures[0]

    return dedupe_triples(triples), len(chunks)


# Extracts triples from a text, scores them heuristically, saves them and returns the result
async def build_extraction_response(
    text: str,
    extractor: str,
    file_name: str = "manual-input",
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
    page_offsets: list[int] | None = None,
) -> ExtractionResponse:
    chunk_count = None

    if chunk_size is not None:
        triples, chunk_count = await _extract_chunked_triples(
            text,
            extractor,
            chunk_size,
            chunk_overlap if chunk_overlap is not None else 0,
            page_offsets=page_offsets,
        )
    else:
        triples = await extract_triples(text, extractor)
        # Without the chunking step the whole document is the passage, so a
        # triple still carries a span — one covering the entire text.
        whole = whole_text_chunk(text)
        if whole is not None:
            _tag_location(triples, whole, page_offsets)

    triples = apply_heuristic_scores(triples)

    save_triples(
        triples=triples,
        file_name=file_name,
        file_id=hashlib.sha256(file_name.encode()).hexdigest()[:16],
        extractor=extractor,
        text=text,
    )

    return ExtractionResponse(
        result={
            "triples": triples,
            "chunk_count": chunk_count,
        }
    )


# Processes a single text in a batch and returns its result or an error
async def build_batch_extraction_item(
    text: str,
    extractor: str,
    index: int,
    file_name: str = "manual-input",
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
    page_offsets: list[int] | None = None,
) -> ExtractionBatchItem:
    try:
        response = await build_extraction_response(
            text,
            extractor,
            file_name=file_name,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            page_offsets=page_offsets,
        )
    except ValueError as exc:
        return ExtractionBatchItem(
            index=index,
            status="error",
            error=str(exc),
        )
    except ExternalServiceTimeoutError as exc:
        return ExtractionBatchItem(
            index=index,
            status="error",
            error=str(exc),
        )
    except ExternalServiceError as exc:
        return ExtractionBatchItem(
            index=index,
            status="error",
            error=str(exc),
        )
    except Exception:
        logger.exception(
            "Unexpected backend error during batch extraction item %s", index
        )
        return ExtractionBatchItem(
            index=index,
            status="error",
            error="Internal server error",
        )

    return ExtractionBatchItem(
        index=index,
        status="ok",
        triples=response.result.triples,
        chunk_count=response.result.chunk_count,
    )


# Processes multiple texts in parallel and returns all results
async def build_batch_extraction_response(
    texts: list[str],
    extractor: str,
    file_names: list[str] | None = None,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
    page_offsets_list: list[list[int]] | None = None,
) -> ExtractionResponse:
    resolved = file_names or []
    resolved_pages = page_offsets_list or []
    tasks = [
        build_batch_extraction_item(
            text,
            extractor,
            index,
            file_name=(
                resolved[index]
                if index < len(resolved)
                else f"file_{index + 1}"
            ),
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            page_offsets=(
                resolved_pages[index] if index < len(resolved_pages) else None
            ),
        )
        for index, text in enumerate(texts)
    ]
    items = await asyncio.gather(*tasks)
    triples = [
        triple
        for item in items
        if item.status == "ok"
        for triple in item.triples
    ]
    chunk_counts = [item.chunk_count for item in items if item.chunk_count]

    return ExtractionResponse(
        result=ExtractionResponseData(
            triples=triples,
            items=items,
            chunk_count=sum(chunk_counts) if chunk_counts else None,
        )
    )


# Reads and returns the text content from an uploaded document, along with the
# offset at which each of its pages starts (empty for unpaginated formats).
# Docling handles rich formats (PDF, DOCX, PPTX, XLSX, HTML, images...); plain
# text and PDFs keep a lightweight fallback if Docling is disabled or fails.
async def extract_text_from_uploaded_file(
    file: UploadFile,
) -> tuple[str, list[int], str]:
    content_type = (file.content_type or "").lower()
    filename = (file.filename or "").lower()
    file_bytes = await file.read()

    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise ValueError("File is too large. Maximum size is 10 MB")

    is_pdf = content_type == "application/pdf" or filename.endswith(".pdf")
    is_txt = content_type == "text/plain" or filename.endswith(".txt")
    parser = "pypdf" if is_pdf else "plain-text"

    if docling_enabled() and docling_supports(filename, content_type):
        try:
            text, offsets = await asyncio.to_thread(
                extract_text_with_docling,
                file_bytes,
                file.filename or filename,
            )
            return text, offsets, "docling"
        except DoclingUnavailableError as exc:
            # Docling missing or conversion failed: fall back when we can.
            if is_pdf:
                logger.warning(
                    "Docling unavailable, falling back to pypdf: %s", exc
                )
                parser = f"pypdf (Docling unavailable: {exc})"
            elif not is_txt:
                raise ValueError(
                    "Unable to parse this document. Docling is unavailable."
                ) from exc

    if is_pdf:
        text, offsets = extract_text_from_pdf_bytes(file_bytes)
        return text, offsets, parser

    if is_txt:
        return extract_text_from_txt_bytes(file_bytes), [], parser

    raise ValueError("Unsupported file type")


# Parse-only endpoint — extracts the text of an uploaded document (via Docling
# when available) without running any extractor. Lets the front preview and edit
# the parsed content before choosing extractors.
@router.post("/parse")
async def parse_uploaded_file(file: UploadFile):
    try:
        content, page_offsets, parser = await extract_text_from_uploaded_file(
            file
        )
        return {
            "name": file.filename or "document",
            "content": content,
            # Offsets travel with the text: the front sends them back at
            # extraction time so chunks can be resolved to a page number.
            "page_offsets": page_offsets,
            "parser": parser,
        }
    except ValueError as e:
        logger.info("Invalid parse request: %s", str(e))
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected backend error during document parsing")
        raise HTTPException(
            status_code=500,
            detail="Internal server error",
        ) from e


# Main endpoint — handles extraction requests from JSON or file upload
@router.post("/extract", response_model=ExtractionResponse)
async def run_extraction(req: Request):
    try:
        content_type = (req.headers.get("content-type") or "").lower()

        if "application/json" in content_type:
            payload = await req.json()
            validated_payload = _validate_extractor_payload(payload)
            if validated_payload.text is not None:
                split_texts = _split_combined_file_text(validated_payload.text)
                if split_texts is not None:
                    return await build_batch_extraction_response(
                        split_texts,
                        validated_payload.extractor,
                        chunk_size=validated_payload.chunk_size,
                        chunk_overlap=validated_payload.chunk_overlap,
                    )

                return await build_extraction_response(
                    validated_payload.text,
                    validated_payload.extractor,
                    file_name=validated_payload.file_name or "manual-input",
                    chunk_size=validated_payload.chunk_size,
                    chunk_overlap=validated_payload.chunk_overlap,
                    page_offsets=validated_payload.page_offsets,
                )

            return await build_batch_extraction_response(
                validated_payload.texts or [],
                validated_payload.extractor,
                file_names=validated_payload.file_names,
                chunk_size=validated_payload.chunk_size,
                chunk_overlap=validated_payload.chunk_overlap,
                page_offsets_list=validated_payload.page_offsets_list,
            )

        if "multipart/form-data" in content_type:
            form = await req.form()
            file = form.get("file")
            validated_payload = _validate_extractor_payload(
                {
                    "text": "uploaded-file",
                    "extractor": form.get("extractor"),
                }
            )

            if file is None:
                raise ValueError("A file is required")

            text, page_offsets, _ = await extract_text_from_uploaded_file(file)
            return await build_extraction_response(
                text,
                validated_payload.extractor,
                file_name=file.filename or "manual-input",
                page_offsets=page_offsets,
            )

        raise ValueError(
            "Unsupported content type. Use application/json or multipart/form-data"
        )
    except ValueError as e:
        logger.info("Invalid extraction request: %s", str(e))
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ExternalServiceTimeoutError as e:
        logger.warning("External extraction service timeout: %s", str(e))
        raise HTTPException(
            status_code=504,
            detail=str(e),
        ) from e
    except ExternalServiceError as e:
        logger.warning("External extraction service error: %s", str(e))
        raise HTTPException(
            status_code=503,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.exception("Unexpected backend error during extraction")
        raise HTTPException(
            status_code=500,
            detail="Internal server error",
        ) from e
