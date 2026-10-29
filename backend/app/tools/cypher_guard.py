"""Read-only guard for LLM-written Cypher.

First line of defense; the second is stores.read(), which runs every query in a
READ transaction so Neo4j itself refuses writes. The guard rejects anything that
isn't a single plain read query and caps the result size.
"""

import re

MAX_LIMIT = 100
DEFAULT_LIMIT = 50

# Clauses that write, change schema, run procedures or reach outside the graph.
FORBIDDEN = re.compile(
    r"\b(CREATE|MERGE|DELETE|DETACH|SET|REMOVE|DROP|FOREACH|CALL|LOAD|USE|ALTER|GRANT|DENY|REVOKE"
    r"|START|STOP|TERMINATE|SHOW|IMPORT|FINISH)\b",
    re.IGNORECASE,
)
ALLOWED_START = re.compile(r"^(MATCH|OPTIONAL\s+MATCH|WITH|UNWIND|RETURN)\b", re.IGNORECASE)
TRAILING_LIMIT = re.compile(r"\bLIMIT\s+(\d+)\s*$", re.IGNORECASE)


class CypherRejected(ValueError):
    pass


def _strip_literals(query: str) -> str:
    """Remove comments, strings and `quoted names` so keywords inside them don't count."""
    query = re.sub(r"//[^\n]*|/\*.*?\*/", " ", query, flags=re.DOTALL)
    return re.sub(r"'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"|`[^`]*`", "''", query)


def check(query: str) -> str:
    """Return a safe version of the query (with a LIMIT) or raise CypherRejected."""
    query = query.strip().rstrip(";").strip()
    if not query:
        raise CypherRejected("empty query")
    bare = _strip_literals(query)
    if ";" in bare:
        raise CypherRejected("only one statement is allowed")
    if not ALLOWED_START.match(bare.lstrip()):
        raise CypherRejected("query must start with MATCH, OPTIONAL MATCH, WITH, UNWIND or RETURN")
    if found := FORBIDDEN.search(bare):
        raise CypherRejected(f"'{found.group(1).upper()}' is not allowed (read-only)")
    if not re.search(r"\bRETURN\b", bare, re.IGNORECASE):
        raise CypherRejected("query must RETURN something")

    if limit := TRAILING_LIMIT.search(query):
        if int(limit.group(1)) > MAX_LIMIT:
            query = query[: limit.start()] + f"LIMIT {MAX_LIMIT}"
    else:
        query = f"{query}\nLIMIT {DEFAULT_LIMIT}"
    return query
