"""Knowledge-graph tools. Each returns facts as text lines that cite papers as [arxiv_id],
plus the arxiv_ids it touched, so the answer step can cite them."""

import json
import re
from dataclasses import dataclass, field
from datetime import date

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
    rows = stores.read(T.RESOLVE_ENTITY, name=name, prefer=prefer)
    # People write "Corrective RAG"; abstracts write "Corrective Retrieval Augmented Generation".
    spelled = re.sub(r"\bRAG\b", "Retrieval Augmented Generation", name, flags=re.I)
    if not rows and spelled != name:
        rows = stores.read(T.RESOLVE_ENTITY, name=spelled, prefer=prefer)
    rows = rows or stores.read(T.RESOLVE_ENTITY_FUZZY, name=name, prefer=prefer)
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
    """The most cited proposing paper. Extraction sometimes marks papers that only apply a
    method (e.g. RAG) as proposing it, and unrelated papers reuse names (two "GraphRAG"s);
    the real origin is almost always the most cited. Ties go to the earliest.
    With no proposing paper in the graph, fall back to a title match."""
    papers = sorted((p for p in proposed_in if p["arxiv_id"]),
                    key=lambda p: (-(p.get("citations") or 0), p["year"] or 9999))
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
(:Author {name}), (:Method {name, aliases}), (:Dataset {name, aliases}), (:Task {name}),
(:Topic {name}), (:Field {name})
Relationships: (Author)-[:WROTE {position}]->(Paper), (Paper)-[:CITES]->(Paper),
(Paper)-[:PROPOSES]->(Method), (Paper)-[:USES]->(Method), (Paper)-[:EVALUATES_ON]->(Dataset),
(Paper)-[:ADDRESSES]->(Task), (Method)-[:IMPROVES_ON {papers}]->(Method),
(Paper)-[:IN_TOPIC]->(Topic), (Topic)-[:PART_OF]->(Field)"""


# --- Trends: what the data shows, never forecasts. ---

RECENT_YEARS = 3  # "recent" = this year and the 2 before; "earlier" = the 3 years before that
MIN_RECENT_PAPERS = 3  # a rising method must appear in at least this many recent papers


def growth(years: list[int], counts: list[int], this_year: int) -> float | None:
    """Change in yearly paper volume: last 2 complete years vs the 2 before (the current year
    is still filling up, so it's left out). None when there isn't enough history."""
    by_year = dict(zip(years, counts))
    recent = [by_year.get(this_year - 1), by_year.get(this_year - 2)]
    prior = [by_year.get(this_year - 3), by_year.get(this_year - 4)]
    if None in recent or None in prior or not sum(prior):
        return None
    return (sum(recent) - sum(prior)) / sum(prior)


def rising_methods(period_papers: dict[str, int], rows: list[dict], limit: int = 8) -> list[dict]:
    """Methods whose share of papers grew most from the earlier to the recent period."""
    counts: dict[str, dict[str, int]] = {}
    for r in rows:
        counts.setdefault(r["method"], {})[r["period"]] = r["papers"]
    recent_total, earlier_total = period_papers.get("recent", 0), period_papers.get("earlier", 0)
    if not recent_total or not earlier_total:
        return []
    out = []
    for method, c in counts.items():
        n_recent = c.get("recent", 0)
        if n_recent < MIN_RECENT_PAPERS:
            continue
        share_recent, share_earlier = n_recent / recent_total, c.get("earlier", 0) / earlier_total
        out.append({"method": method, "recent_papers": n_recent, "share_recent": share_recent,
                    "share_earlier": share_earlier, "change": share_recent - share_earlier})
    return sorted(out, key=lambda m: m["change"], reverse=True)[:limit]


def trends(field: str | None = None, topic: str | None = None, this_year: int | None = None) -> dict:
    this_year = this_year or date.today().year
    params = {"field": field, "topic": topic, "this_year": this_year,
              "recent_from": this_year - RECENT_YEARS + 1, "from_year": this_year - 2 * RECENT_YEARS + 1}
    topics = []
    for r in stores.read(T.TOPIC_VOLUME, field=field, topic=topic):
        g = growth(r["years"] or [], r["counts"] or [], this_year)
        topics.append({**r, "growth": g})
    topics.sort(key=lambda t: (t["growth"] is None, -(t["growth"] or 0)))
    period_papers = {r["period"]: r["papers"] for r in stores.read(T.PERIOD_PAPERS, **params)}
    return {
        "field": field,
        "topic": topic,
        "recent_years": [params["recent_from"], this_year],
        "earlier_years": [params["from_year"], params["recent_from"] - 1],
        "topics": topics,
        "rising_methods": rising_methods(period_papers, stores.read(T.PERIOD_METHODS, **params)),
        "breakout_papers": stores.read(T.BREAKOUT_PAPERS, **params),
    }


def resolve_scope(name: str | None) -> tuple[str | None, str | None]:
    """Map a name from the question to (field, topic): "physics" -> the Physics field."""
    if not name:
        return None, None
    key = name.lower()
    rows = stores.read(T.TOPIC_NAMES)
    # Exact names first, so "Physics" is the field, not "Machine learning for physics".
    for r in rows:
        if key == r["topic"].lower():
            return None, r["topic"]
        if key == r["field"].lower():
            return r["field"], None
    for r in rows:
        if key in r["topic"].lower() or r["topic"].lower() in key:
            return None, r["topic"]
    for r in rows:
        if key in r["field"].lower() or r["field"].lower() in key:
            return r["field"], None
    return None, None


def trend_facts(scope: str | None) -> GraphResult:
    """Trend data as citable facts for the agent's answer."""
    field, topic = resolve_scope(scope)
    data = trends(field, topic)
    out = GraphResult()
    where = topic or field or "the whole library"
    r0, r1 = data["recent_years"]
    e0, e1 = data["earlier_years"]
    for t in [t for t in data["topics"] if t["growth"] is not None][:6]:
        out.add(f"Field-wide papers on {t['topic']} changed by {t['growth']:+.0%} "
                f"(last 2 complete years vs the 2 before; Semantic Scholar counts).")
    for m in data["rising_methods"]:
        out.add(f"In {where}, {m['method']} appears in {m['share_recent']:.1%} of {r0}-{r1} papers "
                f"vs {m['share_earlier']:.1%} in {e0}-{e1}.")
    for p in data["breakout_papers"]:
        out.add(f"Breakout paper: {_paper(p)}, {p['citations']} citations (~{p['per_year']:.0f}/year).", p["arxiv_id"])
    if not out.facts:
        out.add(f"No trend data for {where} yet.")
    return out


def run_llm_cypher(cypher: str) -> GraphResult:
    """Run LLM-written Cypher after the read-only guard; rows become JSON fact lines."""
    out = GraphResult()
    rows = stores.read(check(cypher))
    out.add(f"Graph query returned {len(rows)} rows:")
    for row in rows[:25]:
        ids = [v for v in row.values() if isinstance(v, str) and re.fullmatch(r"\d{4}\.\d{4,5}", v)]
        out.add("- " + json.dumps(row, default=str)[:300], *ids)
    return out
