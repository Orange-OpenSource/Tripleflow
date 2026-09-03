"""
Software Name : Tripleflow
SPDX-FileCopyrightText: Copyright (c) Orange SA
SPDX-License-Identifier: MIT

This software is distributed under the MIT License,
see the "LICENSE" file for more details or https://spdx.org/licenses/MIT.html

Authors: Sonia Hadjab, Antoine Py, Yoan Chabot
Software description: Tripleflow is a tool that enables semi-supervised data feeding of knowledge graphs from unstructured documents.

"""

import os

import httpx
from fastapi import APIRouter, HTTPException, Query

router = APIRouter()

# Public Wikidata search API, used when the extractor's knowledge base is
# "wikidata" (or when no extractor is specified).
WIKIDATA_SEARCH_API_URL = "https://www.wikidata.org/w/api.php"

# Wikimedia's robot policy requires callers to identify themselves, and answers
# 403 to those that do not. Deployments should put a contact address in here:
# https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_User-Agent_Policy
USER_AGENT = os.getenv(
    "TRIPLEFLOW_USER_AGENT",
    "TripleFlow/1.0 (open-source knowledge graph construction tool)",
)

HTTP_CLIENT = httpx.AsyncClient(
    timeout=10.0,
    headers={"User-Agent": USER_AGENT},
    # TLS verification is disabled to get through the corporate proxy, whose
    # interception certificate is not in the container's CA bundle.
    verify=False,
)


def _resolve_search_api_url(extractor_id: str | None) -> str | None:
    """
    Returns the MediaWiki api.php URL to search against for this extractor:
    the public Wikidata API for "wikidata" knowledge bases, the optional
    search_api_url declared on the extractor for other Wikibase instances,
    or None when the knowledge base declares no search API.
    """
    if not extractor_id:
        return WIKIDATA_SEARCH_API_URL

    from app.services.extractors_service import get_extractor

    config = get_extractor(extractor_id.strip().lower()) or {}
    knowledge_base = config.get("knowledge_base") or {}

    if knowledge_base.get("type", "wikidata") == "wikidata":
        return WIKIDATA_SEARCH_API_URL

    return (knowledge_base.get("search_api_url") or "").strip() or None


# Searches for entities or properties in the knowledge base declared by the extractor
@router.get("/search/entities")
async def search_entities(
    q: str = Query(..., min_length=1),
    type: str = Query("item", pattern="^(item|property)$"),
    limit: int = Query(10, ge=1, le=20),
    extractor: str | None = Query(None),
):
    search_api_url = _resolve_search_api_url(extractor)
    if not search_api_url:
        raise HTTPException(
            status_code=503,
            detail="This extractor's knowledge base declares no search API",
        )

    params = {
        "action": "wbsearchentities",
        "search": q,
        "language": "en",
        "format": "json",
        "type": type,
        "limit": limit,
    }

    try:
        response = await HTTP_CLIENT.get(search_api_url, params=params)
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=503, detail=f"Entity search API unreachable: {exc}"
        )

    if response.status_code != 200:
        print(
            f"[search] Entity search API {response.status_code}: {response.text[:500]}"
        )
        raise HTTPException(
            status_code=502,
            detail=f"Entity search API returned {response.status_code}: {response.text[:300]}",
        )

    data = response.json()
    results = [
        {
            "id": hit.get("id", ""),
            "label": hit.get("label", ""),
            "description": hit.get("description", ""),
        }
        for hit in data.get("search", [])
    ]

    return {"results": results}
