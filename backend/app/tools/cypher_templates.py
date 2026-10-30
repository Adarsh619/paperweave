"""Hand-written Cypher for the questions PaperWeave answers most. All read-only.

Templates are trusted code, so they skip the text-to-Cypher guard, but they still
run through stores.read() (READ transaction + timeout) like everything else.
"""

# Exact name or alias match, case-insensitive. Aliases also match without their
# "(ABBR)" part, so "Dense Passage Retrieval" finds DPR via "Dense Passage Retrieval (DPR)".
# Order: the kind the caller wants ($prefer, e.g. Method for lineage), then exact name over
# alias, then methods > datasets > tasks, then the most mentioned.
RESOLVE_ENTITY = """
MATCH (n) WHERE (n:Method OR n:Dataset OR n:Task)
  AND (toLower(n.name) = toLower($name)
       OR any(a IN coalesce(n.aliases, []) WHERE toLower(a) = toLower($name)
              OR toLower(trim(split(a, '(')[0])) = toLower($name)))
RETURN labels(n)[0] AS label, n.name AS name, coalesce(n.aliases, []) AS aliases, coalesce(n.paper_mentions, 0) AS mentions
ORDER BY CASE WHEN labels(n)[0] = $prefer THEN 0 ELSE 1 END,
         CASE WHEN toLower(n.name) = toLower($name) THEN 0 ELSE 1 END,
         CASE labels(n)[0] WHEN 'Method' THEN 0 WHEN 'Dataset' THEN 1 ELSE 2 END, mentions DESC LIMIT 3
"""

# Fallback when nothing matches exactly: "graph rag" -> "GraphRAG-style ...".
RESOLVE_ENTITY_FUZZY = """
MATCH (n) WHERE (n:Method OR n:Dataset OR n:Task) AND toLower(n.name) CONTAINS toLower($name)
RETURN labels(n)[0] AS label, n.name AS name, coalesce(n.aliases, []) AS aliases, coalesce(n.paper_mentions, 0) AS mentions
ORDER BY CASE WHEN labels(n)[0] = $prefer THEN 0 ELSE 1 END, mentions DESC, size(n.name) LIMIT 3
"""

# A paper named in the question ("Attention Is All You Need"), via the fulltext index.
RESOLVE_PAPER = """
CALL db.index.fulltext.queryNodes('paper_text', $query) YIELD node, score
RETURN node.arxiv_id AS arxiv_id, node.title AS title, node.year AS year, score
ORDER BY score DESC LIMIT 1
"""

# Papers whose title contains a phrase (Lucene syntax, e.g. title:"Dense Passage Retrieval").
TITLE_MATCH = """
CALL db.index.fulltext.queryNodes('paper_text', $query) YIELD node, score
RETURN node.arxiv_id AS arxiv_id, node.title AS title, node.year AS year, score
ORDER BY score DESC LIMIT 3
"""

# Methods that improve on $name, who proposed them and where they were evaluated.
IMPROVED_BY = """
MATCH (new:Method)-[:IMPROVES_ON]->(:Method {name: $name})
MATCH (p:Paper)-[:PROPOSES]->(new)
OPTIONAL MATCH (p)-[:EVALUATES_ON]->(d:Dataset)
WITH new, p, collect(DISTINCT d.name) AS datasets
RETURN new.name AS method, p.arxiv_id AS arxiv_id, p.title AS title, p.year AS year, datasets
ORDER BY p.year DESC, p.citation_count DESC LIMIT 10
"""

# Influential papers that use $name as a building block (e.g. RAG and FiD use DPR).
USED_BY = """
MATCH (p:Paper)-[:USES]->(:Method {name: $name})
RETURN p.arxiv_id AS arxiv_id, p.title AS title, p.year AS year
ORDER BY p.citation_count DESC LIMIT 8
"""

# What $name itself improves on, and which paper introduced it.
METHOD_ORIGIN = """
MATCH (m:Method {name: $name})
OPTIONAL MATCH (p:Paper)-[:PROPOSES]->(m)
OPTIONAL MATCH (m)-[:IMPROVES_ON]->(base:Method)
RETURN collect(DISTINCT {arxiv_id: p.arxiv_id, title: p.title, year: p.year}) AS proposed_in,
       collect(DISTINCT base.name) AS improves_on
"""

# Everything needed for one row of a comparison table.
METHOD_PROFILE = """
MATCH (m:Method {name: $name})
OPTIONAL MATCH (p:Paper)-[:PROPOSES]->(m)
OPTIONAL MATCH (p)-[:EVALUATES_ON]->(d:Dataset)
OPTIONAL MATCH (p)-[:ADDRESSES]->(t:Task)
OPTIONAL MATCH (m)-[:IMPROVES_ON]->(base:Method)
OPTIONAL MATCH (succ:Method)-[:IMPROVES_ON]->(m)
OPTIONAL MATCH (u:Paper)-[:USES]->(m)
RETURN m.name AS method,
       collect(DISTINCT {arxiv_id: p.arxiv_id, title: p.title, year: p.year}) AS proposed_in,
       collect(DISTINCT d.name) AS datasets, collect(DISTINCT t.name) AS tasks,
       collect(DISTINCT base.name) AS improves_on, collect(DISTINCT succ.name) AS improved_by,
       count(DISTINCT u) AS used_by_papers
"""

DATASET_USERS = """
MATCH (:Dataset {name: $name})<-[:EVALUATES_ON]-(p:Paper)
OPTIONAL MATCH (p)-[:PROPOSES]->(m:Method)
WITH p, collect(DISTINCT m.name) AS methods
RETURN p.arxiv_id AS arxiv_id, p.title AS title, p.year AS year, methods
ORDER BY p.citation_count DESC LIMIT 20
"""

# Most cited inside the corpus, optionally since a year and/or linked to one entity.
TOP_CITED = """
MATCH (p:Paper)
WHERE ($min_year IS NULL OR p.year >= $min_year)
  AND ($entity IS NULL OR EXISTS {
        MATCH (p)-[:PROPOSES|USES|EVALUATES_ON|ADDRESSES]->(e) WHERE e.name = $entity })
OPTIONAL MATCH (p)<-[:CITES]-(c:Paper)
WITH p, count(c) AS in_corpus
RETURN p.arxiv_id AS arxiv_id, p.title AS title, p.year AS year,
       in_corpus, p.citation_count AS total_citations
ORDER BY in_corpus DESC, total_citations DESC LIMIT 10
"""

# Influential corpus papers that cite (build on) a given paper.
CITED_BY = """
MATCH (:Paper {arxiv_id: $arxiv_id})<-[:CITES]-(p:Paper)
RETURN p.arxiv_id AS arxiv_id, p.title AS title, p.year AS year, p.citation_count AS total_citations
ORDER BY total_citations DESC LIMIT 15
"""

PAPER_DETAILS = """
MATCH (p:Paper) WHERE p.arxiv_id IN $ids
RETURN p.arxiv_id AS arxiv_id, p.title AS title, p.year AS year, p.abstract AS abstract,
       p.abs_url AS abs_url, p.citation_count AS citation_count
"""

# Subgraph for the UI: papers, their entities, and links among them.
SUBGRAPH_ENTITIES = """
MATCH (p:Paper)-[r:PROPOSES|EVALUATES_ON]->(e) WHERE p.arxiv_id IN $ids
RETURN p.arxiv_id AS paper, type(r) AS rel, labels(e)[0] AS label, e.name AS name
"""
SUBGRAPH_CITES = """
MATCH (a:Paper)-[:CITES]->(b:Paper) WHERE a.arxiv_id IN $ids AND b.arxiv_id IN $ids
RETURN a.arxiv_id AS source, b.arxiv_id AS target
"""
SUBGRAPH_IMPROVES = """
MATCH (a:Method)-[:IMPROVES_ON]->(b:Method) WHERE a.name IN $names AND b.name IN $names
RETURN a.name AS source, b.name AS target
"""
