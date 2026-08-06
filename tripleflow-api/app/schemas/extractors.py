"""  
Software Name : Tripleflow
SPDX-FileCopyrightText: Copyright (c) Orange SA
SPDX-License-Identifier: MIT
 
This software is distributed under the MIT License,
see the "LICENSE" file for more details or https://spdx.org/licenses/MIT.html
 
Authors: Sonia Hadjab, Antoine Py, Yoan Chabot
Software description: Tripleflow is a tool that enables semi-supervised data feeding of knowledge graphs from unstructured documents.  

"""

from __future__ import annotations

import re
from typing import Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator

EXTRACTOR_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


class ExtractorEndpointHeaders(BaseModel):
    """Arbitrary HTTP headers to send with the extractor request."""

    model_config = {"extra": "allow"}


class ExtractorEndpoint(BaseModel):
    url: str = Field(..., min_length=1)
    # "GET" is kept for backward compatibility with previously stored extractors;
    # the form only offers POST.
    method: Literal["POST", "GET"] = "POST"
    headers: Optional[dict[str, str]] = None
    # "json" -> body_template is a JSON object sent as application/json
    # "raw"  -> body_template is a plain string sent as the request body
    #           (text/plain unless a Content-Type header is set)
    # "form" -> body_template is a flat JSON object sent form-urlencoded
    body_type: Literal["json", "raw", "form"] = "json"
    body_template: Optional[Union[dict, str]] = None
    timeout_seconds: int = Field(30, ge=1, le=300)

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v

    @model_validator(mode="after")
    def validate_body_template_type(self) -> "ExtractorEndpoint":
        if self.body_template is None:
            return self
        if self.body_type == "raw":
            if not isinstance(self.body_template, str):
                raise ValueError("body_template must be a string when body_type is 'raw'")
        elif not isinstance(self.body_template, dict):
            raise ValueError(f"body_template must be a JSON object when body_type is '{self.body_type}'")
        return self


class ExtractorNodeMapping(BaseModel):
    id: str = Field(..., min_length=1)
    label: Optional[str] = None


class ExtractorOutputMapping(BaseModel):
    # Optional dot-path to a string field holding JSON (e.g. an LLM response's
    # "choices.0.message.content"); it is parsed and triples_path is resolved
    # inside the decoded document instead of the raw response.
    decode_json_path: Optional[str] = None
    triples_path: str = Field(..., min_length=1)
    subject: ExtractorNodeMapping
    predicate: ExtractorNodeMapping
    object: ExtractorNodeMapping
    date: Optional[str] = None


class ExtractorKnowledgeBase(BaseModel):
    # "wikidata"  -> QIDs/PIDs link to public wikidata.org
    # "wikibase"  -> link to another Wikibase instance given by base_url (Item:/Property: pages)
    # "custom" is kept for backward compatibility with previously stored extractors.
    type: Literal["wikidata", "wikibase", "custom"] = "wikidata"
    base_url: Optional[str] = None
    # MediaWiki api.php used for entity autocomplete. Only meaningful for
    # non-wikidata bases ("wikidata" always searches the public Wikidata API);
    # unset -> no suggestions for this extractor.
    search_api_url: Optional[str] = None
    entity_id_format: Optional[str] = None
    property_id_format: Optional[str] = None

    @field_validator("base_url", "search_api_url")
    @classmethod
    def validate_http_url(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if v and not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v or None


class ExtractorConfig(BaseModel):
    id: str = Field(..., min_length=1, max_length=64)
    label: str = Field(..., min_length=1, max_length=128)
    description: Optional[str] = None
    endpoint: ExtractorEndpoint
    output_mapping: ExtractorOutputMapping
    knowledge_base: Optional[ExtractorKnowledgeBase] = None

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        v = v.strip().lower()
        if not EXTRACTOR_ID_RE.match(v):
            raise ValueError(
                "id must contain only lowercase letters, digits, hyphens and underscores, "
                "and start with a letter or digit"
            )
        return v


class ExtractorTestRequest(BaseModel):
    config: ExtractorConfig
    sample_text: str = Field(..., min_length=1, max_length=50000)


class ExtractorPublic(BaseModel):
    """
    Public listing shape for extractors. Endpoint details (URL, headers, body
    template) are deliberately excluded so secrets stored in headers are never
    re-exposed.
    """

    id: str
    label: str
    description: Optional[str] = None
    knowledge_base: Optional[ExtractorKnowledgeBase] = None


class ExtractorListResponse(BaseModel):
    extractors: list[ExtractorPublic]
