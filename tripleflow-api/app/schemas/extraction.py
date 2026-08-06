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

    @model_validator(mode="after")
    def validate_text_inputs(self) -> "ExtractionRequest":
        has_text = self.text is not None
        has_texts = self.texts is not None

        if has_text == has_texts:
            raise ValueError(
                "Provide exactly one of 'text' or 'texts'"
            )

        return self


class ExtractionResponse(BaseModel):
    result: "ExtractionResponseData"


class ExtractionResponseData(BaseModel):
    triples: list["TripleItem"] = Field(default_factory=list)
    items: Optional[list["ExtractionBatchItem"]] = None


class ExtractionBatchItem(BaseModel):
    index: int
    status: Literal["ok", "error"]
    triples: list["TripleItem"] = Field(default_factory=list)
    error: Optional[str] = None


class TripleItem(BaseModel):
    triple_id: str
    subject: "TripleNode"
    predicate: "TripleNode"
    obj: "TripleNode"
    date: str | None = None
    source: str
    heuristic_score: float | None = None
    metadata: JSONObject


class TripleNode(BaseModel):
    label: str | None = None
    id: str | None = None
