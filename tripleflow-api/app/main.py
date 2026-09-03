"""
Software Name : Tripleflow
SPDX-FileCopyrightText: Copyright (c) Orange SA
SPDX-License-Identifier: MIT

This software is distributed under the MIT License,
see the "LICENSE" file for more details or https://spdx.org/licenses/MIT.html

Authors: Sonia Hadjab, Antoine Py, Yoan Chabot
Software description: Tripleflow is a tool that enables semi-supervised data feeding of knowledge graphs from unstructured documents.

"""

from dotenv import load_dotenv

load_dotenv()

import os
from contextlib import asynccontextmanager

from app.db import ensure_indexes
from app.routes.database import router as database_router
from app.routes.extraction import router as extraction_router
from app.routes.extractors import router as extractors_router
from app.routes.files import router as files_router
from app.routes.search import router as search_router
from app.routes.sinks import router as sinks_router
from app.routes.triples import router as triples_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Comma-separated list of allowed front-end origins; deployment-specific hosts
# belong in the CORS_ORIGINS env var, not in code.
# An empty/unset value falls back to the local dev origins, so a blank
# CORS_ORIGINS= copied from the template does not lock out the front-end.
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in (
        os.getenv("CORS_ORIGINS")
        or "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origin.strip()
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensures database indexes (including the audit-log TTL) exist before serving requests."""
    ensure_indexes()
    yield


app = FastAPI(title="TripleFlow API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(extraction_router)
app.include_router(extractors_router)
app.include_router(files_router)
app.include_router(search_router)
app.include_router(sinks_router)
app.include_router(triples_router)
app.include_router(database_router)


@app.get("/")
def read_root():
    return {"message": "TripleFlow API is running"}
