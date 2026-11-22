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
    TOPICS,
)
from jsonl import read_jsonl

SNAPSHOT = [PAPERS_FILE, CITATIONS_FILE, ENTITIES_FILE, ENTITY_INDEX_FILE]


# AuraDB Free limits (confirm in the Aura console; they have changed before).
AURA_FREE_NODES = 200_000
AURA_FREE_RELATIONSHIPS = 400_000


def graph_size(papers: list[dict], citations: list[dict], entities: list[dict], entity_index: list[dict]) -> tuple[int, int]:
    """Nodes and relationships load_neo4j.py will create, counted from the snapshot files."""
    authors = {a for p in papers for a in p["authors"]}
    nodes = len(papers) + len(authors) + len(entity_index) + len(TOPICS) + len({t["field"] for t in TOPICS.values()})
    entity_links = sum(len(e[k]) for e in entities for k in ("methods_proposed", "methods_used", "datasets", "tasks"))
    improves = sum(len(e["methods_proposed"]) * len(e["improves_on"]) for e in entities)  # upper bound
    rels = (sum(len(p["authors"]) for p in papers) + len(citations) + entity_links + improves
            + sum(len(p.get("topics", [])) for p in papers) + len(TOPICS))
    return nodes, rels


def check_snapshot() -> None:
    missing = [f.name for f in SNAPSHOT if not f.exists()]
    if missing:
        raise SystemExit(f"Snapshot incomplete, missing: {missing}. Run the full pipeline first.")
    papers = read_jsonl(PAPERS_FILE)
    citations = read_jsonl(CITATIONS_FILE)
    entities = read_jsonl(ENTITIES_FILE)
    ids = {p["arxiv_id"] for p in papers}
    extracted = {e["arxiv_id"] for e in entities}
    print(f"Snapshot: {len(ids)} papers, {len(citations)} citations, "
          f"entities for {len(ids & extracted)}/{len(ids)} papers")
    if ids - extracted:
        print(f"  warning: {len(ids - extracted)} papers have no entities; run extract_entities.py + normalize.py")

    nodes, rels = graph_size(papers, citations, entities, read_jsonl(ENTITY_INDEX_FILE))
    print(f"Graph size: ~{nodes:,} nodes, ~{rels:,} relationships "
          f"(AuraDB Free: {AURA_FREE_NODES:,} / {AURA_FREE_RELATIONSHIPS:,})")
    if NEO4J_URI.startswith("neo4j+s://") and (nodes > AURA_FREE_NODES or rels > AURA_FREE_RELATIONSHIPS):
        raise SystemExit(
            "Too big for AuraDB Free. Shrink the corpus (--max-papers), or store authors as a list on each "
            "Paper instead of Author nodes (drops ~1 node and ~1 relationship per author)."
        )


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
