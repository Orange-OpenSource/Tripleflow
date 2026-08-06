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
from app.services.extraction_service import (
    ExternalServiceError,
    ExternalServiceTimeoutError,
    apply_heuristic_scores,
    extract_text_from_pdf_bytes,
    extract_text_from_txt_bytes,
    extract_triples,
)

router = APIRouter()
logger = logging.getLogger(__name__)
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
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


# Extracts triples from a text, scores them heuristically, saves them and returns the result
async def build_extraction_response(
    text: str,
    extractor: str,
    file_name: str = "manual-input",
) -> ExtractionResponse:
    triples = await extract_triples(text, extractor)
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
        }
    )


# Processes a single text in a batch and returns its result or an error
async def build_batch_extraction_item(
    text: str,
    extractor: str,
    index: int,
    file_name: str = "manual-input",
) -> ExtractionBatchItem:
    try:
        response = await build_extraction_response(text, extractor, file_name=file_name)
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
    )


# Processes multiple texts in parallel and returns all results
async def build_batch_extraction_response(
    texts: list[str],
    extractor: str,
    file_names: list[str] | None = None,
) -> ExtractionResponse:
    resolved = file_names or []
    tasks = [
        build_batch_extraction_item(
            text,
            extractor,
            index,
            file_name=resolved[index] if index < len(resolved) else f"file_{index + 1}",
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

    return ExtractionResponse(
        result=ExtractionResponseData(
            triples=triples,
            items=items,
        )
    )


# Reads and returns the text content from an uploaded PDF or TXT file
async def extract_text_from_uploaded_file(file: UploadFile) -> str:
    content_type = (file.content_type or "").lower()
    filename = (file.filename or "").lower()
    file_bytes = await file.read()

    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise ValueError("File is too large. Maximum size is 10 MB")

    if content_type == "application/pdf" or filename.endswith(".pdf"):
        return extract_text_from_pdf_bytes(file_bytes)

    if content_type == "text/plain" or filename.endswith(".txt"):
        return extract_text_from_txt_bytes(file_bytes)

    raise ValueError("Only TXT and PDF files are supported")


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
                    )

                return await build_extraction_response(
                    validated_payload.text,
                    validated_payload.extractor,
                    file_name=validated_payload.file_name or "manual-input",
                )

            return await build_batch_extraction_response(
                validated_payload.texts or [],
                validated_payload.extractor,
                file_names=validated_payload.file_names,
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

            text = await extract_text_from_uploaded_file(file)
            return await build_extraction_response(
                text,
                validated_payload.extractor,
                file_name=file.filename or "manual-input",
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
