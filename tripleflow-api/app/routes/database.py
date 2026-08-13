"""
Software Name : Tripleflow
SPDX-FileCopyrightText: Copyright (c) Orange SA
SPDX-License-Identifier: MIT

This software is distributed under the MIT License,
see the "LICENSE" file for more details or https://spdx.org/licenses/MIT.html

Authors: Sonia Hadjab, Antoine Py, Yoan Chabot
Software description: Tripleflow is a tool that enables semi-supervised data feeding of knowledge graphs from unstructured documents.

"""

from fastapi import APIRouter, Query

from app.db import AUDIT_MAX_ENTRIES
from app.services.triple_db_service import clear_database, get_audit_log

router = APIRouter(prefix="/database", tags=["database"])


@router.get("/audit")
def get_audit(
    limit: int = Query(
        default=min(200, AUDIT_MAX_ENTRIES), ge=1, le=AUDIT_MAX_ENTRIES
    )
):
    """
    Returns the audit log (who deleted or published what, and when), most recent first.
    The log itself is capped at `max_entries`, which is returned so a caller can say
    whether it is looking at the whole history or only its tail.
    """
    return {"entries": get_audit_log(limit), "max_entries": AUDIT_MAX_ENTRIES}


@router.delete("")
def reset_database(user_name: str):
    """
    Clears all review data (files and triples) from the database, keeping extractor
    configurations. Intended to reset the workspace once a review round is complete.
    The reviewer name is required and recorded in the audit log.
    """
    deleted = clear_database(user_name)
    return {"message": "Database cleared", **deleted}
