"""  
Software Name : Tripleflow
SPDX-FileCopyrightText: Copyright (c) Orange SA
SPDX-License-Identifier: MIT
 
This software is distributed under the MIT License,
see the "LICENSE" file for more details or https://spdx.org/licenses/MIT.html
 
Authors: Sonia Hadjab, Antoine Py, Yoan Chabot
Software description: Tripleflow is a tool that enables semi-supervised data feeding of knowledge graphs from unstructured documents.  

"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.services.triple_db_service import (
    get_triples,
    update_triple_status,
)

router = APIRouter(prefix="/triples", tags=["triples"])


class UpdateTripleRequest(BaseModel):
    triple_id: str
    status: str
    user_id: str
    user_name: str
    comment: Optional[str] = None
    modified_triple: Optional[dict] = None


# Returns triples with optional filters by status, file or extractor
@router.get("/")
def list_triples(
    status: Optional[str] = None,
    file_id: Optional[str] = None,
    extractor: Optional[str] = None,
):

    triples = get_triples(status=status, file_id=file_id, extractor=extractor)
    return {"triples": triples, "count": len(triples)}


# Updates the validation status of a triple (validated, rejected, needs_review)
@router.patch("/validate")
def validate_triple(req: UpdateTripleRequest):
    allowed_statuses = {"validated", "rejected", "needs_review"}
    if req.status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Status must be one of: {allowed_statuses}",
        )

    success = update_triple_status(
        triple_id=req.triple_id,
        status=req.status,
        user_id=req.user_id,
        user_name=req.user_name,
        comment=req.comment,
        modified_triple=req.modified_triple,
    )

    if not success:
        raise HTTPException(status_code=404, detail="Triple not found")

    return {"message": "Triple updated successfully"}
