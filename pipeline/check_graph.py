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
}

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

        lineage = records(RAG_LINEAGE)
        verdict = f"yes, {lineage[0]['hops']} hop(s)" if lineage else "NOT FOUND"
        print(f"\nGraphRAG -> RAG lineage path: {verdict}")


if __name__ == "__main__":
    main()
