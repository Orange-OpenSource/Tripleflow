import logging

from fastapi import APIRouter, HTTPException

from app.schemas.sinks import (
    PublishRequest,
    PublishResponse,
    SinkConfig,
    SinkListResponse,
)
from app.services.sinks_service import (
    build_update,
    delete_sink,
    get_sink,
    insert_sink,
    list_sinks,
    publish_http,
    send_update,
)
from app.services.triple_db_service import (
    get_triples_by_ids,
    mark_triples_published,
    record_publication,
)

router = APIRouter(prefix="/sinks", tags=["sinks"])
logger = logging.getLogger(__name__)


@router.get("", response_model=SinkListResponse)
def get_sinks():
    """Returns all publication targets registered on the backend."""
    return SinkListResponse(sinks=list_sinks())


@router.post("")
def create_sink(config: SinkConfig):
    """Registers a new SPARQL UPDATE target."""
    try:
        return insert_sink(config)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.delete("/{sink_id}")
def remove_sink(sink_id: str):
    """Deletes a publication target by id."""
    try:
        delete_sink(sink_id)
        return {"ok": True}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{sink_id}/publish", response_model=PublishResponse)
async def publish(sink_id: str, req: PublishRequest):
    """
    Inserts validated triples into the target's graph with a SPARQL `INSERT DATA`.

    Only triples whose status is "validated" are eligible: publishing is the last
    step of the review workflow, so anything still pending, rejected or unknown is
    reported as skipped rather than pushed. Triples without resolved Q/P
    identifiers are skipped too, since they have no IRI in the target graph.

    With dry_run, the update is built and returned but never sent, and nothing is
    marked as published.
    """
    sink = get_sink(sink_id)
    if sink is None:
        raise HTTPException(status_code=404, detail=f"Target '{sink_id}' not found")

    triples = get_triples_by_ids(req.triple_ids)
    found_ids = {triple.get("triple_id") for triple in triples}

    skipped = [
        {"triple_id": triple_id, "reason": "triple not found"}
        for triple_id in req.triple_ids
        if triple_id not in found_ids
    ]

    eligible = []
    for triple in triples:
        status = triple.get("status")
        if status == "validated":
            eligible.append(triple)
        else:
            skipped.append({
                "triple_id": triple.get("triple_id"),
                "reason": f"status is '{status or 'unknown'}', only validated triples are published",
            })

    if (sink.get("type") or "sparql") == "http":
        return await _publish_over_http(sink_id, sink, eligible, skipped, req)

    update, unmappable = build_update(eligible, sink, req.user_name)
    skipped.extend(unmappable)

    unmappable_ids = {item["triple_id"] for item in unmappable}
    published_ids = [
        triple["triple_id"]
        for triple in eligible
        if triple.get("triple_id") not in unmappable_ids
    ]

    if req.dry_run:
        return PublishResponse(
            sink_id=sink_id,
            dry_run=True,
            published_count=len(published_ids),
            skipped=skipped,
            sparql=update or None,
        )

    if not published_ids:
        raise HTTPException(
            status_code=400,
            detail="No publishable triple in the selection: validate them and make sure "
                   "their subject, predicate and object are all linked to an identifier.",
        )

    try:
        await send_update(sink, update)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected error while publishing to target '%s'", sink_id)
        raise HTTPException(status_code=500, detail="Internal server error") from exc

    mark_triples_published(published_ids, sink_id, req.user_name)
    record_publication(sink_id, req.user_name, len(published_ids), len(skipped))

    return PublishResponse(
        sink_id=sink_id,
        dry_run=False,
        published_count=len(published_ids),
        skipped=skipped,
        sparql=None,
    )


async def _publish_over_http(
    sink_id: str,
    sink: dict,
    eligible: list[dict],
    skipped: list[dict],
    req: PublishRequest,
) -> PublishResponse:
    """
    Publishes to a target written through its own API rather than SPARQL.

    Each triple is a separate call, so unlike a SPARQL update this is not all or
    nothing: whatever the target accepted is recorded as published, and the rest
    is reported with the reason the target gave.
    """
    try:
        published_ids, failures, prepared = await publish_http(
            sink, eligible, req.user_name, dry_run=req.dry_run
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected error while publishing to target '%s'", sink_id)
        raise HTTPException(status_code=500, detail="Internal server error") from exc

    skipped = skipped + failures

    if req.dry_run:
        return PublishResponse(
            sink_id=sink_id,
            dry_run=True,
            published_count=len(prepared),
            skipped=skipped,
            requests=prepared,
        )

    if published_ids:
        mark_triples_published(published_ids, sink_id, req.user_name)
        record_publication(sink_id, req.user_name, len(published_ids), len(skipped))

    return PublishResponse(
        sink_id=sink_id,
        dry_run=False,
        published_count=len(published_ids),
        skipped=skipped,
    )
