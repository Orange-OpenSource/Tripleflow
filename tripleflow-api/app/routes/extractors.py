"""  
Software Name : Tripleflow
SPDX-FileCopyrightText: Copyright (c) Orange SA
SPDX-License-Identifier: MIT
 
This software is distributed under the MIT License,
see the "LICENSE" file for more details or https://spdx.org/licenses/MIT.html
 
Authors: Sonia Hadjab, Antoine Py, Yoan Chabot
Software description: Tripleflow is a tool that enables semi-supervised data feeding of knowledge graphs from unstructured documents.  

"""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from app.schemas.extractors import (
    ExtractorConfig,
    ExtractorListResponse,
    ExtractorTestRequest,
)
from app.services.extractors_service import (
    call_custom_extractor,
    delete_extractor,
    insert_extractor,
    list_extractors,
)

router = APIRouter(prefix="/extractors", tags=["extractors"])
logger = logging.getLogger(__name__)


@router.get("", response_model=ExtractorListResponse)
def get_extractors():
    """Returns all custom extractors registered on the backend."""
    return ExtractorListResponse(extractors=list_extractors())


@router.post("")
def create_extractor(config: ExtractorConfig):
    """Registers a new custom extractor configuration."""
    try:
        created = insert_extractor(config)
        return created
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.delete("/{extractor_id}")
def remove_extractor(extractor_id: str):
    """Deletes a custom extractor by id."""
    try:
        delete_extractor(extractor_id)
        return {"ok": True}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/test")
async def test_extractor(payload: ExtractorTestRequest):
    """
    Dry-runs an extractor configuration against sample text without saving it.
    Calls the configured endpoint, applies the output mapping, and returns the
    resulting triples so the user can verify the configuration.
    """
    try:
        config_dict = payload.config.model_dump()
        triples = await call_custom_extractor(config_dict, payload.sample_text)
        return {"triples": triples}
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected error during extractor test")
        raise HTTPException(status_code=500, detail="Internal server error") from exc
