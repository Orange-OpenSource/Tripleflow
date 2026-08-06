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
from typing import Optional
from app.services.triple_db_service import (
    delete_file,
    get_files,
    get_triples,
    get_file_content,
)

router = APIRouter(prefix="/files", tags=["files"])


# Returns all files with their review progress counts
@router.get("/")
def list_files():
    files = get_files()
    return {"files": files, "count": len(files)}


# Returns the stored text content of a file
@router.get("/{file_id}/content")
def get_file_text(file_id: str):
    content = get_file_content(file_id)
    if content is None:
        raise HTTPException(status_code=404, detail="File content not available")
    return {"file_id": file_id, "content": content}


# Returns all triples for a given file, with optional status filter
@router.get("/{file_id}/triples")
def list_file_triples(
    file_id: str,
    status: Optional[str] = None,
):
    triples = get_triples(file_id=file_id, status=status)
    return {"triples": triples, "count": len(triples)}


# Deletes a file and all of its triples. The reviewer name is required and audited.
@router.delete("/{file_id}")
def remove_file(file_id: str, user_name: str):
    try:
        deleted = delete_file(file_id, user_name)
        return {"message": "File deleted", **deleted}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
