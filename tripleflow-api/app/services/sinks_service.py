import json
import logging
import re
import uuid
from datetime import datetime, timezone
from urllib.parse import urlencode

import httpx

from app.db import sinks_collection
from app.schemas.sinks import PLACEHOLDER_RE, SinkConfig

# Same dot-path semantics as the extractor registry uses to read an arbitrary
# response. One implementation, so a path means the same thing on both sides.
from app.services.extractors_service import _resolve_dot_path

logger = logging.getLogger(__name__)

# Own client rather than the extractors' shared one: this is a write path, so TLS
# certificates are verified. A sink behind a private CA needs that CA trusted by
# the container (SSL_CERT_FILE), not verification turned off.
HTTP_CLIENT = httpx.AsyncClient(timeout=60.0)

ITEM_ID_RE = re.compile(r"^Q\d+$", re.IGNORECASE)
PROPERTY_ID_RE = re.compile(r"^P\d+$", re.IGNORECASE)

# ── CRUD ────────────────────────────────────────────────────────────────────────


def _to_public(doc: dict) -> dict:
    """
    Projects a stored sink config onto the public listing shape. Auth credentials
    are intentionally never re-exposed through the API; only the auth *type* is,
    so the UI can show how the sink authenticates. Header names are listed for the
    same reason — a name tells the UI a token is configured, the value never
    leaves the backend.
    """
    auth = doc.get("auth") or {}
    header_names = sorted(
        {*(doc.get("headers") or {}), *(auth.get("headers") or {})}
    )
    request_config = doc.get("request") or {}
    return {
        "id": doc["id"],
        "label": doc.get("label") or doc["id"],
        "description": doc.get("description"),
        "type": doc.get("type") or "sparql",
        "update_url": doc.get("update_url"),
        "request_url": request_config.get("url"),
        "request_method": request_config.get("method"),
        "prepare_steps": [
            step.get("name", "") for step in (doc.get("prepare") or [])
        ],
        "graph_uri": doc.get("graph_uri"),
        "namespaces": doc.get("namespaces") or {},
        "knowledge_base": doc.get("knowledge_base") or {},
        "auth_type": auth.get("type", "none"),
        "header_names": header_names,
        "body_format": doc.get("body_format") or "sparql-update",
        "prefixes": doc.get("prefixes"),
        "update_template": doc.get("update_template"),
    }


def list_sinks() -> list[dict]:
    """Returns the publication targets registered in the database."""
    return [
        _to_public(doc)
        for doc in sinks_collection.find({}, {"_id": 0})
        if doc.get("id")
    ]


def get_sink(sink_id: str) -> dict | None:
    """Returns a single sink by id, credentials included, or None."""
    doc = sinks_collection.find_one({"id": sink_id}, {"_id": 0})
    return doc or None


def insert_sink(config: SinkConfig) -> dict:
    """Validates and inserts a new sink. Raises ValueError on conflict."""
    if sinks_collection.find_one({"id": config.id}):
        raise ValueError(f"A target with id '{config.id}' already exists")

    doc = config.model_dump()
    sinks_collection.insert_one(dict(doc))
    return _to_public(doc)


def delete_sink(sink_id: str) -> None:
    """Deletes a sink. Raises ValueError if not found."""
    result = sinks_collection.delete_one({"id": sink_id})
    if result.deleted_count == 0:
        raise ValueError(f"Target '{sink_id}' not found")


# ── SPARQL UPDATE building ──────────────────────────────────────────────────────


def _entity_id(node: object) -> str:
    """Returns a triple node's entity ID, tolerating missing or malformed nodes."""
    if not isinstance(node, dict):
        return ""
    return str(node.get("id") or "").strip()


def _triple_iris(
    triple: dict, namespaces: dict
) -> tuple[str, str, str] | None:
    """
    Maps a triple's subject/predicate/object IDs onto absolute IRIs.
    Returns None when any node lacks a well-formed Wikibase-style ID: those
    triples cannot be expressed in the target graph and are reported as skipped
    instead of being silently dropped.
    """
    item_base = (
        namespaces.get("item_base_uri") or "http://www.wikidata.org/entity/"
    )
    property_base = (
        namespaces.get("property_base_uri")
        or "http://www.wikidata.org/prop/direct/"
    )

    subject_id = _entity_id(triple.get("subject"))
    predicate_id = _entity_id(triple.get("predicate"))
    object_id = _entity_id(triple.get("obj"))

    if not (
        ITEM_ID_RE.match(subject_id)
        and PROPERTY_ID_RE.match(predicate_id)
        and ITEM_ID_RE.match(object_id)
    ):
        return None

    return (
        f"{item_base}{subject_id.upper()}",
        f"{property_base}{predicate_id.upper()}",
        f"{item_base}{object_id.upper()}",
    )


def _is_safe_iri(iri: str) -> bool:
    """
    Rejects any IRI that could break out of a SPARQL <…> term. IDs are already
    constrained to Q/P + digits and bases are validated at config time, so this
    is a last line of defence rather than the primary one.
    """
    return (
        not any(char in iri for char in ' <>"{}|\\^`')
        and "\n" not in iri
        and "\r" not in iri
    )


_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")


def _escape_literal(value: str) -> str:
    """
    Escapes a value for use inside a SPARQL double-quoted string literal.
    Labels come from extracted text, so they are the one substitution an attacker
    could influence: a stray quote or brace must never break out of the literal.
    The backslash pass has to come first, or it would re-escape its own output.
    """
    result = (
        str(value)
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )
    return _CONTROL_CHAR_RE.sub(lambda m: f"\\u{ord(m.group()):04X}", result)


def _entity_label(node: object) -> str:
    if not isinstance(node, dict):
        return ""
    return str(node.get("label") or "").strip()


def _template_values(
    triple: dict, sink: dict, iris: tuple[str, str, str], user_name: str
) -> dict:
    """
    Builds the substitution map for one triple. IRI values are already validated
    and go in verbatim; every other value is escaped as a string literal here, so
    callers never have to remember which is which.
    """
    subject_iri, predicate_iri, object_iri = iris
    source = triple.get("source") or {}
    extractors = source.get("extractors") or []

    values = {
        "subject_iri": subject_iri,
        "predicate_iri": predicate_iri,
        "object_iri": object_iri,
        "graph": sink.get("graph_uri") or "",
    }

    literals = {
        "subject_id": _entity_id(triple.get("subject")).upper(),
        "predicate_id": _entity_id(triple.get("predicate")).upper(),
        "object_id": _entity_id(triple.get("obj")).upper(),
        "subject_label": _entity_label(triple.get("subject")),
        "predicate_label": _entity_label(triple.get("predicate")),
        "object_label": _entity_label(triple.get("obj")),
        "triple_id": triple.get("triple_id") or "",
        "reviewer": user_name,
        "source_file": source.get("file_name") or "",
        "extractors": ", ".join(str(e) for e in extractors),
        "now": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "uuid": str(uuid.uuid4()).upper(),
    }
    values.update(
        {key: _escape_literal(value) for key, value in literals.items()}
    )

    return values


def _render_template(template: str, values: dict) -> str:
    """Substitutes {{placeholder}} occurrences. Unknown names are rejected at config time."""
    return PLACEHOLDER_RE.sub(
        lambda match: values.get(match.group(1), ""), template
    )


def build_update(
    triples: list[dict], sink: dict, user_name: str = ""
) -> tuple[str, list[dict]]:
    """
    Builds the SPARQL 1.1 update sent to the sink, and returns it along with the
    triples that could not be mapped.

    Without an `update_template`, every triple becomes one row of a single
    `INSERT DATA` — idempotent by RDF's set semantics, so re-publishing changes
    nothing and a retry after a partial failure is safe.

    With a template, it is rendered once per triple and the resulting operations
    are joined with `;` into one request, letting a deployment write triples the
    way its own graph expects. What that costs: the tool no longer knows what the
    update does, so idempotence and duplicate handling become the template's
    responsibility.
    """
    namespaces = sink.get("namespaces") or {}
    graph_uri = sink.get("graph_uri")
    template = sink.get("update_template")

    parts: list[str] = []
    skipped: list[dict] = []

    for triple in triples:
        triple_id = triple.get("triple_id") or str(triple.get("_id") or "")
        iris = _triple_iris(triple, namespaces)

        if iris is None:
            skipped.append(
                {
                    "triple_id": triple_id,
                    "reason": "subject, predicate or object has no resolved Q/P identifier",
                }
            )
            continue

        if not all(_is_safe_iri(iri) for iri in iris):
            skipped.append(
                {
                    "triple_id": triple_id,
                    "reason": "resolved IRI contains illegal characters",
                }
            )
            continue

        if template:
            values = _template_values(triple, sink, iris, user_name)
            parts.append(_render_template(template, values))
        else:
            subject_iri, predicate_iri, object_iri = iris
            parts.append(
                f"    <{subject_iri}> <{predicate_iri}> <{object_iri}> ."
            )

    if not parts:
        return "", skipped

    prefixes = (sink.get("prefixes") or "").strip()
    prologue = f"{prefixes}\n\n" if prefixes else ""

    if template:
        return prologue + " ;\n".join(parts), skipped

    body = "\n".join(parts)
    if graph_uri:
        return (
            prologue
            + f"INSERT DATA {{\n  GRAPH <{graph_uri}> {{\n{body}\n  }}\n}}",
            skipped,
        )
    return prologue + f"INSERT DATA {{\n{body}\n}}", skipped


# ── HTTP targets ────────────────────────────────────────────────────────────────


def _numeric_id(entity_id: str) -> str:
    """Digits of a Q id. Wikibase-style APIs want the number, not the "Q" prefix."""
    return entity_id[1:] if entity_id[:1].upper() == "Q" else ""


def _json_escape(value: str) -> str:
    """
    Escapes a value for use *inside* a nested JSON string — the case a plain
    substitution cannot handle, since the outer serialisation escapes the
    fragment as a whole rather than what a caller pasted inside it.
    json.dumps quotes the result, so the quotes are trimmed back off.
    """
    return json.dumps(str(value))[1:-1]


def _http_template_values(
    triple: dict,
    sink: dict,
    iris: tuple[str, str, str],
    user_name: str,
    captured: dict,
) -> dict:
    """
    Builds the substitution map for one triple on an HTTP target.

    Unlike the SPARQL path, values go in raw: the body is serialised as JSON or
    form data afterwards, which escapes them properly. The `_json` variants exist
    for the one place that cannot protect: a JSON fragment nested inside a string
    parameter, as Wikibase's API expects for a claim value.
    """
    subject_iri, predicate_iri, object_iri = iris
    source = triple.get("source") or {}
    subject_id = _entity_id(triple.get("subject")).upper()
    object_id = _entity_id(triple.get("obj")).upper()

    values = {
        "subject_iri": subject_iri,
        "predicate_iri": predicate_iri,
        "object_iri": object_iri,
        "graph": sink.get("graph_uri") or "",
        "subject_id": subject_id,
        "predicate_id": _entity_id(triple.get("predicate")).upper(),
        "object_id": object_id,
        "subject_numeric_id": _numeric_id(subject_id),
        "object_numeric_id": _numeric_id(object_id),
        "subject_label": _entity_label(triple.get("subject")),
        "predicate_label": _entity_label(triple.get("predicate")),
        "object_label": _entity_label(triple.get("obj")),
        "triple_id": triple.get("triple_id") or "",
        "reviewer": user_name,
        "source_file": source.get("file_name") or "",
        "extractors": ", ".join(
            str(e) for e in (source.get("extractors") or [])
        ),
        "now": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "uuid": str(uuid.uuid4()).upper(),
    }

    for name in (
        "subject_label",
        "predicate_label",
        "object_label",
        "source_file",
        "reviewer",
    ):
        values[f"{name}_json"] = _json_escape(values[name])

    # Captured values last: a prepare step cannot shadow a built-in slot, that is
    # rejected at config time, so this only adds.
    values.update({name: str(value) for name, value in captured.items()})

    return values


def _render_http_template(template: object, values: dict) -> object:
    """Substitutes {{slot}} in every string of a JSON-shaped template."""
    if isinstance(template, str):
        return PLACEHOLDER_RE.sub(
            lambda m: str(values.get(m.group(1), "")), template
        )
    if isinstance(template, dict):
        return {
            _render_http_template(key, values): _render_http_template(
                value, values
            )
            for key, value in template.items()
        }
    if isinstance(template, list):
        return [_render_http_template(item, values) for item in template]
    return template


def _http_body_kwargs(body_type: str, rendered: object) -> tuple[dict, str]:
    """Returns the httpx kwargs for a rendered body, and a readable form of it."""
    if body_type == "raw":
        text = rendered if isinstance(rendered, str) else str(rendered)
        return {"content": text.encode("utf-8")}, text

    if body_type == "form":
        data = {
            str(key): "" if value is None else str(value)
            for key, value in (rendered or {}).items()
        }
        return {"data": data}, urlencode(data)

    return {"json": rendered}, json.dumps(
        rendered, ensure_ascii=False, indent=2
    )


def _response_error(
    response: httpx.Response, error_path: str | None
) -> str | None:
    """
    Returns why a call failed, or None when it succeeded.

    A non-2xx status is a failure on its own. Beyond that, APIs in the MediaWiki
    family answer 200 and put the problem in the body, so a target says where to
    look; without that check every failed write would be counted as published.
    """
    if response.status_code >= 400:
        body = response.text[:300] if response.text else "empty response"
        return f"HTTP {response.status_code}: {body}"

    if not error_path:
        return None

    try:
        payload = response.json()
    except ValueError:
        return None

    problem = _resolve_dot_path(payload, error_path)
    if problem is None or problem == "" or problem == [] or problem == {}:
        return None

    return (
        json.dumps(problem, ensure_ascii=False)
        if isinstance(problem, (dict, list))
        else str(problem)
    )


async def _run_prepare_steps(client: httpx.AsyncClient, sink: dict) -> dict:
    """
    Runs a target's prepare chain and returns everything it captured. Steps share
    the client, so a session opened by one (a login cookie) is still open for the
    next — and for the per-triple calls that follow.
    """
    captured: dict[str, str] = {}
    timeout = sink.get("timeout_seconds") or 30
    base_headers = _request_kwargs(sink, content_type=None)

    for step in sink.get("prepare") or []:
        name = step.get("name") or "prepare"
        url = _render_http_template(step["url"], captured)
        kwargs = dict(base_headers)

        if step.get("method", "GET").upper() == "POST":
            body_kwargs, _ = _http_body_kwargs(
                step.get("body_type", "form"),
                _render_http_template(
                    step.get("body_template") or {}, captured
                ),
            )
            kwargs.update(body_kwargs)
            request = client.post
        else:
            request = client.get

        try:
            response = await request(url, timeout=timeout, **kwargs)
        except httpx.TimeoutException:
            raise RuntimeError(
                f"Preparation step '{name}' timed out after {timeout}s calling {url}"
            )
        except httpx.RequestError as exc:
            raise RuntimeError(
                f"Preparation step '{name}' request error: {exc}"
            )

        problem = _response_error(response, None)
        if problem:
            raise RuntimeError(f"Preparation step '{name}' failed — {problem}")

        try:
            payload = response.json()
        except ValueError:
            raise RuntimeError(
                f"Preparation step '{name}' did not return JSON"
            )

        for slot, path in (step.get("capture") or {}).items():
            value = _resolve_dot_path(payload, path)
            if value is None or value == "":
                raise RuntimeError(
                    f"Preparation step '{name}': nothing found at '{path}' for slot '{slot}'"
                )
            captured[slot] = str(value)

    return captured


def build_http_requests(
    triples: list[dict], sink: dict, user_name: str, captured: dict
) -> tuple[list[dict], list[dict]]:
    """
    Renders the per-triple calls for an HTTP target, and returns them along with
    the triples that could not be expressed — same identifier rule as the SPARQL
    path, since a triple without resolved Q/P ids has nothing to send.
    """
    namespaces = sink.get("namespaces") or {}
    request_config = sink["request"]
    prepared: list[dict] = []
    skipped: list[dict] = []

    for triple in triples:
        triple_id = triple.get("triple_id") or str(triple.get("_id") or "")
        iris = _triple_iris(triple, namespaces)

        if iris is None:
            skipped.append(
                {
                    "triple_id": triple_id,
                    "reason": "subject, predicate or object has no resolved Q/P identifier",
                }
            )
            continue

        values = _http_template_values(triple, sink, iris, user_name, captured)
        rendered = _render_http_template(
            request_config["body_template"], values
        )
        body_kwargs, body_text = _http_body_kwargs(
            request_config.get("body_type", "form"), rendered
        )

        prepared.append(
            {
                "triple_id": triple_id,
                "method": request_config.get("method", "POST").upper(),
                "url": _render_http_template(request_config["url"], values),
                "body": body_text,
                "kwargs": body_kwargs,
            }
        )

    return prepared, skipped


async def publish_http(
    sink: dict, triples: list[dict], user_name: str, dry_run: bool = False
) -> tuple[list[str], list[dict], list[dict]]:
    """
    Publishes triples to an HTTP target: one call each, after the prepare chain.

    Returns the ids actually written, the ones that were not, and the rendered
    calls. Unlike a SPARQL update — one request, all or nothing — these succeed or
    fail independently, so only what the target accepted is reported as published.

    A dry run still runs the prepare chain: it is read-only by nature, and it is
    the part most worth checking before trusting a target with real writes.
    """
    timeout = sink.get("timeout_seconds") or 30
    request_config = sink.get("request") or {}
    error_path = request_config.get("error_path")

    # Its own client, kept for the whole run: prepare steps and writes must share
    # a session, and its cookie jar must not outlive the publication.
    async with httpx.AsyncClient(
        timeout=timeout, follow_redirects=True
    ) as client:
        captured = await _run_prepare_steps(client, sink)
        prepared, skipped = build_http_requests(
            triples, sink, user_name, captured
        )

        if dry_run:
            return [], skipped, prepared

        published: list[str] = []
        headers = _request_kwargs(sink, content_type=None)

        for call in prepared:
            try:
                response = await client.request(
                    call["method"],
                    call["url"],
                    timeout=timeout,
                    **headers,
                    **call["kwargs"],
                )
            except httpx.TimeoutException:
                skipped.append(
                    {
                        "triple_id": call["triple_id"],
                        "reason": f"timed out after {timeout}s calling {call['url']}",
                    }
                )
                continue
            except httpx.RequestError as exc:
                skipped.append(
                    {
                        "triple_id": call["triple_id"],
                        "reason": f"request error: {exc}",
                    }
                )
                continue

            problem = _response_error(response, error_path)
            if problem:
                skipped.append(
                    {"triple_id": call["triple_id"], "reason": problem}
                )
                continue

            published.append(call["triple_id"])

        return published, skipped, prepared


# ── Publication ─────────────────────────────────────────────────────────────────


def _body_format(sink: dict) -> str:
    """
    Returns how the update is carried in the request body. Sinks stored before the
    field existed default to the raw form, which is what they were sent then.
    """
    return sink.get("body_format") or "sparql-update"


def _sparql_content_type(sink: dict) -> str:
    return (
        "application/x-www-form-urlencoded"
        if _body_format(sink) == "form-urlencoded"
        else "application/sparql-update"
    )


def _request_kwargs(sink: dict, content_type: str | None = "") -> dict:
    """
    Builds the httpx auth/header kwargs for the sink's configured call.

    Layering matters: the Content-Type implied by the body format goes first so
    free headers can override it for a store with its own expectations, and auth
    headers go last so a credential is never shadowed by a free header of the
    same name.

    An empty content_type means "the SPARQL one"; None means httpx sets it from
    the body it is given, which is what an HTTP target wants.
    """
    auth = sink.get("auth") or {}
    auth_type = auth.get("type", "none")

    headers = {}
    if content_type == "":
        headers["Content-Type"] = _sparql_content_type(sink)
    elif content_type:
        headers["Content-Type"] = content_type
    headers.update(sink.get("headers") or {})

    kwargs: dict = {}

    if auth_type == "basic":
        kwargs["auth"] = (
            auth.get("username") or "",
            auth.get("password") or "",
        )
    elif auth_type == "header":
        headers.update(auth.get("headers") or {})

    kwargs["headers"] = headers
    return kwargs


async def send_update(sink: dict, update: str) -> None:
    """
    Sends a SPARQL UPDATE to the sink's endpoint. Raises RuntimeError with a
    readable message on any transport or HTTP failure.

    Both body formats are SPARQL 1.1 Protocol: the raw one posts the update as the
    whole body, the form-encoded one passes it as the `update` parameter. Stores
    disagree on which they accept, hence the per-target setting.
    """
    url = sink["update_url"]
    timeout = sink.get("timeout_seconds") or 30

    body = (
        {"data": {"update": update}}
        if _body_format(sink) == "form-urlencoded"
        else {"content": update.encode("utf-8")}
    )

    try:
        response = await HTTP_CLIENT.post(
            url,
            timeout=timeout,
            **body,
            **_request_kwargs(sink),
        )
    except httpx.TimeoutException:
        raise RuntimeError(
            f"Target '{sink['id']}' timed out after {timeout}s calling {url}. "
            "Increase the target's timeout or publish fewer triples at once."
        )
    except httpx.RequestError as exc:
        raise RuntimeError(
            f"Target '{sink['id']}' request error: {exc}. "
            "Check network access, DNS resolution, and the configured update URL."
        )

    # SPARQL 1.1 Update leaves the success code open; stores answer 200 or 204.
    if response.status_code not in (200, 201, 204):
        body_text = response.text[:300] if response.text else "empty response"
        raise RuntimeError(
            f"Target '{sink['id']}' returned HTTP {response.status_code}: {body_text}"
        )
