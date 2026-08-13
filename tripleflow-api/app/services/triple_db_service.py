"""  
Software Name : Tripleflow
SPDX-FileCopyrightText: Copyright (c) Orange SA
SPDX-License-Identifier: MIT
 
This software is distributed under the MIT License,
see the "LICENSE" file for more details or https://spdx.org/licenses/MIT.html
 
Authors: Sonia Hadjab, Antoine Py, Yoan Chabot
Software description: Tripleflow is a tool that enables semi-supervised data feeding of knowledge graphs from unstructured documents.  

"""

import re
from datetime import datetime, timezone
from typing import Optional
from bson import ObjectId
from app.db import (
    AUDIT_MAX_ENTRIES,
    triples_collection,
    files_collection,
    audit_collection,
)


def now_utc() -> datetime:
    """Returns the current UTC time."""
    return datetime.now(timezone.utc)


def _find_existing_triple(
    subject: dict, predicate: dict, obj: dict
) -> dict | None:
    """Looks for a triple with the same subject, predicate and object IDs in the DB."""
    subject_id = (subject.get("id") or "").strip()
    predicate_id = (predicate.get("id") or "").strip()
    obj_id = (obj.get("id") or "").strip()

    if not (subject_id and predicate_id and obj_id):
        return None

    return triples_collection.find_one(
        {
            "subject.id": subject_id,
            "predicate.id": predicate_id,
            "obj.id": obj_id,
        }
    )


def _find_matching_triple(
    subject: dict, predicate: dict, obj: dict, exclude_id: ObjectId
) -> dict | None:
    """Looks for a triple matching by ID or label, excluding a given document."""
    subject_id = (subject.get("id") or "").strip()
    predicate_id = (predicate.get("id") or "").strip()
    obj_id = (obj.get("id") or "").strip()

    if subject_id and predicate_id and obj_id:
        query = {
            "_id": {"$ne": exclude_id},
            "subject.id": subject_id,
            "predicate.id": predicate_id,
            "obj.id": obj_id,
        }
    else:
        s_label = (subject.get("label") or "").strip()
        p_label = (predicate.get("label") or "").strip()
        o_label = (obj.get("label") or "").strip()
        if not (s_label and p_label and o_label):
            return None
        query = {
            "_id": {"$ne": exclude_id},
            "subject.label": {"$regex": f"^{re.escape(s_label)}$", "$options": "i"},
            "predicate.label": {"$regex": f"^{re.escape(p_label)}$", "$options": "i"},
            "obj.label": {"$regex": f"^{re.escape(o_label)}$", "$options": "i"},
        }

    return triples_collection.find_one(query)


def _merge_into(
    target: dict,
    source: dict,
    status: str,
    user_id: str,
    user_name: str,
    comment: Optional[str],
) -> None:
    """Merges a duplicate triple into an existing one and deletes the duplicate."""
    source_extractors = source.get("source", {}).get("extractors", [])
    source_occurrences = source.get("source", {}).get("occurrences", [])
    merged_history = sorted(
        target.get("history", []) + source.get("history", []),
        key=lambda h: h.get("timestamp", datetime.min.replace(tzinfo=timezone.utc)),
    )
    merged_history.append({
        "action": status,
        "user_id": user_id,
        "user_name": user_name,
        "timestamp": now_utc(),
        "comments": comment,
        "previous_value": {
            "subject": target.get("subject"),
            "predicate": target.get("predicate"),
            "obj": target.get("obj"),
            "status": target.get("status"),
        },
    })

    triples_collection.update_one(
        {"_id": target["_id"]},
        {
            "$set": {"status": status, "history": merged_history},
            "$addToSet": {
                "source.extractors": {"$each": source_extractors},
                # The passages the merged-away triple was found in are part of its
                # provenance; losing them would break the source-text panel.
                "source.occurrences": {"$each": source_occurrences},
            },
        },
    )
    triples_collection.delete_one({"_id": source["_id"]})


def _build_occurrence(
    triple: dict, file_id: str, file_name: str, extractor: str
) -> dict | None:
    """
    Describes where one extraction found this triple: which document, which chunk
    of it, the offsets of that chunk in the document text, and the page they fall
    on. The validation interface uses the offsets to point the reviewer at the
    exact passage. Returns None for a triple carrying no location.
    """
    chunk = triple.get("chunk") or {}

    if not chunk:
        return None

    return {
        "file_id": file_id,
        "file_name": file_name,
        "extractor": extractor,
        "chunk_id": chunk.get("chunk_id"),
        "start": chunk.get("start"),
        "end": chunk.get("end"),
        "page": chunk.get("page"),
    }


def save_triples(
    triples: list[dict],
    file_name: str,
    file_id: str,
    extractor: str,
    text: str | None = None,
) -> list[str]:
    """Saves extracted triples to the DB, updating existing ones if they already exist."""
    affected_ids = []
    inserted_count = 0

    for triple in triples:
        subject = triple.get("subject") or {}
        predicate = triple.get("predicate") or {}
        obj = triple.get("obj") or {}
        occurrence = _build_occurrence(triple, file_id, file_name, extractor)

        existing = _find_existing_triple(subject, predicate, obj)

        if existing:
            # A triple several extractors (or several documents) agree on stays a
            # single row, but every occurrence is kept: that is what lets the
            # reviewer see each passage it was found in.
            additions: dict = {"source.extractors": extractor}
            if occurrence is not None:
                additions["source.occurrences"] = occurrence

            triples_collection.update_one(
                {"_id": existing["_id"]},
                {"$addToSet": additions},
            )
            affected_ids.append(str(existing["_id"]))
        else:
            doc = {
                "triple_id": triple.get("triple_id"),
                "subject": subject,
                "predicate": predicate,
                "obj": obj,
                "source": {
                    "file_name": file_name,
                    "file_id": file_id,
                    "extractors": [extractor],
                    "extraction_date": now_utc(),
                    "occurrences": [occurrence] if occurrence is not None else [],
                },
                "heuristic_score": triple.get("heuristic_score"),
                "status": "pending",
                "modified_triple": None,
                "history": [
                    {
                        "action": "extracted",
                        "user_id": None,
                        "user_name": None,
                        "timestamp": now_utc(),
                        "comments": None,
                        "previous_value": None,
                    }
                ],
            }
            result = triples_collection.insert_one(doc)
            affected_ids.append(str(result.inserted_id))
            inserted_count += 1

    _save_file(
        file_id=file_id,
        file_name=file_name,
        extractor=extractor,
        triple_count=inserted_count,
        text=text,
    )

    return affected_ids


def _save_file(
    file_id: str,
    file_name: str,
    extractor: str,
    triple_count: int,
    text: str | None = None,
) -> None:
    """Saves or updates a file record in the DB with the extractor and triple count."""
    set_fields: dict = {"file_name": file_name}
    if text is not None:
        set_fields["text"] = text
    files_collection.update_one(
        {"file_id": file_id},
        {
            "$set": set_fields,
            "$setOnInsert": {"extraction_date": now_utc()},
            "$addToSet": {"extractors": extractor},
            "$inc": {"triple_count": triple_count},
        },
        upsert=True,
    )


def get_file_content(file_id: str) -> str | None:
    """Returns the stored text content of a file, or None if not available."""
    doc = files_collection.find_one({"file_id": file_id}, {"text": 1})
    if doc is None:
        return None
    return doc.get("text")


def rename_file(file_id: str, file_name: str) -> dict:
    """
    Renames a file. The name is copied onto every triple extracted from it (and
    onto each of their occurrences), so the whole review stays consistent instead
    of showing the old name wherever provenance is displayed or published.
    Raises ValueError if the file does not exist.
    """
    name = (file_name or "").strip()

    if not name:
        raise ValueError("File name is required")

    result = files_collection.update_one(
        {"file_id": file_id}, {"$set": {"file_name": name}}
    )

    if result.matched_count == 0:
        raise ValueError(f"File '{file_id}' not found")

    triples_collection.update_many(
        {"source.file_id": file_id},
        {"$set": {"source.file_name": name}},
    )
    triples_collection.update_many(
        {"source.occurrences.file_id": file_id},
        {"$set": {"source.occurrences.$[occurrence].file_name": name}},
        array_filters=[{"occurrence.file_id": file_id}],
    )

    return {"file_id": file_id, "file_name": name}


def get_files() -> list[dict]:
    """Returns all files with their review progress counts (pending, validated, rejected)."""
    files = list(files_collection.find())
    result = []
    for file in files:
        file["_id"] = str(file["_id"])
        counts = triples_collection.aggregate(
            [
                {"$match": _from_file(file["file_id"])},
                {"$group": {"_id": "$status", "count": {"$sum": 1}}},
            ]
        )
        status_counts = {doc["_id"]: doc["count"] for doc in counts}
        file["review_progress"] = {
            "pending": status_counts.get("pending", 0),
            "validated": status_counts.get("validated", 0),
            "rejected": status_counts.get("rejected", 0),
        }
        result.append(file)
    return result


def _from_file(file_id: str) -> dict:
    """
    Matches every triple found in a document. A triple several documents agree on
    is stored once, attached to the first of them, so matching only on the primary
    file_id would hide it under all the others. Its occurrences name them all.
    The primary file_id alone is still matched, for triples saved before
    occurrences were recorded.
    """
    return {
        "$or": [
            {"source.file_id": file_id},
            {"source.occurrences.file_id": file_id},
        ]
    }


def get_triples(
    status: Optional[str] = None,
    file_id: Optional[str] = None,
    extractor: Optional[str] = None,
) -> list[dict]:
    """Returns triples from the DB with optional filters by status, file or extractor."""
    query = {}
    if status:
        query["status"] = status
    if file_id:
        query.update(_from_file(file_id))
    if extractor:
        query["source.extractors"] = extractor

    triples = list(triples_collection.find(query))
    for triple in triples:
        triple["_id"] = str(triple["_id"])
    return triples


def get_triples_by_ids(triple_ids: list[str]) -> list[dict]:
    """Returns the triples matching the given triple_ids, in no particular order."""
    triples = list(triples_collection.find({"triple_id": {"$in": triple_ids}}))
    for triple in triples:
        triple["_id"] = str(triple["_id"])
    return triples


def mark_triples_published(
    triple_ids: list[str],
    sink_id: str,
    user_name: str,
) -> int:
    """
    Records that the given triples were inserted into a sink's graph, and appends
    a history entry so the publication shows up in each triple's timeline.
    Returns the number of triples updated.
    """
    timestamp = now_utc()
    result = triples_collection.update_many(
        {"triple_id": {"$in": triple_ids}},
        {
            "$set": {
                "published": {
                    "sink_id": sink_id,
                    "user_name": user_name,
                    "timestamp": timestamp,
                }
            },
            "$push": {
                "history": {
                    "action": "published",
                    "user_id": None,
                    "user_name": user_name,
                    "timestamp": timestamp,
                    "comments": f"Published to target '{sink_id}'",
                    "previous_value": None,
                }
            },
        },
    )
    return result.modified_count


def _prune_audit_log() -> None:
    """
    Drops the oldest entries so the audit log never holds more than AUDIT_MAX_ENTRIES.

    Ordering is on _id rather than timestamp: ObjectIds follow insertion order and are
    unique, so two entries written in the same instant still have a defined oldest one
    and the cap stays exact.
    """
    oldest_kept = list(
        audit_collection.find({}, {"_id": 1})
        .sort("_id", -1)
        .skip(AUDIT_MAX_ENTRIES - 1)
        .limit(1)
    )
    if not oldest_kept:
        return
    audit_collection.delete_many({"_id": {"$lt": oldest_kept[0]["_id"]}})


def _record_audit(action: str, user_name: str, **details) -> None:
    """Appends an entry to the audit log and trims it back down to its cap."""
    audit_collection.insert_one(
        {
            "action": action,
            "user_name": (user_name or "").strip() or "unknown",
            "timestamp": now_utc(),
            **details,
        }
    )
    _prune_audit_log()


def record_publication(
    sink_id: str,
    user_name: str,
    published_count: int,
    skipped_count: int,
) -> None:
    """Appends a publication entry to the audit log so pushes to an external KG stay traceable."""
    _record_audit(
        "publish",
        user_name,
        sink_id=sink_id,
        published_count=published_count,
        skipped_count=skipped_count,
    )


def _record_deletion(action: str, user_name: str, **details) -> None:
    """Appends an entry to the audit log so deletions remain traceable after the data is gone."""
    _record_audit(action, user_name, **details)


def get_audit_log(limit: int = 200) -> list[dict]:
    """Returns recent audit entries, most recent first, never more than the log's cap."""
    capped = max(1, min(limit, AUDIT_MAX_ENTRIES))
    entries = list(audit_collection.find({}).sort("_id", -1).limit(capped))
    for entry in entries:
        entry["_id"] = str(entry["_id"])
    return entries


def clear_database(user_name: str) -> dict:
    """
    Deletes every file and triple from the database. Extractor configurations are kept,
    since they are user-defined settings rather than review data. Records who performed the
    reset in the audit log. Returns the number of deleted documents in each collection.
    """
    triples_deleted = triples_collection.delete_many({}).deleted_count
    files_deleted = files_collection.delete_many({}).deleted_count
    _record_deletion(
        "clear_database",
        user_name,
        triples_deleted=triples_deleted,
        files_deleted=files_deleted,
    )
    return {"triples_deleted": triples_deleted, "files_deleted": files_deleted}


def _detach_file_from_triples(file_id: str) -> int:
    """
    Removes a document from every triple found in it, and returns how many triples
    that left with nothing to point at.

    A triple several documents agree on survives the deletion of one of them: it
    is re-attached to a document it was also found in, and its extractor list is
    recomputed from what is left — otherwise the deletion would take away a triple
    another document still supports, and keep claiming an extractor that only ever
    found it in the document being removed.
    """
    triples_collection.update_many(
        {"source.occurrences.file_id": file_id},
        {"$pull": {"source.occurrences": {"file_id": file_id}}},
    )

    deleted = 0

    for triple in triples_collection.find({"source.file_id": file_id}):
        remaining = (triple.get("source") or {}).get("occurrences") or []

        if not remaining:
            triples_collection.delete_one({"_id": triple["_id"]})
            deleted += 1
            continue

        fallback = remaining[0]
        extractors = sorted({
            occurrence["extractor"]
            for occurrence in remaining
            if occurrence.get("extractor")
        })
        updates = {
            "source.file_id": fallback.get("file_id"),
            "source.file_name": fallback.get("file_name"),
        }
        if extractors:
            updates["source.extractors"] = extractors

        triples_collection.update_one({"_id": triple["_id"]}, {"$set": updates})

    return deleted


def delete_file(file_id: str, user_name: str) -> dict:
    """
    Deletes a single file and the triples that only it supported, recording who did
    it in the audit log. Raises ValueError if the file does not exist. Returns the
    deleted counts.
    """
    file_doc = files_collection.find_one({"file_id": file_id})
    if file_doc is None:
        raise ValueError(f"File '{file_id}' not found")

    triples_deleted = _detach_file_from_triples(file_id)
    files_collection.delete_one({"file_id": file_id})
    _record_deletion(
        "delete_file",
        user_name,
        file_id=file_id,
        file_name=file_doc.get("file_name"),
        triples_deleted=triples_deleted,
    )
    return {"file_id": file_id, "triples_deleted": triples_deleted}


def update_triple_status(
    triple_id: str,
    status: str,
    user_id: str,
    user_name: str,
    comment: Optional[str] = None,
    modified_triple: Optional[dict] = None,
) -> bool:
    """Updates the status of a triple and records the action in its history."""
    current = triples_collection.find_one({"triple_id": triple_id})
    if not current:
        return False

    history_entry = {
        "action": status,
        "user_id": user_id,
        "user_name": user_name,
        "timestamp": now_utc(),
        "comments": comment,
        "previous_value": {
            "subject": current.get("subject"),
            "predicate": current.get("predicate"),
            "obj": current.get("obj"),
            "status": current.get("status"),
        },
    }

    if modified_triple:
        new_subject = modified_triple.get("subject")
        new_predicate = modified_triple.get("predicate")
        new_obj = modified_triple.get("obj")

        duplicate = _find_matching_triple(new_subject, new_predicate, new_obj, current["_id"])
        if duplicate:
            _merge_into(duplicate, current, status, user_id, user_name, comment)
            return True

    set_fields = {
        "status": status,
        "modified_triple": modified_triple,
    }
    if modified_triple:
        set_fields["subject"] = modified_triple.get("subject")
        set_fields["predicate"] = modified_triple.get("predicate")
        set_fields["obj"] = modified_triple.get("obj")

    result = triples_collection.update_one(
        {"triple_id": triple_id},
        {"$set": set_fields, "$push": {"history": history_entry}},
    )
    return result.modified_count > 0
