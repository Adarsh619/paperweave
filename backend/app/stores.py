"""Shared Neo4j and Qdrant clients, created once per process."""

from functools import lru_cache

from neo4j import READ_ACCESS, Driver, GraphDatabase, unit_of_work
from qdrant_client import QdrantClient

from app import config


@lru_cache
def neo4j() -> Driver:
    return GraphDatabase.driver(config.NEO4J_URI, auth=(config.NEO4J_USER, config.NEO4J_PASSWORD))


@lru_cache
def qdrant() -> QdrantClient:
    return QdrantClient(
        url=config.QDRANT_URL,
        api_key=config.QDRANT_API_KEY,
        cloud_inference=config.QDRANT_CLOUD_INFERENCE,
        timeout=30,
    )


@unit_of_work(timeout=10)
def _run(tx, query: str, params: dict) -> list[dict]:
    return tx.run(query, params).data()


def read(cypher: str, **params) -> list[dict]:
    """Run Cypher in a READ transaction: Neo4j itself rejects any write, and a 10 s timeout
    stops runaway queries. Every query in the app goes through here."""
    with neo4j().session(default_access_mode=READ_ACCESS) as session:
        return session.execute_read(_run, cypher, params)


def close() -> None:
    if neo4j.cache_info().currsize:
        neo4j().close()
    if qdrant.cache_info().currsize:
        qdrant().close()
