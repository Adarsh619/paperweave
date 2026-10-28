"""Fetch citation edges between corpus papers from Semantic Scholar.

Reads data/papers.jsonl and writes data/citations.jsonl as
{"source": <citing arxiv_id>, "target": <cited arxiv_id>}. Only edges where both
ends are in the corpus are kept, so the graph stays closed.

    python pipeline/fetch_citations.py
"""

import s2
from config import CITATIONS_FILE, PAPERS_FILE
from jsonl import read_jsonl, write_jsonl

BATCH_SIZE = 100  # API allows 500, but reference lists make big batches slow


def main() -> None:
    papers = read_jsonl(PAPERS_FILE)
    if not papers:
        raise SystemExit(f"No papers found in {PAPERS_FILE}; run fetch_papers.py first")
    corpus_ids = [p["arxiv_id"] for p in papers]
    corpus_set = set(corpus_ids)

    edges: set[tuple[str, str]] = set()
    no_refs: list[str] = []
    with s2.client() as http:
        for i in range(0, len(corpus_ids), BATCH_SIZE):
            chunk = corpus_ids[i : i + BATCH_SIZE]
            print(f"Fetching references for papers {i + 1}-{i + len(chunk)} of {len(corpus_ids)}...")
            results = s2.request(
                http,
                "POST",
                "/paper/batch",
                params={"fields": "references.externalIds"},
                json={"ids": [f"ARXIV:{a}" for a in chunk]},
            )
            # Results come back in request order, with null for unknown IDs.
            for arxiv_id, item in zip(chunk, results):
                refs = (item or {}).get("references") or []
                if not refs:
                    no_refs.append(arxiv_id)
                for ref in refs:
                    target = s2.arxiv_id_of(ref)
                    if target and target in corpus_set and target != arxiv_id:
                        edges.add((arxiv_id, target))

    count = write_jsonl(CITATIONS_FILE, ({"source": s, "target": t} for s, t in sorted(edges)))
    print(f"Wrote {count} in-corpus citation edges to {CITATIONS_FILE}")
    if no_refs:
        print(f"  note: {len(no_refs)} papers returned no references: {no_refs[:10]}")


if __name__ == "__main__":
    main()
