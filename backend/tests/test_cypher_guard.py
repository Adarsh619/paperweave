import pytest

from app.tools.cypher_guard import CypherRejected, check


def test_read_query_passes_and_gets_a_limit():
    q = check("MATCH (p:Paper) RETURN p.title")
    assert q.endswith("LIMIT 50")


def test_existing_small_limit_is_kept_and_large_one_clamped():
    assert check("MATCH (p:Paper) RETURN p LIMIT 10").endswith("LIMIT 10")
    assert check("MATCH (p:Paper) RETURN p LIMIT 100000").endswith("LIMIT 100")


def test_trailing_semicolon_is_tolerated():
    assert "LIMIT" in check("MATCH (p:Paper) RETURN p;")


@pytest.mark.parametrize("query", [
    "MATCH (p:Paper) DETACH DELETE p",
    "CREATE (:Paper {arxiv_id: 'x'})",
    "MERGE (a:Author {name: 'x'}) RETURN a",
    "MATCH (p:Paper) SET p.title = 'x' RETURN p",
    "MATCH (p:Paper) REMOVE p.title RETURN p",
    "CALL db.labels()",
    "MATCH (p) CALL { WITH p DETACH DELETE p } RETURN 1",
    "LOAD CSV FROM 'http://evil.example/x.csv' AS row RETURN row",
    "MATCH (p) FOREACH (x IN [1] | SET p.a = x) RETURN p",
    "DROP INDEX paper_year",
    "SHOW USERS",
])
def test_writes_procedures_and_admin_are_rejected(query):
    with pytest.raises(CypherRejected):
        check(query)


def test_multiple_statements_are_rejected():
    with pytest.raises(CypherRejected):
        check("MATCH (p) RETURN p; MATCH (q) DETACH DELETE q")


def test_must_start_with_a_read_clause_and_return():
    with pytest.raises(CypherRejected):
        check("UNWIND [1,2] AS x WITH x WHERE x > 1")
    with pytest.raises(CypherRejected):
        check("PROFILE MATCH (p) RETURN p")


def test_keywords_inside_strings_are_not_false_positives():
    assert check("MATCH (m:Method) WHERE m.name = 'SET-based CREATE' RETURN m")


def test_keywords_in_comments_do_not_hide_writes():
    with pytest.raises(CypherRejected):
        check("MATCH (p) // harmless\nDETACH DELETE p")
