"""Knowledge-graph tools. Each returns facts as text lines that cite papers as [arxiv_id],
plus the arxiv_ids it touched, so the answer step can cite them."""

import json
import re
from dataclasses import dataclass, field

from app import stores
from app.tools import cypher_templates as T
from app.tools.cypher_guard import check


@dataclass
class GraphResult:
    facts: list[str] = field(default_factory=list)
    paper_ids: list[str] = field(default_factory=list)

    def add(self, fact: str, *ids: str | None) -> None:
        self.facts.append(fact)
        self.paper_ids.extend(i for i in ids if i and i not in self.paper_ids)


def resolve_entity(name: str, prefer: str | None = None) -> dict | None:
    """Map a name from the question to a graph entity: exact/alias match, then substring.
    prefer ("Method", "Dataset", "Task") breaks ambiguity: "Retrieval-Augmented Generation"
    is both a task and an alias of the RAG method."""
    rows = (stores.read(T.RESOLVE_ENTITY, name=name, prefer=prefer)
            or stores.read(T.RESOLVE_ENTITY_FUZZY, name=name, prefer=prefer))
    return rows[0] if rows else None


def resolve_paper(title: str) -> dict | None:
    # Escape Lucene syntax so titles with ':' or '?' don't break the fulltext query.
    query = re.sub(r'([+\-&|!(){}\[\]^"~*?:\\/])', r"\\\1", title)
    rows = stores.read(T.RESOLVE_PAPER, query=query)
    return rows[0] if rows and rows[0]["score"] > 1.0 else None


def _paper(row: dict) -> str:
    return f"{row['title']} ({row['year']}) [{row['arxiv_id']}]"


def _lucene_phrase(text: str) -> str:
    return '"' + re.sub(r'(["\\])', r"\\\1", text) + '"'


def _title_match(entity: dict) -> list[dict]:
    """Find a method's defining paper by its name in paper titles, when extraction didn't
    link it (the DPR paper's abstract says "dense retriever", never "DPR"). The earliest
    matching paper wins: the original comes before follow-ups that reuse the name."""
    names = {entity["name"], *(re.sub(r"\s*\([^)]*\)", "", a) for a in entity.get("aliases", []))}
    hits: dict[str, dict] = {}
    for name in sorted(n for n in names if len(n) >= 3)[:6]:
        for row in stores.read(T.TITLE_MATCH, query=f"title:{_lucene_phrase(name)}"):
            hits.setdefault(row["arxiv_id"], row)
    return sorted(hits.values(), key=lambda p: (p["year"] or 9999, -p["score"]))[:1]


def _origin(proposed_in: list[dict], entity: dict | None = None) -> list[dict]:
    """The earliest proposing paper. Extraction sometimes marks later papers that only
    apply a method (e.g. RAG) as proposing it; the first one is the real origin.
    With no proposing paper in the graph, fall back to a title match."""
    papers = sorted((p for p in proposed_in if p["arxiv_id"]), key=lambda p: p["year"] or 9999)
    if not papers and entity:
        return _title_match(entity)
    return papers[:1]


def lineage(name: str) -> GraphResult:
    """What improved on a method; for a paper title, which corpus papers build on (cite) it."""
    out = GraphResult()
    entity = resolve_entity(name, prefer="Method")
    if entity and entity["label"] == "Method":
        method = entity["name"]
        origin = stores.read(T.METHOD_ORIGIN, name=method)[0]
        for p in _origin(origin["proposed_in"], entity):
            out.add(f"{method} was proposed in {_paper(p)}.", p["arxiv_id"])
        if origin["improves_on"]:
            out.add(f"{method} improves on: {', '.join(origin['improves_on'])}.")
        rows = stores.read(T.IMPROVED_BY, name=method)
        for r in rows:
            datasets = f"; evaluated on {', '.join(r['datasets'])}" if r["datasets"] else ""
            out.add(f"{r['method']} improves on {method}: proposed in {_paper(r)}{datasets}.", r["arxiv_id"])
        users = [u for u in stores.read(T.USED_BY, name=method) if u["arxiv_id"] not in out.paper_ids]
        for u in users[:6]:
            out.add(f"{_paper(u)} uses {method} as a building block.", u["arxiv_id"])
        if not rows and not users:
            out.add(f"No method in the graph is recorded as improving on {method}.")
        return out

    paper = resolve_paper(name)
    if paper:
        rows = stores.read(T.CITED_BY, arxiv_id=paper["arxiv_id"])
        out.add(f"{len(rows)} corpus papers cite {_paper(paper)}.", paper["arxiv_id"])
        for r in rows:
            out.add(f"{_paper(r)} cites it ({r['total_citations']} total citations).", r["arxiv_id"])
    return out


def compare(names: list[str]) -> GraphResult:
    out = GraphResult()
    for name in names:
        entity = resolve_entity(name, prefer="Method")
        if not entity or entity["label"] != "Method":
            out.add(f"'{name}' is not a method in the graph.")
            continue
        p = stores.read(T.METHOD_PROFILE, name=entity["name"])[0]
        papers = _origin(p["proposed_in"], entity)
        parts = [f"{p['method']}:"]
        if papers:
            parts.append("proposed in " + ", ".join(_paper(x) for x in papers) + ";")
        for label, key in [("improves on", "improves_on"), ("improved on by", "improved_by"),
                           ("evaluated on", "datasets"), ("tasks", "tasks")]:
            if p[key]:
                parts.append(f"{label}: {', '.join(p[key][:8])};")
        parts.append(f"used by {p['used_by_papers']} other corpus papers.")
        out.add(" ".join(parts), *(x["arxiv_id"] for x in papers))
    return out


def dataset_users(name: str) -> GraphResult:
    out = GraphResult()
    entity = resolve_entity(name, prefer="Dataset")
    if not entity or entity["label"] != "Dataset":
        return out
    rows = stores.read(T.DATASET_USERS, name=entity["name"])
    out.add(f"{len(rows)} papers in the graph evaluate on {entity['name']} (most cited first):")
    for r in rows:
        methods = f", proposing {', '.join(r['methods'][:3])}" if r["methods"] else ""
        out.add(f"- {_paper(r)}{methods}", r["arxiv_id"])
    return out


def top_cited(min_year: int | None = None, topic: str | None = None) -> GraphResult:
    out = GraphResult()
    entity = resolve_entity(topic) if topic else None
    rows = stores.read(T.TOP_CITED, min_year=min_year, entity=entity["name"] if entity else None)
    scope = f" linked to {entity['name']}" if entity else ""
    since = f" since {min_year}" if min_year else ""
    out.add(f"Most cited papers within the corpus{scope}{since}:")
    for r in rows:
        out.add(f"- {_paper(r)}: cited by {r['in_corpus']} corpus papers, {r['total_citations']} overall",
                r["arxiv_id"])
    return out


SCHEMA_FOR_LLM = """Nodes: (:Paper {arxiv_id, title, abstract, year, venue, citation_count}),
(:Author {name}), (:Method {name, aliases}), (:Dataset {name, aliases}), (:Task {name})
Relationships: (Author)-[:WROTE {position}]->(Paper), (Paper)-[:CITES]->(Paper),
(Paper)-[:PROPOSES]->(Method), (Paper)-[:USES]->(Method), (Paper)-[:EVALUATES_ON]->(Dataset),
(Paper)-[:ADDRESSES]->(Task), (Method)-[:IMPROVES_ON {papers}]->(Method)"""


def run_llm_cypher(cypher: str) -> GraphResult:
    """Run LLM-written Cypher after the read-only guard; rows become JSON fact lines."""
    out = GraphResult()
    rows = stores.read(check(cypher))
    out.add(f"Graph query returned {len(rows)} rows:")
    for row in rows[:25]:
        ids = [v for v in row.values() if isinstance(v, str) and re.fullmatch(r"\d{4}\.\d{4,5}", v)]
        out.add("- " + json.dumps(row, default=str)[:300], *ids)
    return out
