"""Build the paper corpus into data/papers.jsonl using Semantic Scholar.

Seed papers are always included. Each topic in config.TOPICS then adds its most cited
arXiv papers *per year* (MIN_YEAR..this year), with the same quota for every
(topic, year), so recent work isn't crowded out by older classics and per-year shares
are comparable for trends. Only papers with an arXiv ID and an abstract are kept.

Every paper records the topics that found it. The same searches also give each topic's
field-wide paper count per year (all of Semantic Scholar, not just our corpus), saved to
data/topic_stats.jsonl for the trends page.

Search results are cached in data/.s2_cache/, so an interrupted run resumes cheaply.
Papers from an earlier corpus that the new searches didn't return are kept (their
extractions are reused) and tagged by matching topic phrases.

    python pipeline/fetch_papers.py --max-papers 10000
"""

import argparse
import json
import re
from datetime import date

import s2
from config import DATA_DIR, PAPERS_FILE, SEED_ARXIV_IDS, TOPIC_STATS_FILE, TOPICS
from jsonl import read_jsonl, write_jsonl

FIELDS = "title,abstract,authors,year,publicationDate,venue,externalIds,citationCount,influentialCitationCount"
BATCH_SIZE = 100
MIN_YEAR = 2017
CACHE_DIR = DATA_DIR / ".s2_cache"
# Bare words in topic queries too generic to tag a paper on their own.
GENERIC_WORDS = {"learning", "manipulation", "navigation", "physics", "pretraining", "llm"}


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
        "topics": [],
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


def search_topic(http, name: str, year: int, limit: int) -> tuple[list[dict], int]:
    """Most-cited arXiv papers for one topic and year, and the field-wide match count."""
    cache = CACHE_DIR / f"{re.sub(r'[^a-z0-9]+', '-', name.lower())}-{year}-{limit}.json"
    if cache.exists():
        cached = json.loads(cache.read_text(encoding="utf-8"))
        return cached["records"], cached["total"]

    topic = TOPICS[name]
    params = {
        "query": topic["query"],
        "fields": FIELDS,
        "fieldsOfStudy": topic["fos"],
        "year": str(year),
        "sort": "citationCount:desc",
    }
    records: list[dict] = []
    total = None
    while len(records) < limit:
        page = s2.request(http, "GET", "/paper/search/bulk", params=params)
        total = page.get("total", 0) if total is None else total
        records.extend(r for r in (_to_record(p, "topic") for p in page.get("data") or []) if r)
        if not page.get("token"):
            break
        params["token"] = page["token"]
    records = records[:limit]
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({"records": records, "total": total or 0}), encoding="utf-8")
    return records, total or 0


def topic_phrases(query: str) -> list[str]:
    """Quoted phrases and distinctive bare words of a bulk-search query, lowercased."""
    quoted = re.findall(r'"([^"]+)"', query)
    bare = re.findall(r"[A-Za-z][A-Za-z-]{3,}", re.sub(r'"[^"]*"', " ", query))
    return [p.lower() for p in quoted + [w for w in bare if w.lower() not in GENERIC_WORDS]]


def match_topics(paper: dict) -> list[str]:
    """Topics whose query the paper satisfies: every '+'-joined part (AND) must have a phrase
    in the title or abstract. Parts with only generic words count as satisfied."""
    text = f"{paper['title']} {paper['abstract']}".lower()

    def matches(query: str) -> bool:
        parts = [topic_phrases(part) for part in query.split("+")]
        return all(not phrases or any(p in text for p in phrases) for phrases in parts) and any(parts)

    return [name for name, t in TOPICS.items() if matches(t["query"])]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--max-papers", type=int, default=10000)
    args = parser.parse_args()

    previous = {p["arxiv_id"]: p for p in read_jsonl(PAPERS_FILE)}
    seed_topics = {s: name for name, t in TOPICS.items() for s in t["seeds"]}
    years = range(MIN_YEAR, date.today().year + 1)
    corpus: dict[str, dict] = {}
    stats = []

    with s2.client() as http:
        print(f"Fetching {len(SEED_ARXIV_IDS)} seed papers...")
        for rec in fetch_seeds(http):
            rec["topics"] = [seed_topics[rec["arxiv_id"]]]
            corpus[rec["arxiv_id"]] = rec
        missing = sorted(set(SEED_ARXIV_IDS) - corpus.keys())
        if missing:
            print(f"  warning: seeds missing or without abstract: {missing}")

        quota = max(1, -(-(args.max_papers - len(corpus)) // (len(TOPICS) * len(years))))
        print(f"{len(TOPICS)} topics x {len(years)} years, up to {quota} papers each")
        for name in TOPICS:
            added = 0
            for year in years:
                # Over-fetch: results overlap with seeds and other topics.
                records, total = search_topic(http, name, year, quota * 2)
                stats.append({"topic": name, "field": TOPICS[name]["field"], "year": year, "total": total})
                year_added = 0
                for rec in records:
                    if rec["arxiv_id"] in corpus:
                        topics = corpus[rec["arxiv_id"]]["topics"]
                        if name not in topics:
                            topics.append(name)
                    elif year_added < quota:
                        rec["topics"] = [name]
                        corpus[rec["arxiv_id"]] = rec
                        year_added += 1
                added += year_added
            print(f"  {name}: +{added} papers (corpus: {len(corpus)})")

    carried = [p for i, p in previous.items() if i not in corpus]
    for p in carried:
        p["topics"] = match_topics(p)
        corpus[p["arxiv_id"]] = p
    if carried:
        untagged = sum(1 for p in carried if not p["topics"])
        print(f"Kept {len(carried)} papers from the previous corpus ({untagged} without a topic match)")

    count = write_jsonl(PAPERS_FILE, sorted(corpus.values(), key=lambda p: p["arxiv_id"]))
    write_jsonl(TOPIC_STATS_FILE, stats)
    print(f"Wrote {count} papers to {PAPERS_FILE} and {len(stats)} topic-year counts to {TOPIC_STATS_FILE.name}")


if __name__ == "__main__":
    main()
