"""Print sanity checks for the Neo4j graph: counts, orphans and known lineage.

    python pipeline/check_graph.py
"""

from neo4j import GraphDatabase

from config import NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER

CHECKS = {
    "papers": "MATCH (p:Paper) RETURN count(p) AS n",
    "authors": "MATCH (a:Author) RETURN count(a) AS n",
    "WROTE edges": "MATCH ()-[r:WROTE]->() RETURN count(r) AS n",
    "CITES edges": "MATCH ()-[r:CITES]->() RETURN count(r) AS n",
    "papers with no citation links": "MATCH (p:Paper) WHERE NOT (p)-[:CITES]-() RETURN count(p) AS n",
    "papers missing citation stats": "MATCH (p:Paper) WHERE p.citation_count IS NULL RETURN count(p) AS n",
    "methods": "MATCH (m:Method) RETURN count(m) AS n",
    "datasets": "MATCH (d:Dataset) RETURN count(d) AS n",
    "tasks": "MATCH (t:Task) RETURN count(t) AS n",
    "PROPOSES edges": "MATCH ()-[r:PROPOSES]->() RETURN count(r) AS n",
    "USES edges": "MATCH ()-[r:USES]->() RETURN count(r) AS n",
    "IMPROVES_ON edges": "MATCH ()-[r:IMPROVES_ON]->() RETURN count(r) AS n",
    "EVALUATES_ON edges": "MATCH ()-[r:EVALUATES_ON]->() RETURN count(r) AS n",
    "ADDRESSES edges": "MATCH ()-[r:ADDRESSES]->() RETURN count(r) AS n",
    "orphan entities (no links)": (
        "MATCH (n) WHERE (n:Method OR n:Dataset OR n:Task) AND NOT (n)--() RETURN count(n) AS n"
    ),
    "papers with no entities": (
        "MATCH (p:Paper) WHERE NOT (p)-[:PROPOSES|USES|EVALUATES_ON|ADDRESSES]->() RETURN count(p) AS n"
    ),
}

TOP_ENTITIES = """
MATCH (n:{label})<-[r]-(:Paper)
RETURN n.name AS name, count(r) AS papers
ORDER BY papers DESC, name LIMIT 5
"""

LINEAGE_SAMPLE = """
MATCH (new:Method)-[r:IMPROVES_ON]->(old:Method)
RETURN new.name AS new, old.name AS old, size(r.papers) AS papers
ORDER BY papers DESC, new LIMIT 8
"""

TOP_CITED_IN_CORPUS = """
MATCH (p:Paper)<-[:CITES]-(citing)
RETURN p.title AS title, p.year AS year, count(citing) AS in_corpus_citations
ORDER BY in_corpus_citations DESC LIMIT 5
"""

# Known fact: GraphRAG (2404.16130) builds on the original RAG paper (2005.11401).
RAG_LINEAGE = """
MATCH path = (g:Paper {arxiv_id: '2404.16130'})-[:CITES*1..2]->(r:Paper {arxiv_id: '2005.11401'})
RETURN length(path) AS hops LIMIT 1
"""


def main() -> None:
    with GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD)) as driver:
        records = lambda q: driver.execute_query(q).records  # noqa: E731
        for label, query in CHECKS.items():
            print(f"{label:32} {records(query)[0]['n']}")

        print("\nMost cited within the corpus:")
        for r in records(TOP_CITED_IN_CORPUS):
            print(f"  {r['in_corpus_citations']:3}  {r['title']} ({r['year']})")

        for label in ("Method", "Dataset", "Task"):
            top = records(TOP_ENTITIES.format(label=label))
            print(f"\nTop {label.lower()}s by papers: " + ", ".join(f"{r['name']} ({r['papers']})" for r in top))

        print("\nMethod lineage (IMPROVES_ON):")
        for r in records(LINEAGE_SAMPLE):
            print(f"  {r['new']} -> {r['old']}")

        lineage = records(RAG_LINEAGE)
        verdict = f"yes, {lineage[0]['hops']} hop(s)" if lineage else "NOT FOUND"
        print(f"\nGraphRAG -> RAG lineage path: {verdict}")


if __name__ == "__main__":
    main()
