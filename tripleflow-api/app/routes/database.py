"""  
Software Name : Tripleflow
SPDX-FileCopyrightText: Copyright (c) Orange SA
SPDX-License-Identifier: MIT
 
This software is distributed under the MIT License,
see the "LICENSE" file for more details or https://spdx.org/licenses/MIT.html
 
Authors: Sonia Hadjab, Antoine Py, Yoan Chabot
Software description: Tripleflow is a tool that enables semi-supervised data feeding of knowledge graphs from unstructured documents.  

"""

from fastapi import APIRouter

from app.services.triple_db_service import clear_database, get_audit_log

router = APIRouter(prefix="/database", tags=["database"])


@router.get("/audit")
def get_audit():
    """Returns the deletion audit log (who deleted what and when), most recent first."""
    return {"entries": get_audit_log()}


@router.delete("")
def reset_database(user_name: str):
    """
    Clears all review data (files and triples) from the database, keeping extractor
    configurations. Intended to reset the workspace once a review round is complete.
    The reviewer name is required and recorded in the audit log.
    """
    deleted = clear_database(user_name)
    return {"message": "Database cleared", **deleted}
