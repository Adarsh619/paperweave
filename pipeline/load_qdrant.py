"""Index papers from data/papers.jsonl into Qdrant for hybrid (dense + BM25) search.

Idempotent: each paper has a stable point ID, so re-running overwrites.
Entity names from data/entities.jsonl go into the payload for filtering.

    python pipeline/load_qdrant.py              # create collection if missing, upsert
    python pipeline/load_qdrant.py --recreate   # drop and rebuild the collection

The first local run downloads the two small embedding models (~100 MB) to the
fastembed cache.
"""

import argparse
import time

from qdrant_client import models

from config import ENTITIES_FILE, PAPERS_FILE, QDRANT_COLLECTION, QDRANT_URL
from jsonl import read_jsonl
from qdrant_store import DENSE, SPARSE, client, dense_doc, ensure_collection, paper_text, point_id, sparse_doc

BATCH_SIZE = 32


def to_point(paper: dict, entities: dict) -> models.PointStruct:
    text = paper_text(paper)
    return models.PointStruct(
        id=point_id(paper["arxiv_id"]),
        vector={DENSE: dense_doc(text), SPARSE: sparse_doc(text)},
        payload={
            "arxiv_id": paper["arxiv_id"],
            "title": paper["title"],
            "abstract": paper["abstract"],
            "authors": paper["authors"],
            "year": paper.get("year"),
            "venue": paper.get("venue"),
            "citation_count": paper.get("citation_count"),
            "abs_url": paper.get("abs_url"),
            "pdf_url": paper.get("pdf_url"),
            "methods": entities.get("methods_proposed", []) + entities.get("methods_used", []),
            "datasets": entities.get("datasets", []),
            "tasks": entities.get("tasks", []),
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--recreate", action="store_true", help="drop and rebuild the collection")
    args = parser.parse_args()

    papers = read_jsonl(PAPERS_FILE)
    if not papers:
        raise SystemExit(f"No papers found in {PAPERS_FILE}; run fetch_papers.py first")
    entities = {row["arxiv_id"]: row for row in read_jsonl(ENTITIES_FILE)}

    qdrant = client()
    ensure_collection(qdrant, recreate=args.recreate)
    print(f"Collection '{QDRANT_COLLECTION}' ready at {QDRANT_URL}")

    start = time.perf_counter()
    for i in range(0, len(papers), BATCH_SIZE):
        batch = papers[i : i + BATCH_SIZE]
        qdrant.upsert(QDRANT_COLLECTION, points=[to_point(p, entities.get(p["arxiv_id"], {})) for p in batch])
        print(f"  indexed {min(i + BATCH_SIZE, len(papers))}/{len(papers)}")

    count = qdrant.count(QDRANT_COLLECTION, exact=True).count
    print(f"Indexed {len(papers)} papers in {time.perf_counter() - start:.1f}s; collection has {count} points")


if __name__ == "__main__":
    main()
