from __future__ import annotations

"""Simple retrieval evaluation helper.

This script assumes your points have payload fields:
- caption: str
- tags: list[str] (optional)
- stock: bool
- filename: str

It runs a *synthetic* evaluation:
- picks N random items
- uses their caption as a query (text->image)
- checks whether the same item appears in Top-K

This is not a scientific benchmark, but it's a good sanity check for a course project.
"""

import random
from typing import List

from src.config import settings
from src.features.embedding import embed_text
from src.services.qdrant_service import get_qdrant_client, ensure_collection_exists, list_points, search


def main(sample_n: int = 20, k: int = 10, seed: int = 42) -> None:
    random.seed(seed)

    qdrant = get_qdrant_client()
    ensure_collection_exists(qdrant)

    items = list_points(qdrant, limit=1000)
    if len(items) < 5:
        print("Not enough items in Qdrant. Seed images first.")
        return

    candidates = [it for it in items if (it.get("payload") or {}).get("caption")]
    if len(candidates) < 5:
        print("Not enough items with captions.")
        return

    picks = random.sample(candidates, k=min(sample_n, len(candidates)))
    hits = 0

    for it in picks:
        pid = it.get("id")
        cap = (it.get("payload") or {}).get("caption", "")
        qvec = embed_text(cap)
        res = search(qdrant, qvec, top_k=k)
        got_ids = [str(r.id) for r in res]
        if pid in got_ids:
            hits += 1

    print(f"Self-retrieval hit@{k}: {hits}/{len(picks)} = {hits/len(picks):.2%}")


if __name__ == "__main__":
    main()
