"""Print sanity checks for the Qdrant index: counts and dense vs BM25 vs hybrid results.

    python pipeline/check_search.py
    python pipeline/check_search.py "your own question"
"""

import sys

from config import PAPERS_FILE, QDRANT_COLLECTION
from jsonl import read_jsonl
from qdrant_store import client, search

# Each query has a paper that should rank near the top, so a regression is visible.
QUERIES = [
    ("graph-based retrieval for summarizing a whole corpus", "2404.16130"),  # GraphRAG
    ("HotpotQA multi-hop question answering", None),
    ("retrieval model decides when to retrieve and critiques its own output", "2310.11511"),  # Self-RAG
    ("low-rank adapters for cheap fine-tuning", "2106.09685"),  # LoRA
    ("why models ignore information in the middle of long inputs", "2307.03172"),  # Lost in the Middle
]


def main() -> None:
    qdrant = client()
    count = qdrant.count(QDRANT_COLLECTION, exact=True).count
    papers = len(read_jsonl(PAPERS_FILE))
    print(f"points in '{QDRANT_COLLECTION}': {count} (papers.jsonl has {papers})")

    queries = [(q, None) for q in sys.argv[1:]] or QUERIES
    hits = 0
    for query, expected in queries:
        print(f"\nQ: {query}")
        for mode in ("dense", "bm25", "hybrid"):
            points = search(qdrant, query, mode=mode, limit=3)
            ids = [p.payload["arxiv_id"] for p in points]
            print(f"  {mode:6} " + " | ".join(f"{p.payload['title'][:45]} ({p.payload['arxiv_id']})" for p in points))
            if mode == "hybrid" and expected:
                found = expected in ids
                hits += found
                print(f"  expected {expected} in hybrid top 3: {'yes' if found else 'NO'}")

    expected_total = sum(1 for _, e in queries if e)
    if expected_total:
        print(f"\nHybrid top-3 hits: {hits}/{expected_total}")

    print("\nFiltered (year >= 2024): " + ", ".join(
        f"{p.payload['title'][:40]} ({p.payload['year']})"
        for p in search(qdrant, "retrieval-augmented generation", limit=3, min_year=2024)
    ))


if __name__ == "__main__":
    main()
