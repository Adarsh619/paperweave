"""Clean and merge entity names from data/entities_raw.jsonl.

LLMs name the same thing many ways ("RAG", "Retrieval-Augmented Generation",
"retrieval augmented generation (RAG)"). Left alone, each spelling would become
its own graph node. This step:

  1. cleans whitespace/quotes and drops generic or citation-style names
  2. compares names by a loose key (lowercase, letters and digits only),
     so "Hotpot QA" == "HotpotQA" == "hotpot-qa"
  3. splits "Long Name (ABBR)" so both forms point to one entity
  4. applies a small hand-written alias list for well-known names
  5. picks one display name per entity

Writes:
  data/entities.jsonl      per-paper canonical names (what load_neo4j.py reads)
  data/entity_index.jsonl  one row per entity: kind, name, aliases, paper count

    python pipeline/normalize.py
"""

import re
from collections import Counter, defaultdict

from config import ENTITIES_FILE, ENTITIES_RAW_FILE, ENTITY_INDEX_FILE, PAPERS_FILE
from jsonl import read_jsonl, write_jsonl

# Which raw fields share a namespace: a name in improves_on is a Method too.
FIELD_KIND = {
    "methods_proposed": "Method",
    "methods_used": "Method",
    "improves_on": "Method",
    "datasets": "Dataset",
    "tasks": "Task",
}

# Canonical display name -> other spellings. Only needed where the loose key
# doesn't already merge them (case, spaces and hyphens are handled by the key).
ALIASES = {
    "Method": {
        "RAG": ["Retrieval-Augmented Generation", "RAG models", "RAG model"],
        "Transformer": ["Transformers", "Transformer architecture", "Transformer model"],
        "Chain-of-Thought": ["CoT", "chain of thought prompting", "CoT prompting"],
        "In-Context Learning": ["ICL"],
        "DPR": ["Dense Passage Retrieval", "Dense Passage Retriever"],
        "Fusion-in-Decoder": ["FiD"],
        "LoRA": ["Low-Rank Adaptation"],
        "RLHF": ["Reinforcement Learning from Human Feedback"],
        "GPT-3": ["GPT3"],
        "GraphRAG": ["Graph RAG"],
        "BM25": ["Lucene-BM25", "Okapi BM25"],
    },
    "Dataset": {
        "Natural Questions": ["NQ"],
        "WebQuestions": ["WebQ"],
    },
    "Task": {},
}

# Loose keys of names too generic to be useful graph nodes.
GENERIC = {
    "llm", "llms", "largelanguagemodel", "largelanguagemodels", "languagemodel", "languagemodels",
    "pretrainedlanguagemodels", "plms", "baseline", "baselines", "stateoftheart", "sota",
    "stateoftheartmethods", "stateoftheartmodels", "existingmethods", "existingmodels",
    "existingbestresults", "previousmethods", "priorwork", "priormethods", "ensembles",
    "deeplearning", "neuralnetworks", "neuralnetwork", "machinelearning", "otherdatasets",
    "variousbenchmarks", "benchmarks", "datasets",
    # A concept every KG paper mentions, not a method; as a node it would link everything.
    "kg", "kgs", "knowledgegraph", "knowledgegraphs",
}

ABBREV_RE = re.compile(r"^(?P<long>.+?)\s*\((?P<short>[^()]{1,20})\)$")
CITATION_RE = re.compile(r"\bet al\b|\b(19|20)\d\d[a-z]?\b")
# Vague descriptions rather than names: "two recent passage search datasets",
# "non-BERT baselines", "several existing methods".
VAGUE_RE = re.compile(
    r"^(\d|(a|an|the|two|three|four|several|various|many|multiple|recent|existing|other|previous|prior)\b)"
    r"|\b(baselines?|datasets|benchmarks|methods|approaches|models|techniques|architectures|systems"
    r"|records?|results)$",
    re.IGNORECASE,
)
# Model size and anything after it: "GPT-3 175B fine-tuned with Adam" -> "GPT-3".
MODEL_SIZE_RE = re.compile(r"\s+\d+(\.\d+)?\s?[BbMm]\b.*$")


def key(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


# Per kind: loose key of every alias (and canonical name) -> canonical name.
ALIAS_KEYS = {
    kind: {key(v): canon for canon, variants in table.items() for v in [canon, *variants]}
    for kind, table in ALIASES.items()
}


def clean(name: str, kind: str | None = None) -> str:
    """Tidy whitespace/punctuation; known aliases become their canonical name."""
    name = re.sub(r"\s+", " ", name).strip().strip("\"'`.,;:")
    if kind == "Method":
        name = MODEL_SIZE_RE.sub("", name)
    return ALIAS_KEYS.get(kind, {}).get(key(name), name) if kind else name


def usable(name: str) -> bool:
    k = key(name)
    return (
        len(k) >= 2
        and k not in GENERIC
        and not CITATION_RE.search(name)
        and not VAGUE_RE.search(name)
        and len(name.split()) <= 8
    )


class UnionFind:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def find(self, x: str) -> str:
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: str, b: str) -> None:
        self.parent[self.find(a)] = self.find(b)


def forms(name: str) -> list[str]:
    """A raw name, or its two parts if written as 'Long Name (ABBR)'.

    The combined string is never used itself, so a generic pair such as
    "large language models (LLMs)" is dropped when both parts are generic.
    A parenthetical that can't be an abbreviation (different first letter, as in
    "MS MARCO (V1)") is a qualifier and is dropped.
    """
    match = ABBREV_RE.match(name)
    if not match:
        return [name]
    long, short = match["long"], match["short"]
    return [long, short] if long[0].lower() == short[0].lower() else [long]


def build_groups(rows: list[dict]) -> dict[str, dict]:
    """Per kind: merge spellings and choose a display name for each entity."""
    groups: dict[str, dict] = {}
    for kind in ("Method", "Dataset", "Task"):
        uf = UnionFind()
        surface = Counter()  # how often each cleaned spelling appears
        abbreviations = set()  # keys that appeared as the ABBR in "Long (ABBR)"
        canonical_keys = {key(c): c for c in ALIASES[kind]}
        spellings: dict[str, set[str]] = defaultdict(set)  # name -> raw spellings seen

        for row in rows:
            for field, field_kind in FIELD_KIND.items():
                if field_kind != kind:
                    continue
                for raw in row.get(field, []):
                    name = clean(raw, kind)
                    parts = [p for p in (clean(f, kind) for f in forms(name)) if usable(p)]
                    if not parts:
                        continue
                    if ABBREV_RE.match(name) and len(parts) == 2:
                        abbreviations.add(key(parts[1]))
                    spellings[parts[0]].add(clean(raw))
                    for p in parts:
                        surface[p] += 1
                        uf.union(key(p), key(parts[0]))

        members: dict[str, list[str]] = defaultdict(list)
        for name in surface:
            members[uf.find(key(name))].append(name)

        lookup: dict[str, str] = {}
        index: dict[str, dict] = {}
        for names in members.values():
            keys = {key(n) for n in names}
            if keys & canonical_keys.keys():
                display = canonical_keys[next(iter(keys & canonical_keys.keys()))]
            elif keys & abbreviations:
                abbr_names = [n for n in names if key(n) in abbreviations]
                display = max(abbr_names, key=lambda n: (surface[n], -len(n)))
            else:
                display = max(names, key=lambda n: (surface[n], -len(n)))
            for n in names:
                lookup[key(n)] = display
            seen = set(names).union(*(spellings[n] for n in names))
            index[display] = {"kind": kind, "name": display, "aliases": sorted(seen - {display})}
        groups[kind] = {"lookup": lookup, "index": index}
    return groups


def canonical(groups: dict, kind: str, raw: str) -> str | None:
    name = clean(raw, kind)
    for part in reversed(forms(name)):  # prefer the ABBR, then the long form
        hit = groups[kind]["lookup"].get(key(clean(part, kind)))
        if hit:
            return hit
    return None


def main() -> None:
    raw_rows = read_jsonl(ENTITIES_RAW_FILE)
    if not raw_rows:
        raise SystemExit(f"No rows in {ENTITIES_RAW_FILE}; run extract_entities.py first")
    # Extraction is append-only, so it may hold papers since dropped from the corpus.
    corpus = {p["arxiv_id"] for p in read_jsonl(PAPERS_FILE)}
    raw_rows = [r for r in raw_rows if r["arxiv_id"] in corpus]

    groups = build_groups(raw_rows)
    paper_counts: Counter = Counter()
    out_rows = []
    for row in raw_rows:
        clean_row = {"arxiv_id": row["arxiv_id"]}
        for field, kind in FIELD_KIND.items():
            names = []
            for raw in row.get(field, []):
                name = canonical(groups, kind, raw)
                if name and name not in names:
                    names.append(name)
            clean_row[field] = names
        # A method can't be both new and existing in one paper, or improve on itself.
        proposed = set(clean_row["methods_proposed"])
        clean_row["methods_used"] = [m for m in clean_row["methods_used"] if m not in proposed]
        # IMPROVES_ON links new methods to old ones, so it needs a proposed method.
        clean_row["improves_on"] = [m for m in clean_row["improves_on"] if m not in proposed] if proposed else []
        for field, kind in FIELD_KIND.items():
            for name in clean_row[field]:
                paper_counts[(kind, name)] += 1
        out_rows.append(clean_row)

    index_rows = []
    for kind in ("Method", "Dataset", "Task"):
        for entity in groups[kind]["index"].values():
            count = paper_counts[(kind, entity["name"])]
            if count:  # skip names only seen in rows later filtered out
                index_rows.append({**entity, "paper_mentions": count})
    index_rows.sort(key=lambda e: (e["kind"], -e["paper_mentions"], e["name"].lower()))

    write_jsonl(ENTITIES_FILE, out_rows)
    write_jsonl(ENTITY_INDEX_FILE, index_rows)
    by_kind = Counter(e["kind"] for e in index_rows)
    merged = sum(len(e["aliases"]) for e in index_rows)
    print(f"Normalized {len(out_rows)} papers -> {ENTITIES_FILE.name}")
    print(f"Entities: {dict(by_kind)}; {merged} alternate spellings merged -> {ENTITY_INDEX_FILE.name}")


if __name__ == "__main__":
    main()
