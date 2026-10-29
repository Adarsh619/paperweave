"""Hybrid paper search over Qdrant: MiniLM (meaning) + BM25 (exact terms), fused with RRF.

Same index layout as pipeline/qdrant_store.py. Text goes in as models.Document, so
Qdrant Cloud embeds it server-side in production and fastembed does it locally.
"""

from qdrant_client import models

from app import config, stores

DENSE = "dense"
SPARSE = "bm25"


def search(query: str, limit: int = 6, min_year: int | None = None) -> list[dict]:
    flt = None
    if min_year:
        flt = models.Filter(must=[models.FieldCondition(key="year", range=models.Range(gte=min_year))])
    points = stores.qdrant().query_points(
        config.QDRANT_COLLECTION,
        prefetch=[
            models.Prefetch(
                query=models.Document(text=query, model=config.DENSE_MODEL), using=DENSE, filter=flt, limit=limit * 4
            ),
            models.Prefetch(
                query=models.Document(text=query, model=config.SPARSE_MODEL), using=SPARSE, filter=flt, limit=limit * 4
            ),
        ],
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        limit=limit,
    ).points
    return [
        {
            "arxiv_id": p.payload["arxiv_id"],
            "title": p.payload["title"],
            "year": p.payload.get("year"),
            "abstract": p.payload.get("abstract", ""),
            "abs_url": p.payload.get("abs_url"),
            "citation_count": p.payload.get("citation_count"),
        }
        for p in points
    ]
