"""Qdrant client and hybrid search shared by the loader, checks and (later) the backend.

Each paper is one point with two named vectors over "title + abstract":
  dense   MiniLM embedding: finds papers that mean the same thing
  bm25    sparse keyword vector: finds exact terms such as "HotpotQA" or "LoRA"
Hybrid search runs both and merges the rankings with Reciprocal Rank Fusion.

Text goes in as models.Document, so the same code works in both places:
locally qdrant-client embeds with fastembed; on Qdrant Cloud (cloud_inference)
the server embeds it.
"""

import uuid

from qdrant_client import QdrantClient, models

from config import (
    DENSE_MODEL,
    QDRANT_API_KEY,
    QDRANT_CLOUD_INFERENCE,
    QDRANT_COLLECTION,
    QDRANT_URL,
    SPARSE_MODEL,
)

DENSE = "dense"
SPARSE = "bm25"
DENSE_SIZE = 384


def client() -> QdrantClient:
    return QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, cloud_inference=QDRANT_CLOUD_INFERENCE, timeout=60)


def point_id(arxiv_id: str) -> str:
    """Stable ID per paper, so re-loading overwrites instead of duplicating."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"arxiv:{arxiv_id}"))


def paper_text(paper: dict) -> str:
    return f"{paper['title']}\n\n{paper['abstract']}"


def dense_doc(text: str) -> models.Document:
    return models.Document(text=text, model=DENSE_MODEL)


def sparse_doc(text: str) -> models.Document:
    return models.Document(text=text, model=SPARSE_MODEL)


def ensure_collection(qdrant: QdrantClient, recreate: bool = False) -> None:
    if recreate and qdrant.collection_exists(QDRANT_COLLECTION):
        qdrant.delete_collection(QDRANT_COLLECTION)
    if not qdrant.collection_exists(QDRANT_COLLECTION):
        qdrant.create_collection(
            QDRANT_COLLECTION,
            vectors_config={DENSE: models.VectorParams(size=DENSE_SIZE, distance=models.Distance.COSINE)},
            sparse_vectors_config={SPARSE: models.SparseVectorParams(modifier=models.Modifier.IDF)},
        )
    # Filters the agent will use: "papers since 2024", "this paper", "uses MMLU".
    for field, schema in {
        "arxiv_id": models.PayloadSchemaType.KEYWORD,
        "year": models.PayloadSchemaType.INTEGER,
        "methods": models.PayloadSchemaType.KEYWORD,
        "datasets": models.PayloadSchemaType.KEYWORD,
    }.items():
        qdrant.create_payload_index(QDRANT_COLLECTION, field, schema)


def year_filter(min_year: int | None) -> models.Filter | None:
    if min_year is None:
        return None
    return models.Filter(must=[models.FieldCondition(key="year", range=models.Range(gte=min_year))])


def search(
    qdrant: QdrantClient, query: str, mode: str = "hybrid", limit: int = 5, min_year: int | None = None
) -> list[models.ScoredPoint]:
    """mode: "hybrid" (dense + BM25 fused with RRF), "dense" or "bm25"."""
    flt = year_filter(min_year)
    if mode == "dense":
        return qdrant.query_points(
            QDRANT_COLLECTION, query=dense_doc(query), using=DENSE, query_filter=flt, limit=limit
        ).points
    if mode == "bm25":
        return qdrant.query_points(
            QDRANT_COLLECTION, query=sparse_doc(query), using=SPARSE, query_filter=flt, limit=limit
        ).points
    return qdrant.query_points(
        QDRANT_COLLECTION,
        prefetch=[
            models.Prefetch(query=dense_doc(query), using=DENSE, filter=flt, limit=limit * 4),
            models.Prefetch(query=sparse_doc(query), using=SPARSE, filter=flt, limit=limit * 4),
        ],
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        limit=limit,
    ).points
