from __future__ import annotations

from typing import Any, Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    Filter,
    FieldCondition,
    MatchValue,
    PointStruct,
    PointsSelector,
    VectorParams,
)

from src.config import settings


def get_qdrant_client() -> QdrantClient:
    """Create Qdrant client.

    Use remote Qdrant only when explicitly configured AND reachable.
    Otherwise fallback to local embedded storage (no Docker, no server).
    """
    # Try remote only if configured and reachable
    if getattr(settings, "qdrant_url", None):
        try:
            remote = QdrantClient(
                url=settings.qdrant_url,
                api_key=getattr(settings, "qdrant_api_key", None),
                timeout=10,
            )
            # Force an actual HTTP call; if it fails, we fallback
            remote.get_collections()
            return remote
        except Exception:
            pass

    # Local embedded Qdrant (file-based)
    return QdrantClient(path="qdrant_local", timeout=60)


def ensure_collection_exists(client: QdrantClient) -> None:
    """Create collection if missing."""
    try:
        exists = client.collection_exists(settings.qdrant_collection)
    except Exception:
        # older clients: try get_collection
        try:
            client.get_collection(settings.qdrant_collection)
            exists = True
        except Exception:
            exists = False

    if exists:
        return

    client.create_collection(
        collection_name=settings.qdrant_collection,
        vectors_config=VectorParams(size=settings.embedding_dim, distance=Distance.COSINE),
    )


def upsert_point(client: QdrantClient, point_id: str, vector: List[float], payload: Dict[str, Any]) -> None:
    pt = PointStruct(id=point_id, vector=vector, payload=payload)
    client.upsert(collection_name=settings.qdrant_collection, points=[pt])


def build_source_filter(source_choice: str | None) -> Optional[Filter]:
    """source_choice: 'All' | 'Stock' | 'User uploads'"""
    if not source_choice or source_choice == "All":
        return None
    if source_choice == "Stock":
        return Filter(must=[FieldCondition(key="stock", match=MatchValue(value=True))])
    if source_choice == "User uploads":
        return Filter(must=[FieldCondition(key="stock", match=MatchValue(value=False))])
    return None


def search(
    client: QdrantClient,
    vector: List[float],
    top_k: int,
    qfilter: Optional[Filter] = None,
):
    """Compatibility layer for different qdrant-client versions.

    Some versions expose client.search(...),
    others expose client.query_points(...).
    """
    # Common API
    if hasattr(client, "search"):
        return client.search(
            collection_name=settings.qdrant_collection,
            query_vector=vector,
            limit=top_k,
            query_filter=qfilter,
            with_payload=True,
            with_vectors=False,
        )

    # Alternative API (some versions)
    if hasattr(client, "query_points"):
        res = client.query_points(
            collection_name=settings.qdrant_collection,
            query=vector,
            limit=top_k,
            query_filter=qfilter,
            with_payload=True,
            with_vectors=False,
        )
        # Many versions return an object with .points
        return getattr(res, "points", res)

    raise AttributeError("Qdrant client has no supported search method (search/query_points).")


def list_points(client: QdrantClient, limit: int = 1000) -> List[Dict[str, Any]]:
    """Return latest points (best-effort). Uses scroll; ordering is not guaranteed by Qdrant,
    but works well enough for a gallery in a course project.
    """
    points: List[Dict[str, Any]] = []
    next_offset = None
    remaining = limit

    while remaining > 0:
        batch, next_offset = client.scroll(
            collection_name=settings.qdrant_collection,
            limit=min(remaining, 256),
            with_payload=True,
            with_vectors=False,
            offset=next_offset,
        )
        if not batch:
            break
        for p in batch:
            points.append({"id": str(p.id), "payload": p.payload or {}})
        remaining = limit - len(points)
        if next_offset is None:
            break

    # sort by added_at desc if present
    points.sort(key=lambda x: (x.get("payload", {}).get("added_at") or 0), reverse=True)
    return points[:limit]


def delete_points_by_filter(client: QdrantClient, qfilter: Filter) -> None:
    client.delete(
        collection_name=settings.qdrant_collection,
        points_selector=PointsSelector(filter=qfilter),
    )
