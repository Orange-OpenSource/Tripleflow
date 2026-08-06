"""  
Software Name : Tripleflow
SPDX-FileCopyrightText: Copyright (c) Orange SA
SPDX-License-Identifier: MIT
 
This software is distributed under the MIT License,
see the "LICENSE" file for more details or https://spdx.org/licenses/MIT.html
 
Authors: Sonia Hadjab, Antoine Py, Yoan Chabot
Software description: Tripleflow is a tool that enables semi-supervised data feeding of knowledge graphs from unstructured documents.  

"""

import json
import logging
from urllib.parse import quote

import httpx

from app.db import extractors_collection
from app.schemas.extractors import ExtractorConfig

logger = logging.getLogger(__name__)

HTTP_CLIENT = httpx.AsyncClient(timeout=120.0, verify=False)

# ── CRUD ────────────────────────────────────────────────────────────────────────


def _to_public(doc: dict) -> dict:
    """
    Projects a stored extractor config onto the public listing shape.
    Endpoint details (URL, headers with possible secrets, body template) are
    intentionally never re-exposed through the API.
    """
    return {
        "id": doc["id"],
        "label": doc.get("label") or doc["id"],
        "description": doc.get("description"),
        "knowledge_base": doc.get("knowledge_base"),
    }


def list_extractors() -> list[dict]:
    """Returns the extractors registered in the database."""
    return [
        _to_public(doc)
        for doc in extractors_collection.find({}, {"_id": 0})
        if doc.get("id")
    ]


def get_extractor(extractor_id: str) -> dict | None:
    """Returns a single custom extractor by id, or None."""
    doc = extractors_collection.find_one({"id": extractor_id}, {"_id": 0})
    return _doc_to_config(doc) if doc else None


def insert_extractor(config: ExtractorConfig) -> dict:
    """Validates and inserts a new custom extractor. Raises ValueError on conflict."""
    if extractors_collection.find_one({"id": config.id}):
        raise ValueError(f"An extractor with id '{config.id}' already exists")

    doc = config.model_dump()
    extractors_collection.insert_one(doc)
    return _doc_to_config(doc)


def delete_extractor(extractor_id: str) -> None:
    """Deletes a custom extractor. Raises ValueError if not found."""
    result = extractors_collection.delete_one({"id": extractor_id})
    if result.deleted_count == 0:
        raise ValueError(f"Extractor '{extractor_id}' not found")


def _doc_to_config(doc: dict) -> dict:
    """Strips MongoDB's _id and returns a plain dict."""
    doc.pop("_id", None)
    return doc


# ── Dynamic extraction ──────────────────────────────────────────────────────────


def _resolve_dot_path(data: object, path: str) -> object:
    """
    Traverses a nested dict/list using a dot-separated path.
    Supports numeric indices for lists (e.g. "results.0.triples") and a `*`
    wildcard that maps over a list and flattens one level (e.g.
    "sentences.*.openie" collects every sentence's triples into a single list).
    A path of "." refers to the document itself (top-level array responses).
    """
    if path == ".":
        return data
    return _resolve_segments(data, path.split("."))


def _resolve_segments(current: object, segments: list[str]) -> object:
    for position, segment in enumerate(segments):
        if current is None:
            return None
        if segment == "*":
            if not isinstance(current, list):
                return None
            rest = segments[position + 1:]
            flattened = []
            for element in current:
                resolved = _resolve_segments(element, rest) if rest else element
                if isinstance(resolved, list):
                    flattened.extend(resolved)
                elif resolved is not None:
                    flattened.append(resolved)
            return flattened
        if isinstance(current, dict):
            current = current.get(segment)
        elif isinstance(current, list):
            try:
                current = current[int(segment)]
            except (ValueError, IndexError):
                return None
        else:
            return None
    return current


def _resolve_first_path(data: object, path: str) -> object:
    """
    Resolves a dot-path that may list fallback alternatives separated by `|`
    (e.g. "owiki|oliteral"): the first alternative yielding a non-empty value wins.
    """
    for candidate in path.split("|"):
        candidate = candidate.strip()
        if not candidate:
            continue
        value = _resolve_dot_path(data, candidate)
        if _str(value):
            return value
    return None


def _render_body_template(template: object, text: str) -> object:
    """
    Recursively replaces {{text}} placeholders in a JSON template with the actual text.
    """
    if isinstance(template, str):
        return template.replace("{{text}}", text)
    if isinstance(template, dict):
        return {key: _render_body_template(value, text) for key, value in template.items()}
    if isinstance(template, list):
        return [_render_body_template(item, text) for item in template]
    return template


def _normalize_custom_triples(
    raw_triples: list,
    mapping: dict,
    source_label: str,
) -> list[dict]:
    """
    Converts raw extractor output into the standard triple format using the output mapping.
    """
    from app.services.extraction_service import build_triple_id

    subject_mapping = mapping["subject"]
    predicate_mapping = mapping["predicate"]
    object_mapping = mapping["object"]
    date_path = mapping.get("date")

    triples = []
    for index, item in enumerate(raw_triples):
        if not isinstance(item, dict):
            continue

        subject = {
            "label": _str(_resolve_first_path(item, subject_mapping.get("label", ""))) if subject_mapping.get("label") else "",
            "id": _str(_resolve_first_path(item, subject_mapping["id"])),
        }
        predicate = {
            "label": _str(_resolve_first_path(item, predicate_mapping.get("label", ""))) if predicate_mapping.get("label") else "",
            "id": _str(_resolve_first_path(item, predicate_mapping["id"])),
        }
        obj = {
            "label": _str(_resolve_first_path(item, object_mapping.get("label", ""))) if object_mapping.get("label") else "",
            "id": _str(_resolve_first_path(item, object_mapping["id"])),
        }

        triple = {
            "subject": subject,
            "predicate": predicate,
            "obj": obj,
            "date": (_str(_resolve_first_path(item, date_path)) or None) if date_path else None,
            "source": source_label,
            "heuristic_score": None,
            "metadata": {"raw": item},
        }
        triple["triple_id"] = build_triple_id(triple, fallback_index=index)
        triples.append(triple)

    return triples


def _str(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _build_post_kwargs(endpoint: dict, text: str, text_in_url: bool) -> dict:
    """
    Builds the httpx POST kwargs for the endpoint's body_type:
    "json" (default), "raw" (string body, text/plain unless a Content-Type
    header is set), or "form" (urlencoded key/value pairs).
    Without a body_template, the default {"text": ...} JSON body is only sent
    when the text is not already carried by the URL.
    """
    body_type = endpoint.get("body_type", "json")
    body_template = endpoint.get("body_template")

    if body_type == "raw":
        rendered = (body_template or "{{text}}").replace("{{text}}", text)
        return {"content": rendered.encode("utf-8")}

    if body_template is None:
        return {} if text_in_url else {"json": {"text": text}}

    body = _render_body_template(body_template, text)
    if body_type == "form":
        return {"data": {key: _str(value) for key, value in body.items()}}
    return {"json": body}


def _decode_embedded_json(data: object, decode_json_path: str, extractor_id: str) -> object:
    """
    Extracts a JSON document embedded as a string in the response (e.g. an LLM
    chat completion's message content), tolerating markdown code fences.
    """
    raw = _resolve_dot_path(data, decode_json_path)
    if not isinstance(raw, str):
        raise RuntimeError(
            f"Custom extractor '{extractor_id}': decode_json_path '{decode_json_path}' "
            "did not resolve to a string in the response"
        )

    stripped = raw.strip()
    if stripped.startswith("```"):
        stripped = stripped.split("\n", 1)[1] if "\n" in stripped else ""
        stripped = stripped.rsplit("```", 1)[0].strip()

    try:
        return json.loads(stripped)
    except ValueError:
        raise RuntimeError(
            f"Custom extractor '{extractor_id}': the value at decode_json_path "
            f"'{decode_json_path}' is not valid JSON"
        )


async def call_custom_extractor(config: dict, text: str) -> list[dict]:
    """
    Calls a custom extractor endpoint with the given text, parses the response
    using the output mapping, and returns normalized triples.
    """
    endpoint = config["endpoint"]
    url = endpoint["url"]
    method = endpoint.get("method", "POST").upper()
    headers = endpoint.get("headers") or {}
    # Configs stored before timeout_seconds existed fall back to the historical
    # 120s client default so slow extractors already registered keep working.
    timeout = endpoint.get("timeout_seconds") or 120.0
    output_mapping = config["output_mapping"]
    source_label = config.get("label", config["id"]).upper()

    # The URL itself may carry the text as a query parameter, e.g.
    # https://service.example/api?text={{text}}&nel=true
    text_in_url = "{{text}}" in url
    if text_in_url:
        url = url.replace("{{text}}", quote(text, safe=""))

    try:
        if method == "POST":
            post_kwargs = _build_post_kwargs(endpoint, text, text_in_url)
            response = await HTTP_CLIENT.post(url, headers=headers, timeout=timeout, **post_kwargs)
        else:
            params = None if text_in_url else {"text": text}
            response = await HTTP_CLIENT.get(url, params=params, headers=headers, timeout=timeout)
    except httpx.TimeoutException:
        raise RuntimeError(
            f"Custom extractor '{config['id']}' timed out after {timeout}s calling {url}. "
            "Increase the extractor's timeout if the endpoint is slow."
        )
    except httpx.RequestError as exc:
        raise RuntimeError(
            f"Custom extractor '{config['id']}' request error: {exc}. "
            "Check VPN/intranet access, DNS resolution, and the configured URL."
        )

    if response.status_code != 200:
        body_text = response.text[:300] if response.text else "empty response"
        raise RuntimeError(
            f"Custom extractor '{config['id']}' returned HTTP {response.status_code}: {body_text}"
        )

    try:
        data = response.json()
    except ValueError:
        raise RuntimeError(f"Custom extractor '{config['id']}' returned invalid JSON")

    decode_json_path = output_mapping.get("decode_json_path")
    if decode_json_path:
        data = _decode_embedded_json(data, decode_json_path, config["id"])

    triples_path = output_mapping["triples_path"]
    raw_triples = _resolve_dot_path(data, triples_path)

    if not isinstance(raw_triples, list):
        raise RuntimeError(
            f"Custom extractor '{config['id']}': "
            f"triples_path '{triples_path}' did not resolve to a list in the response"
        )

    return _normalize_custom_triples(raw_triples, output_mapping, source_label)
