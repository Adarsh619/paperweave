"""Paper cards and per-paper graphs for the UI."""

from fastapi import APIRouter, HTTPException, Path

from app import stores

router = APIRouter()
ArxivId = Path(pattern=r"^\d{4}\.\d{4,5}$", description="versionless arXiv ID, e.g. 2005.11401")

PAPER_CARD = """
MATCH (p:Paper {arxiv_id: $id})
OPTIONAL MATCH (a:Author)-[w:WROTE]->(p)
WITH p, a ORDER BY w.position
WITH p, collect(a.name) AS authors
OPTIONAL MATCH (p)-[:PROPOSES]->(m:Method)
OPTIONAL MATCH (p)-[:EVALUATES_ON]->(d:Dataset)
OPTIONAL MATCH (p)-[:ADDRESSES]->(t:Task)
RETURN p {.arxiv_id, .title, .abstract, .year, .venue, .citation_count, .abs_url, .pdf_url} AS paper, authors,
       collect(DISTINCT m.name) AS proposes, collect(DISTINCT d.name) AS datasets, collect(DISTINCT t.name) AS tasks,
       COUNT { (p)-[:CITES]->(:Paper) } AS cites_in_corpus,
       COUNT { (p)<-[:CITES]-(:Paper) } AS cited_by_in_corpus
"""

PAPER_NEIGHBORHOOD = """
MATCH (p:Paper {arxiv_id: $id})
OPTIONAL MATCH (p)-[r:PROPOSES|USES|EVALUATES_ON|ADDRESSES]->(e)
WITH p, collect(DISTINCT {type: type(r), label: labels(e)[0], name: e.name}) AS entities
OPTIONAL MATCH (p)-[:CITES]->(out:Paper)
WITH p, entities, out ORDER BY out.citation_count DESC
WITH p, entities, collect(out {.arxiv_id, .title, .year})[..10] AS cites
OPTIONAL MATCH (p)<-[:CITES]-(inc:Paper)
WITH p, entities, cites, inc ORDER BY inc.citation_count DESC
RETURN p {.arxiv_id, .title, .year} AS paper, entities, cites,
       collect(inc {.arxiv_id, .title, .year})[..10] AS cited_by
"""


@router.get("/api/papers/{arxiv_id}")
def paper(arxiv_id: str = ArxivId):
    rows = stores.read(PAPER_CARD, id=arxiv_id)
    if not rows:
        raise HTTPException(404, f"Paper {arxiv_id} is not in the corpus")
    row = rows[0]
    return {**row["paper"], "authors": row["authors"], "proposes": row["proposes"], "datasets": row["datasets"],
            "tasks": row["tasks"], "cites_in_corpus": row["cites_in_corpus"],
            "cited_by_in_corpus": row["cited_by_in_corpus"]}


@router.get("/api/graph/paper/{arxiv_id}")
def paper_graph(arxiv_id: str = ArxivId):
    """The paper, its methods/datasets/tasks and its top 10 citing and cited papers, as nodes + links."""
    rows = stores.read(PAPER_NEIGHBORHOOD, id=arxiv_id)
    if not rows:
        raise HTTPException(404, f"Paper {arxiv_id} is not in the corpus")
    row = rows[0]
    center = f"paper:{arxiv_id}"
    nodes = {center: {"id": center, "type": "Paper", "label": row["paper"]["title"], "arxiv_id": arxiv_id,
                      "year": row["paper"]["year"]}}
    links = []
    for e in row["entities"]:
        if e["name"] is None:
            continue
        node_id = f"{e['label'].lower()}:{e['name']}"
        nodes.setdefault(node_id, {"id": node_id, "type": e["label"], "label": e["name"]})
        links.append({"source": center, "target": node_id, "type": e["type"]})
    for key, outgoing in (("cites", True), ("cited_by", False)):
        for p in row[key]:
            node_id = f"paper:{p['arxiv_id']}"
            nodes.setdefault(node_id, {"id": node_id, "type": "Paper", "label": p["title"],
                                       "arxiv_id": p["arxiv_id"], "year": p["year"]})
            src, dst = (center, node_id) if outgoing else (node_id, center)
            links.append({"source": src, "target": dst, "type": "CITES"})
    return {"nodes": list(nodes.values()), "links": links}
