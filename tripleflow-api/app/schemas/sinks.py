from __future__ import annotations

import re
from typing import Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator

SINK_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")

# RFC 7230 token characters: a header name outside this set would let a caller
# smuggle a second header into the request line.
HEADER_NAME_RE = re.compile(r"^[A-Za-z0-9!#$%&'*+.^_`|~-]+$")


def _validate_headers(headers: Optional[dict[str, str]]) -> Optional[dict[str, str]]:
    """
    Normalises a free header map, rejecting anything that could break the request.
    Returns None for an empty map so a sink without headers stays absent from the
    stored document rather than carrying an empty object.
    """
    if not headers:
        return None

    cleaned: dict[str, str] = {}
    for raw_name, raw_value in headers.items():
        name = str(raw_name).strip()
        value = str(raw_value if raw_value is not None else "")
        if not name:
            continue
        if not HEADER_NAME_RE.match(name):
            raise ValueError(f"Invalid header name '{name}'")
        if "\n" in value or "\r" in value:
            raise ValueError(f"Header '{name}' must not contain line breaks")
        cleaned[name] = value.strip()

    return cleaned or None


class SinkAuth(BaseModel):
    """
    Credentials used to reach the SPARQL UPDATE endpoint. They are stored in the
    database and never returned by the API.
    """

    # "none"   -> the endpoint is open (or protected by network rules only)
    # "basic"  -> HTTP Basic, from username/password
    # "header" -> arbitrary headers, e.g. {"Authorization": "Bearer …"}. Kept for
    #             backward compatibility with sinks stored before the endpoint
    #             grew its own `headers` field; the form no longer offers it.
    type: Literal["none", "basic", "header"] = "none"
    username: Optional[str] = None
    password: Optional[str] = None
    headers: Optional[dict[str, str]] = None

    @field_validator("headers")
    @classmethod
    def validate_auth_headers(cls, v: Optional[dict[str, str]]) -> Optional[dict[str, str]]:
        return _validate_headers(v)

    @model_validator(mode="after")
    def validate_credentials(self) -> "SinkAuth":
        if self.type == "basic" and not (self.username and self.password):
            raise ValueError("username and password are required when auth type is 'basic'")
        if self.type == "header" and not self.headers:
            raise ValueError("headers are required when auth type is 'header'")
        return self


class SinkNamespaces(BaseModel):
    """
    How a triple's entity IDs are turned into IRIs in the target graph. Defaults
    mirror the public Wikidata namespaces; an internal Wikibase or a custom
    triplestore sets its own bases.
    """

    item_base_uri: str = Field("http://www.wikidata.org/entity/", min_length=1)
    property_base_uri: str = Field("http://www.wikidata.org/prop/direct/", min_length=1)

    @field_validator("item_base_uri", "property_base_uri")
    @classmethod
    def validate_base_uri(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith(("http://", "https://")):
            raise ValueError("Base URI must start with http:// or https://")
        if any(c in v for c in ' <>"{}|\\^`'):
            raise ValueError("Base URI must not contain spaces or the characters <>\"{}|\\^`")
        return v


class SinkKnowledgeBase(BaseModel):
    """
    Where a published identifier can be *browsed*, as opposed to `namespaces`
    which says how it is *written* as an IRI. The two differ in practice: a
    Wikibase writes `…/entity/Q42` into the graph but serves the human page at
    `…/wiki/Item:Q42`, so the UI cannot derive one from the other.

    Declaring it turns the IDs of a published triple into links into the
    organisation's knowledge base; "none" means no link is offered.
    """

    type: Literal["none", "wikidata", "wikibase"] = "none"
    # Wiki base URL for type "wikibase", e.g. "https://kg.example.org/wiki/".
    base_url: Optional[str] = None

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if not v.startswith(("http://", "https://")):
            raise ValueError("Knowledge base URL must start with http:// or https://")
        return v

    @model_validator(mode="after")
    def validate_base_url_present(self) -> "SinkKnowledgeBase":
        if self.type == "wikibase" and not self.base_url:
            raise ValueError("base_url is required when the knowledge base type is 'wikibase'")
        return self


# Placeholders a sink's update_template may use. Everything here is substituted by
# the backend; anything else is rejected at config time rather than silently left
# in the SPARQL. IRI placeholders are built from validated Q/P ids and go in
# unescaped; every other value is escaped as a SPARQL string literal.
TEMPLATE_IRI_PLACEHOLDERS = frozenset({
    "subject_iri",
    "predicate_iri",
    "object_iri",
    "graph",
})
TEMPLATE_LITERAL_PLACEHOLDERS = frozenset({
    "subject_id",
    "predicate_id",
    "object_id",
    "subject_label",
    "predicate_label",
    "object_label",
    "triple_id",
    "reviewer",
    "source_file",
    "extractors",
    "now",
    "uuid",
})
TEMPLATE_PLACEHOLDERS = TEMPLATE_IRI_PLACEHOLDERS | TEMPLATE_LITERAL_PLACEHOLDERS

# Extra slots an HTTP target may use on top of the ones above.
#   *_numeric_id  -> the digits of a Q id. Wikibase's API asks for the numeric id
#                    inside a value, where the "Q" prefix would be rejected.
#   *_json        -> the same free text, escaped for use *inside* a nested JSON
#                    string. Values are substituted raw otherwise, which is right
#                    for a plain field but would break a quoted JSON fragment.
HTTP_EXTRA_PLACEHOLDERS = frozenset({
    "subject_numeric_id",
    "object_numeric_id",
    "subject_label_json",
    "predicate_label_json",
    "object_label_json",
    "source_file_json",
    "reviewer_json",
})
HTTP_PLACEHOLDERS = (
    TEMPLATE_IRI_PLACEHOLDERS | TEMPLATE_LITERAL_PLACEHOLDERS | HTTP_EXTRA_PLACEHOLDERS
)

PLACEHOLDER_RE = re.compile(r"\{\{\s*([A-Za-z_]+)\s*\}\}")
PLACEHOLDER_NAME_RE = re.compile(r"^[A-Za-z_]+$")


def _collect_placeholders(template: object) -> set[str]:
    """Returns every {{slot}} used anywhere in a string, dict or list template."""
    if isinstance(template, str):
        return set(PLACEHOLDER_RE.findall(template))
    if isinstance(template, dict):
        found: set[str] = set()
        for key, value in template.items():
            found |= _collect_placeholders(key)
            found |= _collect_placeholders(value)
        return found
    if isinstance(template, list):
        found = set()
        for item in template:
            found |= _collect_placeholders(item)
        return found
    return set()


class SinkPrepareStep(BaseModel):
    """
    A request sent once before publishing, whose response feeds values into the
    per-triple request. This is what lets a target obtain a CSRF token, or log in,
    without TripleFlow knowing anything about the API on the other end: the step
    says where to call and which paths of the JSON response to keep.

    Steps run in order, over one HTTP session, so cookies set by an earlier step
    (a login) are still there for the later ones.
    """

    name: str = Field(..., min_length=1, max_length=64)
    method: Literal["GET", "POST"] = "GET"
    url: str = Field(..., min_length=1)
    body_type: Literal["json", "form", "raw"] = "form"
    body_template: Optional[Union[dict, str]] = None
    # Slot name -> dot path in the JSON response, e.g.
    # {"token": "query.tokens.csrftoken"}.
    capture: dict[str, str] = Field(default_factory=dict)

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v

    @field_validator("capture")
    @classmethod
    def validate_capture(cls, v: dict[str, str]) -> dict[str, str]:
        for name, path in v.items():
            if not PLACEHOLDER_NAME_RE.match(name):
                raise ValueError(
                    f"Captured name '{name}' must contain only letters and underscores"
                )
            if name in HTTP_PLACEHOLDERS:
                raise ValueError(
                    f"Captured name '{name}' collides with a built-in slot"
                )
            if not str(path).strip():
                raise ValueError(f"Captured name '{name}' has an empty path")
        return v


class SinkHttpRequest(BaseModel):
    """
    The call sent once per published triple. The body is written by whoever
    registers the target, so any write API can be driven without changing
    TripleFlow's code.
    """

    method: Literal["POST", "PUT", "PATCH"] = "POST"
    url: str = Field(..., min_length=1)
    body_type: Literal["json", "form", "raw"] = "form"
    body_template: Union[dict, str] = Field(...)
    # Where an error hides in a 200 response. MediaWiki-style APIs answer 200 with
    # {"error": {...}}; without this a failed write would be counted as published.
    error_path: Optional[str] = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v

    @model_validator(mode="after")
    def validate_body_type(self) -> "SinkHttpRequest":
        if self.body_type == "raw":
            if not isinstance(self.body_template, str):
                raise ValueError("body_template must be a string when body_type is 'raw'")
        elif not isinstance(self.body_template, dict):
            raise ValueError(
                f"body_template must be a JSON object when body_type is '{self.body_type}'"
            )
        return self


class SinkConfig(BaseModel):
    id: str = Field(..., min_length=1, max_length=64)
    label: str = Field(..., min_length=1, max_length=128)
    description: Optional[str] = None
    # How the target is written to.
    #   "sparql" -> one SPARQL 1.1 Update sent to update_url. Right for a
    #               triplestore (Fuseki, GraphDB, Virtuoso...).
    #   "http"   -> one arbitrary HTTP call per triple, described by `request`.
    #               Needed by knowledge bases that are not written through SPARQL
    #               at all: a Wikibase, whose SPARQL endpoint is a read-only
    #               mirror, is written through its own API — as is any in-house
    #               REST service. Targets stored before this field existed are
    #               SPARQL ones, which is what they were.
    type: Literal["sparql", "http"] = "sparql"
    # SPARQL 1.1 Update endpoint, e.g. http://fuseki.example/dataset/update.
    # Required for type "sparql", unused for "http".
    update_url: Optional[str] = None
    # Requests sent once before publishing, capturing values (a CSRF token, a
    # session) reused by every per-triple call. Type "http" only.
    prepare: list[SinkPrepareStep] = Field(default_factory=list)
    # The call sent per triple. Required for type "http".
    request: Optional[SinkHttpRequest] = None
    auth: SinkAuth = Field(default_factory=SinkAuth)
    # Free HTTP headers sent with every request, independent of `auth`, so a
    # target can need both Basic credentials and, say, a tenant header. Auth
    # headers are applied last and win on a name collision.
    headers: Optional[dict[str, str]] = None
    # How the update is carried in the request body. Both forms are SPARQL 1.1
    # Protocol; stores disagree on which they accept, so it is the deployment's
    # call rather than ours.
    #   "sparql-update"   -> raw body, Content-Type: application/sparql-update
    #   "form-urlencoded" -> update=<escaped> as application/x-www-form-urlencoded
    body_format: Literal["sparql-update", "form-urlencoded"] = "sparql-update"
    namespaces: SinkNamespaces = Field(default_factory=SinkNamespaces)
    knowledge_base: SinkKnowledgeBase = Field(default_factory=SinkKnowledgeBase)
    # Optional named graph the triples are inserted into; unset -> default graph.
    graph_uri: Optional[str] = None
    timeout_seconds: int = Field(30, ge=1, le=300)
    # PREFIX lines emitted once at the top of the request, so a template does not
    # repeat them for every triple.
    prefixes: Optional[str] = None
    # SPARQL operation rendered once per triple, letting a deployment write triples
    # the way its own graph expects. Unset -> a plain INSERT DATA of the three IRIs.
    update_template: Optional[str] = None

    @field_validator("headers")
    @classmethod
    def validate_endpoint_headers(cls, v: Optional[dict[str, str]]) -> Optional[dict[str, str]]:
        return _validate_headers(v)

    @field_validator("prefixes", "update_template")
    @classmethod
    def strip_optional_text(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return v.strip() or None

    @field_validator("update_template")
    @classmethod
    def validate_template_placeholders(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        unknown = sorted(set(PLACEHOLDER_RE.findall(v)) - TEMPLATE_PLACEHOLDERS)
        if unknown:
            known = ", ".join(sorted(TEMPLATE_PLACEHOLDERS))
            raise ValueError(
                f"Unknown placeholder(s): {', '.join(unknown)}. Available: {known}"
            )
        return v

    @model_validator(mode="after")
    def validate_graph_placeholder(self) -> "SinkConfig":
        if self.update_template and "{{graph}}" in self.update_template and not self.graph_uri:
            raise ValueError(
                "The template uses {{graph}} but no named graph URI is set on this target"
            )
        return self

    @model_validator(mode="after")
    def validate_target_type(self) -> "SinkConfig":
        """
        Checks each target type carries what it needs, and that an HTTP target's
        templates only use slots the backend can actually fill — the built-in ones
        plus whatever its prepare steps capture. An unknown slot is rejected here
        rather than silently sent as a literal "{{typo}}" to the target's API.
        """
        if self.type == "sparql":
            if not self.update_url:
                raise ValueError("update_url is required for a SPARQL target")
            return self

        if self.request is None:
            raise ValueError("request is required for an HTTP target")

        captured = {name for step in self.prepare for name in step.capture}
        available = HTTP_PLACEHOLDERS | captured

        used = _collect_placeholders(self.request.body_template)
        used |= _collect_placeholders(self.request.url)
        for step in self.prepare:
            # A prepare step may only use what the steps before it captured, since
            # nothing about a triple is known yet at that point.
            used |= _collect_placeholders(step.body_template) - captured
            used |= _collect_placeholders(step.url) - captured

        unknown = sorted(used - available)
        if unknown:
            known = ", ".join(sorted(available))
            raise ValueError(
                f"Unknown slot(s): {', '.join(unknown)}. Available: {known}"
            )

        return self

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        v = v.strip().lower()
        if not SINK_ID_RE.match(v):
            raise ValueError(
                "id must contain only lowercase letters, digits, hyphens and underscores, "
                "and start with a letter or digit"
            )
        return v

    @field_validator("update_url")
    @classmethod
    def validate_update_url(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v

    @field_validator("graph_uri")
    @classmethod
    def validate_graph_uri(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not v:
            return None
        if not v.startswith(("http://", "https://")):
            raise ValueError("Graph URI must start with http:// or https://")
        if any(c in v for c in ' <>"{}|\\^`'):
            raise ValueError("Graph URI must not contain spaces or the characters <>\"{}|\\^`")
        return v


class SinkPublic(BaseModel):
    """
    Public listing shape for sinks. Auth credentials are deliberately excluded so
    passwords and tokens stored in the database are never re-exposed. Header
    *names* are listed — they let the UI show how a target authenticates without
    ever returning the token that sits in the value.
    """

    id: str
    label: str
    description: Optional[str] = None
    type: Literal["sparql", "http"] = "sparql"
    update_url: Optional[str] = None
    # For an HTTP target: where the per-triple call goes, and the names of its
    # prepare steps. The body templates stay on the backend — they are free text
    # and may well hold a credential.
    request_url: Optional[str] = None
    request_method: Optional[str] = None
    prepare_steps: list[str] = Field(default_factory=list)
    graph_uri: Optional[str] = None
    namespaces: SinkNamespaces
    knowledge_base: SinkKnowledgeBase = Field(default_factory=SinkKnowledgeBase)
    auth_type: Literal["none", "basic", "header"] = "none"
    header_names: list[str] = Field(default_factory=list)
    body_format: Literal["sparql-update", "form-urlencoded"] = "sparql-update"
    prefixes: Optional[str] = None
    update_template: Optional[str] = None


class SinkListResponse(BaseModel):
    sinks: list[SinkPublic]


class PublishRequest(BaseModel):
    """
    Asks for a set of validated triples to be inserted into the sink's graph.
    Triples are named explicitly so the front publishes exactly what the reviewer
    sees, rather than re-running the page's filters server-side.
    """

    triple_ids: list[str] = Field(..., min_length=1, max_length=5000)
    user_name: str = Field(..., min_length=1, max_length=128)
    # Builds and returns the SPARQL UPDATE without sending it to the endpoint.
    dry_run: bool = False


class SkippedTriple(BaseModel):
    triple_id: str
    reason: str


class PreparedRequest(BaseModel):
    """One rendered call, returned by a dry run so it can be inspected before sending."""

    triple_id: str
    method: str
    url: str
    body: str


class PublishResponse(BaseModel):
    sink_id: str
    dry_run: bool
    published_count: int
    skipped: list[SkippedTriple]
    # The SPARQL a dry run would have sent, for a "sparql" target.
    sparql: Optional[str] = None
    # The calls a dry run would have sent, for an "http" target.
    requests: Optional[list[PreparedRequest]] = None
