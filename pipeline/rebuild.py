"""Rebuild Neo4j and Qdrant from the committed data/ snapshot.

No Semantic Scholar or Ollama calls: everything comes from data/*.jsonl, so this
restores a wiped or deleted free-tier database in a few minutes. Point it at
production by setting NEO4J_* and QDRANT_* (plus QDRANT_CLOUD_INFERENCE=true)
in .env first.

    python pipeline/rebuild.py            # upsert into both databases
    python pipeline/rebuild.py --fresh    # wipe both first (removes stale data)
"""

import argparse
import time

import load_neo4j
import load_qdrant
from config import (
    CITATIONS_FILE,
    ENTITIES_FILE,
    ENTITY_INDEX_FILE,
    NEO4J_URI,
    PAPERS_FILE,
    QDRANT_URL,
)
from jsonl import read_jsonl

SNAPSHOT = [PAPERS_FILE, CITATIONS_FILE, ENTITIES_FILE, ENTITY_INDEX_FILE]


def check_snapshot() -> None:
    missing = [f.name for f in SNAPSHOT if not f.exists()]
    if missing:
        raise SystemExit(f"Snapshot incomplete, missing: {missing}. Run the full pipeline first.")
    papers = {p["arxiv_id"] for p in read_jsonl(PAPERS_FILE)}
    extracted = {e["arxiv_id"] for e in read_jsonl(ENTITIES_FILE)}
    print(f"Snapshot: {len(papers)} papers, {len(read_jsonl(CITATIONS_FILE))} citations, "
          f"entities for {len(papers & extracted)}/{len(papers)} papers")
    if papers - extracted:
        print(f"  warning: {len(papers - extracted)} papers have no entities; run extract_entities.py + normalize.py")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fresh", action="store_true", help="wipe both databases before loading")
    args = parser.parse_args()

    check_snapshot()
    start = time.perf_counter()
    print(f"\n== Neo4j ({NEO4J_URI}) ==")
    load_neo4j.load(fresh=args.fresh)
    print(f"\n== Qdrant ({QDRANT_URL}) ==")
    load_qdrant.load(recreate=args.fresh)
    print(f"\nRebuild finished in {time.perf_counter() - start:.0f}s. "
          "Verify with check_graph.py and check_search.py.")


if __name__ == "__main__":
    main()
