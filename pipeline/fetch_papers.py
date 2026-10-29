"""Build the paper corpus into data/papers.jsonl using Semantic Scholar.

Seed papers are always included; topic searches (sorted by citation count) fill
the rest up to --max-papers. Only papers with an arXiv ID and an abstract are
kept, so every node links to arXiv and has text to embed.

    python pipeline/fetch_papers.py --max-papers 50
"""

import argparse

import s2
from config import PAPERS_FILE, SEED_ARXIV_IDS, TOPIC_QUERIES
from jsonl import write_jsonl

FIELDS = "title,abstract,authors,year,publicationDate,venue,externalIds,citationCount,influentialCitationCount"
BATCH_SIZE = 100
MIN_YEAR = 2017


def _to_record(paper: dict, source: str) -> dict | None:
    arxiv_id = s2.arxiv_id_of(paper)
    if not arxiv_id or not paper.get("abstract") or not paper.get("title"):
        return None
    year = paper.get("year")
    return {
        "arxiv_id": arxiv_id,
        "s2_id": paper.get("paperId"),
        "title": paper["title"].strip(),
        "abstract": paper["abstract"].strip(),
        "authors": [a["name"] for a in paper.get("authors") or [] if a.get("name")],
        "year": year,
        "published": paper.get("publicationDate") or (f"{year}-01-01" if year else None),
        "venue": paper.get("venue") or None,
        "citation_count": paper.get("citationCount") or 0,
        "influential_citation_count": paper.get("influentialCitationCount") or 0,
        "abs_url": f"https://arxiv.org/abs/{arxiv_id}",
        "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}",
        "source": source,
    }


def fetch_seeds(http) -> list[dict]:
    records = []
    for i in range(0, len(SEED_ARXIV_IDS), BATCH_SIZE):
        chunk = SEED_ARXIV_IDS[i : i + BATCH_SIZE]
        results = s2.request(
            http, "POST", "/paper/batch", params={"fields": FIELDS}, json={"ids": [f"ARXIV:{a}" for a in chunk]}
        )
        records.extend(r for r in (_to_record(p, "seed") for p in results if p) if r)
    return records


def search_topic(http, query: str, limit: int) -> list[dict]:
    """Most-cited arXiv papers matching the query, up to `limit` usable records."""
    records: list[dict] = []
    params = {
        "query": query,
        "fields": FIELDS,
        "fieldsOfStudy": "Computer Science",
        "year": f"{MIN_YEAR}-",
        "sort": "citationCount:desc",
    }
    while len(records) < limit:
        page = s2.request(http, "GET", "/paper/search/bulk", params=params)
        records.extend(r for r in (_to_record(p, "topic") for p in page.get("data") or []) if r)
        if not page.get("token"):
            break
        params["token"] = page["token"]
    return records[:limit]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--max-papers", type=int, default=500)
    args = parser.parse_args()

    corpus: dict[str, dict] = {}
    with s2.client() as http:
        print(f"Fetching {len(SEED_ARXIV_IDS)} seed papers...")
        for rec in fetch_seeds(http):
            corpus[rec["arxiv_id"]] = rec
        missing = sorted(set(SEED_ARXIV_IDS) - corpus.keys())
        if missing:
            print(f"  warning: seeds missing or without abstract: {missing}")

        # Each topic gets an equal share of the remaining slots, so early topics
        # can't crowd out later ones. Over-fetch 2x: results overlap with seeds
        # and with each other; a topic that falls short leaves slots for the next.
        for i, query in enumerate(TOPIC_QUERIES):
            remaining = args.max_papers - len(corpus)
            if remaining <= 0:
                break
            quota = -(-remaining // (len(TOPIC_QUERIES) - i))
            print(f"Searching (up to {quota}): {query}")
            added = 0
            for rec in search_topic(http, query, max(10, quota * 2)):
                if added >= quota:
                    break
                if rec["arxiv_id"] not in corpus:
                    corpus[rec["arxiv_id"]] = rec
                    added += 1
            print(f"  +{added} papers (corpus: {len(corpus)})")

    count = write_jsonl(PAPERS_FILE, sorted(corpus.values(), key=lambda p: p["arxiv_id"]))
    print(f"Wrote {count} papers to {PAPERS_FILE}")


if __name__ == "__main__":
    main()
