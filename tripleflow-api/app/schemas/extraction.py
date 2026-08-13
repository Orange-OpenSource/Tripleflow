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

from typing import Annotated, Literal, Optional

from pydantic import BaseModel, Field, model_validator

JSONObject = dict[str, object]
TextInput = Annotated[str, Field(min_length=1, max_length=50000)]

ExtractorName = Annotated[str, Field(min_length=1, max_length=64)]


class ExtractionRequest(BaseModel):
    text: TextInput | None = None
    texts: list[TextInput] | None = Field(default=None, min_length=1)
    extractor: ExtractorName
    file_name: str | None = None
    file_names: list[str] | None = None
    # Optional chunking step, in tokens. Omitted means no chunking at all.
    chunk_size: int | None = Field(default=None, ge=50, le=8000)
    chunk_overlap: int | None = Field(default=None, ge=0, le=2000)
    # Offsets at which each page of the source document starts, as reported by
    # whichever parser produced the text. They let a chunk position be resolved
    # to a page number; omitted for formats that have no pages.
    # page_offsets goes with 'text', page_offsets_list with 'texts'.
    page_offsets: list[int] | None = None
    page_offsets_list: list[list[int]] | None = None

    @model_validator(mode="after")
    def validate_text_inputs(self) -> "ExtractionRequest":
        has_text = self.text is not None
        has_texts = self.texts is not None

        if has_text == has_texts:
            raise ValueError(
                "Provide exactly one of 'text' or 'texts'"
            )

        if (
            self.chunk_size is not None
            and self.chunk_overlap is not None
            and self.chunk_overlap >= self.chunk_size
        ):
            raise ValueError(
                "'chunk_overlap' must be smaller than 'chunk_size'"
            )

        return self


class ExtractionResponse(BaseModel):
    result: "ExtractionResponseData"


class ExtractionResponseData(BaseModel):
    triples: list["TripleItem"] = Field(default_factory=list)
    items: Optional[list["ExtractionBatchItem"]] = None
    # Number of chunks the input was split into; None when chunking was off.
    chunk_count: Optional[int] = None


class ExtractionBatchItem(BaseModel):
    index: int
    status: Literal["ok", "error"]
    triples: list["TripleItem"] = Field(default_factory=list)
    error: Optional[str] = None
    chunk_count: Optional[int] = None


class TripleItem(BaseModel):
    triple_id: str
    subject: "TripleNode"
    predicate: "TripleNode"
    obj: "TripleNode"
    date: str | None = None
    source: str
    heuristic_score: float | None = None
    metadata: JSONObject
    chunk: Optional["TripleChunk"] = None


class TripleNode(BaseModel):
    label: str | None = None
    id: str | None = None


class TripleChunk(BaseModel):
    """Where in the source document a triple was extracted from."""

    chunk_id: str
    # Half-open character offsets of the passage in the document text.
    start: int
    end: int
    # 1-based, None when the document has no pagination.
    page: int | None = None
