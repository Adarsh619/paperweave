"""Load papers, authors and citations from data/*.jsonl into Neo4j.

Idempotent: every write is a MERGE, so re-running updates rather than duplicates.
Works against local docker-compose Neo4j or AuraDB (set NEO4J_* in .env).

    python pipeline/load_neo4j.py
"""

from pathlib import Path

from neo4j import GraphDatabase

from config import CITATIONS_FILE, NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER, PAPERS_FILE
from jsonl import read_jsonl

SCHEMA_FILE = Path(__file__).with_name("schema.cypher")
BATCH_SIZE = 500

UPSERT_PAPERS = """
UNWIND $rows AS row
MERGE (p:Paper {arxiv_id: row.arxiv_id})
SET p.title = row.title,
    p.abstract = row.abstract,
    p.s2_id = row.s2_id,
    p.year = row.year,
    p.published = CASE WHEN row.published IS NULL THEN null ELSE date(row.published) END,
    p.venue = row.venue,
    p.citation_count = row.citation_count,
    p.influential_citation_count = row.influential_citation_count,
    p.abs_url = row.abs_url,
    p.pdf_url = row.pdf_url,
    p.source = row.source
WITH p, row
UNWIND range(0, size(row.authors) - 1) AS i
MERGE (a:Author {name: row.authors[i]})
MERGE (a)-[w:WROTE]->(p)
SET w.position = i
"""

UPSERT_CITATIONS = """
UNWIND $rows AS row
MATCH (src:Paper {arxiv_id: row.source})
MATCH (dst:Paper {arxiv_id: row.target})
MERGE (src)-[:CITES]->(dst)
"""


def _statements(cypher: str) -> list[str]:
    lines = [line for line in cypher.splitlines() if not line.strip().startswith("//")]
    return [s.strip() for s in "\n".join(lines).split(";") if s.strip()]


def _write_batches(session, query: str, rows: list[dict]) -> None:
    for i in range(0, len(rows), BATCH_SIZE):
        session.execute_write(lambda tx, batch: tx.run(query, rows=batch).consume(), rows[i : i + BATCH_SIZE])


def main() -> None:
    papers = read_jsonl(PAPERS_FILE)
    if not papers:
        raise SystemExit(f"No papers found in {PAPERS_FILE}; run fetch_papers.py first")
    citations = read_jsonl(CITATIONS_FILE)

    with GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD)) as driver:
        driver.verify_connectivity()
        with driver.session() as session:
            for statement in _statements(SCHEMA_FILE.read_text(encoding="utf-8")):
                session.run(statement).consume()
            print("Schema applied")

            _write_batches(session, UPSERT_PAPERS, papers)
            print(f"Upserted {len(papers)} papers with authors")
            _write_batches(session, UPSERT_CITATIONS, citations)
            print(f"Upserted {len(citations)} citation edges")


if __name__ == "__main__":
    main()
