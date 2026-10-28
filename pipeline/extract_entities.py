"""Extract methods, datasets, tasks and "improves on" claims from abstracts with a local LLM.

Reads data/papers.jsonl and appends one JSON row per paper to data/entities_raw.jsonl.
Resumable: papers already in the output file are skipped, so it is safe to stop and
re-run. Use --redo to start over.

Ollama's structured outputs constrain the model to the JSON schema below, so every
row parses. Names are left as the model wrote them; normalize.py cleans them up.

    python pipeline/extract_entities.py            # all papers not yet extracted
    python pipeline/extract_entities.py --limit 5  # quick trial run
"""

import argparse
import json
import time

import httpx

from config import ENTITIES_RAW_FILE, OLLAMA_MODEL, OLLAMA_URL, PAPERS_FILE
from jsonl import read_jsonl

MAX_ITEMS = 6

_name_list = {"type": "array", "items": {"type": "string"}, "maxItems": MAX_ITEMS}
SCHEMA = {
    "type": "object",
    "properties": {
        "methods_proposed": _name_list,
        "methods_used": _name_list,
        "datasets": _name_list,
        "tasks": _name_list,
        "improves_on": _name_list,
    },
    "required": ["methods_proposed", "methods_used", "datasets", "tasks", "improves_on"],
}

SYSTEM_PROMPT = """You extract structured facts from AI research paper abstracts for a knowledge graph.
Return JSON with these lists (use [] when the abstract does not say):
- methods_proposed: names of new models, methods, frameworks or techniques THIS paper introduces.
- methods_used: existing named methods or models this paper builds on or applies (not ones it proposes).
- datasets: named datasets or benchmarks the paper evaluates on (e.g. "Natural Questions", "MMLU").
- tasks: research tasks addressed, as short noun phrases (e.g. "open-domain question answering").
- improves_on: named existing methods or models the paper says it outperforms, extends or improves.
Rules:
- Only include names explicitly stated in the abstract. Never guess.
- Use the shortest common name; keep acronyms as written (e.g. "RAG", "BERT", "DPR").
- Skip generic phrases like "large language models", "baselines", "state-of-the-art methods",
  "existing best results", "ensembles".
- improves_on must name specific methods or models (e.g. "BERT", "ELMo"), never citations like
  "Peters et al., 2018" and never vague phrases.
- At most 6 items per list."""


def extract(http: httpx.Client, paper: dict) -> dict:
    user = f"Title: {paper['title']}\n\nAbstract: {paper['abstract']}"
    resp = http.post(
        f"{OLLAMA_URL}/api/chat",
        json={
            "model": OLLAMA_MODEL,
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}],
            "format": SCHEMA,
            "stream": False,
            "options": {"temperature": 0, "num_ctx": 4096},
        },
    )
    resp.raise_for_status()
    data = json.loads(resp.json()["message"]["content"])
    return {key: [s.strip() for s in data.get(key, []) if s and s.strip()][:MAX_ITEMS] for key in SCHEMA["required"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--limit", type=int, help="extract at most N papers this run")
    parser.add_argument("--redo", action="store_true", help="discard previous output and start over")
    args = parser.parse_args()

    papers = read_jsonl(PAPERS_FILE)
    if not papers:
        raise SystemExit(f"No papers found in {PAPERS_FILE}; run fetch_papers.py first")
    if args.redo:
        ENTITIES_RAW_FILE.unlink(missing_ok=True)

    done = {row["arxiv_id"] for row in read_jsonl(ENTITIES_RAW_FILE)}
    todo = [p for p in papers if p["arxiv_id"] not in done][: args.limit]
    print(f"{len(done)} already extracted, {len(todo)} to go (model: {OLLAMA_MODEL})")

    ENTITIES_RAW_FILE.parent.mkdir(parents=True, exist_ok=True)
    failures = []
    started = time.monotonic()
    with httpx.Client(timeout=300) as http, ENTITIES_RAW_FILE.open("a", encoding="utf-8", newline="\n") as out:
        for i, paper in enumerate(todo, 1):
            try:
                row = {"arxiv_id": paper["arxiv_id"], "model": OLLAMA_MODEL, **extract(http, paper)}
            except (httpx.HTTPError, json.JSONDecodeError, KeyError) as exc:
                failures.append(paper["arxiv_id"])
                print(f"  [{i}/{len(todo)}] {paper['arxiv_id']} failed: {exc}")
                continue
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            out.flush()  # keep progress if the run is interrupted
            elapsed = time.monotonic() - started
            print(f"  [{i}/{len(todo)}] {paper['arxiv_id']} ({elapsed / i:.1f}s/paper) {paper['title'][:60]}")

    print(f"Done. {len(todo) - len(failures)} extracted, {len(failures)} failed")
    if failures:
        print(f"  re-run to retry: {failures}")


if __name__ == "__main__":
    main()
