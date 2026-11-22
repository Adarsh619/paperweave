"""Write frontend/public/stats.json: corpus totals and paper counts per field and topic.

The home and About pages read this static file, so they show coverage even while the
backend sleeps. Re-run after rebuilding the snapshot.

    python pipeline/export_stats.py
"""

import json
from collections import Counter

from config import CITATIONS_FILE, ENTITY_INDEX_FILE, PAPERS_FILE, ROOT, TOPICS
from fetch_papers import match_topics
from jsonl import read_jsonl

OUT = ROOT / "frontend" / "public" / "stats.json"


def main() -> None:
    papers = read_jsonl(PAPERS_FILE)
    # Older snapshots have no "topics" field; tag those by topic phrases.
    paper_topics = [p.get("topics") or match_topics(p) for p in papers]
    per_topic = Counter(t for topics in paper_topics for t in topics)

    fields = []
    for field in dict.fromkeys(t["field"] for t in TOPICS.values()):
        names = [n for n, t in TOPICS.items() if t["field"] == field and per_topic[n]]
        if not names:
            continue
        field_papers = sum(1 for topics in paper_topics if set(topics) & set(names))
        fields.append({"name": field, "papers": field_papers,
                       "topics": [{"name": n, "papers": per_topic[n]} for n in names]})

    stats = {
        "totals": {
            "papers": len(papers),
            "citations": len(read_jsonl(CITATIONS_FILE)),
            "entities": len(read_jsonl(ENTITY_INDEX_FILE)),
        },
        "fields": fields,
    }
    OUT.write_text(json.dumps(stats, indent=1), encoding="utf-8")
    print(f"Wrote {OUT}: {stats['totals']}, {len(fields)} fields")


if __name__ == "__main__":
    main()
