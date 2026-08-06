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

from pymongo import MongoClient
from pymongo.collection import Collection

client = MongoClient(os.environ["MONGO_URI"])
db = client["tripleflow_db"]

print("Connected to MongoDB at", os.environ["MONGO_URI"])

triples_collection: Collection = db["triples"]
files_collection: Collection = db["files"]
extractors_collection: Collection = db["extractors"]
audit_collection: Collection = db["audit_logs"]

# Deletion audit entries are kept for one year, then purged automatically by MongoDB.
AUDIT_RETENTION_SECONDS = 365 * 24 * 60 * 60


def ensure_indexes() -> None:
    """
    Creates the indexes the app relies on. In particular, a TTL index on the audit log so
    entries older than one year are removed automatically and the collection stays small.
    """
    audit_collection.create_index(
        "timestamp",
        name="audit_ttl",
        expireAfterSeconds=AUDIT_RETENTION_SECONDS,
    )
